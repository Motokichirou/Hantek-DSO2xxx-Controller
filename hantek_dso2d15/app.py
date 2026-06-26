"""Точка входа десктоп-клиента Hantek DSO2D15.

Запуск:  .venv/Scripts/python.exe -m hantek_dso2d15.app
"""
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from hantek_dso2d15.gui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Hantek DSO2D15")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
