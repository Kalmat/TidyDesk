#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import platform
import subprocess
from typing import List
import ctypes
import utils

if "Windows" in platform.platform():
    import pywintypes
    import win32con
    import win32gui
    import win32api

    def findWindowHandlesB(parent: int = None, window_class: str = None, title: str = None) -> List[int]:
        # https://stackoverflow.com/questions/56973912/how-can-i-set-windows-10-desktop-background-with-smooth-transition

        def _make_filter(class_name: str, title: str):
            """https://docs.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-enumwindows"""

            def enum_windows(handle: int, h_list: list):
                if not (class_name or title):
                    h_list.append(handle)
                if class_name and class_name not in win32gui.GetClassName(handle):
                    return True  # continue enumeration
                if title and title not in win32gui.GetWindowText(handle):
                    return True  # continue enumeration
                h_list.append(handle)

            return enum_windows

        cb = _make_filter(window_class, title)
        try:
            handle_list = []
            if parent:
                win32gui.EnumChildWindows(parent, cb, handle_list)
            else:
                win32gui.EnumWindows(cb, handle_list)
            return handle_list
        except pywintypes.error:
            return []

    def findWindowHandles(parent: int = None, window_class: str = None, title: str = None) -> List[int]:
        # https://stackoverflow.com/questions/61151811/how-to-get-handle-for-a-specific-application-window-in-python-using-pywin32
        # WARNING: Crashes when using QtWebEngineWidgets!!!!
        thelist = []

        def findit(hwnd, ctx):
            if (not parent or (parent and parent == win32gui.GetParent(hwnd))) and \
                    (not window_class or (window_class and window_class == win32gui.GetClassName(hwnd))) and \
                    (not title or (title and title == win32gui.GetWindowText(hwnd))):
                thelist.append(hwnd)

        win32gui.EnumWindows(findit, None)
        return thelist

    def findWindowHandle(title):
        return win32gui.FindWindowEx(0, 0, None, title)

    def sendBehind(name):

        def getWorkerW():

            thelist = []

            def findit(hwnd, ctx):
                p = win32gui.FindWindowEx(hwnd, None, "SHELLDLL_DefView", "")
                if p != 0:
                    thelist.append(win32gui.FindWindowEx(None, hwnd, "WorkerW", ""))

            win32gui.EnumWindows(findit, None)
            return thelist

        # https://www.codeproject.com/Articles/856020/Draw-Behind-Desktop-Icons-in-Windows-plus
        hWnd = findWindowHandle(name)
        progman = win32gui.FindWindow("Progman", None)
        win32gui.SendMessageTimeout(progman, 0x052C, 0, 0, win32con.SMTO_NORMAL, 1000)
        workerw = getWorkerW()
        if hWnd and workerw:
            win32gui.SetParent(hWnd, workerw[0])
        return

    def sendFront(name, parent):
        hWnd = findWindowHandle(name)
        win32gui.SetParent(hWnd, parent)

    def getWallpaper():
        wp = win32gui.SystemParametersInfo(win32con.SPI_GETDESKWALLPAPER, 260, 0)
        return utils.resource_path(wp)

    def setWallpaper(img=""):
        win32gui.SystemParametersInfo(win32con.SPI_SETDESKWALLPAPER, img, win32con.SPIF_UPDATEINIFILE | win32con.SPIF_SENDCHANGE)

    def closeWindow(hWnd):
        win32gui.PostMessage(hWnd, win32con.WM_CLOSE, 0, 0)

    def clearWindow(hWnd):
        win32gui.PostMessage(hWnd, win32con.WM_CLEAR, 0, 0)

    def refreshDesktop():
        # https://newbedev.com/how-to-refresh-reload-desktop

        hWnd = win32gui.GetWindow(win32gui.FindWindow("Progman", "Program Manager"), win32con.GW_CHILD)
        if not hWnd:
            ptrs = findWindowHandles(window_class="WorkerW")
            for i in range(len(ptrs)):
                hWnd = win32gui.FindWindowEx(ptrs[i], 0, "SHELLDLL_DefView", "")
        if hWnd:
            win32gui.SendMessage(hWnd, 0x111, 0x7402, 0)

    def refreshDesktopB():
        win32gui.SendMessage(win32con.HWND_BROADCAST, win32con.WM_SETTINGCHANGE, 0, 1)

    def force_refresh():
        ctypes.windll.user32.UpdatePerUserSystemParameters(1)

    def enable_activedesktop():
        """https://stackoverflow.com/a/16351170"""
        try:
            progman = findWindowHandles(window_class='Progman')[0]
            cryptic_params = (0x52c, 0, 0, 0, 500, None)
            ctypes.windll.user32.SendMessageTimeoutW(progman, *cryptic_params)
        except IndexError as e:
            raise WindowsError('Cannot enable Active Desktop') from e

    def toggleDesktopIcons():

        thelist = []

        def findit(hwnd, ctx):
            p = win32gui.FindWindowEx(hwnd, None, "SHELLDLL_DefView", "")
            if p != 0:
                thelist.append(p)

        win32gui.EnumWindows(findit, None)
        if thelist:
            win32gui.SendMessage(thelist[0], 0x111, 0x7402, 0)

    def getWorkArea():
        monitor_info = win32api.GetMonitorInfo(win32api.MonitorFromPoint((0, 0)))
        work_area = monitor_info.get("Work")
        return work_area[0], work_area[1], work_area[2], work_area[3]

