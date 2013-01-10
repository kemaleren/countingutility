from __future__ import division

import logging

import sys
import scipy.misc
import numpy
from PyQt4 import QtGui, QtCore

RADIUS = 3

class QDotSignaller(QtCore.QObject):
    deletedSignal = QtCore.pyqtSignal(int, int)

SIGNALLER = QDotSignaller()

class QDot(QtGui.QGraphicsEllipseItem):
    _hoverColor    = QtGui.QColor(255, 0, 0, 120)
    _normalColor   = QtGui.QColor(0, 0, 255, 120)
    
    def __init__(self, x, y):
        radius = RADIUS
        size = radius * 2
        super(QDot, self).__init__(y - radius, x - radius, size, size)
        self._updateColor(self._normalColor)
        self.setAcceptHoverEvents(True)
        self.setAcceptedMouseButtons(QtCore.Qt.RightButton)
        self.x = x
        self.y = y
        self.radius = radius
        self._dragging = False
        
    def hoverEnterEvent(self, event):
        event.setAccepted(True)
        self._updateColor(self._hoverColor)
        radius = self.radius * 2
        size = radius * 2
        self.setRect(self.y - radius, self.x - radius, size, size)
        self.setCursor(QtCore.Qt.BlankCursor)

    def hoverLeaveEvent(self, event):
        event.setAccepted(True)
        self._updateColor(self._normalColor)
        radius = self.radius
        size = radius * 2
        self.setRect(self.y - radius, self.x - radius, size, size)
        self.setCursor(QtCore.Qt.ArrowCursor)

    def mousePressEvent(self, event):
        if QtCore.Qt.RightButton == event.button():
            event.setAccepted(True)
            SIGNALLER.deletedSignal.emit(self.x, self.y)
        
    def _updateColor(self, color):
        self.setPen(QtGui.QPen(color))
        self.setBrush(QtGui.QBrush(color, QtCore.Qt.SolidPattern))


class MyGraphicsView(QtGui.QGraphicsView):

    def __init__ (self, parent = None):
        super (MyGraphicsView, self).__init__ (parent)
        self.parent = parent

    def mousePressEvent(self, event):
        if QtCore.Qt.LeftButton == event.button():
            event.setAccepted(True)
            pos = QtCore.QPointF(self.mapToScene(event.pos()))
            x = int(pos.y())
            y = int(pos.x())
            self.parent.add_dot(x, y)
        else:
            super (MyGraphicsView, self).mousePressEvent(event)


class MyGraphicsScene(QtGui.QGraphicsScene):

    def __init__(self, pos_to_dot, xdim, ydim, *args, **kwargs):
        super(MyGraphicsScene, self).__init__(*args, **kwargs)
        self.xdim = xdim
        self.ydim = ydim
        self.pos_to_dot = pos_to_dot
        SIGNALLER.deletedSignal.connect(self.remove_dot)

    def add_dot(self, x, y):
        if 0 <= x < self.xdim and 0 <= y < self.ydim:
            dot = QDot(x, y)
            self.addItem(dot)
            self.pos_to_dot[(x, y)] = dot

    def remove_dot(self, x, y):
        dot = self.pos_to_dot.pop((x, y))
        self.removeItem(dot)

    @property
    def dots(self):
        return sorted(self.pos_to_dot.keys())



class MainWindow(QtGui.QMainWindow):
    def __init__(self, dotsfile, pos_to_dot, shape):
        QtGui.QMainWindow.__init__(self)
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+S"), self, self.save)
        self.dotsfile = dotsfile
        self.pos_to_dot = pos_to_dot
        self.shape = shape

    def save(self):
        logging.info('saving ground truth')
        arr = numpy.zeros(self.shape)
        dots = self.pos_to_dot.keys()
        arr[zip(*dots)] = 1
        scipy.misc.imsave(self.dotsfile, arr)
        

if __name__ == "__main__":
    format = '%(asctime)s - %(levelname)s - %(message)s'
    logging.basicConfig(level=logging.INFO, format=format)

    image = QtGui.QImage(sys.argv[1])
    dotsfile = sys.argv[2]
    dots = scipy.misc.imread(dotsfile)

    pos_to_dot = {}

    app = QtGui.QApplication(sys.argv)
    scene = MyGraphicsScene(pos_to_dot, dots.shape[0], dots.shape[1])

    item = QtGui.QGraphicsPixmapItem(QtGui.QPixmap.fromImage(image))
    scene.addItem(item)

    for x, y in zip(*numpy.where(dots != 0)):
        scene.add_dot(x, y)

    view = MyGraphicsView(scene)

    window = MainWindow(dotsfile, pos_to_dot, dots.shape)
    window.setCentralWidget(view)

    window.show()

    sys.exit(app.exec_())