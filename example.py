import tkinter as tk
import math


class Application(tk.Tk):
    def __init__(self):
        tk.Tk.__init__(self)
        self.after(1, lambda: self.focus_force())
        self.geometry('500x500')
        self.canvas = tk.Canvas(self)
        self.canvas.pack(side='top', fill='both', expand=True)

        self.canvas.bind('<ButtonPress-1>', lambda e: self._pen_create(e))
        self.canvas.bind('<B1-Motion>', lambda e: self._pen_draw(e))
        self.canvas.bind('<ButtonRelease-1>', lambda e: self._pen_recognise())
        self.canvas.bind('<ButtonPress-3>', lambda e: self.canvas.delete('all'))

    def _pen_create(self, event):
        self.coords = [event.x, event.y, event.x, event.y]
        self.pen = self.canvas.create_line(self.coords, width=5, capstyle='round', fill='red')

    def _pen_draw(self, event):
        x1, y1 = self.coords[-2:]
        x2, y2 = event.x, event.y
        distance = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        if distance > 3:
            self.coords += (x2, y2)
            self.canvas.coords(self.pen, self.coords)

    def _pen_recognise(self):
        points = []
        for point in range(len(self.coords) // 2):
            points.append((float(self.coords[point * 2]), float(self.coords[(point * 2) + 1])))
        tolerance = 15.0
        shape = simplify_points(points, tolerance=tolerance)
        corners = len(shape)
        if corners == 2:  # line
            pass
        elif math.dist(shape[0], shape[-1]) < tolerance * 2:
            corners -= 1
            if corners == 3:  # triangle
                shape[-1] = shape[0]
            elif corners == 4:  # rectangle
                x1 = min([point[0] for point in points])
                y1 = min([point[1] for point in points])
                x2 = max([point[0] for point in points])
                y2 = max([point[1] for point in points])
                shape = [(x1, y1), (x2, y1), (x2, y2), (x1, y2), (x1, y1)]
            else:  # circle
                x = sum([point[0] for point in points]) / len(points)
                y = sum([point[1] for point in points]) / len(points)
                r = sum([math.dist((x, y), point) for point in points]) / len(points)
                poly = 50
                shape = []
                for angle in range(poly+1):
                    xc = int(x + r * math.sin(math.pi * 2 / poly * angle))
                    yc = int(y + r * math.cos(math.pi * 2 / poly * angle))
                    shape.append((xc, yc))
        else:  # something else
            shape = self.coords
        self.canvas.coords(self.pen, shape)


def simplify_points(pts, tolerance):
    anchor = 0
    floater = len(pts) - 1
    stack = []
    keep = set()

    stack.append((anchor, floater))
    while stack:
        anchor, floater = stack.pop()

        # инициализация отрезка
        if pts[floater] != pts[anchor]:
            anchor_x = float(pts[floater][0] - pts[anchor][0])
            anchor_y = float(pts[floater][1] - pts[anchor][1])
            seg_len = math.sqrt(anchor_x ** 2 + anchor_y ** 2)
            # get the unit vector
            anchor_x /= seg_len
            anchor_y /= seg_len
        else:
            anchor_x = anchor_y = seg_len = 0.0

        # внутренний цикл:
        max_dist = 0.0
        farthest = anchor + 1
        for i in range(anchor + 1, floater):
            dist_to_seg = 0.0
            # compare to anchor
            vec_x = float(pts[i][0] - pts[anchor][0])
            vec_y = float(pts[i][1] - pts[anchor][1])
            seg_len = math.sqrt(vec_x ** 2 + vec_y ** 2)
            # dot product:
            proj = vec_x * anchor_x + vec_y * anchor_y
            if proj < 0.0:
                dist_to_seg = seg_len
            else:
                # compare to floater
                vec_x = float(pts[i][0] - pts[floater][0])
                vec_y = float(pts[i][1] - pts[floater][1])
                seg_len = math.sqrt(vec_x ** 2 + vec_y ** 2)
                # dot product:
                proj = vec_x * (-anchor_x) + vec_y * (-anchor_y)
                if proj < 0.0:
                    dist_to_seg = seg_len
                else:  # расстояние от точки до прямой по теореме Пифагора:
                    dist_to_seg = math.sqrt(abs(seg_len ** 2 - proj ** 2))
                if max_dist < dist_to_seg:
                    max_dist = dist_to_seg
                    farthest = i

        if max_dist <= tolerance:  # использование отрезка
            keep.add(anchor)
            keep.add(floater)
        else:
            stack.append((anchor, farthest))
            stack.append((farthest, floater))

    keep = list(keep)
    keep.sort()
    return [pts[i] for i in keep]


if __name__ == '__main__':
    app = Application()
    app.mainloop()
