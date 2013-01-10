from __future__ import division

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

    def __init__(self, xdim, ydim, *args, **kwargs):
        super(MyGraphicsScene, self).__init__(*args, **kwargs)
        self.xdim = xdim
        self.ydim = ydim
        self.pos_to_dot = {}
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


def save():
    print 'got save call'


class MainWindow(QtGui.QMainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+S"), self, save)
        

if __name__ == "__main__":
    image = QtGui.QImage(sys.argv[1])
    dots = scipy.misc.imread(sys.argv[2])

    app = QtGui.QApplication(sys.argv)
    scene = MyGraphicsScene(dots.shape[0], dots.shape[1])

    item = QtGui.QGraphicsPixmapItem(QtGui.QPixmap.fromImage(image))
    scene.addItem(item)

    for x, y in zip(*numpy.where(dots != 0)):
        scene.add_dot(x, y)

    view = MyGraphicsView(scene)

    window = MainWindow()
    window.setCentralWidget(view)

    window.show()

    sys.exit(app.exec_())