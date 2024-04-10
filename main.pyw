from PIL import ImageGrab, ImageTk, ImageEnhance, ImageFilter
import tkinter as tk
from tkinter import ttk, filedialog
import pytesseract
from io import BytesIO
import win32clipboard
from math import sqrt, atan2, pi, sin, cos
import ctypes
from functools import partial
from pynput import mouse
import argparse
import os
import time
from colorsys import rgb_to_hsv, rgb_to_hls


class Application(tk.Tk):
    def __init__(self):
        tk.Tk.__init__(self)

        self.attributes('-fullscreen', True)
        self.attributes('-topmost', True)
        self.after(1000, lambda: self.focus_force())

        self.canvas = tk.Canvas(self, cursor='cross', highlightthickness=0)
        self.canvas.pack(side='top', fill='both', expand=True)

        self.canvas.bind('<ButtonPress-1>', self._create_editor)
        self.canvas.bind('<B1-Motion>', self._set_viewport)
        self.canvas.bind('<ButtonRelease-1>', self._start_editing)
        self.bind('<Escape>', lambda e: self.destroy())

        self.x1 = self.y1 = None
        self.x2 = self.y2 = None

        self.screenshot_area_tk = None
        self.txt = ''
        self.txt_rect = None
        self.screenshot_area = None
        self.viewport = None
        self.border = None
        self.palette = ['red', 'orange', 'yellow', 'lime', 'cyan', 'blue', 'magenta', 'white', 'black']
        self.colors = len(self.palette)
        self.color = 0
        self.num = 1
        self.point = {}
        self.blur_stack = []

        self.panel = ttk.Frame(self.canvas)
        self.arrow_button = ttk.Button(self.panel, text='Стрелка', command=lambda: self._set_arrow())
        self.pen_button = ttk.Button(self.panel, text='Карандаш', command=lambda: self._set_pen())
        self.line_button = ttk.Button(self.panel, text='Линия', command=lambda: self._set_line())
        self.rect_button = ttk.Button(self.panel, text='Рамка', command=lambda: self._set_rect())
        self.text_button = ttk.Button(self.panel, text='Надпись', command=lambda: self._set_text())
        self.blur_button = ttk.Button(self.panel, text='Размытие', command=lambda: self._set_blur())
        self.num_button = ttk.Button(self.panel, text=self.num, command=lambda: self._set_number())
        self.color_panel = ttk.Label(self.panel, width=3, background=self.palette[self.color % self.colors])
        self.recognize_button = ttk.Button(self.panel, text='Распознать', command=lambda: self._recognize())
        done_txt = tk.StringVar(value='Ok')
        self.done_button = ttk.Button(self.panel, textvariable=done_txt, command=lambda: self._done())

        self.bind('<KeyPress-Shift_L>', lambda e: done_txt.set('Сохранить'))
        self.bind('<KeyRelease-Shift_L>', lambda e: done_txt.set('Ok'))
        self.bind('<KeyPress-Shift_R>', lambda e: done_txt.set('Сохранить'))
        self.bind('<KeyRelease-Shift_R>', lambda e: done_txt.set('Ok'))

        self.image = ImageGrab.grab()
        self.blur_image = self.image.filter(ImageFilter.GaussianBlur(5))

        background = self.image.convert('L')
        background = ImageEnhance.Brightness(background).enhance(0.8)

        self.background_tk = ImageTk.PhotoImage(background)
        self.canvas.create_image(0, 0, anchor='nw', image=self.background_tk)

    def _change_cursor(self, cursor):
        self.canvas.config(cursor=cursor)

    def _create_corner(self, position, x, y, cursor):
        self.point[position] = self.canvas.create_rectangle(x - 4, y - 4, x + 4, y + 4, width=2,
                                                            outline='lightgrey', fill='black', tags='service')
        self.canvas.tag_bind(self.point[position], '<Enter>', lambda e: self._change_cursor(cursor))
        self.canvas.tag_bind(self.point[position], '<Leave>', lambda e: self._change_cursor('arrow'))
        self.canvas.tag_bind(self.point[position], '<B1-Motion>', lambda e: self._change_viewport(position, e))
        self.canvas.tag_bind(self.point[position], '<ButtonRelease-1>', lambda e: self._fix_viewport(position, e))

    def _move_corner(self, position, x, y):
        self.canvas.moveto(self.point[position], x - 5, y - 5)

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
            image = ImageGrab.grab(bbox=(self.x1, self.y1, self.x2, self.y2))
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
            h, s, v = rgb_to_hsv(red/255, green/255, blue/255)
            hls = rgb_to_hls(red/255, green/255, blue/255)
            color_txt = (f'HEX: {hex_color}\n'
                         f'RGB: rgb({red}, {green}, {blue})\n'
                         f'HSL: hsl({hls[0]*360:.0f}, {hls[2]:.0%}, {hls[1]:.0%})\n'
                         f'HSV: {h*360:.0f}° {s:.0%} {v:.0%}')
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

        self._change_cursor('arrow')

        self.border = self.canvas.create_rectangle(x1, y1, x2, y2,
                                                   width=2, dash=50, outline='lightgrey',
                                                   tags='service')
        cursors = {'nw': 'top_left_corner',
                   'n':  'top_side',
                   'ne': 'top_right_corner',
                   'e':  'right_side',
                   'se': 'bottom_right_corner',
                   's':  'bottom_side',
                   'sw': 'bottom_left_corner',
                   'w':  'left_side'}
        for corner in cursors:
            self._create_corner(corner, x1, y1, cursors[corner])

        self.x1, self.x2, self.y1, self.y2 = x1, x2, y1, y2

        self.txt_rect = self.canvas.create_rectangle(0, 0, 0, 0, tags='service', dash=5, width=2, outline='darkgrey')
        self.canvas.itemconfig(self.txt_rect, state='hidden')

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
                                                  font='Helvetica 11 bold',
                                                  tags=['service', 'precision'])
        self.color_pick_bg = self.canvas.create_rectangle(self.canvas.bbox(self.viewport_size),
                                                          tags=['service', 'precision'])
        self.canvas.tag_lower(self.color_pick_bg, self.color_pick)

        self.canvas.itemconfig('precision', state='hidden')

        self.bind('<KeyPress-Alt_L>', lambda e: self._precision())
        self.bind('<KeyRelease-Alt_L>', lambda e: self.canvas.itemconfig('precision', state='hidden'))
        self.bind('<KeyPress-Alt_R>', lambda e: self._precision())
        self.bind('<KeyRelease-Alt_R>', lambda e: self.canvas.itemconfig('precision', state='hidden'))

        self.bind('<Control-KeyPress>', lambda e: self._control(e))

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
                    r, g, b = self.image.getpixel((xp-3+col, yp-3+row))
                except IndexError:
                    r, g, b = self.image.getpixel((xp, yp))
                self.canvas.itemconfig(f'z_{row}{col}', fill=f'#{r:02x}{g:02x}{b:02x}')
                self.canvas.moveto(f'z_{row}{col}', x-35+col*10, y-30+row*10+70)

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
        self.canvas.moveto(self.color_pick, x-width_pick//2+1, y-height_pick-32+70)
        self.canvas.coords(self.color_pick_bg, (x-34, y-height_pick-32+70, x+36, y-32+70))
        self.canvas.tag_raise('precision')
        self.canvas.tag_raise('z_33')

    def _set_viewport(self, event):
        x1, x2, y1, y2 = self.x1, event.x, self.y1, event.y

        anchor = 's' if y2 < y1 else 'n'
        anchor = anchor + 'e' if x2 < x1 else anchor + 'w'

        x2, x1 = (x1, x2) if x2 < x1 else (x2, x1)
        y2, y1 = (y1, y2) if y2 < y1 else (y2, y1)

        self.screenshot_area = self.image.crop((x1, y1, x2, y2))
        self.screenshot_area_tk = ImageTk.PhotoImage(self.screenshot_area)
        self.canvas.itemconfig(self.viewport, image=self.screenshot_area_tk, anchor=anchor)

        self.canvas.coords(self.border, (x1, y1, x2, y2))

        self._move_corner('nw', x1, y1)
        self._move_corner('n', (x2 + x1) // 2, y1)
        self._move_corner('ne', x2, y1)
        self._move_corner('e', x2, (y2 + y1) // 2)
        self._move_corner('se', x2, y2)
        self._move_corner('s', (x2 + x1) // 2, y2)
        self._move_corner('sw', x1, y2)
        self._move_corner('w', x1, (y2 + y1) // 2)

        self.x2, self.y2 = x2, y2

    def _change_viewport(self, corner, event):
        x1 = event.x if 'w' in corner else self.x1
        y1 = event.y if 'n' in corner else self.y1
        x2 = event.x if 'e' in corner else self.x2
        y2 = event.y if 's' in corner else self.y2

        self.x1, self.x2, self.y1, self.y2 = x1, x2, y1, y2

        x2, x1 = (x1, x2) if x2 < x1 else (x2, x1)
        y2, y1 = (y1, y2) if y2 < y1 else (y2, y1)

        self.screenshot_area = self.image.crop((x1, y1, x2, y2))
        self.screenshot_area_tk = ImageTk.PhotoImage(self.screenshot_area)
        self.canvas.moveto(self.viewport, x1, y1)
        self.canvas.itemconfig(self.viewport, image=self.screenshot_area_tk, anchor='nw')

        self.canvas.coords(self.border, (x1, y1, x2, y2))

        self._move_corner('nw', x1, y1)
        self._move_corner('n', (x2 + x1) // 2, y1)
        self._move_corner('ne', x2, y1)
        self._move_corner('e', x2, (y2 + y1) // 2)
        self._move_corner('se', x2, y2)
        self._move_corner('s', (x2 + x1) // 2, y2)
        self._move_corner('sw', x1, y2)
        self._move_corner('w', x1, (y2 + y1) // 2)

    def _fix_viewport(self, corner, event):
        x1 = event.x if 'w' in corner else self.x1
        y1 = event.y if 'n' in corner else self.y1
        x2 = event.x if 'e' in corner else self.x2
        y2 = event.y if 's' in corner else self.y2

        x2, x1 = (x1, x2) if x2 < x1 else (x2, x1)
        y2, y1 = (y1, y2) if y2 < y1 else (y2, y1)

        self.x1, self.x2, self.y1, self.y2 = x1, x2, y1, y2

    def _move_viewport(self, x1, y1, x2, y2):
        self.screenshot_area = self.image.crop((x1, y1, x2, y2))
        self.screenshot_area_tk = ImageTk.PhotoImage(self.screenshot_area)
        self.canvas.moveto(self.viewport, x1, y1)
        self.canvas.itemconfig(self.viewport, image=self.screenshot_area_tk, anchor='nw')

        self.canvas.coords(self.border, (x1, y1, x2, y2))

        self._move_corner('nw', x1, y1)
        self._move_corner('n', (x2 + x1) // 2, y1)
        self._move_corner('ne', x2, y1)
        self._move_corner('e', x2, (y2 + y1) // 2)
        self._move_corner('se', x2, y2)
        self._move_corner('s', (x2 + x1) // 2, y2)
        self._move_corner('sw', x1, y2)
        self._move_corner('w', x1, (y2 + y1) // 2)

    def _start_editing(self, event):
        if [self.x1, self.x2, self.y1, self.y2] == [None, None, None, None]:
            return
        self._fix_viewport('se', event)
        self.canvas.unbind('<B1-Motion>')
        self.canvas.unbind('<ButtonPress-1>')
        self.canvas.unbind('<ButtonRelease-1>')

        self.canvas.create_window(self.canvas.winfo_width() // 2, 10, window=self.panel, anchor='n', tags='service')

        self.arrow_button.grid(padx=3, pady=3, column=0, row=1)
        self.pen_button.grid(padx=3, pady=3, column=1, row=1)
        self.line_button.grid(padx=3, pady=3, column=2, row=1)
        self.rect_button.grid(padx=3, pady=3, column=3, row=1)
        self.text_button.grid(padx=3, pady=3, column=4, row=1)
        self.blur_button.grid(padx=3, pady=3, column=5, row=1)
        self.num_button.bind('<MouseWheel>', lambda e: self._change_number(e))
        self.num_button.grid(padx=3, pady=3, column=6, row=1)
        self.color_panel.bind('<MouseWheel>', lambda e: self._change_color(e))
        self.color_panel.grid(padx=3, pady=3, column=7, row=1)
        self.recognize_button.grid(padx=3, pady=3, column=8, row=1)
        self.done_button.grid(padx=3, pady=3, column=9, row=1)

        self._set_arrow()

    def _set_selection(self, button):
        for w in button.master.winfo_children():
            ttk.Button.state(w, ['!pressed'])
        ttk.Button.state(button, ['pressed'])
        if button != self.text_button:
            self._text_stop()

    def _set_arrow(self):
        self.canvas.tag_bind('editor', '<ButtonPress-1>', lambda e: self._arrow_create(e))
        self.canvas.tag_bind('editor', '<B1-Motion>', lambda e: self._arrow_move(e))
        self.canvas.tag_unbind('editor', '<ButtonRelease-1>')
        self.canvas.tag_unbind('editor', '<Shift-B1-Motion>')
        self._set_selection(self.arrow_button)

    def _arrow_create(self, event):
        self.arrow = self.canvas.create_line(event.x, event.y, event.x, event.y,
                                             fill=self.palette[self.color % self.colors],
                                             width=5, tags='editor',
                                             arrowshape=(17, 25, 7), capstyle='round',
                                             arrow=tk.LAST)
        self.canvas.tag_bind(self.arrow, '<ButtonPress-3>', partial(self.canvas.delete, self.arrow))

    def _arrow_move(self, event):
        x1, y1, *_ = self.canvas.coords(self.arrow)
        x2, y2 = event.x, event.y
        xe1, xe2, ye1, ye2 = self.x1, self.x2, self.y1, self.y2
        if x2 < self.x1:
            xe1 = x2
        if x2 > self.x2:
            xe2 = x2
        if y2 < self.y1:
            ye1 = y2
        if y2 > self.y2:
            ye2 = y2

        if [self.x1, self.x2, self.y1, self.y2] != [xe1, xe2, ye1, ye2]:
            self.x1, self.x2, self.y1, self.y2 = xe1, xe2, ye1, ye2
            self._move_viewport(xe1, ye1, xe2, ye2)

        self.canvas.coords(self.arrow, x1, y1, x2, y2)

    def _set_pen(self):
        self.canvas.tag_bind('editor', '<ButtonPress-1>', lambda e: self._pen_create(e))
        self.canvas.tag_bind('editor', '<B1-Motion>', lambda e: self._pen_draw(e))
        self.canvas.tag_unbind('editor', '<ButtonRelease-1>')
        self.canvas.tag_unbind('editor', '<Shift-B1-Motion>')
        self._set_selection(self.pen_button)

    def _pen_create(self, event):
        self.pen = self.canvas.create_line(event.x, event.y, event.x, event.y, width=5,
                                           fill=self.palette[self.color % self.colors],
                                           tags='editor')
        self.canvas.tag_bind(self.pen, '<ButtonPress-3>', partial(self.canvas.delete, self.pen))

    def _pen_draw(self, event):
        coords = self.canvas.coords(self.pen)

        *_, x1, y1 = coords
        x2, y2 = event.x, event.y
        dist = sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        if dist > 3:
            xe1, xe2, ye1, ye2 = self.x1, self.x2, self.y1, self.y2
            if x2 < self.x1:
                xe1 = x2
            if x2 > self.x2:
                xe2 = x2
            if y2 < self.y1:
                ye1 = y2
            if y2 > self.y2:
                ye2 = y2

            if [self.x1, self.x2, self.y1, self.y2] != [xe1, xe2, ye1, ye2]:
                self.x1, self.x2, self.y1, self.y2 = xe1, xe2, ye1, ye2
                self._move_viewport(xe1, ye1, xe2, ye2)

            coords.append(x2)
            coords.append(y2)
            self.canvas.coords(self.pen, coords)

    def _set_line(self):
        self.canvas.tag_bind('editor', '<ButtonPress-1>', lambda e: self._line_create(e))
        self.canvas.tag_bind('editor', '<B1-Motion>', lambda e: self._line_move(e))
        self.canvas.tag_bind('editor', '<Shift-B1-Motion>', lambda e: self._line_angle_move(pi / 8, e))
        self.canvas.tag_unbind('editor', '<ButtonRelease-1>')
        self._set_selection(self.line_button)

    def _line_create(self, event):
        self.line = self.canvas.create_line(event.x, event.y, event.x, event.y, tags='editor',
                                            fill=self.palette[self.color % self.colors], width=5, capstyle='round')
        self.canvas.tag_bind(self.line, '<ButtonPress-3>', partial(self.canvas.delete, self.line))

    def _line_move(self, event):
        x1, y1, *_ = self.canvas.coords(self.line)
        x2, y2 = event.x, event.y
        xe1, xe2, ye1, ye2 = self.x1, self.x2, self.y1, self.y2
        if x2 < self.x1:
            xe1 = x2
        if x2 > self.x2:
            xe2 = x2
        if y2 < self.y1:
            ye1 = y2
        if y2 > self.y2:
            ye2 = y2

        if [self.x1, self.x2, self.y1, self.y2] != [xe1, xe2, ye1, ye2]:
            self.x1, self.x2, self.y1, self.y2 = xe1, xe2, ye1, ye2
            self._move_viewport(xe1, ye1, xe2, ye2)

        self.canvas.coords(self.line, x1, y1, x2, y2)

    def _line_angle_move(self, angle, event):
        x1, y1, *_ = self.canvas.coords(self.line)
        x2, y2 = event.x, event.y
        alpha = (atan2(x2 - x1, y2 - y1) + angle / 2) // angle * angle
        length = sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        x2 = int(x1 + length * sin(alpha))
        y2 = int(y1 + length * cos(alpha))
        xe1, xe2, ye1, ye2 = self.x1, self.x2, self.y1, self.y2
        if x2 < self.x1:
            xe1 = x2
        if x2 > self.x2:
            xe2 = x2
        if y2 < self.y1:
            ye1 = y2
        if y2 > self.y2:
            ye2 = y2

        if [self.x1, self.x2, self.y1, self.y2] != [xe1, xe2, ye1, ye2]:
            self.x1, self.x2, self.y1, self.y2 = xe1, xe2, ye1, ye2
            self._move_viewport(xe1, ye1, xe2, ye2)

        self.canvas.coords(self.line, x1, y1, x2, y2)

    def _set_rect(self):
        self.canvas.tag_bind('editor', '<ButtonPress-1>', lambda e: self._rect_create(e))
        self.canvas.tag_bind('editor', '<B1-Motion>', lambda e: self._rect_move(e))
        self.canvas.tag_unbind('editor', '<ButtonRelease-1>')
        self.canvas.tag_unbind('editor', '<Shift-B1-Motion>')
        self._set_selection(self.rect_button)

    def _rect_create(self, event):
        self.rect = self.canvas.create_rectangle(event.x, event.y, event.x, event.y, tags='editor',
                                                 outline=self.palette[self.color % self.colors], width=5)
        self.canvas.tag_bind(self.rect, '<ButtonPress-3>', partial(self.canvas.delete, self.rect))
        self.rect_x = event.x
        self.rect_y = event.y

    def _rect_move(self, event):
        x1, y1, *_ = self.canvas.coords(self.rect)
        x2, y2 = event.x, event.y
        xe1, xe2, ye1, ye2 = self.x1, self.x2, self.y1, self.y2
        if x2 < self.x1:
            xe1 = x2
        if x2 > self.x2:
            xe2 = x2
        if y2 < self.y1:
            ye1 = y2
        if y2 > self.y2:
            ye2 = y2

        if [self.x1, self.x2, self.y1, self.y2] != [xe1, xe2, ye1, ye2]:
            self.x1, self.x2, self.y1, self.y2 = xe1, xe2, ye1, ye2
            self._move_viewport(xe1, ye1, xe2, ye2)

        self.canvas.coords(self.rect, self.rect_x, self.rect_y, x2, y2)

    def _set_text(self):
        self.canvas.tag_bind('editor', '<ButtonPress-1>', lambda e: self._text_create(e))
        self.canvas.tag_bind('editor', '<B1-Motion>', lambda e: self._text_move(e))
        self.canvas.tag_bind('editor', '<ButtonRelease-1>', lambda e: self._text_start())
        self.canvas.tag_unbind('editor', '<Shift-B1-Motion>')
        self._set_selection(self.text_button)

    def _text_create(self, event):
        self.txt_rect_x = event.x
        self.txt_rect_y = event.y
        self.canvas.itemconfig(self.txt_rect, state='normal')
        self.canvas.coords(self.txt_rect, self.txt_rect_x, self.txt_rect_y, event.x + 200, event.y + 30)
        self.unbind('<Escape>')

    def _text_move(self, event):
        x1, y1, *_ = self.canvas.coords(self.txt_rect)
        x2, y2 = event.x, event.y
        xe1, xe2, ye1, ye2 = self.x1, self.x2, self.y1, self.y2
        if x2 < self.x1:
            xe1 = x2
        if x2 > self.x2:
            xe2 = x2
        if y2 < self.y1:
            ye1 = y2
        if y2 > self.y2:
            ye2 = y2

        if [self.x1, self.x2, self.y1, self.y2] != [xe1, xe2, ye1, ye2]:
            self.x1, self.x2, self.y1, self.y2 = xe1, xe2, ye1, ye2
            self._move_viewport(xe1, ye1, xe2, ye2)

        self.canvas.coords(self.txt_rect, self.txt_rect_x, self.txt_rect_y, x2, y2)

    def _key_handler(self, event):
        if event.keysym == 'BackSpace':
            self.txt = self.txt[:-1]
        elif event.keysym == 'Escape':
            self._text_stop()
            return
        else:
            self.txt = self.txt + event.char
        self.canvas.itemconfig(self._txt, text=self.txt)
        bounds = self.canvas.bbox(self._txt)
        if bounds[2] > self.canvas.coords(self.txt_rect)[2]:
            self.txt = self.txt[:-1] + '\n' + self.txt[-1]
            self.canvas.itemconfig(self._txt, text=self.txt)
            bounds = self.canvas.bbox(self._txt)
        if bounds[3] > self.canvas.coords(self.txt_rect)[3]:
            x1, y1, x2, _ = self.canvas.coords(self.txt_rect)
            self.canvas.coords(self.txt_rect, x1, y1, x2, bounds[3])

            if bounds[3] > self.y2:
                self.y2 = bounds[3]
                self._move_viewport(self.x1, self.y1, self.x2, self.y2)

    def _text_start(self):
        self.bind('<Key>', self._key_handler)
        self.txt = ''
        text_color = self.palette[self.color % self.colors]
        x, y, *_ = self.canvas.coords(self.txt_rect)
        self._txt = self.canvas.create_text(x, y, text=self.txt, fill=text_color,
                                            anchor='nw', font='Helvetica 18 bold', tags='editor')
        self.canvas.tag_bind(self._txt, '<ButtonPress-3>', partial(self.canvas.delete, self._txt))

    def _text_stop(self):
        self.canvas.itemconfig(self.txt_rect, state='hidden')
        self.unbind('<Key>')
        self.bind('<Escape>', lambda e: self.destroy())

    def _set_blur(self):
        self.canvas.tag_bind('editor', '<ButtonPress-1>', lambda e: self._blur_create(e))
        self.canvas.tag_bind('editor', '<B1-Motion>', lambda e: self._blur_move(e))
        self.canvas.tag_unbind('editor', '<ButtonRelease-1>')
        self.canvas.tag_unbind('editor', '<Shift-B1-Motion>')
        self._set_selection(self.blur_button)

    def _blur_create(self, event):
        x1, y1, x2, y2 = event.x, event.y, event.x, event.y

        blur_area = self.blur_image.crop((x1, y1, x2, y2))
        self.blur_stack.append(ImageTk.PhotoImage(blur_area))
        self.blur = self.canvas.create_image(x1, y1, anchor='nw', image=self.blur_stack[-1], tags='editor')
        self.canvas.tag_raise(self.blur, self.viewport)
        self.blur_x = x1
        self.blur_y = y1
        self.canvas.tag_bind(self.blur, '<ButtonPress-3>', partial(self.canvas.delete, self.blur))

    def _blur_move(self, event):
        x1, y1, *_ = self.canvas.coords(self.blur)
        x2, y2 = event.x, event.y
        xe1, xe2, ye1, ye2 = self.x1, self.x2, self.y1, self.y2
        if x2 < self.x1:
            xe1 = x2
        if x2 > self.x2:
            xe2 = x2
        if y2 < self.y1:
            ye1 = y2
        if y2 > self.y2:
            ye2 = y2

        if [self.x1, self.x2, self.y1, self.y2] != [xe1, xe2, ye1, ye2]:
            self.x1, self.x2, self.y1, self.y2 = xe1, xe2, ye1, ye2
            self._move_viewport(xe1, ye1, xe2, ye2)

        x1, x2, y1, y2 = self.blur_x, event.x, self.blur_y, event.y

        anchor = 's' if y2 < y1 else 'n'
        anchor = anchor + 'e' if x2 < x1 else anchor + 'w'

        x2, x1 = (x1, x2) if x2 < x1 else (x2, x1)
        y2, y1 = (y1, y2) if y2 < y1 else (y2, y1)

        blur_area = self.blur_image.crop((x1, y1, x2, y2))
        self.blur_stack[-1] = ImageTk.PhotoImage(blur_area)
        self.canvas.itemconfig(self.blur, anchor=anchor, image=self.blur_stack[-1], tags='editor')

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
        self.number_arrow = self.canvas.create_line(event.x, event.y, event.x, event.y,
                                                    fill=self.palette[self.color % self.colors],
                                                    arrow=tk.LAST,
                                                    tags=[tag, 'editor'])
        r = 20
        self.number_circle = self.canvas.create_oval(event.x - r, event.y - r, event.x + r, event.y + r,
                                                     fill=self.palette[self.color % self.colors],
                                                     outline=self.palette[self.color % self.colors],
                                                     tags=[tag, 'editor'])
        text_color = 'darkgrey' if self.palette[self.color % self.colors] in ['white', 'yellow'] else 'white'
        self.number_txt = self.canvas.create_text(event.x, event.y, text=self.num, fill=text_color,
                                                  anchor='center', font='Helvetica 18 bold',
                                                  tags=[tag, 'editor'])
        self.canvas.tag_bind(self.number_arrow, '<ButtonPress-3>', partial(self._number_delete, tag))
        self.canvas.tag_bind(self.number_circle, '<ButtonPress-3>', partial(self._number_delete, tag))
        self.canvas.tag_bind(self.number_txt, '<ButtonPress-3>', partial(self._number_delete, tag))

    def _number_move(self, event):
        x1, y1, *_ = self.canvas.coords(self.number_arrow)
        x2, y2 = event.x, event.y
        xe1, xe2, ye1, ye2 = self.x1, self.x2, self.y1, self.y2
        if x2 < self.x1:
            xe1 = x2
        if x2 > self.x2:
            xe2 = x2
        if y2 < self.y1:
            ye1 = y2
        if y2 > self.y2:
            ye2 = y2

        if [self.x1, self.x2, self.y1, self.y2] != [xe1, xe2, ye1, ye2]:
            self.x1, self.x2, self.y1, self.y2 = xe1, xe2, ye1, ye2
            self._move_viewport(xe1, ye1, xe2, ye2)

        length = sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        self.canvas.itemconfig(self.number_arrow, arrowshape=(length, length, 20))
        self.canvas.coords(self.number_arrow, x1, y1, x2, y2)

    def _number_set(self):
        self.num += 1
        self.num_button['text'] = self.num

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

    def _change_color(self, event):
        self.color += 1 if event.delta > 0 else -1
        self.color_panel['background'] = self.palette[self.color % self.colors]
        if self.canvas.itemcget(self.txt_rect, 'state') != 'hidden':
            self.canvas.itemconfig(self._txt, fill=self.palette[self.color % self.colors])

    def _recognize(self):
        txt = pytesseract.image_to_string(self.screenshot_area, lang='rus+eng', config=r'--oem 3 --psm 6')
        bbox = (self.x1, self.y1, self.x2, self.y2)
        self.destroy()
        Notepad(txt, bbox).mainloop()

    def _done(self):
        self.canvas.delete('service')
        self.canvas.update()
        image = ImageGrab.grab(bbox=(self.x1, self.y1, self.x2, self.y2))
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
        self.geometry(f'{bbox[2]-bbox[0]}x{bbox[3]-bbox[1]}+{bbox[0]}+{bbox[1] - 22}')
        self.protocol('WM_DELETE_WINDOW', self._on_destroy)
        self.text = tk.Text(wrap='word', font='Consolas 11')
        self.text.pack(side='top', fill='both', expand=True)

        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label='Выбрать всё', accelerator='Ctrl+A')
        self.context_menu.add_separator()
        self.context_menu.add_command(label='Вырезать', accelerator='Ctrl+X')
        self.context_menu.add_command(label='Копировать', accelerator='Ctrl+C')
        self.context_menu.add_command(label='Вставить', accelerator='Ctrl+V')

        self.text.bind('<Button-3>', self._context_menu)
        self.text.bind('<Escape>', lambda e: self._on_destroy())

        self.text.insert('1.0', txt[:-2])
        self.update()

    def _context_menu(self, event):
        self.context_menu.entryconfigure('Выбрать всё', command=lambda: self.text.event_generate('<<SelectAll>>'))
        self.context_menu.entryconfigure('Вырезать', command=lambda: self.text.event_generate('<<Cut>>'))
        self.context_menu.entryconfigure('Копировать', command=lambda: self.text.event_generate('<<Copy>>'))
        self.context_menu.entryconfigure('Вставить', command=lambda: self.text.event_generate('<<Paste>>'))
        self.context_menu.tk.call('tk_popup', self.context_menu, event.x_root, event.y_root)

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
        app = Application()
        app.mainloop()
        LM_BUTTON = MM_BUTTON = RM_BUTTON = False
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
