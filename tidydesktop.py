#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import platform
import sys
import json
import signal
import pygetwindow
import bkgutils
import qtutils
import utils
from PyQt5 import QtCore, QtWidgets, QtGui
import traceback
if "Linux" in platform.platform():
    # Using pynput to avoid the need for root permissions when using keyboard/mouse modules
    from pynput import mouse
    from pynput import keyboard
else:
    # For some unknown reason, pynput forces to use a delay to allow moving/resizing the window
    # This doesn't happen when dragging INSIDE the window, only when dragging on the title bar (moving the window)
    import keyboard
    import mouse


_CAPTION = "TidyDesk"
_CONFIG_ICON = utils.resource_path("resources/tidy.png")
_SYSTEM_ICON = utils.resource_path("resources/tidy.ico")
_ICON_SELECTED = utils.resource_path("resources/tick.png")
_ICON_NOT_SELECTED = utils.resource_path("resources/notick.png")
_SETTINGS_FILE = "settings.json"

_LINE_WIDTH = 8
_LINE_COLOR = "rgba(255, 0, 255, 128)"
_LINE_HIGHLIGHT_COLOR = "rgba(0, 255, 0, 255)"
_GRID_STYLE = "background-color: transparent; border: %spx solid %s;" % (_LINE_WIDTH, _LINE_COLOR)
_GRID_HIGHLIGHT_STYLE = "background-color: transparent; border: %spx solid %s;" % (_LINE_WIDTH, _LINE_HIGHLIGHT_COLOR)


