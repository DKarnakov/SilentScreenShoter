import numpy as np
from scipy.spatial import Voronoi
import tkinter as tk

from shapely import intersection
from shapely.geometry import Polygon


class Application(tk.Tk):
    def __init__(self):
        tk.Tk.__init__(self)

        self.geometry('600x600')
        self.canvas = tk.Canvas(self, cursor='cross', highlightthickness=0)
        self.canvas.pack(side='top', fill='both', expand=True)

        self.coords = []
        self.start_point = []

        self.bind('<Escape>', lambda e: self.destroy())
        self.canvas.bind('<ButtonPress-1>', lambda e: self._create_rect(e))
        self.canvas.bind('<B1-Motion>', lambda e: self._redraw_rect(e))
        self.canvas.bind('<ButtonRelease-1>', lambda e: self._delete_rect())
        # self.canvas.bind('<ButtonRelease-1>', lambda e: self._draw_voronoi())

    def _create_rect(self, event):
        self.start_point = [event.x, event.y]
        # self.bounds = self.canvas.create_rectangle(event.x, event.y, event.x, event.y, tags='voronoi')

    def _redraw_rect(self, event):
        self.coords = [min(self.start_point[0], event.x), min(self.start_point[1], event.y),
                       max(self.start_point[0], event.x), max(self.start_point[1], event.y)]
        width = self.coords[2] - self.coords[0]
        height = self.coords[3] - self.coords[1]
        dens = 50
        if width > dens and height > dens:
            # np.random.seed(1801)
            gen_points = np.random.rand(max(4, (width * height) // dens ** 2), 2)
            self.canvas.delete('v')
            points = np.array([[point[0]*width+self.coords[0], point[1]*height+self.coords[1]] for point in gen_points])
            ext_points = np.array([[self.coords[0]-width*3, self.coords[1]-height*3],
                                   [self.coords[2]+width*3, self.coords[1]-height*3],
                                   [self.coords[2]+width*3, self.coords[3]+height*3],
                                   [self.coords[0]-width*3, self.coords[3]+height*3]])
            points = np.append(points, ext_points, axis=0)
            # for point in points:
            #     self.canvas.create_oval(point[0] - 1, point[1] - 1, point[0] + 1, point[1] + 1, fill='red',
            #                             tags=['voronoi', 'v'])
            vor = Voronoi(points)
            for region in vor.regions:
                if -1 not in region and region != []:
                    polygon = [(vor.vertices[v][0], vor.vertices[v][1]) for v in region]
                    p1 = Polygon(polygon)
                    p2 = Polygon([(self.coords[:2]),(self.coords[2], self.coords[1]),
                                  (self.coords[2:]), (self.coords[0], self.coords[3])])
                    polygon = p1.intersection(p2)
                    self.canvas.create_polygon(list(polygon.exterior.coords), outline='grey50', fill='', tags=['voronoi', 'v'])
        # self.canvas.coords(self.bounds, self.coords)

    def _draw_voronoi(self):
        gen_points = np.random.rand(15, 2)
        width = self.coords[2] - self.coords[0]
        height = self.coords[3] - self.coords[1]
        points = np.array(
            [[point[0] * width + self.coords[0], point[1] * height + self.coords[1]] for point in gen_points])
        for point in points:
            self.canvas.create_oval(point[0] - 1, point[1] - 1, point[0] + 1, point[1] + 1, fill='red', tags='voronoi')
        vor = Voronoi(points)
        for region in vor.regions:
            if -1 not in region and region != []:
                polygon = [(vor.vertices[v][0], vor.vertices[v][1]) for v in region]
                self.canvas.create_polygon(*polygon, outline='grey50', fill='', tags='voronoi')

    def _delete_rect(self):
        self.canvas.delete('voronoi')


if __name__ == '__main__':
    Application().mainloop()
