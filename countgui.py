from __future__ import division

import sys
import scipy.misc
import numpy
from PyQt4 import QtGui, QtCore

SIZE = 5

class QDot(QtGui.QGraphicsEllipseItem):
    _hoverColor    = QtGui.QColor(255, 0, 0, 120)
    _normalColor   = QtGui.QColor(0, 0, 255, 120)

    def __init__(self, x, y, width, height):
        super(QDot, self).__init__(x, y, width, height)
        self._updateColor(self._normalColor)
        self.setAcceptHoverEvents(True)
        
    def hoverEnterEvent(self, event):
        event.setAccepted(True)
        self._updateColor(self._hoverColor)

    def hoverLeaveEvent(self, event):
        event.setAccepted(True)
        self._updateColor(self._normalColor)

    def mousePressEvent(self, event):
        pass

    def mouseReleaseEvent(self, event):
        # delete self
        pass
        
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
        scene.addItem(QDot(y - radius, x - radius, SIZE, SIZE))

    sys.exit(app.exec_())