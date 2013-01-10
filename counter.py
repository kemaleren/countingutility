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
# - port to ilastik counting applet
# - overlapping dots visualization
# - undo/redo
# - closing without saving warning
# - enable/disable viewing dots
# - preprocessing: train classifier and do connected components
# - do not require initial dots file.
# - allow multiple classes of dots.
# - labeling aids, like masking part of the image.

import logging
import sys
import random

from docopt import docopt
import scipy.misc
import numpy
from PyQt4 import QtGui, QtCore
from PIL import Image, ImageEnhance, ImageQt

CURSOR = QtCore.Qt.CrossCursor

class QDotSignaller(QtCore.QObject):
    deletedSignal = QtCore.pyqtSignal(int, int)

SIGNALLER = QDotSignaller()

class QDot(QtGui.QGraphicsEllipseItem):
    hoverColor    = QtGui.QColor(255, 0, 0)
    normalColor   = QtGui.QColor(0, 0, 255)

    def __init__(self, x, y, radius):
        size = radius * 2
        super(QDot, self).__init__(y - radius, x - radius, size, size)
        self.setAcceptHoverEvents(True)
        self.setAcceptedMouseButtons(QtCore.Qt.RightButton)
        self.x = x
        self.y = y
        self._radius = radius
        self.hovering = False
        self.updateColor()

    def hoverEnterEvent(self, event):
        event.setAccepted(True)
        self.hovering = True
        self.setCursor(QtCore.Qt.BlankCursor)
        self.radius = self.radius # double radius size in setter
        self.updateColor()

    def hoverLeaveEvent(self, event):
        event.setAccepted(True)
        self.hovering = False
        self.setCursor(CURSOR)
        self.radius = self.radius # half radius
        self.updateColor()

    def mousePressEvent(self, event):
        if QtCore.Qt.RightButton == event.button():
            event.setAccepted(True)
            SIGNALLER.deletedSignal.emit(self.x, self.y)

    @property
    def radius(self):
        return self._radius

    @radius.setter
    def radius(self, val):
        self._radius = val
        radius = self.radius
        if self.hovering:
            radius *= 2
        size = radius * 2
        self.setRect(self.y - radius, self.x - radius, size, size)

    def updateColor(self):
        color = self.hoverColor if self.hovering else self.normalColor
        self.setPen(QtGui.QPen(color))
        self.setBrush(QtGui.QBrush(color, QtCore.Qt.SolidPattern))


class MyGraphicsView(QtGui.QGraphicsView):

    def __init__ (self, app, parent=None):
        super (MyGraphicsView, self).__init__ (parent)
        self.parent = parent
        self.setCursor(CURSOR)

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
        self.radius = 1
        self.pos_to_dot = pos_to_dot
        SIGNALLER.deletedSignal.connect(self.remove_dot)

    def add_dot(self, x, y):
        if 0 <= x < self.xdim and 0 <= y < self.ydim:
            logging.info('adding dot at ({}, {})'.format(x, y))
            dot = QDot(x, y, self.radius)
            self.addItem(dot)
            self.pos_to_dot[(x, y)] = dot

    def remove_dot(self, x, y):
        logging.info('removing dot at ({}, {})'.format(x, y))
        dot = self.pos_to_dot.pop((x, y))
        self.removeItem(dot)


def randomColor():
    return QtGui.QColor.fromHsvF(random.random(), 1, 1)


class MainWindow(QtGui.QMainWindow):

    def __init__(self, dotsfile, pos_to_dot, shape, img, imgItem):
        QtGui.QMainWindow.__init__(self)
        self.dotsfile = dotsfile
        self.pos_to_dot = pos_to_dot
        self.shape = shape

        self.alpha = 180
        self.contrast = 1.0

        self.contrastEnhancer = ImageEnhance.Contrast(img)

        self.imgItem = imgItem

        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+S"), self, self.save)

        QtGui.QShortcut(QtGui.QKeySequence("="), self, self.zoomIn)
        QtGui.QShortcut(QtGui.QKeySequence("-"), self, self.zoomOut)

        QtGui.QShortcut(QtGui.QKeySequence("r"), self, self.radiusUp)
        QtGui.QShortcut(QtGui.QKeySequence("f"), self, self.radiusDown)

        QtGui.QShortcut(QtGui.QKeySequence("e"), self, self.alphaUp)
        QtGui.QShortcut(QtGui.QKeySequence("d"), self, self.alphaDown)

        QtGui.QShortcut(QtGui.QKeySequence("w"), self, self.contrastUp)
        QtGui.QShortcut(QtGui.QKeySequence("s"), self, self.contrastDown)

        QtGui.QShortcut(QtGui.QKeySequence("c"), self, self.randomNormalColor)
        QtGui.QShortcut(QtGui.QKeySequence("h"), self, self.randomHoverColor)

    def save(self):
        logging.info('saving ground truth to {}'.format(self.dotsfile))
        arr = numpy.zeros(self.shape)
        dots = self.pos_to_dot.keys()
        arr[zip(*dots)] = 1
        scipy.misc.imsave(self.dotsfile, arr)

    def zoomIn(self):
        logging.info('zooming in')
        self.centralWidget().scale(2, 2)

    def zoomOut(self):
        logging.info('zooming out')
        self.centralWidget().scale(0.5, 0.5)

    def contrastUp(self):
        self.contrast += 1
        self.setContrast()

    def contrastDown(self):
        self.contrast -= 1
        self.setContrast()

    def setContrast(self):
        logging.info('setting contrast to {}'.format(self.contrast))
        img = self.contrastEnhancer.enhance(self.contrast)
        qimg = ImageQt.ImageQt(img)
        pixmap = QtGui.QPixmap.fromImage(qimg)
        self.imgItem.setPixmap(pixmap)

    def alphaUp(self):
        self.alpha = min(255, self.alpha + 20)
        self.setAlpha()

    def alphaDown(self):
        self.alpha = max(0, self.alpha - 20)
        self.setAlpha()

    def setAlpha(self):
        logging.info('setting alpha to {}'.format(self.alpha))
        for dot in self.pos_to_dot.values():
            dot.hoverColor.setAlpha(self.alpha)
            dot.normalColor.setAlpha(self.alpha)
            dot.updateColor()

    @property
    def radius(self):
        return self.centralWidget().scene().radius

    @radius.setter
    def radius(self, val):
        self.centralWidget().scene().radius = val

    def radiusUp(self):
        self.radius += 1
        self.setRadius()

    def radiusDown(self):
        self.radius = max(1, self.radius - 1)
        self.setRadius()

    def setRadius(self):
        logging.info('setting radii to {}'.format(self.radius))
        for dot in self.pos_to_dot.values():
            dot.radius = self.radius

    def randomNormalColor(self):
        logging.info('random normal color')
        c = randomColor()
        for dot in self.pos_to_dot.values():
            dot.normalColor = c
            dot.updateColor()

    def randomHoverColor(self):
        logging.info('random hover color')
        c = randomColor()
        for dot in self.pos_to_dot.values():
            dot.hoverColor = c
            dot.updateColor()


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
    qimg = ImageQt.ImageQt(img)
    pixmap = QtGui.QPixmap.fromImage(qimg)
    imgItem = QtGui.QGraphicsPixmapItem(pixmap)
    scene.addItem(imgItem)

    for x, y in zip(*numpy.where(dots != 0)):
        scene.add_dot(x, y)

    view = MyGraphicsView(app, scene)

    window = MainWindow(dotsfile, pos_to_dot, dots.shape, img, imgItem)
    window.setCentralWidget(view)

    window.show()

    sys.exit(app.exec_())