elif "Linux" in platform.platform():
    import Xlib
    import Xlib.X
    import Xlib.display
    import ewmh
    from pynput import mouse

    DISP = Xlib.display.Display()
    SCREEN = DISP.screen()
    ROOT = SCREEN.root
    EWMH = ewmh.EWMH(_display=DISP, root=ROOT)

    def findWindowHandles(parent=None, window_class="", title=""):

        def getAllWindows(parent=None):
            if not parent:
                parent = ROOT
            windows = parent.query_tree().children
            return windows

        def getWindowsWithTitle(parent=None, window_class="", title=""):
            matches = []
            for win in getAllWindows(parent):
                w = DISP.create_resource_object('window', win)
                if title and title == w.get_wm_name() or \
                        window_class and window_class == w.get_wm_class():
                    matches.append(win)
            return matches

        if title:
            windows = getWindowsWithTitle(parent=parent, title=title)
        else:
            windows = getAllWindows(parent=parent)
        return windows

    def sendBehind(name):
        # Mint/Cinnamon: just clicking on the desktop, it comes up, sending the window/wallpaper to bottom!
        m = mouse.Controller()
        m.click(SCREEN.width_in_pixels - 1, 300, 1)

        # Non-working attempts for Ubuntu/GNOME using Xlib
        # win = findWindowHandles(title=name)
        # if win:
        #     win = win[0]
        #     w = DISP.create_resource_object('window', win)
        #
        #     https://stackoverflow.com/questions/58885803/can-i-use-net-wm-window-type-dock-ewhm-extension-in-openbox
        #     Does not sends current window below. It does with the new window, but not behind the desktop icons
        #     w.change_property(DISP.intern_atom('_NET_WM_WINDOW_TYPE'), Xlib.Xatom.ATOM,
        #                       32, [DISP.intern_atom("_NET_WM_WINDOW_TYPE_DESKTOP"), ],
        #                       Xlib.X.PropModeReplace)
        #     w.map()
        #
        #     newWin = ROOT.create_window(0, 0, 500, 500, 1, SCREEN.root_depth,
        #                                 background_pixel=SCREEN.black_pixel,
        #                                 event_mask=Xlib.X.ExposureMask | Xlib.X.KeyPressMask)
        #     newWin.change_property(DISP.intern_atom('_NET_WM_WINDOW_TYPE'), Xlib.Xatom.ATOM,
        #                            32, [DISP.intern_atom("_NET_WM_WINDOW_TYPE_DESKTOP"), ],
        #                            Xlib.X.PropModeReplace)
        #     newWin.map()
        #     w.reparent(newWin, 0, 0)

    def x11SendBehind(name):
        # Non-working attempts for Ubuntu/GNOME directly using x11 library (Xlib does not have XLowerWindow()???)
        x11 = ctypes.cdll.LoadLibrary('libX11.so.6')
        # m_display = x11.XOpenDisplay(None)
        m_display = x11.XOpenDisplay(bytes(os.environ["DISPLAY"], 'ascii'))
        if m_display == 0: return
        m_root_win = x11.XDefaultRootWindow(m_display, ctypes.c_int(0))

        def x11GetWindowsWithTitle(display, current, name):
            # https://stackoverflow.com/questions/37918260/python3-segfaults-when-using-ctypes-on-xlib-python2-works
            # https://www.unix.com/programming/254680-xlib-search-window-his-name.html
            # https://stackoverflow.com/questions/55173668/xgetwindowproperty-and-ctypes

            winName = ctypes.c_char_p()
            x11.XFetchName(display, current, ctypes.byref(winName))

            retVal = 0
            wName = ""
            if winName.value is not None:
                try:
                    wName = winName.value.decode()
                except:
                    pass

            if wName == name:
                retVal = current

            else:
                root = ctypes.c_ulong()
                children = ctypes.POINTER(ctypes.c_ulong)()
                parent = ctypes.c_ulong()
                nchildren = ctypes.c_uint()

                x11.XQueryTree(display, current, ctypes.byref(root), ctypes.byref(parent), ctypes.byref(children),
                               ctypes.byref(nchildren))

                for i in range(nchildren.value):
                    retVal = x11GetWindowsWithTitle(display, children[i], name)
                    if retVal != 0:
                        break

            return retVal

        hwnd = x11GetWindowsWithTitle(m_display, m_root_win, name)
        if hwnd:
            # https://stackoverflow.com/questions/33578144/xlib-push-window-to-the-back-of-the-other-windows
            window_type = x11.XInternAtom(m_display, "_NET_WM_WINDOW_TYPE", False)
            desktop = x11.XInternAtom(m_display, "_NET_WM_WINDOW_TYPE_DESKTOP", False)
            data = (ctypes.c_ubyte * len(str(desktop)))()

            # newWin = x11.XCreateSimpleWindow(m_display, m_root_win, ctypes.c_uint(0), ctypes.c_uint(0), ctypes.c_uint(1920), ctypes.c_uint(1080), ctypes.c_uint(0), ctypes.c_ulong(0), SCREEN.white_pixel)  # SCREEN.white_pixel) # WhitePixel(m_display, DefaultScreen(m_display)))
            # x11.XChangeProperty(m_display, newWin, window_type, Xlib.Xatom.ATOM, ctypes.c_int(32), Xlib.X.PropModeReplace, data, ctypes.c_int(1))
            # x11.XClearWindow(m_display, newWin)
            # x11.XMapWindow(m_display, newWin)

            x11.XChangeProperty(m_display, hwnd, window_type, Xlib.Xatom.ATOM, ctypes.c_int(32), Xlib.X.PropModeReplace, data, ctypes.c_int(1))
            # x11.XClearWindow(m_display, hwnd)
            x11.XMapWindow(m_display, hwnd)
            # x11.XReparentWindow(m_display, hwnd, newWin)

            x11.XLowerWindow(m_display, hwnd)

    def sendFront(name, parent):
        win = findWindowHandles(title=name)
        w = DISP.create_resource_object('window', win)
        w.reparent(parent, 0, 0)

    def getWallpaper():
        cmd = """gsettings get org.gnome.desktop.background picture-uri"""
        try:
            wp = subprocess.check_output(cmd, shell=True).decode(encoding="utf-8").strip()
        except:
            wp = ""
        return wp

    def setWallpaper(img=""):
        cmd = """gsettings set org.gnome.desktop.background picture-uri '%s'""" % img
        try:
            subprocess.Popen(cmd, shell=True)
            return True
        except:
            return False

    def getWorkArea():
        work_area = EWMH.getWorkArea()
        return work_area[0], work_area[1], work_area[2], work_area[3]

    def getAttributes(win):
        return EWMH.getWmWindowType(win, str=True)


