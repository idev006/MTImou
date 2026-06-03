from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from control_panel_app.constants import WINDOW_TITLE
from control_panel_app.styles import build_app_chrome_stylesheet, build_app_palette
from control_panel_app.window import ControlPanelWindow
from venv_guard import enforce_venv_python


def main() -> int:
    enforce_venv_python()
    app = QApplication(sys.argv)
    app.setApplicationName(WINDOW_TITLE)
    app.setStyle("Fusion")
    app.setPalette(build_app_palette())
    app.setStyleSheet(build_app_chrome_stylesheet())
    window = ControlPanelWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
