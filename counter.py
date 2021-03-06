"""A utility for creating ground truth for counting algorithms.

Usage:
  counter.py [options] <image> <dotfile>
  counter.py -h | --help

Arguments:
  <image>   : Path to an image file containing the data.

  <dotfile> : Path to a numpy array file (*.pkl or *.npy or *.npz)
              containing a binary array of the same shape as <image>.
              If it does not exist, it will be created upon saving;
              otherwise, it will be overwritten.

Options:
  -h --help            Show this screen.
  -r, --reference IMG  Use a reference image.

Mouse controls:
  left click  : place dot
  right click : delete dot
  Ctrl + drag : pan
  mousewheel  : zoom

Key controls :
  Ctrl + s    : save
  arrow keys  : pan
  =/-         : zoom
  r/f         : resize dots
  e/d         : dot transparency
  w/s         : image contrast
  Space       : toggle reference image
  c           : randomize dot colors

Dependencies:
  numpy, pyqt, pil, docopt

Author: Kemal Eren

"""

# TODO
# - generalize multiple channels/reference images
# - overlapping dots visualization
# - undo/redo
# - preprocessing: train classifier and do connected components
# - allow multiple classes of dots.
# - labeling aids, like masking part of the image.

import logging
import sys
import random

from docopt import docopt
import numpy
from PyQt4 import QtGui, QtCore
from PIL import Image, ImageEnhance, ImageQt

CURSOR = QtCore.Qt.CrossCursor

class QDotSignaller(QtCore.QObject):
    createdSignal = QtCore.pyqtSignal(int, int)
    deletedSignal = QtCore.pyqtSignal(int, int)

SIGNALLER = QDotSignaller()

class QDot(QtGui.QGraphicsEllipseItem):
    hoverColor    = QtGui.QColor(255, 0, 0)
    normalColor   = QtGui.QColor(0, 0, 255)

    def __init__(self, x, y, radius):
        x = x + 0.5
        y = y + 0.5
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
        self.radius = self.radius # modified radius b/c hovering
        self.updateColor()

    def hoverLeaveEvent(self, event):
        event.setAccepted(True)
        self.hovering = False
        self.setCursor(CURSOR)
        self.radius = self.radius # no longer hovering
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
            radius *= 1.25
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
        self.setDragMode(QtGui.QGraphicsView.RubberBandDrag)
        self._isPanning = False
        self._mousePressed = False


    def mousePressEvent(self,  event):
        if event.button() == QtCore.Qt.LeftButton:
            self._mousePressed = True
            event.accept()
            if self._isPanning:
                self._dragPos = event.pos()
            else:
                pos = QtCore.QPointF(self.mapToScene(event.pos()))
                x = int(pos.y())
                y = int(pos.x())
                self.parent.add_dot(x, y)
        else:
            super (MyGraphicsView, self).mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._mousePressed and self._isPanning:
            newPos = event.pos()
            diff = newPos - self._dragPos
            self._dragPos = newPos
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - diff.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - diff.y())
            event.accept()
        else:
            super(MyGraphicsView, self).mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            if not (event.modifiers() & QtCore.Qt.ControlModifier):
                self._isPanning = False
            self._mousePressed = False
        super(MyGraphicsView, self).mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Control and not self._mousePressed:
            self._isPanning = True
        else:
            super(MyGraphicsView, self).keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.key() == QtCore.Qt.Key_Control:
            if not self._mousePressed:
                self._isPanning = False
        else:
            super(MyGraphicsView, self).keyPressEvent(event)


class MyGraphicsScene(QtGui.QGraphicsScene):

    def __init__(self, pos_to_dot, xdim, ydim, *args, **kwargs):
        super(MyGraphicsScene, self).__init__(*args, **kwargs)
        self.xdim = xdim
        self.ydim = ydim
        self.radius = 0.5
        self.pos_to_dot = pos_to_dot
        SIGNALLER.deletedSignal.connect(self.remove_dot)

    def add_dot(self, x, y):
        if (x, y) in pos_to_dot:
            return
        if 0 <= x < self.xdim and 0 <= y < self.ydim:
            logging.info('adding dot at ({}, {})'.format(x, y))
            dot = QDot(x, y, self.radius)
            self.addItem(dot)
            self.pos_to_dot[(x, y)] = dot
            SIGNALLER.createdSignal.emit(x, y)

    def remove_dot(self, x, y):
        logging.info('removing dot at ({}, {})'.format(x, y))
        dot = self.pos_to_dot.pop((x, y))
        self.removeItem(dot)


