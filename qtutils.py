#!/usr/bin/python
# -*- coding: utf-8 -*-

import platform
import utils
from PyQt5 import QtWidgets, QtCore, QtGui


def initDisplay(parent, pos=(None, None), size=(None, None), setAsWallpaper=False, fullScreen=False, frameless=False,
                transparentBkg=False, opacity=1, noFocus=False, caption=None, icon=None, aot=False, aob=False):

    if caption:
        parent.setWindowTitle(caption)
    if icon:
        parent.setWindowIcon(QtGui.QIcon(utils.resource_path(icon)))

    xmax, ymax = size
    screen = QtWidgets.QApplication.primaryScreen()
    screenSize = screen.size()

    if setAsWallpaper or fullScreen:
        if setAsWallpaper:
            if "Linux" in platform.platform():
                parent.setAttribute(QtCore.Qt.WA_X11NetWmWindowTypeDesktop)
                parent.setAttribute(QtCore.Qt.WA_X11DoNotAcceptFocus)
            parent.setFocusPolicy(QtCore.Qt.NoFocus)
            parent.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
            parent.setAttribute(QtCore.Qt.WA_InputMethodTransparent)
            parent.setAttribute(QtCore.Qt.WA_ShowWithoutActivating)
            parent.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.CustomizeWindowHint | QtCore.Qt.WindowStaysOnBottomHint | QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowDoesNotAcceptFocus)
        else:
            parent.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.CustomizeWindowHint | QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowDoesNotAcceptFocus)
            parent.showFullScreen()
        xmax, ymax = screenSize.width(), screenSize.height()
    else:
        if frameless:
            parent.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.CustomizeWindowHint | QtCore.Qt.FramelessWindowHint)
        if pos[0] is not None and pos[1] is not None:
            x, y = pos
            parent.move(QtCore.QPoint(int(x), int(y)))
        if (xmax is not None and ymax is not None and (xmax < screenSize.width() or ymax < screenSize.height())) or \
                xmax is None or ymax is None:
            parent.setFixedSize(xmax, ymax)
        else:
            parent.showFullScreen()
            xmax, ymax = screenSize.width(), screenSize.height()

    if aot:
        flags = int(parent.windowFlags()) | QtCore.Qt.Window | QtCore.Qt.CustomizeWindowHint | QtCore.Qt.WindowStaysOnTopHint
        parent.setWindowFlags(flags)
    elif aob and not setAsWallpaper:
        flags = int(parent.windowFlags()) | QtCore.Qt.Window | QtCore.Qt.CustomizeWindowHint | QtCore.Qt.WindowDoesNotAcceptFocus
        parent.setWindowFlags(flags)

    if noFocus:
        if "Linux" in platform.platform():
            parent.setAttribute(QtCore.Qt.WA_X11DoNotAcceptFocus)
        parent.setFocusPolicy(QtCore.Qt.NoFocus)
        parent.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        parent.setAttribute(QtCore.Qt.WA_InputMethodTransparent)
        flags = int(parent.windowFlags()) | QtCore.Qt.Window | QtCore.Qt.CustomizeWindowHint | QtCore.Qt.WindowDoesNotAcceptFocus
        parent.setWindowFlags(flags)

    if transparentBkg:
        parent.setAttribute(QtCore.Qt.WA_NoSystemBackground, True)
        parent.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        parent.setWindowFlags(int(parent.windowFlags()) | QtCore.Qt.Window | QtCore.Qt.CustomizeWindowHint | QtCore.Qt.FramelessWindowHint)
    elif opacity != 1 and not transparentBkg:
        parent.setWindowOpacity(opacity)

    return xmax, ymax


def getScreenSize():
    size = QtWidgets.QApplication.primaryScreen().size()
    return size.width(), size.height()


def loadFont(font):
    loadedFont = -1
    fontId = QtGui.QFontDatabase.addApplicationFont(utils.resource_path(font))
    if fontId >= 0:
        families = QtGui.QFontDatabase.applicationFontFamilies(fontId)
        if len(families) > 0:
            loadedFont = QtGui.QFont(families[0])
    return loadedFont


