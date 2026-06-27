"""Offscreen-тесты CollapsibleSection (аккордеон).

QT_QPA_PLATFORM=offscreen гарантирует безголовый режим.
Запуск: .venv/Scripts/python.exe -m pytest tests/gui/test_accordion.py -q
"""
from __future__ import annotations

import os
import sys

import pytest

# Безголовый Qt — должно быть установлено ДО создания QApplication
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLabel, QWidget  # noqa: E402
from PySide6.QtCore import QCoreApplication  # noqa: E402

from hantek_dso2d15.gui.accordion import CollapsibleSection  # noqa: E402


# ---------------------------------------------------------------------------
# Одно приложение на весь модуль
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def app():
    existing = QCoreApplication.instance()
    if existing is not None:
        yield existing
    else:
        a = QApplication(sys.argv[:1])
        yield a


# ---------------------------------------------------------------------------
# Фикстуры
# ---------------------------------------------------------------------------

@pytest.fixture
def body(app):
    """Тело секции — простой QLabel."""
    return QLabel("тело секции")


@pytest.fixture
def section(body, app):
    """Развёрнутая секция (expanded=True по умолчанию)."""
    s = CollapsibleSection("КАНАЛ 1", body)
    s.show()   # нужно для корректной работы isVisible() у дочерних виджетов
    return s


# ---------------------------------------------------------------------------
# 1. Начальное состояние (expanded=True по умолчанию)
# ---------------------------------------------------------------------------

class TestDefaultExpanded:
    def test_default_is_expanded(self, section):
        assert section.is_expanded() is True

    def test_body_visible_when_expanded(self, section, body):
        assert body.isVisible() is True

    def test_chevron_shows_down_when_expanded(self, section):
        """▾ когда развёрнут."""
        assert section._chevron.text() == "▾", (
            f"Ожидался ▾, получен {section._chevron.text()!r}"
        )

    def test_initial_collapsed(self, app):
        """expanded=False в конструкторе — body сразу скрыт."""
        b = QLabel("тело")
        s = CollapsibleSection("ТЕСТ", b, expanded=False)
        s.show()
        assert s.is_expanded() is False
        assert b.isVisible() is False

    def test_initial_collapsed_chevron(self, app):
        """expanded=False → шеврон ▸."""
        b = QLabel("тело")
        s = CollapsibleSection("ТЕСТ", b, expanded=False)
        assert s._chevron.text() == "▸"


# ---------------------------------------------------------------------------
# 2. Клик по заголовку — сворачивание/разворачивание
# ---------------------------------------------------------------------------

class TestHeaderClick:
    def test_click_collapses_body(self, section, body):
        """Клик по заголовку скрывает body (из expanded=True)."""
        section.set_expanded(True)
        section._on_header_clicked()
        assert body.isVisible() is False

    def test_click_emits_toggled_false(self, section):
        """Клик → toggled(False) при сворачивании."""
        section.set_expanded(True)
        received = []
        section.toggled.connect(lambda v: received.append(v))
        section._on_header_clicked()
        assert received == [False], f"Ожидался [False], получено {received}"

    def test_double_click_expands_back(self, section, body):
        """Два клика: свернуть → развернуть."""
        section.set_expanded(True)
        section._on_header_clicked()
        assert body.isVisible() is False
        section._on_header_clicked()
        assert body.isVisible() is True

    def test_double_click_emits_both(self, section):
        """Два клика эмитят [False, True]."""
        section.set_expanded(True)
        received = []
        section.toggled.connect(lambda v: received.append(v))
        section._on_header_clicked()
        section._on_header_clicked()
        assert received == [False, True], f"Получено {received}"


# ---------------------------------------------------------------------------
# 3. set_expanded — без emit по умолчанию
# ---------------------------------------------------------------------------

class TestSetExpanded:
    def test_set_expanded_false_hides_body(self, section, body):
        section.set_expanded(True)
        section.set_expanded(False)
        assert body.isVisible() is False

    def test_set_expanded_true_shows_body(self, section, body):
        section.set_expanded(False)
        section.set_expanded(True)
        assert body.isVisible() is True

    def test_set_expanded_no_emit_by_default(self, section):
        """set_expanded без emit=True НЕ эмитит toggled."""
        section.set_expanded(True)
        received = []
        section.toggled.connect(lambda v: received.append(v))
        section.set_expanded(False)
        assert received == [], f"Сигнал не должен эмититься, получено {received}"

    def test_set_expanded_emit_true_emits(self, section):
        """set_expanded(True, emit=True) эмитит toggled(True)."""
        section.set_expanded(False)
        received = []
        section.toggled.connect(lambda v: received.append(v))
        section.set_expanded(True, emit=True)
        assert received == [True], f"Ожидался [True], получено {received}"

    def test_set_expanded_false_emit_true_emits(self, section):
        """set_expanded(False, emit=True) эмитит toggled(False)."""
        section.set_expanded(True)
        received = []
        section.toggled.connect(lambda v: received.append(v))
        section.set_expanded(False, emit=True)
        assert received == [False], f"Ожидался [False], получено {received}"

    def test_is_expanded_tracks_set_expanded(self, section):
        section.set_expanded(False)
        assert section.is_expanded() is False
        section.set_expanded(True)
        assert section.is_expanded() is True


# ---------------------------------------------------------------------------
# 4. Шеврон обновляется корректно
# ---------------------------------------------------------------------------

class TestChevron:
    def test_chevron_changes_to_collapsed(self, section):
        section.set_expanded(True)
        section._on_header_clicked()
        assert section._chevron.text() == "▸"

    def test_chevron_changes_to_expanded(self, section):
        section.set_expanded(False)
        section._on_header_clicked()
        assert section._chevron.text() == "▾"

    def test_chevron_via_set_expanded(self, section):
        section.set_expanded(False)
        assert section._chevron.text() == "▸"
        section.set_expanded(True)
        assert section._chevron.text() == "▾"


# ---------------------------------------------------------------------------
# 5. Структура виджета
# ---------------------------------------------------------------------------

class TestStructure:
    def test_header_returns_qwidget(self, section):
        h = section.header()
        assert isinstance(h, QWidget)

    def test_header_fixed_height_32(self, section):
        """Заголовок должен иметь фиксированную высоту 32px."""
        h = section.header()
        # fixedHeight задаётся через setFixedHeight(32)
        assert h.height() == 32 or h.maximumHeight() == 32

    def test_has_toggled_signal(self, section):
        assert hasattr(section, "toggled")

    def test_is_expanded_returns_bool(self, section):
        assert isinstance(section.is_expanded(), bool)

    def test_has_on_header_clicked(self, section):
        assert callable(getattr(section, "_on_header_clicked", None))