elif "macOS" in platform.platform() or "Darwin" in platform.platform():
    import AppKit
    import Quartz

    def sendBehind(name):
        w = None
        for win in AppKit.NSApp().orderedWindows():
            w = win
            break
        if w:
            # https://stackoverflow.com/questions/4982584/how-do-i-draw-the-desktop-on-mac-os-x
            w.setLevel_(Quartz.kCGDesktopWindowLevel - 1)
            w.setCollectionBehavior_(Quartz.NSWindowCollectionBehaviorCanJoinAllSpaces |
                 Quartz.NSWindowCollectionBehaviorStationary |
                 Quartz.NSWindowCollectionBehaviorIgnoresCycle)

    def getWallpaper():
        # https://stackoverflow.com/questions/14099363/get-the-current-wallpaper-in-cocoa
        sharedSpace = AppKit.NSWorkspace.sharedWorkspace()
        mainScreen = AppKit.NSScreen.mainScreen()
        imageURL = sharedSpace.desktopImageURLForScreen_(mainScreen)
        return imageURL

    def setWallpaper(imageURL):
        # https://stackoverflow.com/questions/65936437/change-macos-background-picture-with-adapt-to-screen-parameter-in-python
        # Use this to convert a "normal" image path into a macOS wallpaper path (NSURL)
        # imageURL = Foundation.NSURL.fileURLWithPath_(img)
        sharedSpace = AppKit.NSWorkspace.sharedWorkspace()
        mainScreen = AppKit.NSScreen.mainScreen()
        sharedSpace.setDesktopImageURL_forScreen_options_error_(imageURL, mainScreen, None, None)

        # Use this to change image scaling and other options
        # fillColor = AppKit.NSColor.darkGrayColor()
        # optDict = Foundation.NSDictionary.dictionaryWithObjects_forKeys_([AppKit.NSImageScaleAxesIndependently, fillColor],
        #                                                       [AppKit.NSWorkspaceDesktopImageScalingKey,
        #                                                        AppKit.NSWorkspaceDesktopImageFillColorKey])
        # sharedSpace.setDesktopImageURL_forScreen_options_error_(img, mainScreen, optDict, None)

    def getWorkArea():
        work_area = AppKit.NSScreen.mainScreen().visibleFrame()
        return int(work_area.origin.x), 0, int(work_area.size.width), int(work_area.size.height)


def get_wm():
    # https://stackoverflow.com/questions/3333243/how-can-i-check-with-python-which-window-manager-is-running
    return os.environ.get('XDG_CURRENT_DESKTOP') or ""


def getWMAdjustments(is_macos, line_width):
    wm = get_wm()
    if "GNOME" in wm:
        # PyQt5 geometry is not correct in Ubuntu/GNOME?!?!?!
        xAdj = 0
        yAdj = 0
        xGap = line_width * 6
        yGap = 0
        wGap = line_width * 6
        hGap = line_width * 7
    elif "Cinnamon" in wm:
        # Mouse position does not fit windowsAt coordinates in Cinnamon
        xAdj = 0
        yAdj = 20
        xGap = 0
        yGap = line_width * 3
        wGap = 0
        hGap = - line_width * 3
    elif is_macos:
        xAdj = 0
        yAdj = 0
        xGap = 0
        yGap = line_width * 3
        wGap = 0
        hGap = 0
    else:
        xAdj = 0
        yAdj = 0
        xGap = - line_width
        yGap = 0
        wGap = line_width * 2
        hGap = line_width

    return xAdj, yAdj, xGap, yGap, wGap, hGap
