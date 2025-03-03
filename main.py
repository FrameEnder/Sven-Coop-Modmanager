#!/usr/bin/env python3
import os
import sys
from PyQt5.QtWidgets import QApplication
from modmanager.main_window import ModManagerWindow
from modmanager.ui_components import setDarkMode

if __name__ == "__main__":
    # Force Qt to use the xcb (X11) platform plugin to avoid Wayland issues
    os.environ["QT_QPA_PLATFORM"] = "xcb"

    app = QApplication(sys.argv)
    setDarkMode(app)  # Apply dark mode style
    window = ModManagerWindow()
    window.show()
    sys.exit(app.exec_())
