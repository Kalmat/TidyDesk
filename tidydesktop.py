#!/usr/bin/python
# -*- coding: utf-8 -*-

import json
import os
import platform
import signal
import sys
import traceback

import bkgutils
import utils
import pygetwindowmp
import qtutils
from PyQt5 import QtCore, QtWidgets, QtGui

_IS_WINDOWS = "Windows" in platform.platform()
_IS_LINUX = "Linux" in platform.platform()
_IS_MACOS = "Darwin" in platform.platform() or "macOS" in platform.platform()
if _IS_LINUX or _IS_MACOS:
    # Using pynput to avoid the need for root permissions when using keyboard/mouse modules in Linux
    from pynput import mouse
    from pynput import keyboard
elif _IS_WINDOWS:
    # For some unknown reasons, pynput forces to use a delay to allow moving/resizing the window
    # This doesn't happen when dragging INSIDE the window, only when dragging the title bar (actually MOVING the window)
    import keyboard
    import mouse


_CAPTION = "TidyDesk"
_CONFIG_ICON = utils.resource_path(__file__, "resources/tidy.png")
_SYSTEM_ICON = utils.resource_path(__file__, "resources/tidy.ico")
_ICON_SELECTED = utils.resource_path(__file__, "resources/tick.png")
_ICON_NOT_SELECTED = utils.resource_path(__file__, "resources/notick.png")
_SETTINGS_FILE = "settings.json"

_LINE_WIDTH = 8
_LINE_COLOR = "rgba(255, 0, 255, 128)"
_LINE_HIGHLIGHT_COLOR = "rgba(0, 255, 0, 255)"
_GRID_STYLE = "background-color: transparent; border: %spx solid %s;" % (_LINE_WIDTH, _LINE_COLOR)
_GRID_HIGHLIGHT_STYLE = "background-color: transparent; border: %spx solid %s;" % (_LINE_WIDTH, _LINE_HIGHLIGHT_COLOR)