class Marquee(QtWidgets.QLabel):
    # Based on moving a QLabel with a pixmap generated from the desired text
    # Good try, but still consumes a lot of CPU (for an RPi or alike, not for a PC)
    # Smooth=False is an ugly hack to make it work on RPi 1 whilst not raising CPU usage to 100%

    def __init__(self, parent, font=None, stylesheet=None, fps=60, direction=QtCore.Qt.RightToLeft, smooth=True):
        super(Marquee, self).__init__(parent)

        self.hide()

        self._parent = parent
        self._direction = direction
        self._smooth = smooth
        self._lag = (1 if smooth else 20)
        self._fps = fps
        self._speed = fps / self._lag
        self._initText = ""
        self._blanksLen = 0
        self._initX = 0
        self._x = 0
        self._y = 0

        if font:
            _font = font
        else:
            _font = self._parent.font()
        self.setFont(_font)
        self._fm = QtGui.QFontMetrics(self.font())

        if stylesheet:
            _style = stylesheet
        else:
           _style = self._parent.styleSheet()
        self.setStyleSheet(_style)

        self.setSizePolicy(self._parent.sizePolicy())
        self.setGeometry(self._parent.geometry())

        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self.translate)

    def setText(self, text):

        self._initText = text

        if self._smooth:

            bcolor = getQColorfromRGB(getBkgColor(self.styleSheet()))
            fcolor = getQColorfromRGB(getColor(self.styleSheet()))
            img = QtGui.QPixmap(createImgFromText(text, font=self.font(), bcolor=bcolor, fcolor=fcolor))
            self.setPixmap(img)
            self.setFixedWidth(img.width())
            self.setFixedHeight(img.height())

            if self._direction == QtCore.Qt.LeftToRight:
                self._initX = (self._parent.width() / 2) - self.width()
                self.setAlignment(QtCore.Qt.AlignRight)
            else:
                self._initX = self._parent.width()
                self.setAlignment(QtCore.Qt.AlignLeft)

        else:

            self._blanksLen = int(self._parent.width() / self._fm.width("B") * 1.5)
            if self._direction == QtCore.Qt.LeftToRight:
                text = text + (" " * self._blanksLen)
            else:
                text = (" " * self._blanksLen) + text
            super(Marquee, self).setText(text)

            if self._direction == QtCore.Qt.LeftToRight:
                self._initX = (self._parent.width() / 2) - self.width()
                self.setAlignment(QtCore.Qt.AlignRight)
            else:
                self._initX = 0
                self.setAlignment(QtCore.Qt.AlignLeft)

        self._x = self._initX
        self._y = self._parent.pos().y()

    @QtCore.pyqtSlot()
    def translate(self):
        if self._smooth:
            if self._direction == QtCore.Qt.LeftToRight:
                if self._x < self._parent.width():
                    self._x += self._lag
                else:
                    self._x = self._initX
            else:
                if abs(self._x) + (self._parent.width() / 2) < self.width():
                    self._x -= self._lag
                else:
                    self._x = self._initX
            self.move(self._x, self._y)
        else:
            if self._direction == QtCore.Qt.LeftToRight:
                text = self.text()[:-1]
            else:
                text = self.text()[1:]
            if len(text) == 0:
                text = self._initText
            super(Marquee, self).setText(text)

    def paintEvent(self, event):
        if self._smooth:
            self.move(self._x, self._y)
        super(Marquee, self).paintEvent(event)

    def start(self):
        if not self._timer.isActive():
            self._timer.start(int(1 / self._speed * 1000))
            self.show()

    def pause(self):
        self._timer.stop()

    def stop(self):
        self._timer.stop()
        self.clear()
        self.hide()

    def getFPS(self):
        return self._fps

    def setFPS(self, fps):
        self._fps = fps
        self._speed = fps / self._lag
        if self._timer.isActive():
            self._timer.stop()
            self._timer.start(int(1 / self._speed * 1000))

    def getDirection(self):
        return self._direction

    def setDirection(self, direction):
        self._direction = direction


