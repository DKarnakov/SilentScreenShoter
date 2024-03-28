from PIL import ImageGrab, ImageTk, ImageEnhance, ImageFilter
import tkinter as tk
from tkinter import ttk
import pytesseract
from io import BytesIO
import win32clipboard
from math import sqrt, atan2, pi, sin, cos
from win11toast import notify
from functools import partial


def set_selection(button):
    for w in button.master.winfo_children():
        ttk.Button.state(w, ['!pressed'])
    ttk.Button.state(button, ['pressed'])


class Application(tk.Tk):
    def __init__(self):
        tk.Tk.__init__(self)

        self.txt = ''
        self.txt_rect = None
        self.color_panel = None
        self.screenshot_area = None
        self.move_point = []
        self.attributes('-fullscreen', True)
        self.title("Моя программа")

        self.canvas = tk.Canvas(self, cursor="cross", highlightthickness=0)
        self.canvas.pack(side="top", fill="both", expand=True)

        self.canvas.bind('<ButtonPress-1>', self.create_editor)
        self.canvas.bind('<B1-Motion>', self.set_viewport)
        self.canvas.bind('<ButtonRelease-1>', self.start_editing)
        self.bind('<Escape>', lambda event: self.destroy())

        self.style = ttk.Style()
        # self.style.theme_use('alt')
        self.style.configure('RoundedFrame.TFrame')
        self.panel = ttk.Frame(self.canvas, style='RoundedFrame.TFrame')

        self.x1 = self.y1 = None
        self.x2 = self.y2 = None

        self.screenshot_area_tk = None
        self.viewport = None
        self.border = None
        self.colors = ['red', 'orange', 'yellow', 'lime', 'lightblue', 'blue', 'magenta', 'white', 'black']
        self.color = 0
        self.num = 1
        self.point = {}
        self.blur_stack = []
        self.text_bg_stack = []

        self._background()

    def _background(self):
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
        self.canvas.tag_bind(self.point[position], '<Enter>', lambda event: self._change_cursor(cursor))
        self.canvas.tag_bind(self.point[position], '<Leave>', lambda event: self._change_cursor('arrow'))
        self.canvas.tag_bind(self.point[position], '<B1-Motion>', lambda event: self.change_viewport(position, event))
        self.canvas.tag_bind(self.point[position], '<ButtonRelease-1>',
                             lambda event: self.fix_viewport(position, event))

    def _move_corner(self, position, x, y):
        self.canvas.moveto(self.point[position], x - 5, y - 5)

    def create_editor(self, event):
        x1, y1, x2, y2 = event.x, event.y, event.x + 2, event.y + 2

        screenshot_area = self.image.crop((x1, y1, x2, y2))
        self.screenshot_area_tk = ImageTk.PhotoImage(screenshot_area)

        self.viewport = self.canvas.create_image(x1, y1, anchor="nw", image=self.screenshot_area_tk, tags='editor')

        self._change_cursor('arrow')

        self.border = self.canvas.create_rectangle(x1, y1, x2, y2,
                                                   width=2, dash=50, outline='lightgrey',
                                                   tags='service')

        self._create_corner('nw', x1, y1, 'top_left_corner')
        self._create_corner('n', x1, y1, 'top_side')
        self._create_corner('ne', x1, y1, 'top_right_corner')
        self._create_corner('e', x1, y1, 'right_side')
        self._create_corner('se', x1, y1, 'bottom_right_corner')
        self._create_corner('s', x1, y1, 'bottom_side')
        self._create_corner('sw', x1, y1, 'bottom_left_corner')
        self._create_corner('w', x1, y1, 'left_side')

        self.x1, self.x2, self.y1, self.y2 = x1, x2, y1, y2

        self.txt_rect = self.canvas.create_rectangle(-1, -1, -1, -1, tags='service', dash=5, width=2,
                                                     outline='lightgrey')

    def set_viewport(self, event):

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

    def change_viewport(self, corner, event):
        x1, x2, y1, y2 = self.x1, self.x2, self.y1, self.y2

        if corner == 'nw':
            x1 = event.x
            y1 = event.y
        elif corner == 'n':
            y1 = event.y
        elif corner == 'ne':
            x2 = event.x
            y1 = event.y
        elif corner == 'e':
            x2 = event.x
        elif corner == 'se':
            x2 = event.x
            y2 = event.y
        elif corner == 's':
            y2 = event.y
        elif corner == 'sw':
            x1 = event.x
            y2 = event.y
        elif corner == 'w':
            x1 = event.x

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

    def fix_viewport(self, corner, event):
        x1, x2, y1, y2 = self.x1, self.x2, self.y1, self.y2

        if corner == 'nw':
            x1 = event.x
            y1 = event.y
        elif corner == 'n':
            y1 = event.y
        elif corner == 'ne':
            x2 = event.x
            y1 = event.y
        elif corner == 'e':
            x2 = event.x
        elif corner == 'se':
            x2 = event.x
            y2 = event.y
        elif corner == 's':
            y2 = event.y
        elif corner == 'sw':
            x1 = event.x
            y2 = event.y
        elif corner == 'w':
            x1 = event.x

        x2, x1 = (x1, x2) if x2 < x1 else (x2, x1)
        y2, y1 = (y1, y2) if y2 < y1 else (y2, y1)

        self.x1, self.x2, self.y1, self.y2 = x1, x2, y1, y2

    def move_viewport(self, x1, y1, x2, y2):
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

    def start_editing(self, event):
        self.fix_viewport('se', event)

        self.canvas.unbind('<B1-Motion>')
        self.canvas.unbind('<ButtonPress-1>')
        self.canvas.unbind('<ButtonRelease-1>')

        self.canvas.create_window(self.canvas.winfo_width() // 2, 0, window=self.panel, anchor="n", tags='service')

        padding = (3, 3)

        self.arrow_button = ttk.Button(self.panel, text='Стрелка', command=lambda: self._set_arrow())
        self.arrow_button.grid(padx=padding[0], pady=padding[1], column=0, row=1)

        self.pen_button = ttk.Button(self.panel, text='Карандаш', command=lambda: self._set_pen())
        self.pen_button.grid(padx=padding[0], pady=padding[1], column=1, row=1)

        self.line_button = ttk.Button(self.panel, text='Линия', command=lambda: self._set_line())
        self.line_button.grid(padx=padding[0], pady=padding[1], column=2, row=1)

        self.rect_button = ttk.Button(self.panel, text='Рамка', command=lambda: self._set_rect())
        self.rect_button.grid(padx=padding[0], pady=padding[1], column=3, row=1)

        self.text_button = ttk.Button(self.panel, text='Надпись', command=lambda: self._set_text())
        self.text_button.grid(padx=padding[0], pady=padding[1], column=4, row=1)

        self.blur_button = ttk.Button(self.panel, text='Размытие', command=lambda: self._set_blur())
        self.blur_button.grid(padx=padding[0], pady=padding[1], column=5, row=1)

        self.num_button = ttk.Button(self.panel, text=self.num, command=lambda: self._set_number())
        self.num_button.bind('<MouseWheel>', lambda e: self._change_number(e))
        self.num_button.grid(padx=padding[0], pady=padding[1], column=6, row=1)

        self.color_panel = ttk.Label(self.panel, width=3, background=self.colors[self.color % 9])
        self.color_panel.bind('<MouseWheel>', lambda e: self._change_color(e))
        self.color_panel.grid(padx=padding[0], pady=padding[1], column=7, row=1)

        recognize_button = ttk.Button(self.panel, text='Распознать', command=lambda: self._recognize())
        recognize_button.grid(padx=padding[0], pady=padding[1], column=8, row=1)

        done_button = ttk.Button(self.panel, text="Ok", command=lambda: self._done())
        done_button.grid(padx=padding[0], pady=padding[1], column=9, row=1)

        self._set_arrow()

    def delete_item(self, event):
        print(self.canvas.find_closest(event.x, event.y, start=self.viewport + 1))

    def _set_arrow(self):
        self.canvas.tag_bind('editor', '<ButtonPress-1>', lambda event: self._arrow_create(event))
        self.canvas.tag_bind('editor', '<B1-Motion>', lambda event: self._arrow_move(event))
        self.canvas.tag_unbind('editor', '<ButtonRelease-1>')

        set_selection(self.arrow_button)

    def _arrow_create(self, event):
        self.arrow = self.canvas.create_line(event.x, event.y, event.x, event.y,
                                             fill=self.colors[self.color % 9],
                                             width=5, tags='editor',
                                             arrowshape=(17, 25, 7),
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
            self.move_viewport(xe1, ye1, xe2, ye2)

        self.canvas.coords(self.arrow, x1, y1, x2, y2)

    def _set_pen(self):
        self.canvas.tag_bind('editor', '<ButtonPress-1>', lambda event: self._pen_create(event))
        self.canvas.tag_bind('editor', '<B1-Motion>', lambda event: self._pen_draw(event))
        self.canvas.tag_unbind('editor', '<ButtonRelease-1>')
        set_selection(self.pen_button)

    def _pen_create(self, event):
        pen_size = 5
        x1, y1 = event.x, event.y
        x2, y2 = event.x, event.y
        self.pen = self.canvas.create_line(x1, y1, x2, y2,
                                           fill=self.colors[self.color % 9], width=pen_size,
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
                self.move_viewport(xe1, ye1, xe2, ye2)

            coords.append(x2)
            coords.append(y2)
            self.canvas.coords(self.pen, coords)

    def _set_line(self):
        self.canvas.tag_bind('editor', '<ButtonPress-1>', lambda event: self._line_create(event))
        self.canvas.tag_bind('editor', '<B1-Motion>', lambda event: self._line_move(event))
        self.canvas.tag_bind('editor', '<Shift-B1-Motion>', lambda event: self._line_fix_move(event))
        self.canvas.tag_unbind('editor', '<ButtonRelease-1>')
        set_selection(self.line_button)

    def _line_create(self, event):
        self.line = self.canvas.create_line(event.x, event.y, event.x, event.y, tags='editor',
                                            fill=self.colors[self.color % 9], width=5, capstyle='round')
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
            self.move_viewport(xe1, ye1, xe2, ye2)

        self.canvas.coords(self.line, x1, y1, x2, y2)

    def _line_fix_move(self, event):
        x1, y1, *_ = self.canvas.coords(self.line)
        x2, y2 = event.x, event.y
        alpha = atan2(x2 - x1, y2 - y1)
        alpha = (alpha + pi / 16) // (pi / 8) * (pi / 8)
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
            self.move_viewport(xe1, ye1, xe2, ye2)

        self.canvas.coords(self.line, x1, y1, x2, y2)

    def _set_rect(self):
        self.canvas.tag_bind('editor', '<ButtonPress-1>', lambda event: self._rect_create(event))
        self.canvas.tag_bind('editor', '<B1-Motion>', lambda event: self._rect_move(event))
        self.canvas.tag_unbind('editor', '<ButtonRelease-1>')
        set_selection(self.rect_button)

    def _rect_create(self, event):
        self.rect = self.canvas.create_rectangle(event.x, event.y, event.x, event.y, tags='editor',
                                                 outline=self.colors[self.color % 9], width=5)
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
            self.move_viewport(xe1, ye1, xe2, ye2)

        self.canvas.coords(self.rect, self.rect_x, self.rect_y, x2, y2)

    def _set_text(self):
        self.canvas.tag_bind('editor', '<ButtonPress-1>', lambda event: self._text_create(event))
        self.canvas.tag_bind('editor', '<B1-Motion>', lambda event: self._text_move(event))
        self.canvas.tag_bind('editor', '<ButtonRelease-1>', lambda event: self._text_start(event))
        set_selection(self.text_button)

    def _text_create(self, event):
        self.txt_rect_x = event.x - 30
        self.txt_rect_y = event.y - 50
        self.canvas.coords(self.txt_rect, self.txt_rect_x, self.txt_rect_y, event.x, event.y)

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
            self.move_viewport(xe1, ye1, xe2, ye2)

        self.canvas.coords(self.txt_rect, self.txt_rect_x, self.txt_rect_y, x2, y2)

    def key_handler(self, event):
        # print(event.char, event.keysym, event.keycode)
        if event.keysym == 'BackSpace':
            self.txt = self.txt[:-1]
        else:
            self.txt = self.txt + event.char
        self.canvas.itemconfig(self._txt, text=self.txt)
        bounds = self.canvas.bbox(self._txt)
        # width = bounds[2] - bounds[0]
        # height = bounds[3] - bounds[1]
        if bounds[2] > self.canvas.coords(self.txt_rect)[2]:
            self.txt = self.txt[:-1] + '\n' + self.txt[-1]
            self.canvas.itemconfig(self._txt, text=self.txt)
            bounds = self.canvas.bbox(self._txt)
        if bounds[3] > self.canvas.coords(self.txt_rect)[3]:
            self.canvas.coords(self.txt_rect, self.txt_rect_x, self.txt_rect_y,
                               self.canvas.coords(self.txt_rect)[2], bounds[3])

            if bounds[3] > self.y2:
                self.y2 = bounds[3]
                self.move_viewport(self.x1, self.y1, self.x2, self.y2)

    def _text_start(self, event):
        self.bind('<Key>', self.key_handler)
        self.txt = ''
        text_color = self.colors[self.color % 9]
        self._txt = self.canvas.create_text(self.txt_rect_x, self.txt_rect_y, text=self.txt, fill=text_color,
                                            anchor='nw', font='Helvetica 18 bold', tags='editor')
        self.canvas.tag_bind(self._txt, '<ButtonPress-3>', partial(self.canvas.delete, self._txt))

    def _text_stop(self, event):
        pass

    def _set_blur(self):
        self.canvas.tag_bind('editor', '<ButtonPress-1>', lambda event: self._blur_create(event))
        self.canvas.tag_bind('editor', '<B1-Motion>', lambda event: self._blur_move(event))
        self.canvas.tag_unbind('editor', '<ButtonRelease-1>')
        set_selection(self.blur_button)

    def _blur_create(self, event):
        x1, y1, x2, y2 = event.x, event.y, event.x, event.y

        blur_area = self.blur_image.crop((x1, y1, x2, y2))
        self.blur_stack.append(ImageTk.PhotoImage(blur_area))
        self.blur = self.canvas.create_image(x1, y1, anchor="nw", image=self.blur_stack[-1], tags='editor')
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
            self.move_viewport(xe1, ye1, xe2, ye2)

        x1, x2, y1, y2 = self.blur_x, event.x, self.blur_y, event.y

        anchor = 's' if y2 < y1 else 'n'
        anchor = anchor + 'e' if x2 < x1 else anchor + 'w'

        x2, x1 = (x1, x2) if x2 < x1 else (x2, x1)
        y2, y1 = (y1, y2) if y2 < y1 else (y2, y1)

        blur_area = self.blur_image.crop((x1, y1, x2, y2))
        self.blur_stack[-1] = ImageTk.PhotoImage(blur_area)
        self.canvas.itemconfig(self.blur, anchor=anchor, image=self.blur_stack[-1], tags='editor')

    def _set_number(self):
        self.canvas.tag_bind('editor', '<ButtonPress-1>', lambda event: self._number_create(event))
        self.canvas.tag_bind('editor', '<B1-Motion>', lambda event: self._number_move(event))
        self.canvas.tag_bind('editor', '<ButtonRelease-1>', lambda event: self._number_set(event))
        set_selection(self.num_button)

    def _number_create(self, event):
        tag = 'na_' + str(self.num)
        self.number_arrow = self.canvas.create_line(event.x, event.y, event.x, event.y,
                                                    fill=self.colors[self.color % 9],
                                                    arrow=tk.LAST,
                                                    tags=[tag, 'editor'])
        r = 20
        self.number_circle = self.canvas.create_oval(event.x - r, event.y - r, event.x + r, event.y + r,
                                                     fill=self.colors[self.color % 9],
                                                     outline=self.colors[self.color % 9],
                                                     tags=[tag, 'editor'])
        text_color = 'darkgrey' if self.colors[self.color % 9] in ['white', 'yellow'] else 'white'
        self.number_txt = self.canvas.create_text(event.x, event.y, text=self.num, fill=text_color,
                                                  anchor='center', font='Helvetica 18 bold',
                                                  tags=[tag, 'editor'])
        self.canvas.tag_bind(self.number_arrow, '<ButtonPress-3>', partial(self.canvas.delete, tag))
        self.canvas.tag_bind(self.number_circle, '<ButtonPress-3>', partial(self.canvas.delete, tag))
        self.canvas.tag_bind(self.number_txt, '<ButtonPress-3>', partial(self.canvas.delete, tag))

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
            self.move_viewport(xe1, ye1, xe2, ye2)

        length = sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        self.canvas.itemconfig(self.number_arrow, arrowshape=(length, length, 20))
        self.canvas.coords(self.number_arrow, x1, y1, x2, y2)

    def _number_set(self, event):
        self.num += 1
        self.num_button['text'] = self.num

    def _change_color(self, event):
        self.color += 1
        self.color_panel['background'] = self.colors[self.color % 9]

    def _change_number(self, event):
        if event.delta > 0:
            self.num += 1
        else:
            if self.num > 1:
                self.num -= 1
        self.num_button['text'] = self.num

    def _recognize(self):
        txt = pytesseract.image_to_string(self.screenshot_area, lang='rus+eng', config=r'--oem 3 --psm 6')
        self.clipboard_clear()
        self.clipboard_append(txt)
        self.update()
        self.destroy()
        notify('Распознанный текст добавлен в буфер обмена', txt)
        # button={'activationType': 'protocol', 'arguments': 'file:notepad.exe', 'content': 'Открыть блокнот'})

    def _done(self):
        self.canvas.delete('service')
        self.canvas.update()
        output = BytesIO()
        image = ImageGrab.grab(bbox=(self.x1, self.y1, self.x2, self.y2))
        image.convert('RGB').save(output, 'BMP')
        data = output.getvalue()[14:]
        output.close()
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
        win32clipboard.CloseClipboard()
        notify('Скриншот добавлен в буфер обмена')

        self.destroy()


if __name__ == "__main__":
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    app = Application()
    app.mainloop()