class Window(QtWidgets.QMainWindow):

    showWidgetSig = QtCore.pyqtSignal()
    hideWidgetSig = QtCore.pyqtSignal()
    highlightLabelSig = QtCore.pyqtSignal(int, int)
    placeWindowSig = QtCore.pyqtSignal(int, int)

    def __init__(self, *args, **kwargs):
        QtWidgets.QMainWindow.__init__(self, *args, **kwargs)

        self.xpos, self.ypos, self.xmax, self.ymax = bkgutils.getWorkArea()
        qtutils.initDisplay(parent=self, pos=(self.xpos, self.ypos), size=(self.xmax, self.ymax), frameless=True,
                            noFocus=True, aot= True, opacity=0, caption=_CAPTION, icon=_SYSTEM_ICON)
        self.checkInstances(_CAPTION)
        self.loadSettings()
        self.defineKeys()
        self.setupUI()

        self.showWidgetSig.connect(self.showWidget)
        self.hideWidgetSig.connect(self.hideWidget)
        self.placeWindowSig.connect(self.placeWindow)
        self.highlightLabelSig.connect(self.highlightLabel)

        self.key1Pressed = False
        self.key2Pressed = False
        self.tidyMode = False
        self.clicked = False
        self.ignoreUP = False
        self.clickedWin = None
        self.prevPos = None
        self.prevHighlightLabel = None

        if _IS_LINUX or _IS_MACOS:
            kListener = keyboard.Listener(
                on_press=self.on_press,
                on_release=self.on_release,
                suppress=False)
            kListener.start()

            mListener = mouse.Listener(
                on_move=self.on_move,
                on_click=self.on_click,
                suppress=False)
            mListener.start()
        else:
            keyboard.on_press_key(self.key1, self.keyPress)
            keyboard.on_press_key(self.key2, self.keyPress)
            keyboard.on_press_key(self.key2_alt, self.keyPress)
            keyboard.on_release_key(self.key1, self.keyRelease)
            keyboard.on_release_key(self.key2, self.keyRelease)
            keyboard.on_release_key(self.key2_alt, self.keyRelease)

            mouse.hook(self.mouseHook)

        self.menu = Config(self, self.config)
        self.menu.reloadSettings.connect(self.reloadSettings)
        self.menu.closeAll.connect(self.closeAll)
        self.menu.showHelp.connect(self.showHelp)

    def checkInstances(self, name):
        instances = 0
        for win in pygetwindowmp.getWindowsWithTitle(name):
            if ".py" not in win.title:
                instances += 1
        if instances > 1:
            sys.exit()  # Allow only one instance

    def loadSettings(self):

        if os.path.isfile(_SETTINGS_FILE):
            file = _SETTINGS_FILE
        else:
            file = utils.resource_path(__file__, "resources/" + _SETTINGS_FILE)

        try:
            with open(file, encoding='UTF-8') as file:
                self.config = json.load(file)
        except:
            pass

        self.sections = self.config["sections"]

    def defineKeys(self):
        if _IS_LINUX:
            self.key1Name = "ctrl"
            self.key2Name = "meta"
            self.key1 = keyboard.Key.ctrl_l
            self.key2 = keyboard.Key.cmd
            self.key2_alt = keyboard.Key.ctrl_r
        elif _IS_MACOS:
            self.key1Name = "ctrl"
            self.key2Name = "command"
            self.key1 = keyboard.Key.ctrl_l
            self.key2 = keyboard.Key.cmd
            self.key2_alt = keyboard.Key.ctrl_r
        else:
            self.key1Name = "ctrl"
            self.key2Name = "windows"
            self.key1 = "ctrl"
            # " izquierda"??? This will require to translate the key name to every language!!!
            self.key2 = "windows izquierda"
            # This generic key is not detected
            self.key2_alt = "windows"

    @QtCore.pyqtSlot()
    def reloadSettings(self):
        self.loadSettings()
        self.setGrid(self.sections)

    def setupUI(self):

        self.setGeometry(self.xpos, self.ypos, self.xmax, self.ymax)

        self.widget = QtWidgets.QWidget()
        self.widget.hide()
        self.widget.setGeometry(self.xpos, self.ypos, self.xmax, self.ymax)

        self.myLayout = QtWidgets.QGridLayout()
        self.myLayout.setContentsMargins(0, 0, 0, 0)
        self.myLayout.setSpacing(0)
        self.setGrid(self.sections)
        self.widget.setLayout(self.myLayout)
        self.setCentralWidget(self.widget)

        self.msgBox = QtWidgets.QMessageBox()
        self.msgBox.setIcon(QtWidgets.QMessageBox.Information)
        self.msgBox.setText("Press activation keys: %s + %s to show grid, then drag and drop the windows" % (self.key1Name, self.key2Name))
        self.msgBox.setWindowTitle("TidyDesk Help")
        self.msgBox.setDetailedText("Select your desired grid (layout) configuration\n"
                                    "Press activation keys: %s + %s to show grid\n" % (self.key1Name, self.key2Name) +
                                    "Drag and drop any window inside the desired grid section while keeping activation keys pressed\n"
                                    "The window will automatically adjust to the section where the mouse pointer is over")
        self.msgBox.setStandardButtons(QtWidgets.QMessageBox.Ok)

    def setGrid(self, sections):

        self.labels = []

        for i in range(self.myLayout.count()):
            label = self.myLayout.itemAt(i).widget()
            label.deleteLater()

        if sections in (-4, -5):
            rows = int((abs(sections) + 1) / 2)
            columns = int(abs(sections) / 2)
            for row in range(rows):
                label = QtWidgets.QLabel()
                label.setStyleSheet(_GRID_STYLE)
                self.myLayout.addWidget(label, row, 0, 1, 1)
                self.labels.append(label)

            columnspan = 2
            for column in range(columns):
                label = QtWidgets.QLabel()
                label.setStyleSheet(_GRID_STYLE)
                self.myLayout.addWidget(label, 0, 1 + (column * columnspan), rows, columnspan)
                self.labels.append(label)

        else:
            rows = 2 if sections < 0 or sections >= 4 else 1
            columns = int(abs(sections) / rows)
            for row in range(rows):
                for column in range(columns):
                    label = QtWidgets.QLabel()
                    label.setStyleSheet(_GRID_STYLE)
                    self.myLayout.addWidget(label, row, column, 1, 1)
                    self.labels.append(label)

            if sections % 2 != 0 and rows > 1:
                label = QtWidgets.QLabel()
                label.setStyleSheet(_GRID_STYLE)
                columnspan = 2 if sections >= 9 else 1
                self.myLayout.addWidget(label, 0, columns, 2, columnspan)
                self.labels.append(label)

    @QtCore.pyqtSlot()
    def showWidget(self):
        if self.widget.isHidden():
            self.widget.show()

    @QtCore.pyqtSlot()
    def hideWidget(self):
        if self.widget.isVisible():
            self.widget.hide()
            for widget in self.labels:
                widget.setStyleSheet(_GRID_STYLE)
        self.prevHighlightLabel = None

    @QtCore.pyqtSlot(int, int)
    def highlightLabel(self, x, y):
        for widget in self.labels:
            geom = widget.geometry()
            if geom.x() < x < geom.x() + geom.width() and geom.y() < y < geom.y() + geom.height():
                if self.prevHighlightLabel != widget:
                    widget.setStyleSheet(_GRID_HIGHLIGHT_STYLE)
                    if self.prevHighlightLabel is not None: self.prevHighlightLabel.setStyleSheet(_GRID_STYLE)
                    self.prevHighlightLabel = widget
                    break

    @QtCore.pyqtSlot(int, int)
    def placeWindow(self, x, y):
        xAdj, yAdj, xGap, yGap, wGap, hGap = bkgutils.getWMAdjustments(_IS_MACOS, _LINE_WIDTH)
        windows = pygetwindowmp.getWindowsAt(x + xAdj, y + yAdj)
        for win in windows:
            if win.title and win.title != _CAPTION and \
                    (not _IS_LINUX or (_IS_LINUX and '_NET_WM_WINDOW_TYPE_DESKTOP' not in bkgutils.getAttributes(win._hWnd))):
                geom = self.prevHighlightLabel.geometry()
                win.resizeTo(geom.width() + wGap, geom.height() + hGap)
                win.moveTo(geom.x() + xGap, geom.y() + yGap)
                break
        self.prevHighlightLabel.setStyleSheet(_GRID_STYLE)
        self.prevHighlightLabel = None

    def keyPress(self, event):
        if keyboard.is_pressed(self.key1) and (keyboard.is_pressed(self.key2) or keyboard.is_pressed(self.key2_alt)):
            self.tidyMode = True
            self.showWidgetSig.emit()

    def keyRelease(self, event):
        if not keyboard.is_pressed(self.key1) or (not keyboard.is_pressed(self.key2) and not keyboard.is_pressed(self.key2_alt)):
            self.tidyMode = False
            self.hideWidgetSig.emit()

    def mouseHook(self, event):

        if isinstance(event, mouse.MoveEvent):
            self.mouseMove(event)

        elif isinstance(event, mouse.ButtonEvent):
            if event.button == mouse.LEFT:
                if event.event_type == mouse.DOUBLE:
                    self.ignoreUP = True
                elif event.event_type == mouse.DOWN:
                    self.ignoreUP = False
                    x, y = mouse.get_position()
                    self.buttonDown(x, y)
                elif event.event_type == mouse.UP and not self.ignoreUP:
                    x, y = mouse.get_position()
                    self.buttonUp(x, y)

    def mouseMove(self, event):
        if self.tidyMode and self.clicked:
            if self.prevPos is None or self.clickedWin is None:
                self.clickedWin = pygetwindowmp.getActiveWindow()
                self.prevPos = self.clickedWin.topleft
            if self.prevPos != self.clickedWin.topleft:
                self.highlightLabelSig.emit(int(event.x), int(event.y))

    def on_press(self, key):
        if key == self.key1:
            self.key1Pressed = True
        elif key in (self.key2, self.key2_alt):
            self.key2Pressed = True
        if self.key1Pressed and self.key2Pressed:
            self.tidyMode = True
            self.showWidgetSig.emit()

    def on_release(self, key):
        if key == self.key1:
            self.key1Pressed = False
        elif key in (self.key2, self.key2_alt):
            self.key2Pressed = False
        if not self.key1Pressed or not self.key2Pressed:
            self.tidyMode = False
            self.hideWidgetSig.emit()

    def on_move(self, x, y):
        if self.tidyMode and self.clicked:
            if self.prevPos is None or self.clickedWin is None:
                self.clickedWin = pygetwindowmp.getActiveWindow()
                self.prevPos = self.clickedWin.topleft
            if self.prevPos != self.clickedWin.topleft:
                self.highlightLabelSig.emit(int(x), int(y))

    def on_click(self, x, y, button, pressed):
        if button == mouse.Button.left:
            if pressed:
                self.buttonDown(x, y)
            else:
                self.buttonUp(x, y)

    def buttonDown(self, x, y):
        self.clicked = True
        if self.tidyMode:
            self.highlightLabelSig.emit(int(x), int(y))

    def buttonUp(self, x, y):
        self.clicked = False
        if self.tidyMode:
            if self.clickedWin and self.prevPos and self.prevPos != self.clickedWin.topleft and \
                    self.prevHighlightLabel is not None:
                self.placeWindowSig.emit(int(x), int(y))
            self.hideWidgetSig.emit()
        self.prevPos = None
        self.clickedWin = None

    @QtCore.pyqtSlot()
    def showHelp(self):
        self.msgBox.exec_()

    @QtCore.pyqtSlot()
    def closeAll(self):
        try:
            if _IS_LINUX or _IS_MACOS:
                self.kListener.stop()
                self.mListener.stop()
            elif _IS_WINDOWS:
                keyboard.unhook_all()
                mouse.unhook_all()
        except: pass
        QtWidgets.QApplication.quit()