class Clock(QtWidgets.QLabel):
    # https://www.geeksforgeeks.org/create-analog-clock-using-pyqt5-in-python/

    # constructor
    def __init__(self, bcolor=QtCore.Qt.green, scolor=QtCore.Qt.red, bkcolor="black", size=300, hoffset=0, moffset=0, drawsec=False):
        QtWidgets.QLabel.__init__(self, None)

        # creating a timer object
        self.timer = QtCore.QTimer(self)

        # adding action to the timer
        # update the whole code
        self.timer.timeout.connect(self.update)

        # setting start time of timer i.e 1 second or 1 minute (if no seconds will be painted)
        lag = (1000 if drawsec else 60000)
        self.timer.start(lag)

        # setting window title
        self.setWindowTitle('Clock')

        # setting window geometry
        # self.setGeometry(200, 200, 300, 300)
        self.setFixedSize(size, size)

        # setting background color to the window
        self.setStyleSheet("background-color:"+bkcolor+";")

        # creating hour hand
        self.hPointer = QtGui.QPolygon([QtCore.QPoint(6, 7),
                                        QtCore.QPoint(-6, 7),
                                        QtCore.QPoint(0, -50)])

        # creating minute hand
        self.mPointer = QtGui.QPolygon([QtCore.QPoint(6, 7),
                                  QtCore.QPoint(-6, 7),
                                  QtCore.QPoint(0, -70)])

        # creating second hand
        self.drawsec = drawsec
        if self.drawsec:
            self.sPointer = QtGui.QPolygon([QtCore.QPoint(1, 1),
                                      QtCore.QPoint(-1, 1),
                                      QtCore.QPoint(0, -90)])
        # colors
        # color for minute and hour hand
        self.bColor = bcolor

        # color for second hand
        self.sColor = scolor

        # time offset for different timeZones
        self.hoffset = hoffset
        self.moffset = moffset

    # method for paint event
    def paintEvent(self, event):

        # getting minimum of width and height
        # so that clock remain square
        rec = min(self.width(), self.height())

        # getting current time
        tik = QtCore.QTime.currentTime()
        tik.setHMS(tik.hour() + self.hoffset, tik.minute() + self.moffset, tik.second())

        # creating a painter object
        painter = QtGui.QPainter(self)

        # method to draw the hands
        # argument : color rotation and which hand should be pointed
        def drawPointer(color, rotation, pointer):

            # setting brush
            painter.setBrush(QtGui.QBrush(color))

            # saving painter
            painter.save()

            # rotating painter
            painter.rotate(rotation)

            # draw the polygon i.e hand
            painter.drawConvexPolygon(pointer)

            # restore the painter
            painter.restore()

        # tune up painter
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        # translating the painter
        painter.translate(self.width() / 2, self.height() / 2)

        # scale the painter
        painter.scale(rec / 200, rec / 200)

        # set current pen as no pen
        painter.setPen(QtCore.Qt.NoPen)

        # draw each hand
        drawPointer(self.bColor, (30 * (tik.hour() + tik.minute() / 60)), self.hPointer)
        drawPointer(self.bColor, (6 * (tik.minute() + tik.second() / 60)), self.mPointer)
        if self.drawsec:
            drawPointer(self.sColor, (6 * tik.second()), self.sPointer)

        # drawing background
        painter.setPen(QtGui.QPen(self.bColor))

        # for loop
        for i in range(0, 60):

            # drawing background lines
            if (i % 5) == 0:
                painter.drawLine(87, 0, 97, 0)

            # rotating the painter
            painter.rotate(6)

        # ending the painter
        painter.end()

    def stop(self):
        self.timer.stop()
        self.clear()


