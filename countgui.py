from __future__ import division

import sys
import scipy.misc
import numpy
from PyQt4 import QtGui, QtCore

SIZE = 5

class QDot(QtGui.QGraphicsEllipseItem):
    _hoverColor    = QtGui.QColor(255, 0, 0, 120)
    _normalColor   = QtGui.QColor(0, 0, 255, 120)

    def __init__(self, x, y, size):
        super(QDot, self).__init__(y - radius, x - radius, size, size)
        self._updateColor(self._normalColor)
        self.setAcceptHoverEvents(True)
        self.x = x
        self.y = y
        self.size = size
        self._dragging = False
        
    def hoverEnterEvent(self, event):
        event.setAccepted(True)
        self._updateColor(self._hoverColor)
        size = self.size * 2
        radius = size / 2
        self.setRect(self.y - radius, self.x - radius, size, size)
        self.setCursor(QtCore.Qt.BlankCursor)

    def hoverLeaveEvent(self, event):
        event.setAccepted(True)
        self._updateColor(self._normalColor)
        size = self.size
        radius = size / 2
        self.setRect(self.y - radius, self.x - radius, size, size)
        self.setCursor(QtCore.Qt.ArrowCursor)
        
    def _updateColor(self, color):
        self.setPen(QtGui.QPen(color))
        self.setBrush(QtGui.QBrush(color, QtCore.Qt.SolidPattern))


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    image = QtGui.QImage(sys.argv[1])
    item = QtGui.QGraphicsPixmapItem(QtGui.QPixmap.fromImage(image))

    scene = QtGui.QGraphicsScene();
    scene.addItem(item)

    view = QtGui.QGraphicsView(scene)
    view.show()

    dots = scipy.misc.imread(sys.argv[2])
    for x, y in zip(*numpy.where(dots != 0)):
        radius = SIZE / 2
        scene.addItem(QDot(x, y, SIZE))

    sys.exit(app.exec_())