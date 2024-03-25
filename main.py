from PIL import ImageGrab, ImageTk, ImageEnhance
import tkinter as tk
from tkinter import ttk
import pytesseract
from io import BytesIO
import win32clipboard


class Application(tk.Tk):
    def __init__(self):
        tk.Tk.__init__(self)

        self.screenshot_area = None
        self.move_point = []
        self.attributes('-fullscreen', True)

        self.canvas = tk.Canvas(self, cursor="cross", highlightthickness=0)
        self.canvas.pack(side="top", fill="both", expand=True)

        self.canvas.bind('<ButtonPress-1>', self.create_editor)
        self.canvas.bind('<B1-Motion>', self.place_editor)
        self.canvas.bind('<ButtonRelease-1>', self.start_editing)
        self.bind('<Escape>', lambda event: self.destroy())

        self.style = ttk.Style()
        # self.style.theme_use('alt')
        self.style.configure('RoundedFrame.TFrame')
        self.panel = ttk.Frame(self.canvas, style='RoundedFrame.TFrame')

        self.x1 = self.y1 = None
        self.x2 = self.y2 = None

        self.screenshot_area_tk = None
        self.editor = None
        self.border = None

        self.point = {}

        self._background()

    def _background(self):
        self.image = ImageGrab.grab()

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
        self.canvas.tag_bind(self.point[position], '<B1-Motion>', lambda event: self.change_editor(position, event))
        self.canvas.tag_bind(self.point[position], '<ButtonRelease-1>', lambda event: self.fix_editor(position, event))

    def _move_corner(self, position, x, y):
        self.canvas.moveto(self.point[position], x - 5, y - 5)

    def create_editor(self, event):
        x1, y1, x2, y2 = event.x, event.y, event.x + 2, event.y + 2

        screenshot_area = self.image.crop((x1, y1, x2, y2))
        self.screenshot_area_tk = ImageTk.PhotoImage(screenshot_area)

        self.editor = self.canvas.create_image(x1, y1, anchor="nw", image=self.screenshot_area_tk)

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

    def place_editor(self, event):

        x1, x2, y1, y2 = self.x1, event.x, self.y1, event.y

        anchor = 's' if y2 < y1 else 'n'
        anchor = anchor + 'e' if x2 < x1 else anchor + 'w'

        x2, x1 = (x1, x2) if x2 < x1 else (x2, x1)
        y2, y1 = (y1, y2) if y2 < y1 else (y2, y1)

        self.screenshot_area = self.image.crop((x1, y1, x2, y2))
        self.screenshot_area_tk = ImageTk.PhotoImage(self.screenshot_area)
        self.canvas.itemconfig(self.editor, image=self.screenshot_area_tk, anchor=anchor)

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

    def change_editor(self, corner, event):
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
        self.canvas.moveto(self.editor, x1, y1)
        self.canvas.itemconfig(self.editor, image=self.screenshot_area_tk, anchor='nw')

        self.canvas.coords(self.border, (x1, y1, x2, y2))

        self._move_corner('nw', x1, y1)
        self._move_corner('n', (x2 + x1) // 2, y1)
        self._move_corner('ne', x2, y1)
        self._move_corner('e', x2, (y2 + y1) // 2)
        self._move_corner('se', x2, y2)
        self._move_corner('s', (x2 + x1) // 2, y2)
        self._move_corner('sw', x1, y2)
        self._move_corner('w', x1, (y2 + y1) // 2)

    def fix_editor(self, corner, event):
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

    def start_editing(self, event):
        self.fix_editor('se', event)

        self.canvas.unbind('<B1-Motion>')
        self.canvas.unbind('<ButtonPress-1>')
        self.canvas.unbind('<ButtonRelease-1>')

        self.canvas.create_window(self.canvas.winfo_width() // 2, 10, window=self.panel, anchor="n", tags='service')
        padding = (3, 3)
        arrow_button = ttk.Button(self.panel, text='Стрелка', command=lambda: self._set_arrow())
        arrow_button.pack(padx=padding[0], pady=padding[1], side='left')
        recognize_button = ttk.Button(self.panel, text='Распознать', command=lambda: self._recognize())
        recognize_button.pack(padx=padding[0], pady=padding[1], side='left')
        button3 = ttk.Button(self.panel, text='Карандаш', command=lambda: self._set_pen())
        button3.pack(padx=padding[0], pady=padding[1], side='left')
        done_button = ttk.Button(self.panel, text="Ok", command=lambda: self._done())
        done_button.pack(padx=padding[0], pady=padding[1], side='right')
        self._set_arrow()

    def _recognize(self):
        txt = pytesseract.image_to_string(self.screenshot_area, lang='rus+eng', config=r'--oem 3 --psm 6')
        self.clipboard_clear()
        self.clipboard_append(txt)
        self.update()
        self.destroy()

    def _set_arrow(self):
        self.canvas.tag_bind(self.editor, '<ButtonPress-1>', lambda event: self._arrow_create(event))
        self.canvas.tag_bind(self.editor, '<B1-Motion>', lambda event: self._arrow_move(event))
        self.canvas.unbind('<ButtonRelease-1>')

    def _arrow_create(self, event):
        self.arrow = self.canvas.create_line(event.x, event.y, event.x, event.y,
                                             fill='red',
                                             width=5,
                                             arrowshape=(17, 25, 7),
                                             arrow=tk.LAST)

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

            self.screenshot_area = self.image.crop((xe1, ye1, xe2, ye2))
            self.screenshot_area_tk = ImageTk.PhotoImage(self.screenshot_area)
            self.canvas.moveto(self.editor, xe1, ye1)
            self.canvas.itemconfig(self.editor, image=self.screenshot_area_tk, anchor='nw')

            self.canvas.coords(self.border, (xe1, ye1, xe2, ye2))

            self._move_corner('nw', xe1, ye1)
            self._move_corner('n', (xe2 + xe1) // 2, ye1)
            self._move_corner('ne', xe2, ye1)
            self._move_corner('e', xe2, (ye2 + ye1) // 2)
            self._move_corner('se', xe2, ye2)
            self._move_corner('s', (xe2 + xe1) // 2, ye2)
            self._move_corner('sw', xe1, ye2)
            self._move_corner('w', xe1, (ye2 + ye1) // 2)

        self.canvas.coords(self.arrow, x1, y1, x2, y2)

    def _set_pen(self):
        self.canvas.tag_bind(self.editor, '<ButtonPress-1>', lambda event: self._pen_create(event))
        self.canvas.tag_bind(self.editor, '<B1-Motion>', lambda event: self._pen_draw(event))
        self.canvas.unbind('<ButtonRelease-1>')

    def _pen_create(self, event):
        pen_size = 5
        x1, y1 = event.x, event.y
        x2, y2 = event.x, event.y
        self.pen = self.canvas.create_line(x1, y1, x2, y2, fill='red', width=pen_size)

    def _pen_draw(self, event):
        coord = self.canvas.coords(self.pen)
        coord.append(event.x)
        coord.append(event.y)
        self.canvas.coords(self.pen, coord)

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

        self.destroy()


if __name__ == "__main__":
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    app = Application()
    app.mainloop()