# def sendkeys(parent, char="", qkey=None, modifier=QtCore.Qt.KeyboardModifiers.NoModifier, text=None):
#     # https://stackoverflow.com/questions/33758820/send-keystrokes-from-unicode-string-pyqt-pyside
#
#     if qkey:
#         char = qkey
#     elif char:
#         char = QtGui.QKeySequence.fromString(char)[0]
#     else:
#         return
#
#     if not text:
#         event = QtGui.QKeyEvent(QtCore.QEvent.KeyPress, char, modifier)
#     else:
#         event = QtGui.QKeyEvent(QtCore.QEvent.KeyPress, char, modifier, text)
#     QtCore.QCoreApplication.sendEvent(parent, event)


def createImgFromText(text, font, bcolor=QtGui.QColor(QtCore.Qt.GlobalColor.black), fcolor=QtGui.QColor(QtCore.Qt.GlobalColor.white), saveFile=""):
    # https://stackoverflow.com/questions/41904610/how-to-create-a-simple-image-qimage-with-text-and-colors-in-qt-and-save-it-as

    fm = QtGui.QFontMetrics(font)
    width = int(fm.width(text) * 1.06)
    height = fm.height()
    img = QtGui.QImage(QtCore.QSize(width, height), QtGui.QImage.Format_RGB32)
    p = QtGui.QPainter(img)
    p.setBrush(QtGui.QBrush(bcolor))
    p.fillRect(QtCore.QRectF(0, 0, width, height), bcolor)
    p.setPen(QtGui.QPen(fcolor))
    p.setFont(font)
    p.drawText(QtCore.QRectF(0, 0, width, height), text)
    if saveFile:
        img.save(saveFile)
    return img


def resizeImageWithQT(src, width, height, keepAspectRatio=True, expand=True):

    pixmap_resized = QtGui.QPixmap()
    pixmap = QtGui.QPixmap(src)

    if not pixmap.isNull():
        if keepAspectRatio:
            if expand:
                flag = QtCore.Qt.AspectRatioMode.KeepAspectRatioByExpanding
            else:
                flag = QtCore.Qt.AspectRatioMode.KeepAspectRatio
        else:
            flag = QtCore.Qt.AspectRatioMode.IgnoreAspectRatio
        pixmap_resized = pixmap.scaled(int(width), int(height), flag, QtCore.Qt.TransformationMode.SmoothTransformation)
    return pixmap_resized


def getColor(styleSheet):
    props = styleSheet.replace("\n", "").split(";")
    for prop in props:
        if prop[:6] == "color:":
            return prop
    color = QtGui.QColor(QtGui.QPalette().color(QtGui.QPalette.Normal, QtGui.QPalette.Window))
    return "color:rgba(%i, %i, %i, %i)" % (color.red(), color.green(), color.blue(), color.alpha())


def setColor(styleSheet, RGBcolor):
    newStyleSheet = ""
    props = styleSheet.replace("\n", "").split(";")
    for prop in props:
        if prop and prop[:6] != "color:":
                newStyleSheet += prop + ";"
    newStyleSheet += "color:" + RGBcolor + ";"
    return newStyleSheet


def setColorAlpha(styleSheet, newAlpha):
    newStyleSheet = ""
    props = styleSheet.replace("\n", "").split(";")
    for prop in props:
        if prop[:6] == "color:":
            values = prop.split(",")
            values[0] = values[0].replace("rgb(", "rgba(")
            prop = values[0] + "," + values[1] + "," + values[2] + "," + str(newAlpha) + ")"
        if prop:
            newStyleSheet += prop + ";"
    return newStyleSheet


def getBkgColor(styleSheet):
    props = styleSheet.replace("\n", "").split(";")
    for prop in props:
        if prop[:17] == "background-color:":
            return prop
    color = QtGui.QColor(QtGui.QPalette().color(QtGui.QPalette.Normal, QtGui.QPalette.WindowText))
    return "background-color:rgba(%i, %i, %i, %i)" % (color.red(), color.green(), color.blue(), color.alpha())


def setBkGColor(styleSheet, RGBcolor):
    newStyleSheet = ""
    props = styleSheet.replace("\n", "").split(";")
    for prop in props:
        if prop and prop[:17] != "background-color:":
            newStyleSheet += prop + ";"
    newStyleSheet += "background-color:" + RGBcolor + ";"
    return newStyleSheet


