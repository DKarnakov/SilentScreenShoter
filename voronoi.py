import numpy as np
from scipy.spatial import Voronoi, QhullError
import tkinter as tk
from shapely.geometry import Polygon


class Application(tk.Tk):
    def __init__(self):
        tk.Tk.__init__(self)

        self.geometry('1000x600')
        self.canvas = tk.Canvas(self, cursor='cross', highlightthickness=0)
        self.canvas.pack(side='top', fill='both', expand=True)

        self.coords = []
        self.start_point = []
        self.polygons = []
        self.is_construct = False

        self.bind('<Escape>', lambda e: self.destroy())
        self.canvas.bind('<ButtonPress-1>', lambda e: self._start_drawing(e))
        self.canvas.bind('<B1-Motion>', lambda e: self._redraw_mosaic(e))
        self.canvas.bind('<ButtonRelease-1>', lambda e: self._offset_mosaic(e))

    def _start_drawing(self, event):
        self.start_point = [event.x, event.y]

    def _redraw_mosaic(self, event, relax=False):
        self.coords = [min(self.start_point[0], event.x), min(self.start_point[1], event.y),
                       max(self.start_point[0], event.x), max(self.start_point[1], event.y)]
        width = self.coords[2] - self.coords[0]
        height = self.coords[3] - self.coords[1]
        dens = 30
        self.canvas.delete('all')
        if relax:
            points = np.array([list(*polygon.centroid.coords) for polygon in self.polygons])
        else:
            np.random.seed(1801)
            gen_points = np.random.rand(max(4, (width * height) // dens ** 2), 2)
            points = np.array([[point[0]*width+self.coords[0], point[1]*height+self.coords[1]] for point in gen_points])
        ext_points = np.array([[self.coords[0]-width*3, self.coords[1]-height*3],
                               [self.coords[2]+width*3, self.coords[1]-height*3],
                               [self.coords[2]+width*3, self.coords[3]+height*3],
                               [self.coords[0]-width*3, self.coords[3]+height*3]])
        points = np.append(points, ext_points, axis=0)
        try:
            vor = Voronoi(points)
            self.polygons = []
            for region in vor.regions:
                if -1 not in region and region != []:
                    polygon = [(vor.vertices[v][0], vor.vertices[v][1]) for v in region]
                    p1 = Polygon(polygon)
                    p2 = Polygon([(self.coords[:2]), (self.coords[2], self.coords[1]),
                                  (self.coords[2:]), (self.coords[0], self.coords[3])])
                    polygon = p1.intersection(p2)
                    self.polygons.append(polygon)
                    self.canvas.create_polygon(list(polygon.exterior.coords), outline='grey50', fill='')
        except QhullError:
            ...

    def _offset_mosaic(self, event):
        while not self.is_construct:
            self.is_construct = True
            for polygon in self.polygons:
                polygon_offset = polygon.buffer(-7)
                if polygon_offset.is_empty:
                    self.is_construct = False
                    self._redraw_mosaic(event, relax=True)
                    self.update()
                    break
                else:
                    self.canvas.create_polygon(list(polygon_offset.exterior.coords),
                                               outline='grey25', fill='', smooth=True)
        self.is_construct = False


if __name__ == '__main__':
    Application().mainloop()