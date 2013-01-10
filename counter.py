"""
A simple utility for creating ground truth for counting algorithms.

Author: Kemal Eren

Usage:
  count.py [-c <contrast>] <image> <dotsfile>
  count.py -h | --help

Options:
  -h --help  Show this screen.
  -c <contrast> --contrast=<contrast>  Adjust contrast. [default: 1.0]

"""

from __future__ import division

# TODO
# 0. port to ilastik
# 1. brightness/contrast adjustment
# 2. overlapping dots visualization
# 3. undo/redo
# 4. closing without saving warning
# 5. change size, color, and symbol for dots
# 6. enable/disable viewing dots
# 7. Preprocessing: train classifier and do connected components
# 8. Do not require initial dots file.
# 9. Allow multiple classes of dots.
# 10. Labeling aids, like masking part of the image.

import logging
import sys

from docopt import docopt
import scipy.misc
import numpy
from PyQt4 import QtGui, QtCore
from PIL import Image, ImageEnhance, ImageQt

RADIUS = 3
CURSOR = QtCore.Qt.CrossCursor

class QDotSignaller(QtCore.QObject):
    deletedSignal = QtCore.pyqtSignal(int, int)

SIGNALLER = QDotSignaller()

class QDot(QtGui.QGraphicsEllipseItem):
    _hoverColor    = QtGui.QColor(255, 0, 0, 200)
    _normalColor   = QtGui.QColor(0, 0, 255, 200)

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
        self.setCursor(CURSOR)

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
        if RADIUS <= x < self.xdim - RADIUS and RADIUS <= y < self.ydim - RADIUS:
            logging.info('adding dot at ({}, {})'.format(x, y))
            dot = QDot(x, y)
            self.addItem(dot)
            self.pos_to_dot[(x, y)] = dot

    def remove_dot(self, x, y):
        logging.info('removing dot at ({}, {})'.format(x, y))
        dot = self.pos_to_dot.pop((x, y))
        self.removeItem(dot)


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

    arguments = docopt(__doc__, argv=sys.argv[1:], help=True, version=None)

    dotsfile = arguments['<dotsfile>']
    dots = scipy.misc.imread(dotsfile)

    pos_to_dot = {}

    app = QtGui.QApplication(sys.argv)
    scene = MyGraphicsScene(pos_to_dot, dots.shape[0], dots.shape[1])

    imgfile = arguments['<image>']
    img = Image.open(imgfile).convert('RGBA')

    contrast = ImageEnhance.Contrast(img)
    img = contrast.enhance(float(arguments['--contrast']))
    qimg = ImageQt.ImageQt(img)
    pixmap = QtGui.QPixmap.fromImage(qimg)

    item = QtGui.QGraphicsPixmapItem(pixmap)
    scene.addItem(item)

    for x, y in zip(*numpy.where(dots != 0)):
        scene.add_dot(x, y)

    view = MyGraphicsView(scene)

    window = MainWindow(dotsfile, pos_to_dot, dots.shape)
    window.setCentralWidget(view)

    desktop = app.desktop()
    geom = desktop.screenGeometry()
    sr = view.sceneRect()
    QtCore.QRectF(geom)
    sx = (geom.width() - 10 * RADIUS) / (sr.width())
    sy = (geom.height() - 10 * RADIUS) / (sr.height())

    view.scale(sx, sy)
    view.setCursor(CURSOR)

    window.show()

    sys.exit(app.exec_())