class Config(QtWidgets.QWidget):

    reloadSettings = QtCore.pyqtSignal()
    closeAll = QtCore.pyqtSignal()
    showHelp = QtCore.pyqtSignal()

    def __init__(self, parent, config):
        QtWidgets.QWidget.__init__(self, parent)

        self.config = config
        self.setupUI()

    def setupUI(self):

        self.setGeometry(-1, -1, 1, 1)

        self.iconSelected = QtGui.QIcon(_ICON_SELECTED)
        self.iconNotSelected = QtGui.QIcon(_ICON_NOT_SELECTED)

        self.contextMenu = QtWidgets.QMenu(self)
        if _IS_WINDOWS:
            self.contextMenu.setStyleSheet("""
                QMenu {border: 1px inset #666; font-size: 18px; background-color: #333; color: #fff; padding: 10px;}
                QMenu:selected {background-color: #666; color: #fff;}""")
        self.gridAct = self.contextMenu.addMenu("Select Grid")
        gridType = self.config["sections"]
        grids = self.config["Available_sections"]
        for key in grids.keys():
            self.addGridOpts(self.gridAct, key, grids[key], selected=(gridType == grids[key]))

        self.contextMenu.addSeparator()
        self.helpAct = self.contextMenu.addAction("Help", self.sendShowHelp)
        self.quitAct = self.contextMenu.addAction("Quit", self.sendCloseAll)

        self.trayIcon = QtWidgets.QSystemTrayIcon(QtGui.QIcon(_CONFIG_ICON), self)
        self.trayIcon.setToolTip(_CAPTION)
        self.trayIcon.setContextMenu(self.contextMenu)
        self.trayIcon.show()

    def addGridOpts(self, option, text, value, selected=False):
        act = option.addAction(text, (lambda: self.execGridAct(text, value)))
        if selected:
            act.setIcon(self.iconSelected)
        else:
            act.setIcon(self.iconNotSelected)

    def execGridAct(self, text, sections):
        for option in self.gridAct.actions():
            if option.text() == text:
                option.setIcon(self.iconSelected)
            else:
                option.setIcon(self.iconNotSelected)
        self.gridAct.update()
        self.config["sections"] = sections
        self.saveSettings()

    def sendShowHelp(self):
        self.showHelp.emit()

    def sendCloseAll(self):
        self.closeAll.emit()

    def saveSettings(self):

        if os.path.isfile(_SETTINGS_FILE):
            file = _SETTINGS_FILE
        else:
            file = utils.resource_path(__file__, "resources/" + _SETTINGS_FILE)
        try:
            with open(file, "w", encoding='UTF-8') as file:
                json.dump(self.config, file, ensure_ascii=False, sort_keys=False, indent=4)
        except:
            pass

        self.reloadSettings.emit()


def sigint_handler(*args):
    # https://stackoverflow.com/questions/4938723/what-is-the-correct-way-to-make-my-pyqt-application-quit-when-killed-from-the-co
    app.closeAllWindows()


def exception_hook(exctype, value, tb):
    # https://stackoverflow.com/questions/56991627/how-does-the-sys-excepthook-function-work-with-pyqt5
    traceback_formated = traceback.format_exception(exctype, value, tb)
    traceback_string = "".join(traceback_formated)
    print(traceback_string, file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    if "python" in sys.executable.lower():
        # This will let the script catching Ctl-C interruption (e.g. when running from IDE)
        signal.signal(signal.SIGINT, sigint_handler)
        timer = QtCore.QTimer()
        timer.start(500)
        timer.timeout.connect(lambda: None)
        # This will allow to show some tracebacks (not all, anyway)
        sys._excepthook = sys.excepthook
        sys.excepthook = exception_hook
    win = Window()
    win.show()
    try:
        app.exec_()
    except:
        pass
