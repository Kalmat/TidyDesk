#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import math
import subprocess
import sys
import urllib.request
import json


def resource_path(rel_path):
    """ Thanks to: detly < https://stackoverflow.com/questions/4416336/adding-a-program-icon-in-python-gtk/4416367 > """
    dir_of_py_file = os.path.dirname(__file__)
    rel_path_to_resource = os.path.join(dir_of_py_file, rel_path)
    abs_path_to_resource = os.path.abspath(rel_path_to_resource)
    if os.path.isdir(abs_path_to_resource) and abs_path_to_resource[-1:] != os.path.sep:
        abs_path_to_resource += os.path.sep
    return abs_path_to_resource


def get_CPU_temp(archOS):
    # Will only work on Linux OS
    temp = "n/a"
    if "arm" in archOS or "Linux" in archOS:
        res = os.popen("cat /sys/class/thermal/thermal_zone0/temp").readline().replace(os.linesep, "")
        if res.isdigit():
            temp = str(round(float(res) / 1000, 1)) + "º"

    return temp


def get_CPU_usage(archOS):
    # Will only work on Linux OS
    usage = "n/a"
    if "arm" in archOS or "Linux" in archOS:
        usage = os.popen("top -n1 | awk '/Cpu\(s\):/ {print $2+$4}'").readline().strip() + "%"

    return usage


def get_coordinates(url):

    coordinates = []
    try:
        with urllib.request.urlopen(url) as data:
            resp = json.loads(data.read().decode('utf8'))

        for i in range(20):
            try:
                coordinates.append([resp[i]["display_name"], resp[i]["lat"], resp[i]["lon"]])
            except:
                break
    except:
        pass

    return coordinates


def get_location_by_ip(url):

    ret = []
    try:
        with urllib.request.urlopen(url) as data:
            resp = json.loads((data.read().decode('utf8')))

        if resp["status"] == "success":
            ret = [resp["city"], resp["regionName"], resp["country"], resp["lat"], resp["lon"]]
    except:
        pass

    return ret


# Units
METRIC = 'metric'
IMPERIAL = 'imperial'
def get_distance(origin, destination, units=METRIC):

    lat1, lon1 = origin
    lat2, lon2 = destination
    if units == METRIC:
        radius = 6371  # km
    elif units == IMPERIAL:
        radius = 6371 * 0.6213712  # miles
    else:
        return -1

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) * math.sin(dlat / 2) +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) * math.sin(dlon / 2))
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    d = radius * c

    return d


def notify(message, sound, icon, title='Clock by alef'):
    import playsound
    import plyer

    if message is not None:
        plyer.notification.notify(
            title=title,
            message=message,
            app_icon=icon,
            timeout=5,
        )

    if sound is not None:
        playsound.playsound(sound)


def load_font(archOS, fontpath, private=True, enumerable=False):
    '''
    Makes fonts located in file `fontpath` available to the font system.
    `private`     if True, other processes cannot see this font, and this
                  font will be unloaded when the process dies
    `enumerable`  if True, this font will appear when enumerating fonts
    See https://msdn.microsoft.com/en-us/library/dd183327(VS.85).aspx
    '''
    # This function was taken from
    # https://github.com/ifwe/digsby/blob/f5fe00244744aa131e07f09348d10563f3d8fa99/digsby/src/gui/native/win/winfonts.py#L15

    if "Windows" in archOS:
        from ctypes import windll, byref, create_string_buffer

        FR_PRIVATE = 0x10
        FR_NOT_ENUM = 0x20

        pathbuf = create_string_buffer(fontpath.encode())
        AddFontResourceEx = windll.gdi32.AddFontResourceExA

        flags = (FR_PRIVATE if private else 0) | (FR_NOT_ENUM if not enumerable else 0)
        numFontsAdded = AddFontResourceEx(byref(pathbuf), flags, 0)
        return bool(numFontsAdded)
    else:
        from fontTools.ttLib import TTFont
        try:
            TTFont(fontpath)
            return True
        except:
            return False


def win_run_as_admin(argv=None, debug=False, force_admin=True):
    # https://stackoverflow.com/questions/19672352/how-to-run-python-script-with-elevated-privilege-on-windows (Gary Lee)

    from ctypes import windll
    shell32 = windll.shell32

    if argv is None and shell32.IsUserAnAdmin():
        # Already running as admin
        return True

    if argv is None:
        argv = sys.argv
    if hasattr(sys, '_MEIPASS'):
        # Support pyinstaller wrapped program.
        arguments = argv[1:]
    else:
        arguments = argv
    argument_line = u' '.join(arguments)
    executable = sys.executable
    if debug:
        print('Command line: ', executable, argument_line)
    console_mode = 0
    if debug:
        console_mode = 1
    ret = shell32.ShellExecuteW(None, u"runas", executable, argument_line, None, console_mode)
    if int(ret) <= 32:
        # Not possible to gain admin privileges
        if not force_admin:
            argument_line = "not_admin " + argument_line
            shell32.ShellExecuteW(None, u"open", executable, argument_line, None, console_mode)
        return False

    # Gaining admin privileges in process
    return None


def linux_run_as_admin():
    euid = os.geteuid()
    if euid != 0:
        args = ['sudo', sys.executable] + sys.argv + [os.environ]
        # the next line replaces the currently-running process with the sudo
        os.execlpe('sudo', *args)


def get_screen_pos(name=None):
    # Position doesn't take into account border width and title bar height
    try:
        import pygetwindow

        win = None
        if not name:
            win = pygetwindow.getActiveWindow()
        else:
            windows = pygetwindow.getWindowsWithTitle(name)
            if windows:
                win = windows[0]
        if win:
            return win.left, win.top, win.width, win.height
    except:
        return None, None, 0, 0

    return None, None, 0, 0


