import argparse
import codecs
import ctypes
import os
import pytesseract
import re
import time
import tkinter as tk
import webbrowser
import win32clipboard
import win32print
import win32ui
from colorsys import rgb_to_hsv, rgb_to_hls
from functools import partial
from io import BytesIO
from math import sqrt, atan2, pi, sin, cos, dist
from tkinter import ttk, filedialog, font
from tkinter.scrolledtext import ScrolledText as sText
from PIL import ImageGrab, ImageTk, ImageEnhance, ImageFilter, Image, ImageDraw, ImageWin
from pynput import mouse
from pyzbar.pyzbar import decode
from shapely.geometry import LineString, Polygon


class Application(tk.Tk):
    """Основной класс приложения для создания и редактирования скриншотов.

    Attributes:
        canvas (tk.Canvas): Холст для отображения элементов интерфейса и изображений
        panel (ttk.Frame): Панель инструментов редактирования
        palette (list): Цветовая палитра для рисования
        image (PIL.Image): Текущий снимок экрана
    """
    class Hint:
        """Вспомогательный класс для отображения подсказок при наведении на элементы интерфейса.

        Args:
            widget (ttk.Widget): Виджет, для которого создается подсказка
            hint (list): Список текстовых подсказок для элементов виджета
        """
        def __init__(self, widget, hint):
            self.widget = widget
            self.hint = hint
            self.widget.bind('<Enter>', lambda e: self._schedule())
            self.widget.bind('<Leave>', lambda e: self.hide())
            self._id = None

        def _schedule(self):
            self._unschedule()
            self._id = self.widget.after(3000, self.show)

        def _unschedule(self):
            if self._id:
                self.widget.after_cancel(self._id)
            self._id = None

        def show(self):
            for w, text in zip(self.widget.winfo_children(), self.hint):
                if isinstance(w, ttk.Button):
                    x = w.winfo_rootx() + w.winfo_width() // 2
                    y = w.winfo_rooty() + w.winfo_height() - 0
                    tk.Label(master=self.widget.master, text=text,
                             background='lightyellow', relief='solid', borderwidth=1).place(x=x, y=y, anchor='n')

        def hide(self):
            self._unschedule()
            for w in self.widget.master.winfo_children():
                if isinstance(w, tk.Label):
                    w.destroy()

    class MakeDraggable:
        """Класс для реализации перетаскивания элементов интерфейса.

        Args:
            widget (ttk.Widget): Перетаскиваемый виджет
            on_start (function): Коллбэк при начале перетаскивания
        """
        def __init__(self, widget, on_start=None):
            self.widget = widget
            self.function_on_start = on_start
            self.widget.bind('<Button-1>', lambda e: self._drag_start(e))
            self.widget.bind('<B1-Motion>', lambda e: self._drag_motion(e))

        def _drag_start(self, event):
            if self.function_on_start:
                self.function_on_start()
            self.drag_start_x = event.x
            self.drag_start_y = event.y

        def _drag_motion(self, event):
            x = self.widget.winfo_x() - self.drag_start_x + event.x
            y = self.widget.winfo_y() - self.drag_start_y + event.y
            self.widget.place(x=x, y=y)

    def __init__(self):
        """Инициализирует полноэкранное окно, захватывает снимок экрана и настраивает обработчики событий."""
        tk.Tk.__init__(self)

        self.false_start = None
        self.attributes('-fullscreen', True)
        self.attributes('-topmost', True)

        self.canvas = tk.Canvas(self, cursor='cross', highlightthickness=0)
        self.canvas.pack(side='top', fill='both', expand=True)

        self.canvas.bind('<ButtonPress-1>', lambda e: self._create_editor(e))
        self.canvas.bind('<B1-Motion>', lambda e: self._set_viewport(e))
        self.canvas.bind('<ButtonRelease-1>', lambda e: self._start_editing())
        self.canvas.bind('<Button-3>', lambda e: [setattr(self, 'false_start', True), self.destroy()])

        self.x1 = self.y1 = None
        self.x2 = self.y2 = None

        self.screenshot_area_tk = None
        self.screenshot_area = None
        self.viewport = None
        self.border = None
        self.palette = ['red', 'orange', 'yellow', 'lime', 'cyan', 'blue', 'magenta', 'white', 'black']
        self.color = 0
        self.colorspace = 'hex'
        self.num = 1
        self.corner = {}
        self.image_stack = []
        self.txt = ''
        self.text_edit = False
        self.cursor_visible = False
        self.is_blinking = None
        self.font_size = 18
        self.ruler_scale = 1.0
        self.callback_button = None
        self.lock_viewport = False

        self.panel = ttk.Frame(self.canvas)
        self.panel_hint = self.Hint(self.panel, ['F1', 'F2', 'F3', 'F4', 'F5', 'F6', 'F7', '', 'Ctrl+R', 'Ctrl+C'])
        self.arrow_button = ttk.Button(self.panel, text='Стрелка', command=lambda: self._set_arrow())
        self.pen_button = ttk.Button(self.panel, text='Карандаш', command=lambda: self._set_pen())
        self.line_button = ttk.Button(self.panel, text='Линия', command=lambda: self._set_line())
        self.rect_button = ttk.Button(self.panel, text='Рамка', command=lambda: self._set_rect())
        self.text_button = ttk.Button(self.panel, text='Надпись', command=lambda: self._set_text())
        self.num_button = ttk.Button(self.panel, text=self.num, command=lambda: self._set_number())
        self.blur_button = ttk.Button(self.panel, text='Размытие', command=lambda: self._set_blur())
        self.color_panel = ttk.Label(self.panel, width=3, background=self.palette[self.color])
        self.recognize_button = ttk.Button(self.panel, text='Распознать', command=lambda: self._recognize())
        done_txt = tk.StringVar(value='Ok')
        self.done_button = ttk.Button(self.panel, textvariable=done_txt, command=lambda: self._done())
        self.done_button.bind('<Button-3>', lambda e: [self.panel_hint.hide(), self.destroy()])

        self.bind('<F1>', lambda e: self._set_arrow())
        self.bind('<F2>', lambda e: self._set_pen())
        self.bind('<F3>', lambda e: self._set_line())
        self.bind('<F4>', lambda e: self._set_rect())
        self.bind('<F5>', lambda e: self._set_text())
        self.bind('<F6>', lambda e: self._set_number())
        self.bind('<F7>', lambda e: self._set_blur())
        self.bind('<Escape>', lambda e: self.destroy())
        self.bind('<Key>', lambda e: self._set_color(e.char) if e.char in '1234567890' else None)

        self.bind('<KeyPress-Shift_L>', lambda e: done_txt.set('Сохранить'))
        self.bind('<KeyRelease-Shift_L>', lambda e: done_txt.set('Ok'))
        self.bind('<KeyPress-Shift_R>', lambda e: done_txt.set('Сохранить'))
        self.bind('<KeyRelease-Shift_R>', lambda e: done_txt.set('Ok'))

        self.image = ImageGrab.grab(all_screens=True)
        self.blur_image = self.image.filter(ImageFilter.GaussianBlur(5))

        background = self.image.convert('L')
        background = ImageEnhance.Brightness(background).enhance(0.8)

        self.background = ImageTk.PhotoImage(background)
        self.canvas.create_image(0, 0, anchor='nw', image=self.background)

        self.focus_set()

    def _create_corner(self, position, x, y, cursor):
        """Создает маркер для изменения размера области редактирования.

        Args:
            position (str): Позиция маркера ('nw', 'n', 'ne' и т.д.)
            x (int): Координата X маркера
            y (int): Координата Y маркера
            cursor (str): Вид курсора при наведении
        """
        self.corner[position] = self.canvas.create_rectangle(x - 4, y - 4, x + 4, y + 4, width=2,
                                                             outline='lightgrey', fill='black',
                                                             tags=['service', 'corner'])
        self.canvas.tag_bind(self.corner[position], '<Enter>', lambda e: self.canvas.config(cursor=cursor))
        self.canvas.tag_bind(self.corner[position], '<Leave>', lambda e: self.canvas.config(cursor=''))
        self.canvas.tag_bind(self.corner[position], '<B1-Motion>', lambda e: self._change_viewport(position, e))
        self.canvas.tag_bind(self.corner[position], '<ButtonRelease-1>', lambda e: self._fix_viewport())

    def _move_corner(self, position, x, y):
        """Перемещает маркер изменения размера.

        Args:
            position (str): Позиция маркера
            x (int): Новая координата X
            y (int): Новая координата Y
        """
        self.canvas.moveto(self.corner[position], x - 5, y - 5)

    def _draw_borders(self, x1, y1, x2, y2):
        """Обновляет границы выделенной области и позиции маркеров.

        Args:
            x1, y1 (int): Координаты левого верхнего угла
            x2, y2 (int): Координаты правого нижнего угла
        """
        self.canvas.coords(self.border, (x1, y1, x2, y2))

        self._move_corner('nw', x1, y1)
        self._move_corner('n', (x2 + x1) // 2, y1)
        self._move_corner('ne', x2, y1)
        self._move_corner('e', x2, (y2 + y1) // 2)
        self._move_corner('se', x2, y2)
        self._move_corner('s', (x2 + x1) // 2, y2)
        self._move_corner('sw', x1, y2)
        self._move_corner('w', x1, (y2 + y1) // 2)

    def _control(self, event):
        """Обрабатывает комбинации клавиш для управления приложением.

        Args:
            event (tk.Event): Событие клавиатуры
        """
        # undo
        if event.state == 12 and event.keycode == 90:  # Ctrl+Z
            last_item = self.canvas.find_withtag('editor')[-1]
            if last_item != self.viewport:
                for tag in self.canvas.gettags(last_item):
                    if tag.startswith('_'):
                        last_item = tag
                self.canvas.delete(last_item)
        # save
        elif event.state in [12, 13] and event.keycode == 67:  # Ctrl+C || Ctrl+Shift+C
            self._done()
        elif event.state == 12 and event.keycode == 83:  # Ctrl+S
            self.canvas.delete('service')
            self.canvas.update()
            image = ImageGrab.grab(bbox=self.canvas.bbox(self.viewport))
            self.destroy()
            desktop_folder = os.path.join(os.environ['USERPROFILE'], 'Desktop')
            file_name = f'Снимок экрана {time.strftime('%d-%m-%Y %H%M%S')}'
            if file := filedialog.asksaveasfilename(defaultextension='.png',
                                                    filetypes=[('Portable Network Graphics', '*.png')],
                                                    initialdir=desktop_folder,
                                                    initialfile=file_name):
                image.save(file)
        # save color
        elif event.state == 131084 and event.keycode == 67:  # Ctrl+Alt+C
            hex_color = self.canvas.itemcget('z_33', 'fill')
            self.clipboard_clear()
            self.clipboard_append(self._get_color_by_space(hex_color, self.colorspace)[1])
            self.update()
        # recognize
        elif event.state == 12 and event.keycode == 82:  # Ctrl+R
            self._recognize()
        # print
        elif event.state == 12 and event.keycode == 80:  # Ctrl+P
            printer_name = win32print.GetDefaultPrinter()
            hdc = win32ui.CreateDC()
            hdc.CreatePrinterDC(printer_name)
            printer_info = {'PHYSICALWIDTH': hdc.GetDeviceCaps(110),
                            'PHYSICALHEIGHT': hdc.GetDeviceCaps(111)}

            try:
                hdc.StartDoc(f'Снимок экрана {time.strftime('%d-%m-%Y %H%M%S')}')
                hdc.StartPage()

                self.canvas.itemconfigure('service', state='hidden')
                self.canvas.update()
                bbox = self.canvas.bbox(self.viewport)
                image = ImageGrab.grab(bbox=bbox)
                with BytesIO() as output:
                    image.convert('RGB').save(output, 'BMP')

                image_w = bbox[2]-bbox[0]
                image_h = bbox[3]-bbox[1]
                scale_x = printer_info['PHYSICALWIDTH'] / image_w
                scale_y = printer_info['PHYSICALHEIGHT'] / image_h
                if scale_x < scale_y:
                    image_w = printer_info['PHYSICALWIDTH']
                    image_h = int(image_h * scale_x)
                else:
                    image_w = int(image_w * scale_y)
                    image_h = printer_info['PHYSICALHEIGHT']

                dib = ImageWin.Dib(image)
                dib.draw(hdc.GetHandleOutput(), (0, 0, image_w, image_h))

                hdc.EndPage()
                hdc.EndDoc()
                self.canvas.itemconfigure('service', state='normal')
                self.canvas.itemconfigure('precision', state='hidden')
                if self.lock_viewport:
                    self.canvas.itemconfigure('corner', state='hidden')
            except win32ui.error:
                pass
            hdc.DeleteDC()

    def _viewport_lock(self):
        """Блокировка изменения размеров окна редактора"""
        self.lock_viewport = not self.lock_viewport
        self.canvas.itemconfigure('corner', state='hidden' if self.lock_viewport else 'normal')
        self.canvas.tag_raise('corner')
        if self.text_edit:
            if self.lock_viewport:
                self.canvas.itemconfigure(self.text, width=self.canvas.bbox(self.viewport)[2] - self.coords[0] - 3)
            else:
                self.canvas.itemconfigure(self.text, width=self.winfo_width() - self.coords[0] - 3)
            self._redraw_text()

    def _create_editor(self, event):
        """Создает область редактирования на холсте.

            Args:
                event (tk.Event): Событие мыши с координатами начала выделения
        """
        x1, y1, x2, y2 = event.x, event.y, event.x + 2, event.y + 2

        screenshot_area = self.image.crop((x1, y1, x2, y2))
        self.screenshot_area_tk = ImageTk.PhotoImage(screenshot_area)

        self.viewport = self.canvas.create_image(x1, y1, anchor='nw', image=self.screenshot_area_tk, tags='editor')

        self.border = self.canvas.create_rectangle(x1, y1, x2, y2,
                                                   width=2, dash=50, outline='lightgrey',
                                                   tags='service')
        cursors = {'nw': 'top_left_corner',
                   'n': 'top_side',
                   'ne': 'top_right_corner',
                   'e': 'right_side',
                   'se': 'bottom_right_corner',
                   's': 'bottom_side',
                   'sw': 'bottom_left_corner',
                   'w': 'left_side'}
        for corner in cursors:
            self._create_corner(corner, x1, y1, cursors[corner])

        self.x1, self.x2, self.y1, self.y2 = x1, x2, y1, y2

        self.viewport_size = self.canvas.create_text(x1 - 5, y1 - 7,
                                                     anchor='sw', text='0×0',
                                                     font='Helvetica 10 bold',
                                                     fill='lightgrey',
                                                     tags=['service', 'precision'])
        self.viewport_size_bg = self.canvas.create_rectangle(self.canvas.bbox(self.viewport_size),
                                                             fill='grey', outline='grey',
                                                             tags=['service', 'precision'])
        self.canvas.tag_bind(self.viewport_size, '<Enter>', lambda e: self.canvas.config(cursor='hand2'))
        self.canvas.tag_bind(self.viewport_size, '<Leave>', lambda e: self.canvas.config(cursor=''))
        self.canvas.tag_bind(self.viewport_size, '<ButtonPress-1>', lambda e: self._viewport_lock())

        self.canvas.tag_lower(self.viewport_size_bg, self.viewport_size)

        for row in range(7):
            for col in range(7):
                self.canvas.create_rectangle(0, 0, 10, 10, tags=['service', 'precision', f'z_{row}{col}', 'zoom'])
        self.canvas.itemconfig('z_33', width=3)

        self.color_pick = self.canvas.create_text(0, 0, anchor='sw', text='#000000',
                                                  font='Helvetica 10 bold',
                                                  tags=['service', 'precision', 'zoom'])
        self.color_pick_bg = self.canvas.create_rectangle(self.canvas.bbox(self.viewport_size),
                                                          tags=['service', 'precision', 'zoom'])
        self.canvas.tag_lower(self.color_pick_bg, self.color_pick)

        self.canvas.itemconfig('precision', state='hidden')

        self.bind('<KeyPress-Alt_L>', lambda e: self._precision())
        self.bind('<KeyRelease-Alt_L>', lambda e: self._stop_precision())
        self.bind('<KeyPress-Alt_R>', lambda e: self._precision())
        self.bind('<KeyRelease-Alt_R>', lambda e: self._stop_precision())
        self.canvas.tag_bind('editor', '<Alt-Button-1>', lambda e: [self._set_color(color='0'), self._new_item(e)])
        self.bind('<Control-KeyPress>', lambda e: self._control(e))

        self.canvas.tag_bind('editor', '<ButtonPress-2>', lambda e: self._new_item(e))
        self.canvas.tag_bind('editor', '<B2-Motion>', lambda e: self._ruler_move(e))
        self.canvas.tag_bind('editor', '<ButtonRelease-2>', lambda e: self._ruler_stop())

    def _precision(self):
        """Активирует режим прецизионных измерений (Alt). Показывает размеры области и цвет пикселя."""
        x1, y1, x2, y2 = self.canvas.bbox(self.viewport)
        self.canvas.itemconfig('precision', state='normal')
        size = f'{x2 - x1}×{y2 - y1}'
        self.canvas.itemconfig(self.viewport_size, text=f'>{size}<' if self.lock_viewport else size)
        height = self.canvas.bbox(self.viewport_size)[3] - self.canvas.bbox(self.viewport_size)[1]
        self.canvas.moveto(self.viewport_size, x1 - 5, y1 - height - 7)
        self.canvas.coords(self.viewport_size_bg, self.canvas.bbox(self.viewport_size))

        xp = self.winfo_pointerx() - self.winfo_rootx()
        yp = self.winfo_pointery() - self.winfo_rooty()
        x = min(max(35, xp), self.winfo_width() - 35)
        y = min(yp, self.winfo_height() - 110)

        if x1 <= xp <= x2 and y1 <= yp <= y2:
            self.canvas.itemconfigure('zoom', state='normal')
            for row in range(7):
                for col in range(7):
                    try:
                        r, g, b = self.image.getpixel((xp - 3 + col, yp - 3 + row))
                    except IndexError:
                        r, g, b = self.image.getpixel((xp, yp))
                    self.canvas.itemconfig(f'z_{row}{col}', fill=f'#{r:02x}{g:02x}{b:02x}')
                    self.canvas.moveto(f'z_{row}{col}', x - 35 + col * 10, y - 30 + row * 10 + 70)

            self.cursor_color = self.canvas.itemcget('z_33', 'fill')
            hex_red = int(self.cursor_color[1:3], base=16)
            hex_green = int(self.cursor_color[3:5], base=16)
            hex_blue = int(self.cursor_color[5:7], base=16)
            luminance = hex_red * 0.2126 + hex_green * 0.7152 + hex_blue * 0.0722
            self.canvas.itemconfig(self.color_pick, text=self._get_color_by_space(self.cursor_color, self.colorspace)[0],
                                   fill='lightgrey' if luminance < 140 else 'black')
            if self.colorspace != 'ral':
                self.canvas.itemconfig(self.color_pick_bg, fill=self.cursor_color, outline='black')
            else:
                ral_color = self._get_color_by_space(self.cursor_color, 'ral')[2]
                ral_fill = f'#{ral_color[0]:02x}{ral_color[1]:02x}{ral_color[2]:02x}'
                self.canvas.itemconfig(self.color_pick_bg, fill=ral_fill, outline='black')
            height_pick = self.canvas.bbox(self.color_pick)[3] - self.canvas.bbox(self.color_pick)[1]
            width_pick = self.canvas.bbox(self.color_pick)[2] - self.canvas.bbox(self.color_pick)[0]
            self.canvas.moveto(self.color_pick, x - width_pick // 2 + 1, y - height_pick - 32 + 70)
            self.canvas.coords(self.color_pick_bg, (min(x - 34, x - width_pick // 2), y - height_pick - 32 + 70,
                                                    max(x + 36, x + width_pick // 2 + 2), y - 32 + 70))
            self.canvas.tag_raise('precision')
            self.canvas.tag_raise('z_33')
        else:
            self.canvas.itemconfigure('zoom', state='hidden')

        self.bind('<MouseWheel>', lambda e: self._change_colorspace(e))

    def _stop_precision(self):
        """Завершение режима прецизионных измерений (Alt)"""
        self.canvas.itemconfig('precision', state='hidden')
        self.unbind('<MouseWheel>')

    def _change_colorspace(self, event):
        """Изменяет цветовое пространство определения цвета пикселя.

        Args:
            event (tk.Event): Событие колеса мыши
        """
        spaces = ['hex', 'rgb', 'hsl', 'hsv', 'cmyk', 'ral']
        colorspace = spaces.index(self.colorspace)
        colorspace += 1 if event.delta > 0 else -1
        self.colorspace = spaces[colorspace % 6]

    @staticmethod
    def _get_color_by_space(hex_color, space):
        """Конвертирует HEX-цвет в указанное цветовое пространство.

            Args:
                hex_color (str): Цвет в HEX-формате (#RRGGBB)
                space (str): Целевое цветовое пространство:
                             'hex'  - HEX (#RRGGBB)
                             'rgb'  - RGB (R, G, B)
                             'hsl'  - HSL (H°, S%, L%)
                             'hsv'  - HSV (H°, S%, V%)
                             'cmyk' - CMYK (C, M, Y, K)
                             'ral'  - RAL Classic

            Returns:
                list: Цвет в указанном формате, отформатированный для вывода и сохранения
            """
        red = int(hex_color[1:3], base=16)
        green = int(hex_color[3:5], base=16)
        blue = int(hex_color[5:7], base=16)

        match space:
            case 'hex':
                return [hex_color.upper(),
                        hex_color]
            case 'rgb':
                return [f'R:{red} G:{green} B:{blue}',
                        f'rgb({red} {green} {blue})']
            case 'hsl':
                hls = rgb_to_hls(red / 255, green / 255, blue / 255)
                return [f'HSL: {hls[0] * 360:.0f}° {hls[2]:.0%} {hls[1]:.0%}',
                        f'hsl({hls[0] * 360:.0f}, {hls[2]:.0%}, {hls[1]:.0%})']
            case 'hsv':
                h, s, v = rgb_to_hsv(red / 255, green / 255, blue / 255)
                return [f'HSV: {h * 360:.0f}° {s:.0%} {v:.0%}',
                        f'Hue:{h * 360:.0f}°, Saturation:{s:.0%}, Value/Brightness:{v:.0%}']
            case 'cmyk':
                key = 1 - max(red / 255, green / 255, blue / 255)
                if key == 1:
                    return ['C:0 M:0 Y:0 K:100',
                            'Cyan:0%, Magenta:0%, Yellow:0%, Key:100%']
                cyan = int((1 - red / 255 - key) / (1 - key) * 100)
                magenta = int((1 - green / 255 - key) / (1 - key) * 100)
                yellow = int((1 - blue / 255 - key) / (1 - key) * 100)
                key = int(key * 100)
                return [f'C:{cyan} M:{magenta} Y:{yellow} K:{key}',
                        f'Cyan:{cyan}%, Magenta:{magenta}%, Yellow:{yellow}%, Key:{key}%']
            case 'ral':
                ral_colors = (
                {'RAL': '1000', 'rgb': (205, 186, 136), 'eng': 'Green beige', 'rus': 'Зелено-бежевый'},
                {'RAL': '1001', 'rgb': (208, 176, 132), 'eng': 'Beige', 'rus': 'Бежевый'},
                {'RAL': '1002', 'rgb': (210, 170, 109), 'eng': 'Sand yellow', 'rus': 'Песочно-желтый'},
                {'RAL': '1003', 'rgb': (249, 169, 0), 'eng': 'Signal yellow', 'rus': 'Сигнальный желтый'},
                {'RAL': '1004', 'rgb': (228, 158, 0), 'eng': 'Golden yellow', 'rus': 'Золотисто-желтый'},
                {'RAL': '1005', 'rgb': (203, 143, 0), 'eng': 'Honey yellow', 'rus': 'Медово-желтый'},
                {'RAL': '1006', 'rgb': (225, 144, 0), 'eng': 'Maize yellow', 'rus': 'Кукурузно-желтый'},
                {'RAL': '1007', 'rgb': (232, 140, 0), 'eng': 'Daffodil yellow', 'rus': 'Желтый нарцисс'},
                {'RAL': '1011', 'rgb': (175, 128, 80), 'eng': 'Brown beige', 'rus': 'Коричнево-бежевый'},
                {'RAL': '1012', 'rgb': (221, 175, 40), 'eng': 'Lemon yellow', 'rus': 'Лимонно-желтый'},
                {'RAL': '1013', 'rgb': (227, 217, 199), 'eng': 'Oyster white', 'rus': 'Жемчужно-белый'},
                {'RAL': '1014', 'rgb': (221, 196, 155), 'eng': 'Ivory', 'rus': 'Слоновая кость'},
                {'RAL': '1015', 'rgb': (230, 210, 181), 'eng': 'Light ivory', 'rus': 'Светлая слоновая кость'},
                {'RAL': '1016', 'rgb': (241, 221, 57), 'eng': 'Sulfur yellow', 'rus': 'Желтая сера'},
                {'RAL': '1017', 'rgb': (246, 169, 81), 'eng': 'Saffron yellow', 'rus': 'Шафраново-желтый'},
                {'RAL': '1018', 'rgb': (250, 202, 49), 'eng': 'Zinc yellow', 'rus': 'Цинково-желтый'},
                {'RAL': '1019', 'rgb': (164, 143, 122), 'eng': 'Grey beige', 'rus': 'Серо-бежевый'},
                {'RAL': '1020', 'rgb': (160, 143, 101), 'eng': 'Olive yellow', 'rus': 'Оливково-желтый'},
                {'RAL': '1021', 'rgb': (246, 182, 0), 'eng': 'Colza yellow', 'rus': 'Рапсово-желтый'},
                {'RAL': '1023', 'rgb': (247, 181, 0), 'eng': 'Traffic yellow', 'rus': 'Транспортный желтый'},
                {'RAL': '1024', 'rgb': (186, 143, 76), 'eng': 'Ochre yellow', 'rus': 'Охра желтая'},
                {'RAL': '1026', 'rgb': (255, 255, 0), 'eng': 'Luminous yellow', 'rus': 'Люминесцентно-желтый'},
                {'RAL': '1027', 'rgb': (167, 127, 15), 'eng': 'Curry', 'rus': 'Желтое карри'},
                {'RAL': '1028', 'rgb': (255, 156, 0), 'eng': 'Melon yellow', 'rus': 'Дынно-желтый'},
                {'RAL': '1032', 'rgb': (226, 163, 0), 'eng': 'Broom yellow', 'rus': 'Жёлтый ракитник'},
                {'RAL': '1033', 'rgb': (249, 154, 29), 'eng': 'Dahlia yellow', 'rus': 'Георгиново-желтый'},
                {'RAL': '1034', 'rgb': (235, 156, 82), 'eng': 'Pastel yellow', 'rus': 'Пастельно-желтый'},
                {'RAL': '1035', 'rgb': (143, 131, 112), 'eng': 'Pearl beige', 'rus': 'Жемчужно'},
                {'RAL': '1036', 'rgb': (128, 100, 64), 'eng': 'Pearl gold', 'rus': 'Жемчужно-золотой'},
                {'RAL': '1037', 'rgb': (240, 146, 0), 'eng': 'Sun yellow', 'rus': 'Солнечно-желтый'},
                {'RAL': '2000', 'rgb': (218, 110, 0), 'eng': 'Yellow orange', 'rus': 'Желто-оранжевый'},
                {'RAL': '2001', 'rgb': (186, 72, 28), 'eng': 'Red orange', 'rus': 'Красно-оранжевый'},
                {'RAL': '2002', 'rgb': (191, 57, 34), 'eng': 'Vermilion', 'rus': 'Алый'},
                {'RAL': '2003', 'rgb': (246, 120, 41), 'eng': 'Pastel orange', 'rus': 'Пастельно-оранжевый'},
                {'RAL': '2004', 'rgb': (226, 83, 4), 'eng': 'Pure orange', 'rus': 'Чистый оранжевый'},
                {'RAL': '2005', 'rgb': (255, 77, 8), 'eng': 'Luminous orange', 'rus': 'Люминесцентно-оранжевый'},
                {'RAL': '2007', 'rgb': (255, 178, 0), 'eng': 'Luminous bright orange',
                 'rus': 'Люминесцентный ярко-оранжевый'},
                {'RAL': '2008', 'rgb': (236, 107, 34), 'eng': 'Bright red orange', 'rus': 'Ярко-красно-оранжевый'},
                {'RAL': '2009', 'rgb': (222, 83, 8), 'eng': 'Traffic orange', 'rus': 'Транспортный оранжевый'},
                {'RAL': '2010', 'rgb': (208, 93, 41), 'eng': 'Signal orange', 'rus': 'Сигнальный оранжевый'},
                {'RAL': '2011', 'rgb': (226, 110, 15), 'eng': 'Deep orange', 'rus': 'Насыщенный оранжевый'},
                {'RAL': '2012', 'rgb': (213, 101, 78), 'eng': 'Salmon orange', 'rus': 'Лососево-оранжевый'},
                {'RAL': '2013', 'rgb': (146, 62, 37), 'eng': 'Pearl orange', 'rus': 'Жемчужно-оранжевый'},
                {'RAL': '2017', 'rgb': (252, 85, 0), 'eng': 'RAL orange', 'rus': 'RAL Оранжевый'},
                {'RAL': '3000', 'rgb': (167, 41, 32), 'eng': 'Flame red', 'rus': 'Огненно-красный'},
                {'RAL': '3001', 'rgb': (155, 36, 35), 'eng': 'Signal red', 'rus': 'Сигнальный красный'},
                {'RAL': '3002', 'rgb': (155, 35, 33), 'eng': 'Carmine red', 'rus': 'Карминно-красный'},
                {'RAL': '3003', 'rgb': (134, 26, 34), 'eng': 'Ruby red', 'rus': 'Рубиново-красный'},
                {'RAL': '3004', 'rgb': (107, 28, 35), 'eng': 'Purple red', 'rus': 'Пурпурно-красный'},
                {'RAL': '3005', 'rgb': (89, 25, 31), 'eng': 'Wine red', 'rus': 'Винно-красный'},
                {'RAL': '3007', 'rgb': (62, 32, 34), 'eng': 'Black red', 'rus': 'Черно-красный'},
                {'RAL': '3009', 'rgb': (109, 52, 45), 'eng': 'Oxide red', 'rus': 'Красная окись'},
                {'RAL': '3011', 'rgb': (120, 36, 35), 'eng': 'Brown red', 'rus': 'Коричнево-красный'},
                {'RAL': '3012', 'rgb': (197, 133, 109), 'eng': 'Beige red', 'rus': 'Бежево-красный'},
                {'RAL': '3013', 'rgb': (151, 46, 37), 'eng': 'Tomato red', 'rus': 'Томатно-красный'},
                {'RAL': '3014', 'rgb': (203, 115, 117), 'eng': 'Antique pink', 'rus': 'Темно-розовый'},
                {'RAL': '3015', 'rgb': (216, 160, 166), 'eng': 'Light pink', 'rus': 'Светло-розовый'},
                {'RAL': '3016', 'rgb': (166, 61, 48), 'eng': 'Coral red', 'rus': 'Кораллово-красный'},
                {'RAL': '3017', 'rgb': (202, 85, 93), 'eng': 'Rose', 'rus': 'Розовый'},
                {'RAL': '3018', 'rgb': (198, 63, 74), 'eng': 'Strawberry red', 'rus': 'Клубнично-красный'},
                {'RAL': '3020', 'rgb': (187, 31, 17), 'eng': 'Traffic red', 'rus': 'Транспортный красный'},
                {'RAL': '3022', 'rgb': (207, 105, 85), 'eng': 'Salmon pink', 'rus': 'Лососево-красный'},
                {'RAL': '3024', 'rgb': (255, 45, 33), 'eng': 'Luminous red', 'rus': 'Люминесцентный красный'},
                {'RAL': '3026', 'rgb': (255, 42, 28), 'eng': 'Luminous bright red',
                 'rus': 'Люминесцентный ярко-красный'},
                {'RAL': '3027', 'rgb': (171, 39, 60), 'eng': 'Raspberry red', 'rus': 'Малиновый'},
                {'RAL': '3028', 'rgb': (204, 44, 36), 'eng': 'Pure red', 'rus': 'Красный'},
                {'RAL': '3031', 'rgb': (166, 52, 55), 'eng': 'Orient red', 'rus': 'Восточный красный'},
                {'RAL': '3032', 'rgb': (112, 29, 36), 'eng': 'Pearl ruby red', 'rus': 'Перламутрово-рубиновый'},
                {'RAL': '3033', 'rgb': (165, 58, 46), 'eng': 'Pearl pink', 'rus': 'Перламутрово-розовый'},
                {'RAL': '4001', 'rgb': (129, 97, 131), 'eng': 'Red lilac', 'rus': 'Красно-сиреневый'},
                {'RAL': '4002', 'rgb': (141, 60, 75), 'eng': 'Red violet', 'rus': 'Красно-фиолетовый'},
                {'RAL': '4003', 'rgb': (196, 97, 140), 'eng': 'Heather violet', 'rus': 'Вересково-фиолетовый'},
                {'RAL': '4004', 'rgb': (101, 30, 56), 'eng': 'Claret violet', 'rus': 'Бордово-фиолетовый'},
                {'RAL': '4005', 'rgb': (118, 104, 154), 'eng': 'Blue lilac', 'rus': 'Сине-сиреневый'},
                {'RAL': '4006', 'rgb': (144, 51, 115), 'eng': 'Traffic purple', 'rus': 'Транспортный пурпурный'},
                {'RAL': '4007', 'rgb': (71, 36, 60), 'eng': 'Purple violet', 'rus': 'Пурпурно-фиолетовый'},
                {'RAL': '4008', 'rgb': (132, 76, 130), 'eng': 'Signal violet', 'rus': 'Сигнальный фиолетовый'},
                {'RAL': '4009', 'rgb': (157, 134, 146), 'eng': 'Pastel violet', 'rus': 'Пастельно-фиолетовый'},
                {'RAL': '4010', 'rgb': (187, 64, 119), 'eng': 'Telemagenta', 'rus': 'Телемагента'},
                {'RAL': '4011', 'rgb': (110, 99, 135), 'eng': 'Pearl violet', 'rus': 'Жемчужно-фиолетовый'},
                {'RAL': '4012', 'rgb': (106, 107, 127), 'eng': 'Pearl blackberry', 'rus': 'Жемчужно-ежевичный'},
                {'RAL': '5000', 'rgb': (48, 79, 110), 'eng': 'Violet blue', 'rus': 'Фиолетово-синий'},
                {'RAL': '5001', 'rgb': (14, 76, 100), 'eng': 'Green blue', 'rus': 'Зелено-синий'},
                {'RAL': '5002', 'rgb': (0, 56, 122), 'eng': 'Ultramarine blue', 'rus': 'Ультрамарин'},
                {'RAL': '5003', 'rgb': (31, 56, 85), 'eng': 'Sapphire blue', 'rus': 'Сапфирово-синий'},
                {'RAL': '5004', 'rgb': (25, 30, 40), 'eng': 'Black blue', 'rus': 'Черно-синий'},
                {'RAL': '5005', 'rgb': (0, 83, 135), 'eng': 'Signal blue', 'rus': 'Сигнальный синий'},
                {'RAL': '5007', 'rgb': (55, 107, 140), 'eng': 'Brilliant blue', 'rus': 'Бриллиантово-синий'},
                {'RAL': '5008', 'rgb': (43, 58, 68), 'eng': 'Grey blue', 'rus': 'Серо-синий'},
                {'RAL': '5009', 'rgb': (33, 95, 120), 'eng': 'Azure blue', 'rus': 'Лазурно-синий'},
                {'RAL': '5010', 'rgb': (0, 79, 124), 'eng': 'Gentian blue', 'rus': 'Генцианово-синий'},
                {'RAL': '5011', 'rgb': (26, 43, 60), 'eng': 'Steel blue', 'rus': 'Стальной синий'},
                {'RAL': '5012', 'rgb': (0, 137, 182), 'eng': 'Light blue', 'rus': 'Голубой'},
                {'RAL': '5013', 'rgb': (25, 49, 83), 'eng': 'Cobalt blue', 'rus': 'Кобальтово-синий'},
                {'RAL': '5014', 'rgb': (99, 125, 150), 'eng': 'Pigeon blue', 'rus': 'Голубино-синий'},
                {'RAL': '5015', 'rgb': (0, 124, 175), 'eng': 'Sky blue', 'rus': 'Небесно-синий'},
                {'RAL': '5017', 'rgb': (0, 91, 140), 'eng': 'Traffic blue', 'rus': 'Транспортный синий'},
                {'RAL': '5018', 'rgb': (4, 139, 140), 'eng': 'Turquoise blue', 'rus': 'Бирюзово-синий'},
                {'RAL': '5019', 'rgb': (0, 94, 131), 'eng': 'Capri blue', 'rus': 'Синий капри'},
                {'RAL': '5020', 'rgb': (0, 65, 75), 'eng': 'Ocean blue', 'rus': 'Океанская синь'},
                {'RAL': '5021', 'rgb': (0, 117, 119), 'eng': 'Water blue', 'rus': 'Водная синь'},
                {'RAL': '5022', 'rgb': (34, 45, 90), 'eng': 'Night blue', 'rus': 'Ночной синий'},
                {'RAL': '5023', 'rgb': (65, 105, 140), 'eng': 'Distant blue', 'rus': 'Отдаленно-синий'},
                {'RAL': '5024', 'rgb': (96, 147, 172), 'eng': 'Pastel blue', 'rus': 'Пастельно-синий'},
                {'RAL': '5025', 'rgb': (32, 105, 124), 'eng': 'Pearl gentian blue', 'rus': 'Жемчужно-генцианово-синий'},
                {'RAL': '5026', 'rgb': (15, 48, 82), 'eng': 'Pearl night blue', 'rus': 'Жемчужно-ночной-синий'},
                {'RAL': '6000', 'rgb': (60, 116, 96), 'eng': 'Patina green', 'rus': 'Патиново-зеленый'},
                {'RAL': '6001', 'rgb': (54, 103, 53), 'eng': 'Emerald green', 'rus': 'Изумрудно-зеленый'},
                {'RAL': '6002', 'rgb': (50, 89, 40), 'eng': 'Leaf green', 'rus': 'Лиственно-зеленый'},
                {'RAL': '6003', 'rgb': (80, 83, 60), 'eng': 'Olive green', 'rus': 'Оливково-зеленый'},
                {'RAL': '6004', 'rgb': (2, 68, 66), 'eng': 'Blue green', 'rus': 'Сине-зеленый'},
                {'RAL': '6005', 'rgb': (17, 66, 50), 'eng': 'Moss green', 'rus': 'Зеленый мох'},
                {'RAL': '6006', 'rgb': (60, 57, 46), 'eng': 'Grey olive', 'rus': 'Серо-оливковый'},
                {'RAL': '6007', 'rgb': (44, 50, 34), 'eng': 'Bottle green', 'rus': 'Бутылочно-зеленый'},
                {'RAL': '6008', 'rgb': (54, 52, 42), 'eng': 'Brown green', 'rus': 'Коричнево-зеленый'},
                {'RAL': '6009', 'rgb': (39, 53, 42), 'eng': 'Fir green', 'rus': 'Пихтовый зеленый'},
                {'RAL': '6010', 'rgb': (77, 111, 57), 'eng': 'Grass green', 'rus': 'Травяной зеленый'},
                {'RAL': '6011', 'rgb': (107, 124, 89), 'eng': 'Reseda green', 'rus': 'Резедово-зеленый'},
                {'RAL': '6012', 'rgb': (47, 61, 58), 'eng': 'Black green', 'rus': 'Черно-зеленый'},
                {'RAL': '6013', 'rgb': (124, 118, 90), 'eng': 'Reed green', 'rus': 'Тростниково-зеленый'},
                {'RAL': '6014', 'rgb': (71, 65, 53), 'eng': 'Yellow olive', 'rus': 'Желто-оливковый'},
                {'RAL': '6015', 'rgb': (61, 61, 54), 'eng': 'Black olive', 'rus': 'Черно-оливковый'},
                {'RAL': '6016', 'rgb': (0, 105, 76), 'eng': 'Turquoise green', 'rus': 'Бирюзово-зеленый'},
                {'RAL': '6017', 'rgb': (88, 127, 64), 'eng': 'May green', 'rus': 'Майский зеленый'},
                {'RAL': '6018', 'rgb': (96, 153, 59), 'eng': 'Yellow green', 'rus': 'Желто-зеленый'},
                {'RAL': '6019', 'rgb': (185, 206, 172), 'eng': 'Pastel green', 'rus': 'Бело-зеленый'},
                {'RAL': '6020', 'rgb': (55, 66, 47), 'eng': 'Chrome green', 'rus': 'Хромовый зеленый'},
                {'RAL': '6021', 'rgb': (138, 153, 119), 'eng': 'Pale green', 'rus': 'Бледно-зеленый'},
                {'RAL': '6022', 'rgb': (58, 51, 39), 'eng': 'Olive drab', 'rus': 'Коричнево-оливковый'},
                {'RAL': '6024', 'rgb': (0, 131, 81), 'eng': 'Traffic green', 'rus': 'Транспортный зеленый'},
                {'RAL': '6025', 'rgb': (94, 110, 59), 'eng': 'Fern green', 'rus': 'Папоротниковый зеленый'},
                {'RAL': '6026', 'rgb': (0, 95, 78), 'eng': 'Opal green', 'rus': 'Опаловый зеленый'},
                {'RAL': '6027', 'rgb': (126, 186, 181), 'eng': 'Light green', 'rus': 'Светло-зеленый'},
                {'RAL': '6028', 'rgb': (49, 84, 66), 'eng': 'Pine green', 'rus': 'Сосновый зеленый'},
                {'RAL': '6029', 'rgb': (0, 111, 61), 'eng': 'Mint green', 'rus': 'Мятно-зеленый'},
                {'RAL': '6032', 'rgb': (35, 127, 82), 'eng': 'Signal green', 'rus': 'Сигнальный зеленый'},
                {'RAL': '6033', 'rgb': (69, 135, 127), 'eng': 'Mint turquoise', 'rus': 'Мятно-бирюзовый'},
                {'RAL': '6034', 'rgb': (122, 173, 172), 'eng': 'Pastel turquoise', 'rus': 'Пастельно-бирюзовый'},
                {'RAL': '6035', 'rgb': (25, 77, 37), 'eng': 'Pearl green', 'rus': 'Перламутрово-зеленый'},
                {'RAL': '6036', 'rgb': (4, 87, 75), 'eng': 'Pearl opal green', 'rus': 'Перламутрово-опаловый зеленый'},
                {'RAL': '6037', 'rgb': (0, 139, 41), 'eng': 'Pure green', 'rus': 'Зеленый'},
                {'RAL': '6038', 'rgb': (0, 181, 27), 'eng': 'Luminous green', 'rus': 'Люминесцентный зеленый'},
                {'RAL': '6039', 'rgb': (179, 196, 62), 'eng': 'Fibrous green', 'rus': 'Зеленое волокно'},
                {'RAL': '7000', 'rgb': (122, 136, 142), 'eng': 'Squirrel grey', 'rus': 'Серая белка'},
                {'RAL': '7001', 'rgb': (140, 151, 156), 'eng': 'Silver grey', 'rus': 'Серебристо-серый'},
                {'RAL': '7002', 'rgb': (129, 120, 99), 'eng': 'Olive grey', 'rus': 'Оливково-серый'},
                {'RAL': '7003', 'rgb': (121, 118, 105), 'eng': 'Moss grey', 'rus': 'Серый мох'},
                {'RAL': '7004', 'rgb': (154, 155, 155), 'eng': 'Signal grey', 'rus': 'Сигнальный серый'},
                {'RAL': '7005', 'rgb': (107, 110, 107), 'eng': 'Mouse grey', 'rus': 'Мышино-серый'},
                {'RAL': '7006', 'rgb': (118, 106, 94), 'eng': 'Beige grey', 'rus': 'Бежево-серый'},
                {'RAL': '7008', 'rgb': (116, 95, 61), 'eng': 'Khaki grey', 'rus': 'Серое хаки'},
                {'RAL': '7009', 'rgb': (93, 96, 88), 'eng': 'Green grey', 'rus': 'Зелено-серый'},
                {'RAL': '7010', 'rgb': (88, 92, 86), 'eng': 'Tarpaulin grey', 'rus': 'Брезентово-серый'},
                {'RAL': '7011', 'rgb': (82, 89, 93), 'eng': 'Iron grey', 'rus': 'Железно-серый'},
                {'RAL': '7012', 'rgb': (87, 93, 94), 'eng': 'Basalt grey', 'rus': 'Базальтово-серый'},
                {'RAL': '7013', 'rgb': (87, 80, 68), 'eng': 'Brown grey', 'rus': 'Коричнево-серый'},
                {'RAL': '7015', 'rgb': (79, 83, 88), 'eng': 'Slate grey', 'rus': 'Сланцево-серый'},
                {'RAL': '7016', 'rgb': (56, 62, 66), 'eng': 'Anthracite grey', 'rus': 'Антрацитово-серый'},
                {'RAL': '7021', 'rgb': (47, 50, 52), 'eng': 'Black grey', 'rus': 'Черно-серый'},
                {'RAL': '7022', 'rgb': (76, 74, 68), 'eng': 'Umbra grey', 'rus': 'Серая умбра'},
                {'RAL': '7023', 'rgb': (128, 128, 118), 'eng': 'Concrete grey', 'rus': 'Серый бетон'},
                {'RAL': '7024', 'rgb': (69, 73, 78), 'eng': 'Graphite grey', 'rus': 'Графитовый серый'},
                {'RAL': '7026', 'rgb': (55, 67, 69), 'eng': 'Granite grey', 'rus': 'Гранитовый серый'},
                {'RAL': '7030', 'rgb': (146, 142, 133), 'eng': 'Stone grey', 'rus': 'Каменно-серый'},
                {'RAL': '7031', 'rgb': (91, 104, 109), 'eng': 'Blue grey', 'rus': 'Сине-серый'},
                {'RAL': '7032', 'rgb': (181, 176, 161), 'eng': 'Pebble grey', 'rus': 'Галечный серый'},
                {'RAL': '7033', 'rgb': (127, 130, 116), 'eng': 'Cement grey', 'rus': 'Цементно-серый'},
                {'RAL': '7034', 'rgb': (146, 136, 111), 'eng': 'Yellow grey', 'rus': 'Желто-серый'},
                {'RAL': '7035', 'rgb': (197, 199, 196), 'eng': 'Light grey', 'rus': 'Светло-серый'},
                {'RAL': '7036', 'rgb': (151, 147, 146), 'eng': 'Platinum grey', 'rus': 'Платиново-серый'},
                {'RAL': '7037', 'rgb': (122, 123, 122), 'eng': 'Dusty grey', 'rus': 'Пыльно-серый'},
                {'RAL': '7038', 'rgb': (176, 176, 169), 'eng': 'Agate grey', 'rus': 'Агатовый серый'},
                {'RAL': '7039', 'rgb': (107, 102, 94), 'eng': 'Quartz grey', 'rus': 'Кварцевый серый'},
                {'RAL': '7040', 'rgb': (152, 158, 161), 'eng': 'Window grey', 'rus': 'Серое окно'},
                {'RAL': '7042', 'rgb': (142, 146, 145), 'eng': 'Traffic grey A', 'rus': 'Транспортный серый А'},
                {'RAL': '7043', 'rgb': (79, 82, 80), 'eng': 'Traffic grey B', 'rus': 'Транспортный серый В'},
                {'RAL': '7044', 'rgb': (183, 179, 168), 'eng': 'Silk grey', 'rus': 'Серый шелк'},
                {'RAL': '7045', 'rgb': (141, 146, 149), 'eng': 'Telegrey 1', 'rus': 'Телегрей 1'},
                {'RAL': '7046', 'rgb': (126, 134, 138), 'eng': 'Telegrey 2', 'rus': 'Телегрей 2'},
                {'RAL': '7047', 'rgb': (200, 200, 199), 'eng': 'Telegrey 4', 'rus': 'Телегрей 4'},
                {'RAL': '7048', 'rgb': (129, 123, 115), 'eng': 'Pearl mouse grey', 'rus': 'Перламутровый мышино-серый'},
                {'RAL': '8000', 'rgb': (137, 105, 63), 'eng': 'Green brown', 'rus': 'Зелено-коричневый'},
                {'RAL': '8001', 'rgb': (157, 98, 43), 'eng': 'Ochre brown', 'rus': 'Охра коричневая'},
                {'RAL': '8002', 'rgb': (121, 77, 62), 'eng': 'Signal brown', 'rus': 'Сигнальный коричневый'},
                {'RAL': '8003', 'rgb': (126, 75, 39), 'eng': 'Clay brown', 'rus': 'Глиняный коричневый'},
                {'RAL': '8004', 'rgb': (141, 73, 49), 'eng': 'Copper brown', 'rus': 'Медно-коричневый'},
                {'RAL': '8007', 'rgb': (112, 70, 43), 'eng': 'Fawn brown', 'rus': 'Палево-коричневый'},
                {'RAL': '8008', 'rgb': (114, 74, 37), 'eng': 'Olive brown', 'rus': 'Оливково-коричневый'},
                {'RAL': '8011', 'rgb': (90, 56, 39), 'eng': 'Nut brown', 'rus': 'Орехово-коричневый'},
                {'RAL': '8012', 'rgb': (102, 51, 43), 'eng': 'Red brown', 'rus': 'Красно-коричневый'},
                {'RAL': '8014', 'rgb': (74, 53, 38), 'eng': 'Sepia brown', 'rus': 'Сепия коричневый'},
                {'RAL': '8015', 'rgb': (94, 47, 38), 'eng': 'Chestnut brown', 'rus': 'Каштаново-коричневый'},
                {'RAL': '8016', 'rgb': (76, 43, 32), 'eng': 'Mahogany brown', 'rus': 'Махагон коричневый'},
                {'RAL': '8017', 'rgb': (68, 47, 41), 'eng': 'Chocolate brown', 'rus': 'Шоколадно-коричневый'},
                {'RAL': '8019', 'rgb': (61, 54, 53), 'eng': 'Grey brown', 'rus': 'Серо-коричневый'},
                {'RAL': '8022', 'rgb': (26, 23, 25), 'eng': 'Black brown', 'rus': 'Черно-коричневый'},
                {'RAL': '8023', 'rgb': (164, 87, 41), 'eng': 'Orange brown', 'rus': 'Оранжево-коричневый'},
                {'RAL': '8024', 'rgb': (121, 80, 56), 'eng': 'Beige brown', 'rus': 'Бежево-коричневый'},
                {'RAL': '8025', 'rgb': (117, 88, 71), 'eng': 'Pale brown', 'rus': 'Бледно-коричневый'},
                {'RAL': '8028', 'rgb': (81, 58, 42), 'eng': 'Terra brown', 'rus': 'Земельно-коричневый'},
                {'RAL': '8029', 'rgb': (127, 64, 49), 'eng': 'Pearl copper', 'rus': 'Жемчужно-медный'},
                {'RAL': '9001', 'rgb': (233, 224, 210), 'eng': 'Cream', 'rus': 'Кремово-белый'},
                {'RAL': '9002', 'rgb': (214, 213, 203), 'eng': 'Grey white', 'rus': 'Серо-белый'},
                {'RAL': '9003', 'rgb': (236, 236, 231), 'eng': 'Signal white', 'rus': 'Сигнальный белый'},
                {'RAL': '9004', 'rgb': (43, 43, 44), 'eng': 'Signal black', 'rus': 'Сигнальный черный'},
                {'RAL': '9005', 'rgb': (14, 14, 16), 'eng': 'Jet black', 'rus': 'Глубокий черный'},
                {'RAL': '9006', 'rgb': (161, 161, 160), 'eng': 'White aluminium', 'rus': 'Бело-алюминиевый'},
                {'RAL': '9007', 'rgb': (134, 133, 129), 'eng': 'Grey aluminium', 'rus': 'Серо-алюминиевый'},
                {'RAL': '9010', 'rgb': (241, 237, 225), 'eng': 'Pure white', 'rus': 'Белый'},
                {'RAL': '9011', 'rgb': (39, 41, 43), 'eng': 'Graphite black', 'rus': 'Графитовый черный'},
                {'RAL': '9012', 'rgb': (248, 242, 225), 'eng': 'Cleanroom white', 'rus': 'Белый для чистых помещений'},
                {'RAL': '9016', 'rgb': (241, 241, 234), 'eng': 'Traffic white', 'rus': 'Транспортный белый'},
                {'RAL': '9017', 'rgb': (41, 41, 42), 'eng': 'Traffic black', 'rus': 'Транспортный черный'},
                {'RAL': '9018', 'rgb': (200, 203, 196), 'eng': 'Papyrus white', 'rus': 'Папирусно-белый'},
                {'RAL': '9022', 'rgb': (133, 133, 131), 'eng': 'Pearl light grey', 'rus': 'Жемчужный светло-серый'},
                {'RAL': '9023', 'rgb': (120, 123, 122), 'eng': 'Pearl dark grey', 'rus': 'Жемчужный темно-серый'})

                closest_color = None
                min_distance = float('inf')

                for color in ral_colors:
                    distance = dist((red, green, blue), color['rgb'])
                    if distance < min_distance:
                        min_distance = distance
                        closest_color = color
                return [f'RAL {closest_color["RAL"]}',
                        f'RAL {closest_color["RAL"]} ({closest_color["rus"]})',
                        closest_color['rgb']]


    def _set_color(self, color):
        """Устанавливает активный цвет для инструментов рисования.

        Args:
            color (str): Код цвета (1-9) или '0' для пипетки
        """
        if color == '':
            return
        elif color in '123456789':
            self.color = int(color) - 1
            self.color_panel['background'] = self.palette[self.color]
        elif color == '0':
            x = self.winfo_pointerx() - self.winfo_rootx()
            y = self.winfo_pointery() - self.winfo_rooty()
            r, g, b = self.image.getpixel((x, y))
            self.color_panel['background'] = f'#{r:02x}{g:02x}{b:02x}'

    def _set_viewport(self, event):
        """Обновляет границы выделенной области при перемещении мыши.

        Args:
            event (tk.Event): Событие перемещения мыши с текущими координатами
        """
        x1, x2, y1, y2 = self.x1, event.x, self.y1, event.y

        anchor = 's' if y2 < y1 else 'n'
        anchor += 'e' if x2 < x1 else 'w'

        x2, x1 = (x1, x2) if x2 < x1 else (x2, x1)
        y2, y1 = (y1, y2) if y2 < y1 else (y2, y1)

        self.screenshot_area = self.image.crop((x1, y1, x2, y2))
        self.screenshot_area_tk = ImageTk.PhotoImage(self.screenshot_area)
        self.canvas.itemconfig(self.viewport, image=self.screenshot_area_tk, anchor=anchor)
        self._draw_borders(x1, y1, x2, y2)

        self.x2, self.y2 = x2, y2

    def _change_viewport(self, corner, event):
        """Изменяет размер области редактирования через маркеры.

        Args:
            corner (str): Позиция изменяемого угла
            event (tk.Event): Событие перемещения мыши
        """
        x1 = event.x if 'w' in corner else self.x1
        y1 = event.y if 'n' in corner else self.y1
        x2 = event.x if 'e' in corner else self.x2
        y2 = event.y if 's' in corner else self.y2

        self.x1, self.x2, self.y1, self.y2 = x1, x2, y1, y2

        x2, x1 = (x1, x2) if x2 < x1 else (x2, x1)
        y2, y1 = (y1, y2) if y2 < y1 else (y2, y1)

        bbox = self.canvas.bbox('item')
        if bbox is not None:
            xb1, yb1, xb2, yb2 = bbox
            x1 = min(x1, xb1)
            x2 = max(x2, xb2)
            y1 = min(y1, yb1)
            y2 = max(y2, yb2)

        self.screenshot_area = self.image.crop((x1, y1, x2, y2))
        self.screenshot_area_tk = ImageTk.PhotoImage(self.screenshot_area)
        self.canvas.moveto(self.viewport, x1, y1)
        self.canvas.itemconfig(self.viewport, image=self.screenshot_area_tk, anchor='nw')
        self._draw_borders(x1, y1, x2, y2)

    def _fix_viewport(self):
        """Фиксирует новые границы области редактирования после изменения."""
        self.x1, self.y1, self.x2, self.y2 = self.canvas.coords(self.border)

    def _check_viewport_borders(self, x, y):
        """Расширяет область редактирования при выходе за границы.
        Если стоит запрет на изменения границ, то возвращается точка на границе редактора
        Если границы можно менять, то меняет границы редактора, возвращает те же значения, что получила функция

        Args:
            x, y (int): Координаты проверяемой точки
        """

        if self.lock_viewport:
            x = min(self.canvas.bbox(self.viewport)[2], max(x, self.canvas.bbox(self.viewport)[0]))
            y = min(self.canvas.bbox(self.viewport)[3], max(y, self.canvas.bbox(self.viewport)[1]))

        else:
            x1 = x if x < self.canvas.bbox(self.viewport)[0] else self.canvas.bbox(self.viewport)[0]
            x2 = x if x > self.canvas.bbox(self.viewport)[2] else self.canvas.bbox(self.viewport)[2]
            y1 = y if y < self.canvas.bbox(self.viewport)[1] else self.canvas.bbox(self.viewport)[1]
            y2 = y if y > self.canvas.bbox(self.viewport)[3] else self.canvas.bbox(self.viewport)[3]

            if self.canvas.bbox(self.viewport) != [x1, y1, x2, y2]:
                self.screenshot_area = self.image.crop((x1, y1, x2, y2))
                self.screenshot_area_tk = ImageTk.PhotoImage(self.screenshot_area)
                self.canvas.moveto(self.viewport, x1, y1)
                self.canvas.itemconfig(self.viewport, image=self.screenshot_area_tk, anchor='nw')
                self._draw_borders(x1, y1, x2, y2)
                self.x1, self.y1, self.x2, self.y2 = [x1, y1, x2, y2]

        return [x, y]

    def _start_editing(self):
        """Активирует панель инструментов после завершения выделения области."""
        if [self.x1, self.x2, self.y1, self.y2] == [None, None, None, None]:
            return
        self.x1, self.y1, self.x2, self.y2 = self.canvas.coords(self.border)
        self.canvas.unbind('<B1-Motion>')
        self.canvas.unbind('<ButtonPress-1>')
        self.canvas.unbind('<ButtonRelease-1>')
        self.canvas.unbind('<Button-3>')

        self.bind('<Motion>', lambda e: self._cursor())
        self.bind('<ButtonPress-1>', lambda e: self._viewport_start_move())

        self.canvas.create_window(self.canvas.winfo_width() // 2, 10, window=self.panel, anchor='n', tags='service')
        self.MakeDraggable(self.panel, on_start=self.panel_hint.hide)

        self.arrow_button.grid(padx=3, pady=3, column=0, row=1)
        self.pen_button.grid(padx=3, pady=3, column=1, row=1)
        self.line_button.grid(padx=3, pady=3, column=2, row=1)
        self.rect_button.grid(padx=3, pady=3, column=3, row=1)
        self.text_button.grid(padx=3, pady=3, column=4, row=1)
        self.num_button.bind('<MouseWheel>', lambda e: self._change_number(e))
        self.num_button.grid(padx=3, pady=3, column=5, row=1)
        self.blur_button.grid(padx=3, pady=3, column=6, row=1)
        self.color_panel.bind('<MouseWheel>', lambda e: self._change_color(e))
        self.color_panel.grid(padx=3, pady=3, column=7, row=1)
        self.recognize_button.grid(padx=3, pady=3, column=8, row=1)
        self.done_button.grid(padx=3, pady=3, column=9, row=1)

        self._set_arrow()

    def _cursor(self):
        """Установка типа курсора "fleur" для зоны, где можно менять положение редактора"""
        x, y = self.winfo_pointerxy()
        xv1, yv1, xv2, yv2 = self._offset_bbox(self.canvas.bbox(self.viewport), 5)
        xp1, yp1 = self.panel.winfo_x(), self.panel.winfo_y()
        xp2, yp2 = xp1 + self.panel.winfo_width(), yp1 + self.panel.winfo_height()
        if (xv1 <= x <= xv2 and yv1 <= y <= yv2) or (xp1 <= x <= xp2 and yp1 <= y <= yp2):
            self.config(cursor='')
        else:
            self.config(cursor='fleur')

    def _viewport_start_move(self):
        """Обработчик начала передвижения окна редактора"""
        x, y = self.winfo_pointerxy()
        xv1, yv1, xv2, yv2 = self._offset_bbox(self.canvas.bbox(self.viewport), 5)
        xp1, yp1 = self.panel.winfo_x(), self.panel.winfo_y()
        xp2, yp2 = xp1 + self.panel.winfo_width(), yp1 + self.panel.winfo_height()
        if (xv1 <= x <= xv2 and yv1 <= y <= yv2) or (xp1 <= x <= xp2 and yp1 <= y <= yp2):
            return
        else:
            self.drag_start_coords = [x, y]
            self.bind('<B1-Motion>', lambda e: self._viewport_move(e))
            self.bind('<ButtonRelease-1>', lambda e: self._viewport_stop_move(e))

    def _viewport_move(self, event):
        """Обработчик передвижения окна редактора
        - контроль за зонами границ экрана и границ уже нарисованных элементов"""
        dx = event.x - self.drag_start_coords[0]
        dy = event.y - self.drag_start_coords[1]

        width = self.x2 - self.x1
        height = self.y2 - self.y1

        items = self.canvas.bbox('item')

        right = min(items[0], self.winfo_width() - width) if items else self.winfo_width() - width
        left = max(0, items[2] - width) if items else 0
        top = max(0, items[3] - height) if items else 0
        bottom = min(items[1], self.winfo_height() - height) if items else self.winfo_height() - height

        x1 = max(left, min(self.x1 + dx, right))
        y1 = max(top, min(self.y1 + dy, bottom))
        x2 = x1 + width
        y2 = y1 + height

        self.screenshot_area = self.image.crop((x1, y1, x2, y2))
        self.screenshot_area_tk = ImageTk.PhotoImage(self.screenshot_area)
        self.canvas.itemconfig(self.viewport, image=self.screenshot_area_tk, anchor='nw')
        self.canvas.moveto(self.viewport, x1, y1)
        self._draw_borders(x1, y1, x2, y2)

        self.drag_start_coords = [event.x, event.y]
        self.x1, self.y1, self.x2, self.y2 = x1, y1, x2, y2

    def _viewport_stop_move(self, event):
        """Обработчик окончания перетаскивания окна редактора"""
        self.unbind('<B1-Motion>')
        self.unbind('<ButtonRelease-1>')

    def _set_selection(self, button):
        """Активирует состояние выбранной кнопки на панели инструментов.

        Args:
            button (ttk.Button): Нажатая кнопка инструмента
        """
        for w in button.master.winfo_children():
            ttk.Button.state(w, ['!pressed'])
        ttk.Button.state(button, ['pressed'])
        self.panel_hint.hide()
        if button != self.text_button and self.text_edit:
            self._text_stop()

    def _new_item(self, event):
        """Инициализирует создание нового графического элемента.

        Args:
            event (tk.Event): Событие нажатия мыши
        """
        self.coords = [event.x, event.y]

    def _set_arrow(self):
        """Активирует инструмент 'Стрелка' для создания указателей."""
        self.canvas.tag_bind('editor', '<ButtonPress-1>', lambda e: self._new_item(e))
        self.canvas.tag_bind('editor', '<B1-Motion>', lambda e: self._arrow_move(e))
        self.canvas.tag_bind('editor', '<ButtonRelease-1>', lambda e: self.canvas.unbind('<MouseWheel>'))
        self.canvas.tag_unbind('editor', '<Shift-B1-Motion>')
        self._set_selection(self.arrow_button)

    def _arrow_move(self, event):
        """Обрабатывает создание и перемещение стрелки.

        Args:
            event (tk.Event): Событие перемещения мыши
        """
        if len(self.coords) == 2:
            self.coords += [event.x, event.y]
            self.arrow = self.canvas.create_line(self.coords,
                                                 width=5, tags=['editor', 'item'],
                                                 arrowshape=(17, 25, 7), capstyle='round',
                                                 fill=self.color_panel['background'],
                                                 arrow=tk.LAST)
            self.canvas.tag_bind(self.arrow, '<ButtonPress-3>', partial(self.canvas.delete, self.arrow))
            self.canvas.bind('<MouseWheel>', lambda e: self._arrow_change(e))
        else:
            self.coords = self.coords[:2] + self._check_viewport_borders(event.x, event.y)
            self.canvas.coords(self.arrow, self.coords)

    def _arrow_change(self, event):
        """Изменяет направление стрелки колесом мыши.

        Args:
            event (tk.Event): Событие колеса мыши
        """
        arrows = [tk.FIRST, tk.LAST, tk.BOTH]
        arrow = arrows.index(self.canvas.itemcget(self.arrow, 'arrow'))
        arrow += 1 if event.delta > 0 else -1
        self.canvas.itemconfigure(self.arrow, arrow=arrows[arrow % 3])

    def _set_pen(self):
        """Активирует инструмент 'Карандаш' для свободного рисования."""
        self.canvas.tag_bind('editor', '<ButtonPress-1>', lambda e: self._new_item(e))
        self.canvas.tag_bind('editor', '<B1-Motion>', lambda e: self._pen_draw(e))
        self.canvas.tag_bind('editor', '<ButtonRelease-1>', lambda e: self._pen_control_stop())
        self.canvas.tag_unbind('editor', '<Shift-B1-Motion>')
        self._set_selection(self.pen_button)

    def _pen_control_stop(self):
        """Останавливает обработку специальных режимов для инструмента 'Карандаш'."""
        self.unbind('<KeyPress-Control_L>')
        self.unbind('<KeyRelease-Control_L>')
        self.unbind('<KeyPress-Control_R>')
        self.unbind('<KeyRelease-Control_R>')
        self.canvas.unbind('<MouseWheel>')

    def _pen_draw(self, event):
        """Обрабатывает рисование карандашом.

        Args:
            event (tk.Event): Событие перемещения мыши
        """
        if len(self.coords) == 2:
            self.coords += [event.x, event.y]
            self.pen = self.canvas.create_line(self.coords, width=5, capstyle='round',
                                               fill=self.color_panel['background'], tags=['editor', 'item'])
            self.canvas.tag_bind(self.pen, '<ButtonPress-3>', partial(self.canvas.delete, self.pen))
            self.bind('<KeyPress-Control_L>', lambda e: self._pen_recognise())
            self.bind('<KeyRelease-Control_L>', lambda e: self.canvas.coords(self.pen, self.coords))
            self.bind('<KeyPress-Control_R>', lambda e: self._pen_recognise())
            self.bind('<KeyRelease-Control_R>', lambda e: self.canvas.coords(self.pen, self.coords))
            self.canvas.bind('<MouseWheel>', lambda e: self._pen_width_change(e))
        else:
            x1, y1 = self.coords[:2]
            x2, y2 = event.x, event.y
            distance = sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
            if distance > 3:
                self.coords += self._check_viewport_borders(x2, y2)
                self.canvas.coords(self.pen, self.coords)


    def _pen_width_change(self, event):
        """Изменяет толщину карандаша колесом мыши.

        Args:
            event (tk.Event): Событие колеса мыши
        """
        pen_width = float(self.canvas.itemcget(self.pen, 'width'))
        pen_width = max(pen_width - 1, 0) if event.delta < 0 else pen_width + 1
        self.canvas.itemconfigure(self.pen, width=pen_width)

    def _pen_recognise(self):
        """Автоматически преобразует нарисованные линии в геометрические фигуры."""
        points = []
        for point in range(0, len(self.coords), 2):
            points.append((float(self.coords[point]), float(self.coords[point + 1])))
        height = self.canvas.bbox(self.pen)[3] - self.canvas.bbox(self.pen)[1]
        width = self.canvas.bbox(self.pen)[2] - self.canvas.bbox(self.pen)[0]
        tolerance = max(height, width) / 10
        shape = self._simplify_points(points, tolerance=tolerance)
        corners = len(shape)
        if corners == 2:  # line
            pass
        elif dist(shape[0], shape[-1]) < tolerance * 2:
            corners -= 1
            if corners == 3:  # triangle
                shape[-1] = shape[0]
            elif corners in [4, 5]:  # rectangle (incl. mistake)
                line_string = LineString(points)
                coords = line_string.oriented_envelope.exterior.coords
                shape = [(x, y) for x, y in coords]
            else:  # ellipse
                x1 = min([point[0] for point in points])
                y1 = min([point[1] for point in points])
                x2 = max([point[0] for point in points])
                y2 = max([point[1] for point in points])
                r1 = (x2 - x1) / 2
                r2 = (y2 - y1) / 2
                shape = []
                for angle in range(60 + 1):
                    x = int((x2 + x1) / 2 + r1 * sin(pi * 2 / 60 * angle))
                    y = int((y2 + y1) / 2 + r2 * cos(pi * 2 / 60 * angle))
                    shape.append((x, y))
        else:  # something else
            shape = points
        self.canvas.coords(self.pen, shape)

        self._check_viewport_borders(self.canvas.bbox(self.pen)[0], self.canvas.bbox(self.pen)[1])
        self._check_viewport_borders(self.canvas.bbox(self.pen)[2], self.canvas.bbox(self.pen)[3])

    @staticmethod
    def _simplify_points(pts, tolerance):
        """Упрощает набор точек с заданной точностью.

        Args:
            pts (list): Список точек (x,y)
            tolerance (float): Допустимая погрешность

        Returns:
            list: Упрощенный список точек
        """
        anchor = 0
        floater = len(pts) - 1
        stack = []
        keep = set()

        stack.append((anchor, floater))
        while stack:
            anchor, floater = stack.pop()

            if pts[floater] != pts[anchor]:
                anchor_x = float(pts[floater][0] - pts[anchor][0])
                anchor_y = float(pts[floater][1] - pts[anchor][1])
                seg_len = sqrt(anchor_x ** 2 + anchor_y ** 2)
                anchor_x /= seg_len
                anchor_y /= seg_len
            else:
                anchor_x = anchor_y = 0.0

            max_dist = 0.0
            farthest = anchor + 1
            for i in range(anchor + 1, floater):
                vec_x = float(pts[i][0] - pts[anchor][0])
                vec_y = float(pts[i][1] - pts[anchor][1])
                proj = vec_x * anchor_x + vec_y * anchor_y
                if proj >= 0.0:
                    vec_x = float(pts[i][0] - pts[floater][0])
                    vec_y = float(pts[i][1] - pts[floater][1])
                    seg_len = sqrt(vec_x ** 2 + vec_y ** 2)
                    proj = vec_x * (-anchor_x) + vec_y * (-anchor_y)
                    if proj < 0.0:
                        dist_to_seg = seg_len
                    else:
                        dist_to_seg = sqrt(abs(seg_len ** 2 - proj ** 2))
                    if max_dist < dist_to_seg:
                        max_dist = dist_to_seg
                        farthest = i

            if max_dist <= tolerance:
                keep.add(anchor)
                keep.add(floater)
            else:
                stack.append((anchor, farthest))
                stack.append((farthest, floater))

        keep = list(keep)
        keep.sort()
        return [pts[i] for i in keep]

    def _ruler_move(self, event):
        """Обрабатывает создание и перемещение линейки.

        Args:
            event (tk.Event): Событие перемещения мыши
        """
        if len(self.coords) == 2:
            self.coords += [event.x, event.y]
            self.ruler = self.canvas.create_line(self.coords, tags='ruler', dash=(10, 5),
                                                 width=2,
                                                 arrowshape=(15, 15, 4),
                                                 arrow=tk.BOTH,
                                                 fill='grey50', capstyle='round')
            self.ruler_area = self.canvas.create_polygon(self.coords, tags='ruler', dash=(10, 5), width=2,
                                                         fill='grey90', outline='grey50')
            self.canvas.itemconfigure(self.ruler_area, state='hidden')
            self.ruler_size = self.canvas.create_text(event.x, event.y,
                                                      font='Helvetica 10 bold',
                                                      fill='grey50',
                                                      tags='ruler')
            self.ruler_size_bg = self.canvas.create_rectangle(self.canvas.bbox(self.ruler_size),
                                                              fill='white', outline='grey50',
                                                              tags='ruler')
            self.canvas.tag_raise(self.ruler_size)
            self.ruler_txt = ''
            self.bind('<Key>', self._ruler_scale)
            self.canvas.tag_bind('editor', '<ButtonPress-1>', lambda e: self._ruler_add_point(e))
            self.canvas.tag_unbind('editor', '<B1-Motion>')
            self.canvas.tag_unbind('editor', '<ButtonRelease-1>')
            self.canvas.tag_unbind('editor', '<Shift-B1-Motion>')

            for button in self.panel.winfo_children():
                if 'pressed' in ttk.Button.state(button):
                    self.callback_button = button
                    ttk.Button.state(button, ['!pressed'])
        elif len(self.coords) == 4:
            self.coords = self.coords[:2] + self._check_viewport_borders(event.x, event.y)
            self.canvas.coords(self.ruler, self.coords)
            length = dist(self.coords[2:], self.coords[:2])
            if self.canvas.itemcget(self.ruler_size_bg, 'fill') == 'blue':
                try:
                    true_len = int(self.ruler_txt)
                    self.ruler_scale = true_len / length
                except ValueError:
                    self.ruler_scale = 1.0
                self.ruler_txt = ''
            self._draw_ruler_size(int(length * self.ruler_scale), 'grey50', 'white')
        else:
            self.coords = self.coords[:-2] + self._check_viewport_borders(event.x, event.y)
            self.canvas.coords(self.ruler_area, self.coords)
            self._draw_ruler_area()

    def _ruler_add_point(self, event):
        """Добавляет точку для измерения площади.

        Args:
            event (tk.Event): Событие нажатия мыши
        """
        self.coords += [event.x, event.y]
        if len(self.coords) == 6:
            self.canvas.itemconfigure(self.ruler_area, state='normal')
            self.canvas.itemconfigure(self.ruler, state='hidden')
            self.canvas.tag_bind('editor', '<ButtonPress-3>', lambda e: self._ruler_delete_point(e))
            self.unbind('<Key>')
        self.canvas.coords(self.ruler_area, self.coords)
        self._draw_ruler_area()

    def _ruler_delete_point(self, event):
        """Удаляет последнюю точку измерения площади.

        Args:
            event (tk.Event): Событие нажатия правой кнопки мыши
        """
        self.coords = self.coords[:-4] + [event.x, event.y]
        if len(self.coords) == 4:
            self.canvas.itemconfigure(self.ruler, state='normal')
            self.canvas.itemconfigure(self.ruler_area, state='hidden')
            self.canvas.coords(self.ruler, self.coords)
            length = dist(self.coords[2:], self.coords[:2])
            self._draw_ruler_size(int(length * self.ruler_scale), 'grey50', 'white')
            self.canvas.tag_unbind('editor', '<ButtonPress-3>')
            self.bind('<Key>', self._ruler_scale)
        else:
            self.canvas.coords(self.ruler_area, self.coords)
            self._draw_ruler_area()

    def _draw_ruler_area(self):
        """Рассчитывает и отображает площадь измеряемой области."""
        vertices = [(self.coords[i], self.coords[i + 1]) for i in range(0, len(self.coords), 2)]
        polygon = Polygon(vertices)
        if polygon.is_simple:
            self.canvas.itemconfigure(self.ruler_size, state='normal')
            self.canvas.itemconfigure(self.ruler_size_bg, state='normal')
            self.canvas.itemconfigure(self.ruler_area, fill='grey90')
            self._draw_ruler_size(f'S = {int(polygon.area * self.ruler_scale ** 2):_}'.replace('_', ' '),
                                  'grey50', 'grey95')
        else:
            self.canvas.itemconfigure(self.ruler_size, state='hidden')
            self.canvas.itemconfigure(self.ruler_size_bg, state='hidden')
            self.canvas.itemconfigure(self.ruler_area, fill='')

    def _draw_ruler_size(self, text, text_color, bg_color):
        """Обновляет отображение размеров линейки.

        Args:
            text (int|str): Значение для отображения
            text_color (str): Цвет текста
            bg_color (str): Цвет фона
        """
        self.canvas.itemconfigure(self.ruler_size, text=text, fill=text_color)
        self.canvas.itemconfigure(self.ruler_size_bg, fill=bg_color)
        x = sum(self.coords[::2]) / (len(self.coords) // 2)
        y = sum(self.coords[1::2]) / (len(self.coords) // 2)
        self.canvas.coords(self.ruler_size, x, y)
        self.canvas.coords(self.ruler_size_bg, self._offset_bbox(self.canvas.bbox(self.ruler_size), 3))

    def _ruler_scale(self, event):
        """Изменяет масштаб линейки вводом значений с клавиатуры.

        Args:
            event (tk.Event): Событие клавиатуры
        """
        if event.char in '0123456789':
            self.ruler_txt += event.char
        elif event.keysym == 'BackSpace':
            self.ruler_txt = self.ruler_txt[:-1]
        elif event.keysym == 'Return':
            length = dist(self.coords[2:], self.coords[:2])
            try:
                true_len = int(self.ruler_txt)
                self.ruler_scale = true_len / length
            except ValueError:
                self.ruler_scale = 1.0
            self.ruler_txt = ''
            self._draw_ruler_size(int(length * self.ruler_scale), 'grey50', 'white')
            return
        else:
            return
        self._draw_ruler_size(self.ruler_txt, 'white', 'blue')

    def _ruler_stop(self):
        """Завершает работу с инструментом 'Линейка'."""
        self.canvas.delete('ruler')
        self.bind('<Key>', lambda e: self._set_color(e.char) if e.char in '1234567890' else None)
        self.canvas.tag_unbind('editor', '<ButtonPress-3>')
        if self.callback_button:
            self.callback_button.invoke()
            self.callback_button = None

    @staticmethod
    def _offset_bbox(bbox, offset):
        """Расширяет bounding box на заданное расстояние.

        Args:
            bbox (tuple): Координаты (x1,y1,x2,y2)
            offset (int): Величина расширения

        Returns:
            tuple: Новые координаты
        """
        x1, y1, x2, y2 = bbox
        return (x1 - offset,
                y1 - offset,
                x2 + offset,
                y2 + offset)

    def _set_line(self):
        """Активирует инструмент 'Линия' для рисования прямых с настраиваемым стилем."""
        self.canvas.tag_bind('editor', '<ButtonPress-1>', lambda e: self._new_item(e))
        self.canvas.tag_bind('editor', '<B1-Motion>', lambda e: self._line_move(e))
        self.canvas.tag_bind('editor', '<Shift-B1-Motion>', lambda e: self._line_angle_move(pi / 8, e))
        self.canvas.tag_unbind('editor', '<ButtonRelease-1>')
        self.canvas.tag_bind('editor', '<ButtonRelease-1>', lambda e: self.canvas.unbind('<MouseWheel>'))
        self._set_selection(self.line_button)

    def _line_change(self, event):
        """Изменяет стиль линии колесом мыши.

        Args:
            event (tk.Event): Событие колеса мыши
        """
        dashes = ['', '255', '1', '1 1 1 1', '1 1 1']
        dash = dashes.index(self.canvas.itemcget(self.line, 'dash'))
        dash += 1 if event.delta > 0 else -1
        self.canvas.itemconfigure(self.line, dash=dashes[dash % len(dashes)])

    def _line_move(self, event):
        """Обрабатывает создание и перемещение линии.

        Args:
            event (tk.Event): Событие перемещения мыши
        """
        if len(self.coords) == 2:
            self.coords += [event.x, event.y]
            self.line = self.canvas.create_line(self.coords, tags=['editor', 'item'],
                                                fill=self.color_panel['background'],
                                                width=5, capstyle='round')
            self.canvas.tag_bind(self.line, '<ButtonPress-3>', partial(self.canvas.delete, self.line))
            self.canvas.bind('<MouseWheel>', lambda e: self._line_change(e))
        else:
            self.coords = self.coords[:2] + self._check_viewport_borders(event.x, event.y)
            self.canvas.coords(self.line, self.coords)

    def _line_angle_move(self, angle, event):
        """Рисует линию под фиксированными углами (с зажатым Shift).

        Args:
            angle (float): Шаг угла в радианах
            event (tk.Event): Событие перемещения мыши
        """
        if len(self.coords) == 2:
            self.coords += [event.x, event.y]
            self.line = self.canvas.create_line(self.coords, tags=['editor', 'item'],
                                                fill=self.color_panel['background'],
                                                width=5, capstyle='round')
            self.canvas.tag_bind(self.line, '<ButtonPress-3>', partial(self.canvas.delete, self.line))
        else:
            x1, y1 = self.coords[:2]
            x2, y2 = event.x, event.y
            alpha = (atan2(x2 - x1, y2 - y1) + angle / 2) // angle * angle
            length = sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
            x2 = int(x1 + length * sin(alpha))
            y2 = int(y1 + length * cos(alpha))
            self.coords = [x1, y1, *self._check_viewport_borders(x2, y2)]
            self.canvas.coords(self.line, self.coords)

    @staticmethod
    def _round_rectangle(coords, radius=13):
        """Генерирует координаты для прямоугольника со скругленными углами.

        Args:
            coords (list): Координаты (x1,y1,x2,y2)
            radius (int): Радиус скругления

        Returns:
            list: Координаты для создания фигуры
        """
        x1, y1, x2, y2 = coords

        x1, x2 = (x2, x1) if x2 < x1 else (x1, x2)
        y1, y2 = (y2, y1) if y2 < y1 else (y1, y2)
        radius = min((x2 - x1) // 2, (y2 - y1) // 2, radius)

        return [x1, y1,
                x1 + radius, y1, x1 + radius, y1, x2 - radius, y1, x2 - radius, y1,
                x2, y1,
                x2, y1 + radius, x2, y1 + radius, x2, y2 - radius, x2, y2 - radius,
                x2, y2,
                x2 - radius, y2, x2 - radius, y2, x1 + radius, y2, x1 + radius, y2,
                x1, y2,
                x1, y2 - radius, x1, y2 - radius, x1, y1 + radius, x1, y1 + radius,
                x1, y1]

    def _set_rect(self):
        """Активирует инструмент 'Рамка' для рисования прямоугольников со скругленными углами."""
        self.canvas.tag_bind('editor', '<ButtonPress-1>', lambda e: self._new_item(e))
        self.canvas.tag_bind('editor', '<B1-Motion>', lambda e: self._rect_move(e))
        self.canvas.tag_unbind('editor', '<ButtonRelease-1>')
        self.canvas.tag_unbind('editor', '<Shift-B1-Motion>')
        self.canvas.tag_bind('editor', '<ButtonRelease-1>', lambda e: self.canvas.unbind('<MouseWheel>'))
        self._set_selection(self.rect_button)

    def _rect_move(self, event):
        """Обрабатывает создание и перемещение прямоугольника.

        Args:
            event (tk.Event): Событие перемещения мыши
        """
        if len(self.coords) == 2:
            self.coords += [event.x, event.y]
            self.rect_corner = 13
            self.rect = self.canvas.create_line(self._round_rectangle(self.coords), smooth=True,
                                                fill=self.color_panel['background'], tags=['editor', 'item'], width=5)
            self.canvas.tag_bind(self.rect, '<ButtonPress-3>', partial(self.canvas.delete, self.rect))
            self.canvas.bind('<MouseWheel>', lambda e: self._rect_corner_change(e))
        else:
            self.coords = self.coords[:2] + self._check_viewport_borders(event.x, event.y)
            self.canvas.coords(self.rect, self._round_rectangle(self.coords, self.rect_corner))

    def _rect_corner_change(self, event):
        """Изменяет радиус скругления углов колесом мыши.

        Args:
            event (tk.Event): Событие колеса мыши
        """
        if event.delta < 0:
            self.rect_corner = max(self.rect_corner - ((self.rect_corner // 10) + 1), 0)
        else:
            self.rect_corner += (self.rect_corner // 10) + 1
            x1, y1, x2, y2 = self.coords
            self.rect_corner = min(abs(x2 - x1) // 2, abs(y2 - y1) // 2, self.rect_corner)
        self.canvas.coords(self.rect, self._round_rectangle(self.coords, self.rect_corner))

    def _set_text(self):
        """Активирует инструмент 'Надпись' для добавления текстовых аннотаций."""
        self.canvas.tag_bind('editor', '<ButtonPress-1>', lambda e: self._text_create(e))
        self.canvas.tag_bind('editor', '<B1-Motion>', lambda e: self._text_resize_bg(e))
        self.canvas.tag_bind('editor', '<ButtonRelease-1>', lambda e: self._text_start(e))
        self.canvas.tag_unbind('editor', '<Shift-B1-Motion>')
        self._set_selection(self.text_button)

    def _text_create(self, event):
        """Инициализирует создание текстового блока.

        Args:
            event (tk.Event): Событие нажатия мыши
        """
        if self.text_edit:
            self._text_stop()

        self.txt_tag = 0
        while self.canvas.find_withtag(f'txt{self.txt_tag}') != ():
            self.txt_tag += 1
        height = font.Font(font=f'Helvetica {self.font_size} bold').metrics('linespace') // 2
        width = font.Font(font=f'Helvetica {self.font_size} bold').measure('|')
        self.alpha = 0.8
        self._create_txt_bg(self._offset_bbox((event.x, event.y - height, event.x + width, event.y + height), 3),
                            'white', self.alpha)
        self._check_viewport_borders(event.x - 3, event.y - height)
        self._check_viewport_borders(event.x + width + 3, event.y + height)
        self.coords = [event.x, event.y, 0, 0]
        self.canvas.bind('<MouseWheel>', lambda e: self._alpha_change(e))
        self.unbind('<Escape>')

    def _text_start(self, event):
        """Активирует редактирование текста после создания блока.

        Args:
            event (tk.Event): Событие отпускания мыши
        """
        self.bind('<Key>', self._key_handler)
        self.bind('<Control-Key>', self._key_control_handler)
        self.bind('<Control-MouseWheel>', lambda e: self._mouse_control_wheel_handler(e))
        self.canvas.unbind('<MouseWheel>')
        self.txt = ''
        height = font.Font(font=f'Helvetica {self.font_size} bold').metrics('linespace') // 2
        self.coords[1] -= height if self.coords[2:] == [0, 0] else 0
        x, y  = self._check_viewport_borders(min(self.coords[0], event.x), min(self.coords[1], event.y))
        self.text = self.canvas.create_text(x, y, anchor='nw',
                                            text=self.txt, font=f'Helvetica {self.font_size} bold',
                                            fill=self.color_panel['background'],
                                            tags=['editor', f'txt{self.txt_tag}', 'item'])
        self.text_cursor = self.canvas.create_text(x, y, anchor='nw',
                                                   text='|', font=f'Helvetica {self.font_size} bold',
                                                   fill='grey50', tags=[f'txt{self.txt_tag}', 'service'])
        self.coords = [x, y, max(self.coords[0], self.coords[2]), max(self.coords[1], self.coords[3])]
        if self.lock_viewport:
            self.canvas.itemconfigure(self.text, width=self.canvas.bbox(self.viewport)[2] - self.coords[0] - 3)
        else:
            self.canvas.itemconfigure(self.text, width=self.winfo_width() - self.coords[0] - 3)
        self.canvas.tag_bind(f'txt{self.txt_tag}', '<ButtonPress-3>',
                             partial(self.canvas.delete, f'txt{self.txt_tag}'))
        self.text_edit = True
        self._blink_cursor()

    def _text_resize_bg(self, event):
        """Изменяет размер фона текстового блока.

        Args:
            event (tk.Event): Событие перемещения мыши
        """
        x1, y1 = self.coords[:2]
        x2, y2 = self._check_viewport_borders(event.x, event.y)

        x2, x1 = (x1, x2) if x2 < x1 else (x2, x1)
        y2, y1 = (y1, y2) if y2 < y1 else (y2, y1)

        del self.image_stack[-1]
        self._create_txt_bg(self._offset_bbox((x1, y1, x2, y2), 3), 'white', self.alpha)

        self.coords[2] = x2
        self.coords[3] = y2

    def _alpha_change(self, event):
        """Изменяет прозрачность фона текстового блока колесом мыши.

        Args:
            event (tk.Event): Событие колеса мыши
        """
        self.alpha = min(self.alpha + 0.1, 1) if event.delta > 0 else max(self.alpha - 0.1, 0)
        x1, y1 = self.coords[:2]
        x2, y2 = event.x, event.y
        x2, x1 = (x1, x2) if x2 < x1 else (x2, x1)
        y2, y1 = (y1, y2) if y2 < y1 else (y2, y1)
        del self.image_stack[-1]
        self._create_txt_bg(self._offset_bbox((x1, y1, x2, y2), 3), 'white', self.alpha)

    def _create_txt_bg(self, bbox, color, alpha):
        """Создает полупрозрачный фон для текстового блока.

        Args:
            bbox (tuple): Координаты области (x1,y1,x2,y2)
            color (str): Цвет фона
            alpha (float): Уровень прозрачности (0-1)
        """
        x1, y1, x2, y2 = bbox
        alpha = int(alpha * 255)
        fill = self.winfo_rgb(color) + (alpha,)
        self.txt_bg_image = Image.new('RGBA', (int(x2 - x1), int(y2 - y1)))
        draw = ImageDraw.Draw(self.txt_bg_image)
        draw.rounded_rectangle(((0, 0), (int(x2 - x1), int(y2 - y1))), 6, fill=fill, outline=fill)
        self.image_stack.append(ImageTk.PhotoImage(self.txt_bg_image))
        self.canvas.create_image(x1, y1, image=self.image_stack[-1], anchor='nw',
                                 tags=['editor', f'txt{self.txt_tag}', f'txt{self.txt_tag}_bg', 'item'])
        self.canvas.tag_lower(f'txt{self.txt_tag}_bg', f'txt{self.txt_tag}')

    def _move_txt(self, direction, step=1):
        """Перемещает текстовый блок с заданным шагом.

        Args:
            direction (str): Направление ('Up','Down','Left','Right')
            step (int): Величина перемещения
        """
        bounds = self.canvas.bbox(self.text)
        x1, y1, x2, y2 = (bounds[0], bounds[1], max(self.coords[2], bounds[2]), max(self.coords[3], bounds[3]))
        if self.lock_viewport:
            x_min, y_min, x_max, y_max = self.canvas.bbox(self.viewport)
        else:
            x_min, x_max = 0, self.winfo_width()
            y_min, y_max = 0, self.winfo_height()
        if direction == 'Up' and y1 - step > y_min:
            y1 -= step
            self.coords[3] -= step
        elif direction == 'Down' and y2 + step < y_max:
            y1 += step
            self.coords[3] += step
        elif direction == 'Left' and x1 - step > x_min:
            x1 -= step
            self.coords[2] -= step
        elif direction == 'Right' and x2 + step < x_max:
            x1 += step
            self.coords[2] += step

        self.canvas.moveto(self.text, x1, y1)
        self.canvas.itemconfig(self.text, width=self.winfo_width() - x1)
        self.coords[0] = x1
        self.coords[1] = y1

    def _update_cursor_position(self):
        """Обновляет позицию текстового курсора согласно текущему тексту."""
        max_width = int(self.canvas.itemcget(self.text, 'width'))
        line, lines = '', []

        for char in self.txt:
            line += char
            if font.Font(font=f'Helvetica {self.font_size} bold').measure(line) > max_width or char == '\n':
                lines.append(line[:-1])
                line = char if char != '\n' else ''
        lines.append(line)

        line_width = font.Font(font=f'Helvetica {self.font_size} bold').measure(lines[-1])
        line_height = font.Font(font=f'Helvetica {self.font_size} bold').metrics('linespace')

        x = self.coords[0] + line_width
        y = self.coords[1] + line_height * (len(lines)-1)
        self.canvas.coords(self.text_cursor, x, y)
        self.canvas.itemconfig(self.text_cursor, font=f'Helvetica {self.font_size} bold')

    def _blink_cursor(self):
        """Реализует мигание текстового курсора."""
        if self.text_edit:
            self.cursor_visible = not self.cursor_visible
            self.canvas.itemconfigure(self.text_cursor, state='normal' if self.cursor_visible else 'hidden')
            self.is_blinking = self.after(500, self._blink_cursor)
        else:
            self.after_cancel(self.is_blinking)
            self.is_blinking = None

    def _redraw_text(self):
        """Перерисовывает текстовый блок при изменениях."""
        if not self.text:
            return
        bounds = self.canvas.bbox(self.text)
        bounds = (bounds[0], bounds[1], max(self.coords[2], bounds[2]), max(self.coords[3], bounds[3]))
        self._check_viewport_borders(bounds[0] - 3, bounds[1] - 3)
        self._check_viewport_borders(bounds[2] + 3, bounds[3] + 3)
        del self.image_stack[-1]
        self._create_txt_bg(self._offset_bbox(bounds, 3), 'white', self.alpha)
        self._update_cursor_position()

    def _key_handler(self, event):
        """Обрабатывает ввод текста и специальные клавиши.

        Args:
            event (tk.Event): Событие клавиатуры
        """
        if event.keysym == 'BackSpace':
            self.txt = self.txt[:-1]
        elif event.keysym == 'Escape':
            self._text_stop()
            return
        elif event.keysym in ['Control_L', 'Control_R']:
            return
        elif event.keysym in ['Up', 'Down', 'Left', 'Right']:
            self._move_txt(event.keysym)
        elif event.keysym == 'Return':
            self.txt += '\n'
        elif event.keysym == 'Tab':
            pass
        else:
            self.txt = self.txt + event.char

        if self.lock_viewport:
            line, lines = '', []
            max_width = int(self.canvas.itemcget(self.text, 'width'))

            for char in self.txt:
                line += char
                if font.Font(font=f'Helvetica {self.font_size} bold').measure(line) > max_width or char == '\n':
                    lines.append(line[:-1])
                    line = char if char != '\n' else ''
            lines.append(line)
            line_height = font.Font(font=f'Helvetica {self.font_size} bold').metrics('linespace')

            if self.y2 < self.coords[1] + line_height * len(lines) + 3:
                self.txt = self.txt[:-1]

        self.canvas.itemconfig(self.text, text=self.txt)
        self._redraw_text()

    def _key_control_handler(self, event):
        """Обрабатывает комбинации клавиш для управления текстом.

        Args:
            event (tk.Event): Событие клавиатуры
        """
        if event.keysym == 'Return':
            self._text_stop()
            return
        elif event.keycode in [109, 189]:
            self.font_size = self.font_size - 1 if self.font_size > 9 else 9
        elif event.keycode in [107, 187]:
            self.font_size = self.font_size + 1 if self.font_size < 25 else 25
        elif event.keysym in ['Up', 'Down', 'Left', 'Right']:
            self._move_txt(event.keysym, step=10)

        self.canvas.itemconfig(self.text, font=f'Helvetica {self.font_size} bold')
        self._redraw_text()

    def _mouse_control_wheel_handler(self, event):
        """Изменяет размер шрифта колесом мыши с зажатым Ctrl.

        Args:
            event (tk.Event): Событие колеса мыши
        """
        self.font_size = min(self.font_size + 1, 25) if event.delta > 0 else max(self.font_size - 1, 9)
        self.canvas.itemconfig(self.text, font=f'Helvetica {self.font_size} bold')
        self._redraw_text()

    def _text_stop(self):
        """Завершает редактирование текста."""
        self.bind('<Key>', lambda e: self._set_color(e.char) if e.char in '1234567890' else None)
        self.unbind('<Control-MouseWheel>')
        self.bind('<Control-KeyPress>', lambda e: self._control(e))
        self.bind('<Escape>', lambda e: self.destroy())
        if self.txt == '':
            self.canvas.delete(f'txt{self.txt_tag}')
        self.text_edit = False
        try:
            self.canvas.delete(self.text_cursor)
        except AttributeError:
            pass

    def _set_blur(self):
        """Активирует инструмент 'Размытие' для скрытия конфиденциальных областей."""
        self.canvas.tag_bind('editor', '<ButtonPress-1>', lambda e: self._blur_create(e))
        self.canvas.tag_bind('editor', '<B1-Motion>', lambda e: self._blur_move(e))
        self.canvas.tag_bind('editor', '<ButtonRelease-1>', lambda e: self.canvas.unbind('<MouseWheel>'))
        self.canvas.tag_unbind('editor', '<Shift-B1-Motion>')
        self._set_selection(self.blur_button)

    def _blur_create(self, event):
        """Инициализирует создание размытой области.

        Args:
            event (tk.Event): Событие нажатия мыши
        """
        self.coords = event.x, event.y
        blur_area = self.blur_image.crop(self.coords * 2)
        self.image_stack.append(ImageTk.PhotoImage(blur_area))
        self.blur = self.canvas.create_image(event.x, event.y, anchor='nw', image=self.image_stack[-1],
                                             tags=['editor', 'item'])
        self.canvas.tag_raise(self.blur, self.viewport)
        self.canvas.bind('<MouseWheel>', lambda e: self._blur_change(e))
        self.canvas.tag_bind(self.blur, '<ButtonPress-3>', partial(self.canvas.delete, self.blur))
        self.blur_radius = 5
        self.blur_image = self.image.filter(ImageFilter.GaussianBlur(self.blur_radius))

    def _blur_move(self, event):
        """Изменяет размер и положение размытой области.

        Args:
            event (tk.Event): Событие перемещения мыши
        """
        x1, y1 = self.coords
        x2, y2 = self._check_viewport_borders(event.x, event.y)

        anchor = 's' if y2 < y1 else 'n'
        anchor += 'e' if x2 < x1 else 'w'

        x2, x1 = (x1, x2) if x2 < x1 else (x2, x1)
        y2, y1 = (y1, y2) if y2 < y1 else (y2, y1)

        blur_area = self.blur_image.crop((x1, y1, x2, y2))
        self.image_stack[-1] = ImageTk.PhotoImage(blur_area)
        self.canvas.itemconfig(self.blur, anchor=anchor, image=self.image_stack[-1], tags=['editor', 'item'])

    def _blur_change(self, event):
        """Изменяет интенсивность размытия колесом мыши.

        Args:
            event (tk.Event): Событие колеса мыши
        """
        self.blur_radius = min(self.blur_radius + 1, 10) if event.delta > 0 else max(self.blur_radius - 1, 1)
        self.blur_image = self.image.filter(ImageFilter.GaussianBlur(self.blur_radius))
        self._blur_move(event)

    def _set_number(self):
        """Активирует инструмент 'Нумерация' для создания нумерованных меток."""
        self.canvas.tag_bind('editor', '<ButtonPress-1>', lambda e: self._number_create(e))
        self.canvas.tag_bind('editor', '<B1-Motion>', lambda e: self._number_move(e))
        self.canvas.tag_bind('editor', '<ButtonRelease-1>', lambda e: self._number_set())
        self.canvas.tag_unbind('editor', '<Shift-B1-Motion>')
        self._set_selection(self.num_button)

    def _number_create(self, event):
        """Создает нумерованную метку в указанной позиции.

        Args:
            event (tk.Event): Событие нажатия мыши
        """
        tag = '_' + str(self.num)
        while self.canvas.find_withtag(tag) != ():
            tag = tag + '_' + str(self.num)

        r = 20
        x = max(self.canvas.bbox(self.viewport)[0] + r, min(event.x, self.canvas.bbox(self.viewport)[2] - r))
        y = max(self.canvas.bbox(self.viewport)[1] + r, min(event.y, self.canvas.bbox(self.viewport)[3] - r))

        color = self.canvas.itemcget('z_33', 'fill')
        color = color if self.canvas.itemcget('z_33', 'state') != 'hidden' else self.color_panel['background']

        self.number_arrow = self.canvas.create_line(x, y, x, y,
                                                    fill=color,
                                                    arrow=tk.LAST,
                                                    tags=[tag, 'editor', 'item'])
        self.number_circle = self.canvas.create_oval(x - r, y - r, x + r, y + r,
                                                     fill=color,
                                                     outline=color,
                                                     tags=[tag, 'editor', 'item'])
        red, green, blue = self.winfo_rgb(color)
        luminance = red / 257 * 0.2126 + green / 257 * 0.7152 + blue / 257 * 0.0722
        text_color = 'black' if luminance > 140 else 'white'
        self.number_txt = self.canvas.create_text(x, y, text=self.num, fill=text_color,
                                                  anchor='center', font='Helvetica 18 bold',
                                                  tags=[tag, 'editor', 'item'])
        self.canvas.tag_bind(tag, '<ButtonPress-3>', partial(self._number_delete, tag))
        self.canvas.bind('<MouseWheel>', lambda e: self._num_change(e))

    def _number_move(self, event):
        """Изменяет положение указателя нумерованной метки.

        Args:
            event (tk.Event): Событие перемещения мыши
        """
        x1, y1, *_ = self.canvas.coords(self.number_arrow)
        x2, y2 = self._check_viewport_borders(event.x, event.y)

        length = sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        self.canvas.itemconfig(self.number_arrow, arrowshape=(length, length, 20), fill=self.color_panel['background'])
        self.canvas.itemconfig(self.number_circle, fill=self.color_panel['background'],
                               outline=self.color_panel['background'])
        self.canvas.coords(self.number_arrow, x1, y1, x2, y2)

    def _num_change(self, event):
        """Изменяет номер метки колесом мыши.

        Args:
            event (tk.Event): Событие колеса мыши
        """
        self.num = self.num + 1 if event.delta > 0 else max(self.num - 1, 1)
        self.num_button['text'] = self.num
        tag = '_' + str(self.num)
        while self.canvas.find_withtag(tag) != ():
            tag = tag + '_' + str(self.num)
        self.canvas.itemconfig(self.number_txt, text=self.num, tags=[tag, 'editor', 'item'])
        self.canvas.itemconfig(self.number_arrow, tags=[tag, 'editor', 'item'])
        self.canvas.itemconfig(self.number_circle, tags=[tag, 'editor', 'item'])
        self.canvas.tag_bind(tag, '<ButtonPress-3>', partial(self._number_delete, tag))

    def _number_set(self):
        """Фиксирует созданную нумерованную метку. Добавляет счетчик на кнопке"""
        self.num += 1
        self.num_button['text'] = self.num
        self.canvas.unbind('<MouseWheel>')

    def _number_delete(self, tag, _):
        """Удаляет нумерованную метку по тегу.

        Args:
            tag (str): Идентификатор метки
        """
        self.canvas.delete(tag)
        self.num = int(tag.split('_')[-1])
        self.num_button['text'] = self.num

    def _change_number(self, event):
        """Изменяет текущий номер для инструмента нумерации.

        Args:
            event (tk.Event): Событие колеса мыши
        """
        if event.delta > 0:
            self.num += 1
        elif self.num > 1:
            self.num -= 1
        self.num_button['text'] = self.num
        self._set_number()

    def _change_color(self, event):
        """Изменяет активный цвет колесом мыши.

        Args:
            event (tk.Event): Событие колеса мыши
        """
        self.color += 1 if event.delta > 0 else -1
        self.color_panel['background'] = self.palette[self.color % 9]
        if self.text_edit:
            self.canvas.itemconfig(self.text, fill=self.palette[self.color % 9])

    def _recognize(self):
        """Распознает текст и QR-коды в выделенной области с помощью Tesseract OCR и pyzbar."""
        data = []
        qr_codes = decode(self.screenshot_area)
        if qr_codes:
            for qr_code in qr_codes:
                draw = ImageDraw.Draw(self.screenshot_area)
                x1 = qr_code.rect.left
                y1 = qr_code.rect.top
                x2 = x1 + qr_code.rect.width
                y2 = y1 + qr_code.rect.height
                draw.rectangle((x1, y1, x2, y2), fill='black', outline='black', width=5)
                data.append({'tab': qr_code.type, 'data': codecs.decode(qr_code.data)})

        txt = pytesseract.image_to_string(self.screenshot_area, lang='rus+eng', config=r'--oem 3 --psm 6').strip()
        if txt != '' or data == []:
            data.insert(0, {'tab': 'Текст', 'data': txt})

        bbox = self.canvas.bbox(self.viewport)
        self.panel_hint.hide()
        self.destroy()
        Notepad(data, bbox).mainloop()

    def _done(self):
        """Завершает редактирование: сохраняет в буфер обмена или экспортирует в файл."""
        self.canvas.delete('service')
        self.canvas.update()
        image = ImageGrab.grab(bbox=self.canvas.bbox(self.viewport))
        copy_to_clipboard = self.done_button['text'] == 'Ok'
        self.destroy()
        if copy_to_clipboard:
            with BytesIO() as output:
                image.convert('RGB').save(output, 'BMP')
                data = output.getvalue()[14:]
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
            win32clipboard.CloseClipboard()
        else:
            desktop_folder = os.path.join(os.environ['USERPROFILE'], 'Desktop')
            file_name = f'Снимок экрана {time.strftime('%d-%m-%Y %H%M%S')}'
            if file := filedialog.asksaveasfilename(defaultextension='.png',
                                                    filetypes=[('Portable Network Graphics', '*.png')],
                                                    initialdir=desktop_folder,
                                                    initialfile=file_name):
                image.save(file)


class Notepad(tk.Tk):
    """Окно для работы с распознанным текстом и данными QR-кодов.

    Attributes:
        tabs (ttk.Notebook): Контейнер вкладок для разных типов данных
        text (ScrolledText): Основной текстовый редактор
        data (list): Список распознанных данных (текст + QR-коды)
        context_menu (tk.Menu): Контекстное меню для текста
    """
    class Link:
        """Класс для работы с гиперссылками в тексте.

        Args:
            widget (tk.Text): Текстовый виджет
            x (int): Координата X клика
            y (int): Координата Y клика
        """
        def __init__(self, widget, x, y):
            position = f'@{x},{y}'
            index = f'{widget.index(position)}+1c'
            self.range = widget.tag_prevrange('link', index)
            self.url = widget.get(*self.range)

    def __init__(self, data, bbox):
        """Инициализирует окно редактора с распознанными данными."""
        tk.Tk.__init__(self)
        self.title('SilentScreenShoter — Буфер обмена')
        self.geometry(f'{bbox[2] - bbox[0]}x{bbox[3] - bbox[1]}+{bbox[0]}+{bbox[1] - 22}')
        self.protocol('WM_DELETE_WINDOW', self._on_destroy)
        self.data = data

        if len(self.data) > 1:
            self.tabs = ttk.Notebook()
            for record in self.data:
                self.tabs.add(tk.Frame(self.tabs), text=record['tab'])
                self.tabs.pack(fill='x', side='top')
            self.tabs.bind('<<NotebookTabChanged>>', lambda e: self._tab_change())

        self.text = sText(wrap='word', font='Consolas 11', undo=True, height=1)
        self.text.pack(fill='both', expand=True, side='top')

        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label='Выбрать всё', accelerator='Ctrl+A')
        self.context_menu.add_separator()
        self.context_menu.add_command(label='Вырезать', accelerator='Ctrl+X')
        self.context_menu.add_command(label='Копировать', accelerator='Ctrl+C')
        self.context_menu.add_command(label='Вставить', accelerator='Ctrl+V')
        self.context_menu.add_separator()
        self.context_menu.add_command(label='Поиск в Яндекс')

        self.context_menu.entryconfigure('Выбрать всё', command=lambda: self.text.event_generate('<<SelectAll>>'))
        self.context_menu.entryconfigure('Вырезать', command=lambda: self.text.event_generate('<<Cut>>'))
        self.context_menu.entryconfigure('Копировать', command=lambda: self.text.event_generate('<<Copy>>'))
        self.context_menu.entryconfigure('Вставить', command=lambda: self.text.event_generate('<<Paste>>'))

        self.text.bind('<Button-3>', self._context_menu)
        self.text.bind('<Shift-F3>', lambda e: self._change_case())
        self.text.bind('<Control-KeyPress>', lambda e: self._control_handler(e))
        self.text.bind('<Escape>', lambda e: self._on_destroy())
        self.text.bind('<KeyPress>', lambda e: self._key_handler(e))
        self.text.bind('<KeyRelease>', lambda e: self._recognize_links())

        self.current_tab = 0
        self.text.insert('1.0', data[self.current_tab]['data'])
        self._recognize_links()

        self.results = tk.Label()
        self.find_window = tk.Entry()
        self.find_window.bind('<KeyRelease>', lambda e: self._highlight_matches())
        self.find_window.bind('<Escape>', lambda e: self._close_find())
        self.find_window.bind('<Control-KeyPress>', lambda e: self._close_find() if e.keycode == 70 else None)

        self.text.tag_config('link', foreground='black', underline=True)
        self.text.tag_bind('link', '<Button-1>', lambda e: self._open_link(e))
        self.text.tag_bind('link', '<Enter>', lambda e: self._on_enter_link(e))
        self.text.tag_bind('link', '<Leave>', lambda e: self._on_leave_link())

        self.text.tag_config('hover', foreground='blue', underline=True)
        self.text.tag_config('highlight', background='yellow')

        self.text.focus_force()
        self.update()

    def _control_handler(self, event):
        """Обрабатывает сочетания клавиш для управления редактором.

        Args:
            event (tk.Event): Событие клавиатуры
        """
        if event.keycode == 70:  # Ctrl+F
            self._find_text()
        elif event.keycode == 74:  # Ctrl+J
            self._remove_line_breaks()

    def _remove_line_breaks(self):
        """Удаляет переносы строк в выделенном тексте (Ctrl+J)."""
        try:
            sel_start, sel_end = self.text.tag_ranges('sel')
            selected_text = self.text.get(sel_start, sel_end)
            replace_text = selected_text.replace('\n', ' ')
            self.text.replace(sel_start, sel_end, replace_text)
        except ValueError:
            pass

    def _find_text(self):
        """Активирует панель поиска текста (Ctrl+F)."""
        self.find_window.pack(side='right', padx=5, pady=5)
        self.results.pack(side='right', padx=5, pady=5)
        if sel_range := self.text.tag_ranges('sel'):
            self.find_window.delete(0, 'end')
            self.find_window.insert(0, self.text.get(*sel_range))
        self.find_window.select_range(0, 'end')
        self.find_window.focus_set()
        self.find_window.icursor('end')

    def _close_find(self):
        """Закрывает панель поиска (Esc или Ctrl+F)."""
        self.find_window.pack_forget()
        self.results.pack_forget()
        self.results.configure(text='')
        self.text.tag_remove('highlight', '1.0', 'end')
        self.text.focus_set()

    def _highlight_matches(self):
        """Подсвечивает совпадения при поиске, и показывает статистику."""
        def get_plural(amount, variants):
            """Возвращает правильную форму слова для числа.

            Args:
                amount (int): Количество
                variants (list): Варианты форм (ед.ч., мн.ч., мн.ч. (для 5+))

            Returns:
                str: Строка с числом и правильной формой слова
            """
            assert len(variants) == 3
            if amount % 10 == 1 and amount % 100 != 11:
                plural = variants[0]
            elif 2 <= amount % 10 <= 4 and (amount % 100 < 10 or amount % 100 >= 20):
                plural = variants[1]
            else:
                plural = variants[2]
            return f'{amount} {plural}'

        try:
            self.find_window.pack_info()
        except tk.TclError:
            return
        finally:
            self.text.tag_remove('highlight', '1.0', 'end')

        text_to_find = self.find_window.get()
        if text_to_find == '':
            self.results.configure(text='')
            return
        start_idx = '1.0'
        result = 0
        while True:
            start_idx = self.text.search(text_to_find, start_idx, nocase=True, stopindex='end')
            if start_idx:
                end_idx = f'{start_idx}+{len(text_to_find)}c'
                self.text.tag_add('highlight', start_idx, end_idx)
                start_idx = end_idx
                result += 1
            else:
                break

        if result != 0:
            self.results['text'] = f'Найдено {get_plural(result, ['совпадение', 'совпадения', 'совпадений'])}'
            self.find_window['foreground'] = 'black'
        else:
            self.results['text'] = ''
            self.find_window['foreground'] = 'red'

    @staticmethod
    def _layout():
        """Определяет текущую раскладку клавиатуры.

        Returns:
            str: Код раскладки ('ru' или 'en')
        """
        user32_dll = ctypes.windll.LoadLibrary('user32.dll')
        func_ptr = user32_dll.GetKeyboardLayout
        code_page = hex(func_ptr(0))
        layouts = {'0x4190419': 'ru',
                   '0x4090409': 'en'}
        layout = layouts[code_page] if code_page in layouts else None
        return layout

    def _key_handler(self, event):
        """Обрабатывает специальные символы, автозамену кавычек, закрытие скобок.

        Args:
            event (tk.Event): Событие клавиатуры
        """
        position = self.text.index('insert')
        try:
            sel_start, sel_end = self.text.tag_ranges('sel')
            selected_text = self.text.get(sel_start, sel_end)
            if event.char == '"':
                if self._layout() in ['ru',]:
                    replace_text = f'«{selected_text}»'
                else:
                    replace_text = f'"{selected_text}"'
            elif event.char == "'":
                replace_text = f"'{selected_text}'"
            elif event.char in ['{', '}']:
                replace_text = f'{{{selected_text}}}'
            elif event.char in ['[', ']']:
                replace_text = f'[{selected_text}]'
            elif event.char in ['(', ')']:
                replace_text = f'({selected_text})'
            else:
                return
            self.text.replace(sel_start, sel_end, replace_text)
            self.text.tag_add('sel', f'{sel_start}+1c', f'{sel_end}+1c')
            self.text.mark_set('insert', f'{position}+1c')
            return 'break'
        except ValueError:
            if event.char == '"' and self._layout() in ['ru',]:
                char_left = ord(self.text.get(f'{position}-1c'))
                char_right = ord(self.text.get(f'{position}'))
                if char_left in [10, 32, 9] or position == '1.0':  # Enter, Space, Tab, First letter
                    self.text.insert(position, chr(171))  # «
                    return 'break'
                elif char_right in [10, 32, 9]:  # Enter, Space, Tab
                    self.text.insert(position, chr(187))  # »
                    return 'break'

    def _recognize_links(self):
        """Автоматически обнаруживает URL-адреса и email в тексте, добавляет гиперссылки."""
        self.text.tag_remove('link', '1.0', 'end')
        regex = (r'(\b(http|ftp|https):\/\/([\w_-]+(?:(?:\.[\w_-]+)+))([\w.,@?^=%&:\/~+#-]*[\w@?^=%&\/~+#-])\b)|'
                 r'(\b\w+@(?=.*?\.)[\w.]+\b)')
        for match in re.finditer(regex, self.text.get('1.0', 'end')):
            start = self.text.index(f'1.0 + {match.start()} chars')
            end = self.text.index(f'{start} + {len(match.group(0))} chars')
            self.text.tag_add('link', start, end)

    def _on_enter_link(self, event):
        """Подсвечивает ссылку при наведении, и изменяет курсор.

        Args:
            event (tk.Event): Событие наведения мыши
        """
        self.text['cursor'] = 'hand2'
        link = self.Link(self.text, event.x, event.y)
        self.text.tag_add('hover', *link.range)

    def _on_leave_link(self):
        """Восстанавливает стандартный курсор и убирает подсветку ссылки."""
        self.text['cursor'] = 'xterm'
        self.text.tag_remove('hover', '1.0', 'end')

    def _open_link(self, event):
        """Открывает ссылку в браузере по клику.

        Args:
            event (tk.Event): Событие клика мыши
        """
        link = self.Link(self.text, event.x, event.y)
        if '@' in link.url:
            link.url = 'mailto:' + link.url
        webbrowser.open(link.url)

    def _tab_change(self):
        """Обрабатывает переключение между вкладками с разными типами данных."""
        selected_tab = self.tabs.index(self.tabs.select())
        self.text.tag_remove('all', '1.0', 'end')
        current_text = self.text.get('1.0', 'end-1c')
        self.data[self.current_tab]['data'] = current_text
        self.text.delete('1.0', 'end')
        self.text.insert('1.0', self.data[selected_tab]['data'])
        self._recognize_links()
        self._highlight_matches()

        self.current_tab = selected_tab

    def _context_menu(self, event):
        """Показывает контекстное меню с опциями: копирование, поиск в Яндексе и др.

        Args:
            event (tk.Event): Событие правого клика мыши
        """
        index = self.text.index(f'@{event.x},{event.y}')
        self.text.mark_set('insert', index)
        if 'sel' not in self.text.tag_names(index):
            self.text.tag_remove('sel', '1.0', 'end')
            self.update()

        selection_state = 'normal' if self.text.tag_ranges('sel') else 'disabled'
        clipboard_state = 'normal' if self.clipboard_get() != '' else 'disabled'
        self.context_menu.entryconfigure('Вырезать', state=selection_state)
        self.context_menu.entryconfigure('Копировать', state=selection_state)
        self.context_menu.entryconfigure('Вставить', state=clipboard_state)

        url = 'https://yandex.ru/search/?text='
        if 'sel' in self.text.tag_names(index):
            url += self.text.selection_get()
        else:
            url += self.text.get(f'{index} wordstart', f'{index} wordend')
        self.context_menu.entryconfigure('Поиск в Яндекс', command=lambda: webbrowser.open(url))

        if 'link' in self.text.tag_names(index):
            try:
                self.context_menu.index('Копировать ссылку')
            except tk.TclError:
                self.context_menu.add_separator()
                self.context_menu.add_command(label='Копировать ссылку')
            self.context_menu.entryconfigure('Копировать ссылку',
                                             command=lambda: [link := self.Link(self.text, event.x, event.y),
                                                              self.clipboard_clear(),
                                                              self.clipboard_append(link.url)])
        else:
            try:
                menu_idx = self.context_menu.index('Копировать ссылку')
                self.context_menu.delete(menu_idx - 1, menu_idx)
            except tk.TclError:
                pass

        self.context_menu.tk.call('tk_popup', self.context_menu, event.x_root, event.y_root)

    def _change_case(self):
        """Изменяет регистр выделенного текста (Shift+F3)."""
        try:
            sel_start, sel_end = self.text.tag_ranges('sel')
        except ValueError:
            return

        selected_text = self.text.get(sel_start, sel_end)
        if selected_text.islower():
            replace_text = selected_text.upper()
        elif selected_text.isupper() and selected_text != selected_text.title():
            replace_text = selected_text.title()
        elif selected_text.istitle() and selected_text != selected_text.capitalize():
            replace_text = selected_text.capitalize()
        else:
            replace_text = selected_text.lower()
        self.text.replace(sel_start, sel_end, replace_text)
        self.text.tag_add('sel', sel_start, sel_end)

    def _on_destroy(self):
        """Обработчик закрытия окна: сохраняет текст в буфер обмена."""
        self.clipboard_clear()
        self.clipboard_append(self.text.get('1.0', 'end-1c'))
        self.update()
        self.destroy()


def launcher(_, __, button, pressed):
    """Глобальный обработчик событий мыши для активации приложения.

    Args:
        _ (int): X координата события (игнорируется в обработчике)
        __ (int): Y координата события (игнорируется в обработчике)
        button (mouse.Button): Нажатая кнопка мыши
        pressed (bool): Состояние кнопки (нажата/отпущена)
    """
    def ask_user_about(status):
        action = f'{('Включить', 'Отключить')[status]} SilentScreenShoter?'
        header = 'SilentScreenShoter'
        return not status if ctypes.windll.user32.MessageBoxW(0, action, header, 0x00040004) == 6 else status

    global APPLICATION_IS_RUNNING
    global STATUS, LM_BUTTON, MM_BUTTON, RM_BUTTON
    if APPLICATION_IS_RUNNING:
        LM_BUTTON = MM_BUTTON = RM_BUTTON = False
        return

    if button == mouse.Button.left:
        LM_BUTTON = pressed
    if button == mouse.Button.middle:
        MM_BUTTON = pressed
    if button == mouse.Button.right:
        RM_BUTTON = pressed

    if all([LM_BUTTON, MM_BUTTON, RM_BUTTON]):
        STATUS = ask_user_about(STATUS)
    elif all([STATUS, LM_BUTTON, RM_BUTTON]):
        APPLICATION_IS_RUNNING = True
        app = Application()
        app.mainloop()
        if app.false_start:
            STATUS = ask_user_about(STATUS)
        del app
        APPLICATION_IS_RUNNING = False


if __name__ == '__main__':
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--silent', action='store_true', default=False)
    silent_mode = parser.parse_args().silent
    STATUS = not silent_mode
    LM_BUTTON = MM_BUTTON = RM_BUTTON = False
    APPLICATION_IS_RUNNING = False
    with mouse.Listener(on_click=launcher) as listener:
        listener.join()