class MainWindow(QtGui.QMainWindow):

    def __init__(self, dotfile, pos_to_dot, shape, img, imgItem,
                 ref=None, ref_imgItem=None):
        QtGui.QMainWindow.__init__(self)
        self.dotfile = dotfile
        self.pos_to_dot = pos_to_dot
        self.shape = shape

        self.alpha = 180
        self.contrast = 1.0

        self.contrastEnhancer = ImageEnhance.Contrast(img)
        if ref is not None:
            self.ref_contrastEnhancer = ImageEnhance.Contrast(ref)
            self.ref_contrast = 1.0

        self.imgItem = imgItem
        self.ref_imgItem = ref_imgItem

        self.ref_active = False

        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+S"), self, self.save)

        QtGui.QShortcut(QtGui.QKeySequence("="), self, self.zoomIn)
        QtGui.QShortcut(QtGui.QKeySequence("-"), self, self.zoomOut)

        QtGui.QShortcut(QtGui.QKeySequence("r"), self, self.radiusUp)
        QtGui.QShortcut(QtGui.QKeySequence("f"), self, self.radiusDown)

        QtGui.QShortcut(QtGui.QKeySequence("e"), self, self.alphaUp)
        QtGui.QShortcut(QtGui.QKeySequence("d"), self, self.alphaDown)

        QtGui.QShortcut(QtGui.QKeySequence("w"), self, self.contrastUp)
        QtGui.QShortcut(QtGui.QKeySequence("s"), self, self.contrastDown)

        QtGui.QShortcut(QtGui.QKeySequence("c"), self, self.randomColor)

        if ref is not None and ref_imgItem is not None:
            QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Space), self, self.toggleReference)

        self.dirty = False

        SIGNALLER.deletedSignal.connect(self.setDirty)
        SIGNALLER.createdSignal.connect(self.setDirty)

    def setDirty(self, *args, **kwargs):
        self.dirty = True

    def save(self):
        logging.info('saving ground truth to {}'.format(self.dotfile))
        arr = numpy.zeros(self.shape)
        dots = self.pos_to_dot.keys()
        arr[zip(*dots)] = 1
        numpy.save(self.dotfile, arr)
        self.dirty = False

    def zoomIn(self):
        logging.info('zooming in')
        self.centralWidget().scale(2, 2)

    def zoomOut(self):
        logging.info('zooming out')
        self.centralWidget().scale(0.5, 0.5)

    def contrastUp(self):
        if self.ref_active:
            self.ref_contrast += 1
        else:
            self.contrast += 1
        self.setContrast()

    def contrastDown(self):
        if self.ref_active:
            self.ref_contrast -= 1
        else:
            self.contrast -= 1
        self.setContrast()

    def setContrast(self):
        if self.ref_active:
            img = self.ref_contrastEnhancer.enhance(self.ref_contrast)
            qimg = ImageQt.ImageQt(img)
            pixmap = QtGui.QPixmap.fromImage(qimg)
            self.ref_imgItem.setPixmap(pixmap)
        else:
            img = self.contrastEnhancer.enhance(self.contrast)
            qimg = ImageQt.ImageQt(img)
            pixmap = QtGui.QPixmap.fromImage(qimg)
            self.imgItem.setPixmap(pixmap)

    def alphaUp(self):
        self.alpha = min(255, self.alpha + 50)
        self.setAlpha()

    def alphaDown(self):
        self.alpha = max(0, self.alpha - 50)
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
        self.radius = min(20, self.radius + 0.5)
        self.setRadius()

    def radiusDown(self):
        self.radius = max(0.5, self.radius - 0.5)
        self.setRadius()

    def setRadius(self):
        logging.info('setting radii to {}'.format(self.radius))
        for dot in self.pos_to_dot.values():
            dot.radius = self.radius

    def randomColor(self):
        logging.info('random color')
        h = random.random()
        c1 = QtGui.QColor.fromHsvF(h, 1, 1)
        c2 = QtGui.QColor.fromHsvF((h + 0.5) % 1, 1, 1)
        QDot.normalColor = c1
        QDot.hoverColor = c2

        for dot in self.pos_to_dot.values():
            dot.normalColor = c1
            dot.hoverColor = c2
            dot.updateColor()

    def closeEvent(self, event):
        if self.dirty:
            quit_msg = "You have unsaved changes. Are you sure you want to quit?"
            reply = QtGui.QMessageBox.question(self, 'Message',
                                               quit_msg, QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
            if reply == QtGui.QMessageBox.Yes:
                event.accept()
            else:
                event.ignore()

    def toggleReference(self):
        if self.ref_active:
            self.imgItem.setVisible(True)
            self.ref_imgItem.setVisible(False)
        else:
            self.imgItem.setVisible(False)
            self.ref_imgItem.setVisible(True)
        self.ref_active = not self.ref_active


if __name__ == "__main__":
    format = '%(asctime)s - %(levelname)s - %(message)s'
    logging.basicConfig(level=logging.WARNING, format=format)

    arguments = docopt(__doc__, argv=sys.argv[1:], help=True, version=None)

    imgfile = arguments['<image>']
    img = Image.open(imgfile).convert('RGBA')

    dotfile = arguments['<dotfile>']
    try:
        dots = numpy.load(dotfile).astype(numpy.int8)
    except IOError:
        dots = numpy.zeros(img.size[::-1])

    if not numpy.all((dots == 0) + (dots == 1)):
        raise Exception('dots file contains values besides 0 and 1')

    pos_to_dot = {}

    app = QtGui.QApplication(sys.argv)
    scene = MyGraphicsScene(pos_to_dot, dots.shape[0], dots.shape[1])

    qimg = ImageQt.ImageQt(img)
    pixmap = QtGui.QPixmap.fromImage(qimg)
    imgItem = QtGui.QGraphicsPixmapItem(pixmap)
    scene.addItem(imgItem)

    kwargs = {}

    if arguments['--reference'] is not None:
        ref_imgfile = arguments['--reference']
        ref_img = Image.open(ref_imgfile).convert('RGBA')
        ref_qimg = ImageQt.ImageQt(ref_img)
        ref_pixmap = QtGui.QPixmap.fromImage(ref_qimg)
        ref_imgItem = QtGui.QGraphicsPixmapItem(ref_pixmap)
        scene.addItem(ref_imgItem)
        ref_imgItem.setVisible(False)
        kwargs['ref'] = ref_img
        kwargs['ref_imgItem'] = ref_imgItem

    for x, y in zip(*numpy.where(dots != 0)):
        scene.add_dot(x, y)

    view = MyGraphicsView(app, scene)

    window = MainWindow(dotfile, pos_to_dot, dots.shape, img, imgItem, **kwargs)
    window.setCentralWidget(view)

    window.show()

    sys.exit(app.exec_())