def setBkGColorAlpha(styleSheet, newAlpha):
    newStyleSheet = ""
    props = styleSheet.replace("\n", "").split(";")
    for prop in props:
        if prop[:17] == "background-color:":
            values = prop.split(",")
            values[0] = values[0].replace("rgb(", "rgba(")
            prop = values[0] + "," + values[1] + "," + values[2] + "," + str(newAlpha) + ")"
        if prop:
            newStyleSheet += prop + ";"
    return newStyleSheet


def setStyleSheet(styleSheet, bkgRGBcolor, fontRGBcolor):
    newStyleSheet = "background-color:" + bkgRGBcolor + ";" + "color:" + fontRGBcolor + ";"
    props = styleSheet.replace("\n", "").split(";")
    for prop in props:
        if prop and prop[:17] != "background-color:" and prop[:6] != "color:":
            newStyleSheet += prop + ";"
    return newStyleSheet


def getRGBAfromColorName(name):
    color = QtGui.QColor(name)
    return "rgba(%i, %i, %i, %i)" % (color.red(), color.green(), color.blue(), color.alpha())


def getRGBAfromColorRGB(color):
    colorRGB = color.replace("rgba(", "").replace("rgb(", "").replace(")", ""). split(",")
    r = int(colorRGB[0])
    g = int(colorRGB[1])
    b = int(colorRGB[2])
    if len(colorRGB) > 3:
        a = int(colorRGB[3])
    else:
        a = 255
    return r, g, b, a


def setHTMLStyle(text, color=None, bkgcolor=None, font=None, fontSize=None, align=None, valign=None, strong=False):

    colorHTML = bkgcolorHTML = fontHTML = fontSizeHTML = alignHTML = valignHTML = ""
    if color:
        if "rgb" in color:
            colorRGB = color.replace("rgba(", "").replace("rgb(", "").replace(")", ""). split(",")
            r = "%0.2X" % int(colorRGB[0])
            g = "%0.2X" % int(colorRGB[1])
            b = "%0.2X" % int(colorRGB[2])
            colorHTML = "color:#%s;" % (r+g+b)
        else:
            colorHTML = "color:%s;" % color
    if bkgcolor:
        if "rgb" in bkgcolor:
            bkgcolorRGB = bkgcolor.replace("rgba(", "").replace("rgb(", "").replace(")", "").split(",")
            r = "%0.2X" % int(bkgcolorRGB[0])
            g = "%0.2X" % int(bkgcolorRGB[1])
            b = "%0.2X" % int(bkgcolorRGB[2])
            bkgcolorHTML = "background-color:#%s;" % (r + g + b)
        else:
            bkgcolorHTML = "background-color:%s;" % bkgcolor
    if font:
        fontHTML = "font-family:%s;" % font
    if fontSize:
        fontSizeHTML = "font-size:%ipx;" % fontSize
    if align:
        alignHTML = "text-align:%s;" % align
    if valign:
        valignHTML = "vertical-align:%s;" % valign
    marginHTML = "margin-top:-10%;"
    if strong:
        style = "<span style=\"%s%s%s%s%s%s\"><strong>%s</strong></span>" % (colorHTML, bkgcolorHTML, fontHTML, fontSizeHTML, alignHTML, valignHTML, text)
    else:
        style = "<span style=\"%s%s%s%s%s%s%s\">%s</span>" % (marginHTML, bkgcolorHTML, colorHTML, fontHTML, fontSizeHTML, alignHTML, valignHTML, text)
    return style


def getQColorfromRGB(color):
    rgb = color.replace("background-color:", "").replace("color:", "").replace("rgba(", "").replace("rgb(", "").replace(")", "").split(",")
    r = int(rgb[0])
    g = int(rgb[1])
    b = int(rgb[2])
    if len(rgb) > 3:
        a = int(rgb[3])
    else:
        a = 255
    return QtGui.QColor(r, g, b, a)
