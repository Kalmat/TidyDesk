# TidyDesk

## What is this for

This is a python3 script, based on PyQt5, for windows 8-10 and Linux GNOME/Cinnamon. It also works in macOS (Catalina+), but since it uses Apple Script, it's not very fluent and needs to be granted on Security&Privacy/Accessibility options.

It will allow you to easily arrange all your desktop windows, using different grids to fit your needs according to the number of windows and desired layout 

You won't need any Admin privileges to install it (it's fully portable) or use it.

## Requires

KalmaTools v.0.0.1 or higher, that you can find here: https://bitbucket.org/Kalmat/kalmatools

Download the wheel file located on dist folder, and install it on your system or virtual environment (venv) using:

    pip install kalmatools-0.0.1-py3-none-any.whl

## How to use it

Run it, and right-click on the TidyDesk tray icon to access options menu:

* Select Grid - Select the grid style 
* Help
* Quit

To arrange windows, press ctrl + windows/command keys together to show the grid on screen. Then click on a window title bar, and drag and drop it on the target (highlighted) section of the grid while keeping the activation keys (ctrl+alt) pressed. The window will automatically move and resize to fit the selected area.

#### IMPORTANT

Move and, especially, resize behaviors strongly depend on every application rules. So, it's possible some windows/applications don't perfectly adjust to the desired position and size, or even do not react at all.