class Window(QtWidgets.QMainWindow):

    showWidgetSig = QtCore.pyqtSignal()
    hideWidgetSig = QtCore.pyqtSignal()

    def __init__(self, *args, **kwargs):
        QtWidgets.QMainWindow.__init__(self, *args, **kwargs)

        self.x, self.y, self.xmax, self.ymax = bkgutils.getWorkArea()
        qtutils.initDisplay(parent=self, pos=(self.x, self.y), size=(self.xmax, self.ymax), frameless=True,
                            noFocus=True, aot=True, transparentBkg=True, caption=_CAPTION, icon=_SYSTEM_ICON)
        self.checkInstances(_CAPTION)
        self.loadSettings()
        self.setupUI()

        self.key1Pressed = False
        self.key2Pressed = False
        self.tidyMode = False
        self.clicked = False
        self.ignoreUP = False
        self.initPos = None
        self.prevHighlightLabel = None

        self.showWidgetSig.connect(self.showWidget)
        self.hideWidgetSig.connect(self.hideWidget)

        if "Linux" in platform.platform():
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
            keyboard.on_press_key(self.key2_alt, self.keyPress)

            mouse.hook(self.mouseHook)

        self.menu = Config(self, self.config)
        self.menu.reloadSettings.connect(self.reloadSettings)
        self.menu.closeAll.connect(self.closeAll)
        self.menu.showHelp.connect(self.showHelp)

    def checkInstances(self, name):
        instances = 0
        for win in pygetwindow.getWindowsWithTitle(name):
            if ".py" not in win.title:
                instances += 1
        if instances > 1:
            sys.exit()  # Allow only one instance

    def loadSettings(self):

        if os.path.isfile(_SETTINGS_FILE):
            file = _SETTINGS_FILE
        else:
            file = utils.resource_path("resources/" + _SETTINGS_FILE)

        try:
            with open(file, encoding='UTF-8') as file:
                self.config = json.load(file)
        except:
            pass

        self.sections = self.config["sections"]
        self.key1Name = "ctrl"
        self.key2Name = "windows/command"
        if "Linux" in platform.platform():
            self.key1 = keyboard.Key.ctrl_l
            self.key2 = keyboard.Key.cmd
            self.key2_alt = keyboard.Key.cmd
        else:
            self.key1 = "ctrl"
            # " izquierda"??? This will require to translate the key name to every language!!!
            self.key2 = "windows izquierda"
            self.key2_alt = "windows"

    @QtCore.pyqtSlot()
    def reloadSettings(self):
        self.loadSettings()
        self.setupUI()

    def setupUI(self):

        self.setGeometry(self.x, self.y, self.xmax, self.ymax)

        self.widget = QtWidgets.QWidget()
        self.widget.hide()
        self.widget.setGeometry(self.x, self.y, self.xmax, self.ymax)

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

    def keyPress(self, event):
        if keyboard.is_pressed(self.key1) and (keyboard.is_pressed(self.key2) or keyboard.is_pressed(self.key2_alt)):
            self.tidyMode = True
            self.showWidgetSig.emit()
            # mouse.hook(self.mouseHook)

    def keyRelease(self, event):
        if not keyboard.is_pressed(self.key1) or (not keyboard.is_pressed(self.key2) and not keyboard.is_pressed(self.key2_alt)):
            self.tidyMode = False
            self.hideWidgetSig.emit()
            # mouse.unhook_all()

    @QtCore.pyqtSlot()
    def showWidget(self):
        if self.widget.isHidden():
            self.widget.show()

    @QtCore.pyqtSlot()
    def hideWidget(self):
        if self.widget.isVisible():
            self.widget.hide()

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
            for widget in self.labels:
                geom = widget.geometry()
                if geom.x() < event.x < geom.x() + geom.width() and geom.y() < event.y < geom.y() + geom.height():
                    if self.prevHighlightLabel != widget:
                        widget.setStyleSheet(_GRID_HIGHLIGHT_STYLE)
                        if self.prevHighlightLabel is not None: self.prevHighlightLabel.setStyleSheet(_GRID_STYLE)
                        self.prevHighlightLabel = widget
                        break

    def on_press(self, key):
        if key == self.key1:
            self.key1Pressed = True
        elif key == self.key2:
            self.key2Pressed = True
        if self.key1Pressed and self.key2Pressed:
            self.tidyMode = True
            self.showWidgetSig.emit()

    def on_release(self, key):
        if key == self.key1:
            self.key1Pressed = False
        elif key == self.key2:
            self.key2Pressed = False
        if not self.key1Pressed or not self.key2Pressed:
            self.tidyMode = False
            self.hideWidgetSig.emit()

    def on_move(self, x, y):
        if self.tidyMode and self.clicked:
            for widget in self.labels:
                geom = widget.geometry()
                if geom.x() < x < geom.x() + geom.width() and geom.y() < y < geom.y() + geom.height():
                    if self.prevHighlightLabel != widget:
                        widget.setStyleSheet(_GRID_HIGHLIGHT_STYLE)
                        if self.prevHighlightLabel is not None: self.prevHighlightLabel.setStyleSheet(_GRID_STYLE)
                        self.prevHighlightLabel = widget
                        break

    def on_click(self, x, y, button, pressed):
        if button == mouse.Button.left:
            if pressed:
                self.buttonDown(x, y)
            else:
                self.buttonUp(x, y)

    def buttonDown(self, x, y):
        self.clicked = True
        self.initPos = (x, y)

    def _get_wm(self):
        # https://stackoverflow.com/questions/3333243/how-can-i-check-with-python-which-window-manager-is-running
        return os.environ.get('XDG_CURRENT_DESKTOP') or ""

    def buttonUp(self, x, y):
        self.clicked = False
        if self.tidyMode and self.initPos != (x, y) and self.prevHighlightLabel is not None:
            wm = self._get_wm()
            if "GNOME" in wm:
                # PyQt5 geometry is not correct in Ubuntu/GNOME?!?!?!
                xGap = _LINE_WIDTH * 6
                yGap = 0
                wGap = _LINE_WIDTH * 6
                hGap = _LINE_WIDTH * 7
            else:
                if "Cinnamon" in wm:
                    y = y + 20
                    xGap = 0
                    yGap = + _LINE_WIDTH * 3
                    wGap = 0
                    hGap = - _LINE_WIDTH * 3
                else:
                    xGap = - _LINE_WIDTH
                    yGap = 0
                    wGap = _LINE_WIDTH * 2
                    hGap = _LINE_WIDTH

            geom = self.prevHighlightLabel.geometry()
            windows = pygetwindow.getWindowsAt(x, y)
            for win in windows:
                if win.title and win.title != _CAPTION and \
                        ("Linux" in platform.platform() and '_NET_WM_WINDOW_TYPE_DESKTOP' not in bkgutils.getAttributes(win._hWnd)):
                    # For some unknown reason, pynput forces to use a delay to allow moving/resizing the window
                    # This doesn't happen when dragging INSIDE the window, only when dragging on the title bar (moving the window)
                    # time.sleep(0.3)
                    win.resizeTo(geom.width() + wGap, geom.height() + hGap)
                    win.moveTo(geom.x() + xGap, geom.y() + yGap)
                    break
            self.prevHighlightLabel.setStyleSheet(_GRID_STYLE)
            self.prevHighlightLabel = None

    @QtCore.pyqtSlot()
    def showHelp(self):
        self.msgBox.exec_()

    @QtCore.pyqtSlot()
    def closeAll(self):
        try:
            self.kListener.stop()
            self.mListener.stop()
        except: pass
        QtWidgets.QApplication.quit()


class Config(QtWidgets.QWidget):

    reloadSettings = QtCore.pyqtSignal()
    closeAll = QtCore.pyqtSignal()
    showHelp = QtCore.pyqtSignal()

    def __init__(self, parent, config):
        QtWidgets.QWidget.__init__(self, parent)

        self.isWindows = "Windows" in platform.platform()
        self.isLinux = "Linux" in platform.platform()
        self.isMacOS = "macOS" in platform.platform() or "Darwin" in platform.platform()

        self.config = config
        self.setupUI()

    def setupUI(self):

        # self.setGeometry(-1, -1, 1, 1)

        self.iconSelected = QtGui.QIcon(_ICON_SELECTED)
        self.iconNotSelected = QtGui.QIcon(_ICON_NOT_SELECTED)

        self.contextMenu = QtWidgets.QMenu(self)
        if self.isWindows:
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
            file = utils.resource_path("resources/" + _SETTINGS_FILE)
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