def win_get_screen_pos(hwnd=None, add_decoration=False):
    # https: // stackoverflow.com / questions / 4135928 / pygame - display - position?rq = 1  (Alexandre Willame)

    from ctypes import POINTER, WINFUNCTYPE, windll
    from ctypes.wintypes import BOOL, HWND, RECT

    # get our window ID
    if not hwnd:
        # pygame example:
        # hwnd = pygame.display.get_wm_info()["window"]
        hwnd = windll.user32.GetForegroundWindow()

    # Jump through all the ctypes hoops:
    prototype = WINFUNCTYPE(BOOL, HWND, POINTER(RECT))
    paramflags = (1, "hwnd"), (2, "lprect")

    GetWindowRect = prototype(("GetWindowRect", windll.user32), paramflags)

    # finally get our data!
    rect = GetWindowRect(hwnd)

    # This can be used to adjust the position if needed:
    titlebar_height = 0
    border_width = 0
    if add_decoration:
        try:  # >= win 8.1
            windll.shcore.SetProcessDpiAwareness(2)
        except:  # win 8.0 or less
            windll.user32.SetProcessDPIAware()
        titlebar_height = windll.user32.GetSystemMetrics(4)
        border_width = windll.user32.GetSystemMetrics(5)

    # Return x, y, width, height
    return rect.left - border_width, rect.top - titlebar_height, rect.right - rect.left, rect.bottom - rect.top


def linux_get_screen_pos():
    # https://stackoverflow.com/questions/12775136/get-window-position-and-size-in-python-with-xlib (mgalgs)

    import Xlib.display

    disp = Xlib.display.Display()
    root = disp.screen().root
    win_id = root.get_full_property(disp.intern_atom('_NET_ACTIVE_WINDOW'), Xlib.X.AnyPropertyType).value[0]
    try:
        win = disp.create_resource_object('window', win_id)
    except Xlib.error.XError:
        win = None

    """
    Returns the (x, y, height, width) of a window relative to the top-left
    of the screen.
    """
    if win is not None:
        geom = win.get_geometry()
        (x, y) = (geom._x, geom._y)
        while True:
            parent = win.query_tree()._parent
            pgeom = parent.get_geometry()
            x += pgeom._x
            y += pgeom._y
            if parent.id == root.id:
                break
            win = parent
        return x, y, geom.width, geom.height
    else:
        return None, None, 0, 0


def subprocess_args(include_stdout=True):
    # https: // github.com / pyinstaller / pyinstaller / wiki / Recipe - subprocess (by twisted)
    # The following is true only on Windows.
    if hasattr(subprocess, 'STARTUPINFO'):
        # On Windows, subprocess calls will pop up a command window by default
        # when run from Pyinstaller with the ``--noconsole`` option. Avoid this
        # distraction.
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        # Windows doesn't search the path by default. Pass it an environment so
        # it will.
        env = os.environ
    else:
        si = None
        env = None

    # ``subprocess.check_output`` doesn't allow specifying ``stdout``::
    #
    #   Traceback (most recent call last):
    #     File "test_subprocess.py", line 58, in <module>
    #       **subprocess_args(stdout=None))
    #     File "C:\Python27\lib\subprocess.py", line 567, in check_output
    #       raise ValueError('stdout argument not allowed, it will be overridden.')
    #   ValueError: stdout argument not allowed, it will be overridden.
    #
    # So, add it only if it's needed.
    if include_stdout:
        ret = {'stdout': subprocess.PIPE}
    else:
        ret = {}

    # On Windows, running this from the binary produced by Pyinstaller
    # with the ``--noconsole`` option requires redirecting everything
    # (stdin, stdout, stderr) to avoid an OSError exception
    # "[Error 6] the handle is invalid."
    ret.update({'stdin': subprocess.PIPE,
                'stderr': subprocess.PIPE,
                'startupinfo': si,
                'env': env})
    return ret


def wrap_text(text, font, width):
    # ColdrickSotK
    # https://github.com/ColdrickSotK/yamlui/blob/master/yamlui/util.py#L82-L143
    """Wrap text to fit inside a given width when rendered.
    :param text: The text to be wrapped.
    :param font: The font the text will be rendered in.
    :param width: The width to wrap to."""

    text_lines = text.replace('\t', '    ').split('\n')
    if width is None or width == 0:
        return text_lines

    wrapped_lines = []
    for line in text_lines:
        line = line.rstrip() + ' '
        if line == ' ':
            wrapped_lines.append(line)
            continue

        # Get the leftmost space ignoring leading whitespace
        start = len(line) - len(line.lstrip())
        start = line.index(' ', start)
        while start + 1 < len(line):
            # Get the next potential splitting point
            next = line.index(' ', start + 1)
            if font.size(line[:next])[0] <= width:
                start = next
            else:
                wrapped_lines.append(line[:start])
                line = line[start + 1:]
                start = line.index(' ')
        line = line[:-1]
        if line:
            wrapped_lines.append(line)

    return wrapped_lines


def to_float(s, dec=1):
    num = ''.join(n for n in str(s) if n.isdigit() or n == "." or n == "-")
    try:
        return round(float(num), dec)
    except Exception:
        return 0.0


def getFilesInFolder(folder, extensions):
    try:
        files = [file for file in os.listdir(folder) if os.path.isfile(os.path.join(folder, file))]
        fileList = []
        for file in files:
            if not extensions or file.split(".")[-1].lower() in extensions:
                fileList.append(os.path.join(folder, file))
    except:
        fileList = []
    return fileList

