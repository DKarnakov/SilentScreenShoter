from PIL import ImageGrab, ImageTk, ImageEnhance, ImageFilter, Image, ImageDraw
import tkinter as tk
from tkinter import ttk, filedialog, font
import pytesseract
from io import BytesIO
import win32clipboard
from math import sqrt, atan2, pi, sin, cos, dist
import ctypes
from functools import partial
from pynput import mouse
import argparse
import os
import time
from colorsys import rgb_to_hsv, rgb_to_hls
from shapely import LineString
from shapely.geometry import Polygon


class Application(tk.Tk):
    class Hint:
        def __init__(self, widget, hint):
            self.widget = widget
            self.hint = hint
            self.widget.bind('<Enter>', lambda e: self._schedule())
            self.widget.bind('<Leave>', lambda e: self.hide_hint())
            self._id = None

        def _schedule(self):
            self._unschedule()
            self._id = self.widget.after(3000, self.show_hint)

        def _unschedule(self):
            if self._id:
                self.widget.after_cancel(self._id)
            self._id = None

        def show_hint(self):
            for w, text in zip(self.widget.winfo_children(), self.hint):
                if isinstance(w, ttk.Button):
                    x = w.winfo_rootx() + w.winfo_width() // 2
                    y = w.winfo_rooty() + w.winfo_height() - 0
                    tk.Label(master=self.widget.master, text=text,
                             background='lightyellow', relief='solid', borderwidth=1).place(x=x, y=y, anchor='n')

        def hide_hint(self):
            self._unschedule()
            for w in self.widget.master.winfo_children():
                if isinstance(w, tk.Label):
                    w.destroy()

    class MakeDraggable:
        def __init__(self, widget, on_start=None):
            self.widget = widget
            self.function_on_start = on_start
            widget.bind('<Button-1>', lambda e: self.on_drag_start(e))
            widget.bind('<B1-Motion>', lambda e: self.on_drag_motion(e))

        def on_drag_start(self, event):
            if self.function_on_start:
                self.function_on_start()
            widget = self.widget
            widget.drag_start_x = event.x
            widget.drag_start_y = event.y

        def on_drag_motion(self, event):
            widget = self.widget
            x = widget.winfo_x() - widget.drag_start_x + event.x
            y = widget.winfo_y() - widget.drag_start_y + event.y
            widget.place(x=x, y=y)

    def __init__(self):
        tk.Tk.__init__(self)

        self.attributes('-fullscreen', True)
        self.attributes('-topmost', True)

        self.canvas = tk.Canvas(self, cursor='cross', highlightthickness=0)
        self.canvas.pack(side='top', fill='both', expand=True)

        self.canvas.bind('<ButtonPress-1>', lambda e: self._create_editor(e))
        self.canvas.bind('<B1-Motion>', lambda e: self._set_viewport(e))
        self.canvas.bind('<ButtonRelease-1>', lambda e: self._start_editing())

        self.x1 = self.y1 = None
        self.x2 = self.y2 = None

        self.screenshot_area_tk = None
        self.screenshot_area = None
        self.viewport = None
        self.border = None
        self.palette = ['red', 'orange', 'yellow', 'lime', 'cyan', 'blue', 'magenta', 'white', 'black']
        self.colors = len(self.palette)
        self.color = 0
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

        self.panel = ttk.Frame(self.canvas)
        self.panel_hint = self.Hint(self.panel, ['F1', 'F2', 'F3', 'F4', 'F5', 'F6', 'F7', '', 'Ctrl+R', 'Ctrl+C'])
        self.arrow_button = ttk.Button(self.panel, text='Стрелка', command=lambda: self._set_arrow())
        self.pen_button = ttk.Button(self.panel, text='Карандаш', command=lambda: self._set_pen())
        self.line_button = ttk.Button(self.panel, text='Линия', command=lambda: self._set_line())
        self.rect_button = ttk.Button(self.panel, text='Рамка', command=lambda: self._set_rect())
        self.text_button = ttk.Button(self.panel, text='Надпись', command=lambda: self._set_text())
        self.num_button = ttk.Button(self.panel, text=self.num, command=lambda: self._set_number())
        self.blur_button = ttk.Button(self.panel, text='Размытие', command=lambda: self._set_blur())
        self.color_panel = ttk.Label(self.panel, width=3, background=self.palette[self.color % self.colors])
        self.recognize_button = ttk.Button(self.panel, text='Распознать', command=lambda: self._recognize())
        done_txt = tk.StringVar(value='Ok')
        self.done_button = ttk.Button(self.panel, textvariable=done_txt, command=lambda: self._done())

        self.bind('<F1>', lambda e: self._set_arrow())
        self.bind('<F2>', lambda e: self._set_pen())
        self.bind('<F3>', lambda e: self._set_line())
        self.bind('<F4>', lambda e: self._set_rect())
        self.bind('<F5>', lambda e: self._set_text())
        self.bind('<F6>', lambda e: self._set_number())
        self.bind('<F7>', lambda e: self._set_blur())
        self.bind('<Escape>', lambda e: self.destroy())

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
        self.corner[position] = self.canvas.create_rectangle(x - 4, y - 4, x + 4, y + 4, width=2,
                                                             outline='lightgrey', fill='black', tags='service')
        self.canvas.tag_bind(self.corner[position], '<Enter>', lambda e: self.canvas.config(cursor=cursor))
        self.canvas.tag_bind(self.corner[position], '<Leave>', lambda e: self.canvas.config(cursor=''))
        self.canvas.tag_bind(self.corner[position], '<B1-Motion>', lambda e: self._change_viewport(position, e))
        self.canvas.tag_bind(self.corner[position], '<ButtonRelease-1>', lambda e: self._fix_viewport())

    def _move_corner(self, position, x, y):
        self.canvas.moveto(self.corner[position], x - 5, y - 5)

    def _draw_borders(self, x1, y1, x2, y2):
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
        # undo
        if event.state == 12 and event.keycode == 90:  # Ctrl-z
            last_item = self.canvas.find_withtag('editor')[-1]
            if last_item != self.viewport:
                for tag in self.canvas.gettags(last_item):
                    if tag.startswith('_'):
                        last_item = tag
                self.canvas.delete(last_item)
        # save
        elif event.state in [12, 13] and event.keycode == 67:  # Ctrl-c || Ctrl-Shift-c
            self._done()
        elif event.state == 12 and event.keycode == 83:  # Ctrl-s
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
        elif event.state == 131084 and event.keycode == 67:  # Ctrl-Alt-c
            hex_color = self.canvas.itemcget('z_33', 'fill')
            red = int(hex_color[1:3], base=16)
            green = int(hex_color[3:5], base=16)
            blue = int(hex_color[5:7], base=16)
            h, s, v = rgb_to_hsv(red / 255, green / 255, blue / 255)
            hls = rgb_to_hls(red / 255, green / 255, blue / 255)
            color_txt = (f'HEX: {hex_color}\n'
                         f'RGB: rgb({red}, {green}, {blue})\n'
                         f'HSL: hsl({hls[0] * 360:.0f}, {hls[2]:.0%}, {hls[1]:.0%})\n'
                         f'HSV: {h * 360:.0f}° {s:.0%} {v:.0%}')
            self.clipboard_clear()
            self.clipboard_append(color_txt)
            self.update()
        # recognize
        elif event.state == 12 and event.keycode == 82:  # Ctrl-r
            self._recognize()

    def _create_editor(self, event):
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
        self.canvas.tag_lower(self.viewport_size_bg, self.viewport_size)

        for row in range(7):
            for col in range(7):
                self.canvas.create_rectangle(0, 0, 10, 10, tags=['service', 'precision', f'z_{row}{col}'])
        self.canvas.itemconfig('z_33', width=3)

        self.color_pick = self.canvas.create_text(0, 0, anchor='sw', text='#000000',
                                                  font='Helvetica 10 bold',
                                                  tags=['service', 'precision'])
        self.color_pick_bg = self.canvas.create_rectangle(self.canvas.bbox(self.viewport_size),
                                                          tags=['service', 'precision'])
        self.canvas.tag_lower(self.color_pick_bg, self.color_pick)

        self.canvas.itemconfig('precision', state='hidden')

        self.bind('<KeyPress-Alt_L>', lambda e: self._precision())
        self.bind('<KeyRelease-Alt_L>', lambda e: self.canvas.itemconfig('precision', state='hidden'))
        self.bind('<KeyPress-Alt_R>', lambda e: self._precision())
        self.bind('<KeyRelease-Alt_R>', lambda e: self.canvas.itemconfig('precision', state='hidden'))
        self.bind('<Alt-Button-1>', lambda e: self._add_color())
        self.bind('<Control-KeyPress>', lambda e: self._control(e))

        self.canvas.tag_bind('editor', '<ButtonPress-2>', lambda e: self._new_item(e))
        self.canvas.tag_bind('editor', '<B2-Motion>', lambda e: self._ruler_move(e))
        self.canvas.tag_bind('editor', '<ButtonRelease-2>', lambda e: self._ruler_stop())

    def _precision(self):
        x1, y1, x2, y2 = self.canvas.bbox(self.viewport)
        self.canvas.itemconfig('precision', state='normal')
        self.canvas.itemconfig(self.viewport_size, text=f'{x2 - x1}×{y2 - y1}')
        height = self.canvas.bbox(self.viewport_size)[3] - self.canvas.bbox(self.viewport_size)[1]
        self.canvas.moveto(self.viewport_size, x1 - 5, y1 - height - 7)
        self.canvas.coords(self.viewport_size_bg, self.canvas.bbox(self.viewport_size))

        xp = self.winfo_pointerx() - self.winfo_rootx()
        yp = self.winfo_pointery() - self.winfo_rooty()
        x = min(max(35, xp), self.winfo_width() - 35)
        y = min(yp, self.winfo_height() - 110)

        for row in range(7):
            for col in range(7):
                try:
                    r, g, b = self.image.getpixel((xp - 3 + col, yp - 3 + row))
                except IndexError:
                    r, g, b = self.image.getpixel((xp, yp))
                self.canvas.itemconfig(f'z_{row}{col}', fill=f'#{r:02x}{g:02x}{b:02x}')
                self.canvas.moveto(f'z_{row}{col}', x - 35 + col * 10, y - 30 + row * 10 + 70)

        self.cursor_color = self.canvas.itemcget('z_33', 'fill').upper()
        hex_red = int(self.cursor_color[1:3], base=16)
        hex_green = int(self.cursor_color[3:5], base=16)
        hex_blue = int(self.cursor_color[5:7], base=16)
        luminance = hex_red * 0.2126 + hex_green * 0.7152 + hex_blue * 0.0722
        self.canvas.itemconfig(self.color_pick, text=self.cursor_color,
                               fill='lightgrey' if luminance < 140 else 'black')
        self.canvas.itemconfig(self.color_pick_bg, fill=self.cursor_color, outline='black')
        height_pick = self.canvas.bbox(self.color_pick)[3] - self.canvas.bbox(self.color_pick)[1]
        width_pick = self.canvas.bbox(self.color_pick)[2] - self.canvas.bbox(self.color_pick)[0]
        self.canvas.moveto(self.color_pick, x - width_pick // 2 + 1, y - height_pick - 32 + 70)
        self.canvas.coords(self.color_pick_bg, (x - 34, y - height_pick - 32 + 70, x + 36, y - 32 + 70))
        self.canvas.tag_raise('precision')
        self.canvas.tag_raise('z_33')

    def _add_color(self):
        color = self.canvas.itemcget('z_33', 'fill')
        if color != '':
            self.color_panel['background'] = color

    def _set_viewport(self, event):
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
        self.x1, self.y1, self.x2, self.y2 = self.canvas.coords(self.border)

    def _check_viewport_borders(self, x, y):
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

    def _start_editing(self):
        if [self.x1, self.x2, self.y1, self.y2] == [None, None, None, None]:
            return
        self.x1, self.y1, self.x2, self.y2 = self.canvas.coords(self.border)
        self.canvas.unbind('<B1-Motion>')
        self.canvas.unbind('<ButtonPress-1>')
        self.canvas.unbind('<ButtonRelease-1>')

        self.canvas.create_window(self.canvas.winfo_width() // 2, 10, window=self.panel, anchor='n', tags='service')
        self.MakeDraggable(self.panel, on_start=self.panel_hint.hide_hint)

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

    def _set_selection(self, button):
        for w in button.master.winfo_children():
            ttk.Button.state(w, ['!pressed'])
        ttk.Button.state(button, ['pressed'])
        self.panel_hint.hide_hint()
        if button != self.text_button and self.text_edit:
            self._text_stop()

    def _new_item(self, event):
        self.coords = [event.x, event.y]

    def _set_arrow(self):
        self.canvas.tag_bind('editor', '<ButtonPress-1>', lambda e: self._new_item(e))
        self.canvas.tag_bind('editor', '<B1-Motion>', lambda e: self._arrow_move(e))
        self.canvas.tag_bind('editor', '<ButtonRelease-1>', lambda e: self.canvas.unbind('<MouseWheel>'))
        self.canvas.tag_unbind('editor', '<Shift-B1-Motion>')
        self._set_selection(self.arrow_button)

    def _arrow_move(self, event):
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
            self.coords = self.coords[:2] + [event.x, event.y]
            self._check_viewport_borders(event.x, event.y)
            self.canvas.coords(self.arrow, self.coords)

    def _arrow_change(self, event):
        arrows = [tk.FIRST, tk.LAST, tk.BOTH]
        arrow = arrows.index(self.canvas.itemcget(self.arrow, 'arrow'))
        arrow += 1 if event.delta > 0 else -1
        self.canvas.itemconfigure(self.arrow, arrow=arrows[arrow % 3])

    def _set_pen(self):
        self.canvas.tag_bind('editor', '<ButtonPress-1>', lambda e: self._new_item(e))
        self.canvas.tag_bind('editor', '<B1-Motion>', lambda e: self._pen_draw(e))
        self.canvas.tag_bind('editor', '<ButtonRelease-1>', lambda e: self._pen_control_stop())
        self.canvas.tag_unbind('editor', '<Shift-B1-Motion>')
        self._set_selection(self.pen_button)

    def _pen_control_stop(self):
        self.unbind('<KeyPress-Control_L>')
        self.unbind('<KeyRelease-Control_L>')
        self.unbind('<KeyPress-Control_R>')
        self.unbind('<KeyRelease-Control_R>')
        self.canvas.unbind('<MouseWheel>')

    def _pen_draw(self, event):
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
                self.coords += [event.x, event.y]
                self.canvas.coords(self.pen, self.coords)
            self._check_viewport_borders(x2, y2)

    def _pen_width_change(self, event):
        pen_width = float(self.canvas.itemcget(self.pen, 'width'))
        pen_width = max(pen_width - 1, 0) if event.delta < 0 else pen_width + 1
        self.canvas.itemconfigure(self.pen, width=pen_width)

    def _pen_recognise(self):
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
                coords = LineString(points).oriented_envelope.exterior.coords
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
            self.coords = self.coords[:2] + [event.x, event.y]
            self._check_viewport_borders(event.x, event.y)
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
            self.coords = self.coords[:-2] + [event.x, event.y]
            self._check_viewport_borders(event.x, event.y)
            self.canvas.coords(self.ruler_area, self.coords)
            self._draw_ruler_area()

    def _ruler_add_point(self, event):
        self.coords += [event.x, event.y]
        if len(self.coords) == 6:
            self.canvas.itemconfigure(self.ruler_area, state='normal')
            self.canvas.itemconfigure(self.ruler, state='hidden')
            self.canvas.tag_bind('editor', '<ButtonPress-3>', lambda e: self._ruler_delete_point(e))
            self.unbind('<Key>')
        self.canvas.coords(self.ruler_area, self.coords)
        self._draw_ruler_area()

    def _ruler_delete_point(self, event):
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
        self.canvas.itemconfigure(self.ruler_size, text=text, fill=text_color)
        self.canvas.itemconfigure(self.ruler_size_bg, fill=bg_color)
        x = sum(self.coords[::2]) / (len(self.coords) // 2)
        y = sum(self.coords[1::2]) / (len(self.coords) // 2)
        self.canvas.coords(self.ruler_size, x, y)
        self.canvas.coords(self.ruler_size_bg, self._offset_bbox(self.canvas.bbox(self.ruler_size), 3))

    def _ruler_scale(self, event):
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
        self.canvas.delete('ruler')
        self.unbind('<Key>')
        self.canvas.tag_unbind('editor', '<ButtonPress-3>')
        if self.callback_button:
            self.callback_button.invoke()
            self.callback_button = None

    @staticmethod
    def _offset_bbox(bbox, offset):
        x1, y1, x2, y2 = bbox
        return [x1 - offset,
                y1 - offset,
                x2 + offset,
                y2 + offset]

    def _set_line(self):
        self.canvas.tag_bind('editor', '<ButtonPress-1>', lambda e: self._new_item(e))
        self.canvas.tag_bind('editor', '<B1-Motion>', lambda e: self._line_move(e))
        self.canvas.tag_bind('editor', '<Shift-B1-Motion>', lambda e: self._line_angle_move(pi / 8, e))
        self.canvas.tag_unbind('editor', '<ButtonRelease-1>')
        self.canvas.tag_bind('editor', '<ButtonRelease-1>', lambda e: self.canvas.unbind('<MouseWheel>'))
        self._set_selection(self.line_button)

    def _line_change(self, event):
        dashes = ['', '255', '1', '1 1 1 1', '1 1 1']
        dash = dashes.index(self.canvas.itemcget(self.line, 'dash'))
        dash += 1 if event.delta > 0 else -1
        self.canvas.itemconfigure(self.line, dash=dashes[dash % 5])

    def _line_move(self, event):
        if len(self.coords) == 2:
            self.coords += [event.x, event.y]
            self.line = self.canvas.create_line(self.coords, tags=['editor', 'item'],
                                                fill=self.color_panel['background'],
                                                width=5, capstyle='round')
            self.canvas.tag_bind(self.line, '<ButtonPress-3>', partial(self.canvas.delete, self.line))
            self.canvas.bind('<MouseWheel>', lambda e: self._line_change(e))
        else:
            self.coords = self.coords[:2] + [event.x, event.y]
            self._check_viewport_borders(event.x, event.y)
            self.canvas.coords(self.line, self.coords)

    def _line_angle_move(self, angle, event):
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
            self._check_viewport_borders(x2, y2)
            self.coords = [x1, y1, x2, y2]
            self.canvas.coords(self.line, self.coords)

    @staticmethod
    def _round_rectangle(coords, radius=13):
        x1, y1, x2, y2 = coords

        x1, x2 = (x2, x1) if x2 < x1 else (x1, x2)
        y1, y2 = (y2, y1) if y2 < y1 else (y1, y2)
        radius = min((x2 - x1) // 2, (y2 - y1) // 2, radius)

        return [x1, y1,
                x1 + radius, y1,
                x1 + radius, y1,
                x2 - radius, y1,
                x2 - radius, y1,
                x2, y1,
                x2, y1 + radius,
                x2, y1 + radius,
                x2, y2 - radius,
                x2, y2 - radius,
                x2, y2,
                x2 - radius, y2,
                x2 - radius, y2,
                x1 + radius, y2,
                x1 + radius, y2,
                x1, y2,
                x1, y2 - radius,
                x1, y2 - radius,
                x1, y1 + radius,
                x1, y1 + radius,
                x1, y1]

    def _set_rect(self):
        self.canvas.tag_bind('editor', '<ButtonPress-1>', lambda e: self._new_item(e))
        self.canvas.tag_bind('editor', '<B1-Motion>', lambda e: self._rect_move(e))
        self.canvas.tag_unbind('editor', '<ButtonRelease-1>')
        self.canvas.tag_unbind('editor', '<Shift-B1-Motion>')
        self.canvas.tag_bind('editor', '<ButtonRelease-1>', lambda e: self.canvas.unbind('<MouseWheel>'))
        self._set_selection(self.rect_button)

    def _rect_move(self, event):
        if len(self.coords) == 2:
            self.coords += [event.x, event.y]
            self.rect_corner = 13
            self.rect = self.canvas.create_line(self._round_rectangle(self.coords), smooth=True,
                                                fill=self.color_panel['background'], tags=['editor', 'item'], width=5)
            self.canvas.tag_bind(self.rect, '<ButtonPress-3>', partial(self.canvas.delete, self.rect))
            self.canvas.bind('<MouseWheel>', lambda e: self._rect_corner_change(e))
        else:
            self.coords = self.coords[:2] + [event.x, event.y]
            self._check_viewport_borders(event.x, event.y)
            self.canvas.coords(self.rect, self._round_rectangle(self.coords, self.rect_corner))

    def _rect_corner_change(self, event):
        if event.delta < 0:
            self.rect_corner = max(self.rect_corner - ((self.rect_corner // 10) + 1), 0)
        else:
            self.rect_corner += (self.rect_corner // 10) + 1
            x1, y1, x2, y2 = self.coords
            self.rect_corner = min(abs(x2 - x1) // 2, abs(y2 - y1) // 2, self.rect_corner)
        self.canvas.coords(self.rect, self._round_rectangle(self.coords, self.rect_corner))

    def _set_text(self):
        self.canvas.tag_bind('editor', '<ButtonPress-1>', lambda e: self._text_create(e))
        self.canvas.tag_bind('editor', '<B1-Motion>', lambda e: self._text_resize_bg(e))
        self.canvas.tag_bind('editor', '<ButtonRelease-1>', lambda e: self._text_start(e))
        self.canvas.tag_unbind('editor', '<Shift-B1-Motion>')
        self._set_selection(self.text_button)

    def _text_create(self, event):
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
        self.bind('<Key>', self._key_handler)
        self.bind('<Control-Key>', self._key_control_handler)
        self.bind('<Control-MouseWheel>', lambda e: self._mouse_control_wheel_handler(e))
        self.canvas.unbind('<MouseWheel>')
        self.txt = ''
        height = font.Font(font=f'Helvetica {self.font_size} bold').metrics('linespace') // 2
        self.coords[1] -= height if self.coords[2:] == [0, 0] else 0
        x = min(self.coords[0], event.x)
        y = min(self.coords[1], event.y)
        self.text = self.canvas.create_text(x, y, anchor='nw',
                                            text=self.txt, font=f'Helvetica {self.font_size} bold',
                                            fill=self.color_panel['background'],
                                            width=self.winfo_width() - x,
                                            tags=['editor', f'txt{self.txt_tag}', 'item'])
        self.text_cursor = self.canvas.create_text(x, y, anchor='nw',
                                                   text='|', font=f'Helvetica {self.font_size} bold',
                                                   fill='grey50', tags=f'txt{self.txt_tag}')
        self.coords = [x, y, max(self.coords[0], self.coords[2]), max(self.coords[1], self.coords[3])]
        self.canvas.tag_bind(f'txt{self.txt_tag}', '<ButtonPress-3>',
                             partial(self.canvas.delete, f'txt{self.txt_tag}'))
        self.text_edit = True
        self._blink_cursor()

    def _text_resize_bg(self, event):
        x1, y1 = self.coords[:2]
        x2, y2 = event.x, event.y
        self._check_viewport_borders(x2, y2)

        x2, x1 = (x1, x2) if x2 < x1 else (x2, x1)
        y2, y1 = (y1, y2) if y2 < y1 else (y2, y1)

        del self.image_stack[-1]
        self._create_txt_bg(self._offset_bbox((x1, y1, x2, y2), 3), 'white', self.alpha)

        self.coords[2] = x2
        self.coords[3] = y2

    def _alpha_change(self, event):
        self.alpha = min(self.alpha + 0.1, 1) if event.delta > 0 else max(self.alpha - 0.1, 0)
        x1, y1 = self.coords[:2]
        x2, y2 = event.x, event.y
        x2, x1 = (x1, x2) if x2 < x1 else (x2, x1)
        y2, y1 = (y1, y2) if y2 < y1 else (y2, y1)
        del self.image_stack[-1]
        self._create_txt_bg(self._offset_bbox((x1, y1, x2, y2), 3), 'white', self.alpha)

    def _create_txt_bg(self, bbox, color, alpha):
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
        bounds = self.canvas.bbox(self.text)
        x1, y1, x2, y2 = (bounds[0], bounds[1], max(self.coords[2], bounds[2]), max(self.coords[3], bounds[3]))
        if direction == 'Up' and y1 - step > 0:
            y1 -= step
            self.coords[3] -= step
        elif direction == 'Down' and y2 + step < self.winfo_height():
            y1 += step
            self.coords[3] += step
        elif direction == 'Left' and x1 - step > 0:
            x1 -= step
            self.coords[2] -= step
        elif direction == 'Right' and x2 + step < self.winfo_width():
            x1 += step
            self.coords[2] += step

        self.canvas.moveto(self.text, x1, y1)
        self.canvas.itemconfig(self.text, width=self.winfo_width() - x1)
        self.coords[0] = x1
        self.coords[1] = y1

    def _update_cursor_position(self):
        lines = len(self.txt.split('\n')) - 1
        max_width = int(self.canvas.itemcget(self.text, 'width'))
        for line in self.txt.split('\n'):
            add_line = font.Font(font=f'Helvetica {self.font_size} bold').measure(line) // max_width
            lines += add_line
        text_before_cursor = self.txt.split('\n')[-1]
        line_width = font.Font(font=f'Helvetica {self.font_size} bold').measure(text_before_cursor)
        line_height = font.Font(font=f'Helvetica {self.font_size} bold').metrics('linespace')
        x = self.coords[0] + line_width
        y = self.coords[1] + line_height * lines
        self.canvas.coords(self.text_cursor, x, y)
        self.canvas.itemconfig(self.text_cursor, font=f'Helvetica {self.font_size} bold')

    def _blink_cursor(self):
        if self.text_edit:
            self.cursor_visible = not self.cursor_visible
            self.canvas.itemconfigure(self.text_cursor, state='normal' if self.cursor_visible else 'hidden')
            self.is_blinking = self.after(500, self._blink_cursor)
        else:
            self.after_cancel(self.is_blinking)

    def _redraw_text(self):
        bounds = self.canvas.bbox(self.text)
        bounds = (bounds[0], bounds[1], max(self.coords[2], bounds[2]), max(self.coords[3], bounds[3]))
        self._check_viewport_borders(bounds[0] - 3, bounds[1] - 3)
        self._check_viewport_borders(bounds[2] + 3, bounds[3] + 3)
        del self.image_stack[-1]
        self._create_txt_bg(self._offset_bbox(bounds, 3), 'white', self.alpha)
        self._update_cursor_position()

    def _key_handler(self, event):
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
        else:
            self.txt = self.txt + event.char

        self.canvas.itemconfig(self.text, text=self.txt)
        self._redraw_text()

    def _key_control_handler(self, event):
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
        self.font_size = min(self.font_size + 1, 25) if event.delta > 0 else max(self.font_size - 1, 9)
        self.canvas.itemconfig(self.text, font=f'Helvetica {self.font_size} bold')
        self._redraw_text()

    def _text_stop(self):
        self.unbind('<Key>')
        self.unbind('<Control-MouseWheel>')
        self.bind('<Control-KeyPress>', lambda e: self._control(e))
        self.bind('<Escape>', lambda e: self.destroy())
        if self.txt == '':
            self.canvas.delete(f'txt{self.txt_tag}')
        self.text_edit = False
        try:
            self.canvas.delete(self.text_cursor)
        except AttributeError:
            ...

    def _set_blur(self):
        self.canvas.tag_bind('editor', '<ButtonPress-1>', lambda e: self._blur_create(e))
        self.canvas.tag_bind('editor', '<B1-Motion>', lambda e: self._blur_move(e))
        self.canvas.tag_bind('editor', '<ButtonRelease-1>', lambda e: self.canvas.unbind('<MouseWheel>'))
        self.canvas.tag_unbind('editor', '<Shift-B1-Motion>')
        self._set_selection(self.blur_button)

    def _blur_create(self, event):
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
        x1, y1 = self.coords
        x2, y2 = event.x, event.y
        self._check_viewport_borders(x2, y2)

        anchor = 's' if y2 < y1 else 'n'
        anchor += 'e' if x2 < x1 else 'w'

        x2, x1 = (x1, x2) if x2 < x1 else (x2, x1)
        y2, y1 = (y1, y2) if y2 < y1 else (y2, y1)

        blur_area = self.blur_image.crop((x1, y1, x2, y2))
        self.image_stack[-1] = ImageTk.PhotoImage(blur_area)
        self.canvas.itemconfig(self.blur, anchor=anchor, image=self.image_stack[-1], tags=['editor', 'item'])

    def _blur_change(self, event):
        self.blur_radius = min(self.blur_radius + 1, 10) if event.delta > 0 else max(self.blur_radius - 1, 1)
        self.blur_image = self.image.filter(ImageFilter.GaussianBlur(self.blur_radius))
        self._blur_move(event)

    def _set_number(self):
        self.canvas.tag_bind('editor', '<ButtonPress-1>', lambda e: self._number_create(e))
        self.canvas.tag_bind('editor', '<B1-Motion>', lambda e: self._number_move(e))
        self.canvas.tag_bind('editor', '<ButtonRelease-1>', lambda e: self._number_set())
        self.canvas.tag_unbind('editor', '<Shift-B1-Motion>')
        self._set_selection(self.num_button)

    def _number_create(self, event):
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
        x1, y1, *_ = self.canvas.coords(self.number_arrow)
        x2, y2 = event.x, event.y
        self._check_viewport_borders(x2, y2)

        length = sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        self.canvas.itemconfig(self.number_arrow, arrowshape=(length, length, 20), fill=self.color_panel['background'])
        self.canvas.itemconfig(self.number_circle, fill=self.color_panel['background'],
                               outline=self.color_panel['background'])
        self.canvas.coords(self.number_arrow, x1, y1, x2, y2)

    def _num_change(self, event):
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
        self.num += 1
        self.num_button['text'] = self.num
        self.canvas.unbind('<MouseWheel>')

    def _number_delete(self, tag, _):
        self.canvas.delete(tag)
        self.num = int(tag.split('_')[-1])
        self.num_button['text'] = self.num

    def _change_number(self, event):
        if event.delta > 0:
            self.num += 1
        elif self.num > 1:
            self.num -= 1
        self.num_button['text'] = self.num
        self._set_number()

    def _change_color(self, event):
        self.color += 1 if event.delta > 0 else -1
        self.color_panel['background'] = self.palette[self.color % self.colors]
        if self.text_edit:
            self.canvas.itemconfig(self.text, fill=self.palette[self.color % self.colors])

    def _recognize(self):
        txt = pytesseract.image_to_string(self.screenshot_area, lang='rus+eng', config=r'--oem 3 --psm 6')
        bbox = self.canvas.bbox(self.viewport)
        self.destroy()
        Notepad(txt, bbox).mainloop()

    def _done(self):
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
    def __init__(self, txt, bbox):
        tk.Tk.__init__(self)
        self.title('SilentScreenShoter — Clipboard')
        self.after(1, lambda: self.text.focus_force())
        self.geometry(f'{bbox[2] - bbox[0]}x{bbox[3] - bbox[1]}+{bbox[0]}+{bbox[1] - 22}')
        self.protocol('WM_DELETE_WINDOW', self._on_destroy)
        self.text = tk.Text(wrap='word', font='Consolas 11', undo=True)
        self.text.pack(side='top', fill='both', expand=True)

        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label='Выбрать всё', accelerator='Ctrl+A')
        self.context_menu.add_separator()
        self.context_menu.add_command(label='Вырезать', accelerator='Ctrl+X')
        self.context_menu.add_command(label='Копировать', accelerator='Ctrl+C')
        self.context_menu.add_command(label='Вставить', accelerator='Ctrl+V')

        self.text.bind('<Button-3>', self._context_menu)
        self.text.bind('<Shift-F3>', lambda e: self._change_case())
        self.text.bind('<Escape>', lambda e: self._on_destroy())

        self.text.insert('1.0', txt[:-1])
        self.update()

    def _context_menu(self, event):
        self.context_menu.entryconfigure('Выбрать всё', command=lambda: self.text.event_generate('<<SelectAll>>'))
        self.context_menu.entryconfigure('Вырезать', command=lambda: self.text.event_generate('<<Cut>>'))
        self.context_menu.entryconfigure('Копировать', command=lambda: self.text.event_generate('<<Copy>>'))
        self.context_menu.entryconfigure('Вставить', command=lambda: self.text.event_generate('<<Paste>>'))
        self.context_menu.tk.call('tk_popup', self.context_menu, event.x_root, event.y_root)

    def _change_case(self):
        sel_start, sel_end = self.text.tag_ranges('sel')
        if sel_start and sel_end:
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
        self.clipboard_clear()
        self.clipboard_append(self.text.get('1.0', 'end'))
        self.update()
        self.destroy()


def launcher(_, __, button, pressed):
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
        action = f'{('Включить', 'Отключить')[STATUS]} SilentScreenShoter?'
        header = 'SilentScreenShoter'
        STATUS = not STATUS if ctypes.windll.user32.MessageBoxW(0, action, header, 0x00040004) == 6 else STATUS
    elif all([STATUS, LM_BUTTON, RM_BUTTON]):
        APPLICATION_IS_RUNNING = True
        Application().mainloop()
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
