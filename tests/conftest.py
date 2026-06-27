"""Общие фикстуры тестов.

Единый session-scoped QApplication (GUI) на весь прогон. Иначе разные модули
создают свои QCoreApplication/QApplication: если первым возникает
QCoreApplication (без GUI, напр. из engine-тестов), последующее создание QWidget
в GUI-тестах падает сегфолтом. Создаём GUI-приложение ОДИН раз до всех тестов —
тогда QCoreApplication.instance()/QApplication.instance() всегда отдают его.
"""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest


@pytest.fixture(scope="session", autouse=True)
def _qt_app():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app
    # не удаляем приложение — удаление на teardown интерпретатора рискует сегфолтом
