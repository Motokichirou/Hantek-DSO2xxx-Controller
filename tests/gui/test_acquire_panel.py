"""Headless-тесты панели AcquirePanel.

QT_QPA_PLATFORM=offscreen гарантирует безголовый режим.
Запуск: .venv/Scripts/python.exe -m pytest tests/gui/test_acquire_panel.py -q
"""
from __future__ import annotations

import os
import sys

import pytest

# Безголовый Qt — должно быть установлено ДО создания QApplication
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402
from PySide6.QtCore import QCoreApplication  # noqa: E402

from hantek_dso2d15.gui.panels.acquire import AcquirePanel  # noqa: E402


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
        # не удаляем — может понадобиться другим тестам в сьюте


# ---------------------------------------------------------------------------
# Фейк-scope
# ---------------------------------------------------------------------------

class _FakeAcquire:
    def __init__(self, type_="NORMal", count=4, points=4000, srate=1e9):
        self.type = type_
        self.count = count
        self.points = points
        self.srate = srate


class _FakeScope:
    def __init__(self, **kwargs):
        self.acquire = _FakeAcquire(**kwargs)


# ---------------------------------------------------------------------------
# Фикстура панели
# ---------------------------------------------------------------------------

@pytest.fixture
def panel(app):
    p = AcquirePanel()
    return p


# ---------------------------------------------------------------------------
# Тест 1: load_from_scope заполняет контролы и НЕ эмитирует settingChanged
# ---------------------------------------------------------------------------

class TestLoadFromScope:
    def test_load_does_not_emit(self, panel):
        """load_from_scope не должен эмитировать settingChanged."""
        received = []
        panel.settingChanged.connect(lambda path, val: received.append((path, val)))

        scope = _FakeScope(type_="AVERage", count=16, points=40_000, srate=500e6)
        panel.load_from_scope(scope)

        assert received == [], f"load_from_scope эмитировал: {received}"

    def test_load_sets_type(self, panel):
        """После load текущий тип должен совпадать с загруженным."""
        scope = _FakeScope(type_="PEAK", count=4, points=4000, srate=1e9)
        panel.load_from_scope(scope)
        assert panel._type.currentData() == "PEAK"

    def test_load_sets_count(self, panel):
        scope = _FakeScope(type_="NORMal", count=32, points=4000, srate=1e9)
        panel.load_from_scope(scope)
        assert panel._count.currentData() == 32

    def test_load_sets_points(self, panel):
        scope = _FakeScope(type_="NORMal", count=4, points=400_000, srate=1e9)
        panel.load_from_scope(scope)
        assert panel._points.currentData() == 400_000

    def test_load_shows_srate_in_label(self, panel):
        """srate должна отображаться в QLabel."""
        scope = _FakeScope(type_="NORMal", count=4, points=4000, srate=1e9)
        panel.load_from_scope(scope)
        text = panel._srate_label.text()
        assert text != "—", "srate QLabel должен быть заполнен после load"
        # 1e9 Sa/s → «1 GSa/s»
        assert "1" in text and "GSa" in text, f"Неожиданный текст srate: {text!r}"

    def test_load_srate_msa(self, panel):
        """500 MSa/s корректно форматируется."""
        scope = _FakeScope(type_="NORMal", count=4, points=4000, srate=500e6)
        panel.load_from_scope(scope)
        text = panel._srate_label.text()
        assert "500" in text and "MSa" in text, f"Неожиданный текст srate: {text!r}"


# ---------------------------------------------------------------------------
# Тест 2: изменение режима → settingChanged("acquire.type", canonical_str)
# ---------------------------------------------------------------------------

class TestTypeSignal:
    def test_change_type_emits_canonical(self, panel):
        """Смена режима → settingChanged('acquire.type', 'AVERage')."""
        # Убедимся, что стартуем не с AVERage
        scope = _FakeScope(type_="NORMal", count=4, points=4000, srate=1e9)
        panel.load_from_scope(scope)

        received = []
        panel.settingChanged.connect(lambda p, v: received.append((p, v)))

        idx = panel._type.findData("AVERage")
        panel._type.setCurrentIndex(idx)

        assert len(received) == 1, f"Ожидался 1 сигнал, получено {received}"
        path, value = received[0]
        assert path == "acquire.type"
        assert value == "AVERage"

    def test_change_type_peak(self, panel):
        scope = _FakeScope(type_="NORMal", count=4, points=4000, srate=1e9)
        panel.load_from_scope(scope)

        received = []
        panel.settingChanged.connect(lambda p, v: received.append((p, v)))

        idx = panel._type.findData("PEAK")
        panel._type.setCurrentIndex(idx)

        assert received == [("acquire.type", "PEAK")]

    def test_change_type_value_is_string(self, panel):
        """Значение в сигнале должно быть строкой, не None."""
        scope = _FakeScope(type_="NORMal", count=4, points=4000, srate=1e9)
        panel.load_from_scope(scope)

        received = []
        panel.settingChanged.connect(lambda p, v: received.append((p, v)))

        idx = panel._type.findData("HRESolution")
        panel._type.setCurrentIndex(idx)

        assert received and isinstance(received[0][1], str)


# ---------------------------------------------------------------------------
# Тест 3: изменение глубины → settingChanged("acquire.points", int)
# ---------------------------------------------------------------------------

class TestPointsSignal:
    def test_change_points_emits_int(self, panel):
        """Смена глубины → settingChanged('acquire.points', 40000) — int."""
        scope = _FakeScope(type_="NORMal", count=4, points=4000, srate=1e9)
        panel.load_from_scope(scope)

        received = []
        panel.settingChanged.connect(lambda p, v: received.append((p, v)))

        idx = panel._points.findData(40_000)
        panel._points.setCurrentIndex(idx)

        assert len(received) == 1
        path, value = received[0]
        assert path == "acquire.points"
        assert value == 40_000
        assert isinstance(value, int), f"Ожидался int, получен {type(value)}"

    def test_change_points_4m(self, panel):
        scope = _FakeScope(type_="NORMal", count=4, points=4000, srate=1e9)
        panel.load_from_scope(scope)

        received = []
        panel.settingChanged.connect(lambda p, v: received.append((p, v)))

        idx = panel._points.findData(4_000_000)
        panel._points.setCurrentIndex(idx)

        assert received == [("acquire.points", 4_000_000)]

    def test_points_value_not_label_string(self, panel):
        """Значение в сигнале НЕ должно быть строкой '40K'."""
        scope = _FakeScope(type_="NORMal", count=4, points=4000, srate=1e9)
        panel.load_from_scope(scope)

        received = []
        panel.settingChanged.connect(lambda p, v: received.append((p, v)))

        idx = panel._points.findData(40_000)
        panel._points.setCurrentIndex(idx)

        assert received and received[0][1] != "40K", "Значение не должно быть строкой-меткой"


# ---------------------------------------------------------------------------
# Тест 4: изменение усреднений → settingChanged("acquire.count", int)
# ---------------------------------------------------------------------------

class TestCountSignal:
    def test_change_count_emits_int(self, panel):
        """Смена усреднений → settingChanged('acquire.count', int)."""
        scope = _FakeScope(type_="NORMal", count=4, points=4000, srate=1e9)
        panel.load_from_scope(scope)

        received = []
        panel.settingChanged.connect(lambda p, v: received.append((p, v)))

        idx = panel._count.findData(64)
        panel._count.setCurrentIndex(idx)

        assert len(received) == 1
        path, value = received[0]
        assert path == "acquire.count"
        assert value == 64
        assert isinstance(value, int)

    def test_change_count_128(self, panel):
        scope = _FakeScope(type_="NORMal", count=4, points=4000, srate=1e9)
        panel.load_from_scope(scope)

        received = []
        panel.settingChanged.connect(lambda p, v: received.append((p, v)))

        idx = panel._count.findData(128)
        panel._count.setCurrentIndex(idx)

        assert received == [("acquire.count", 128)]


# ---------------------------------------------------------------------------
# Тест 5: структура виджета — наличие сигнала settingChanged
# ---------------------------------------------------------------------------

class TestPanelStructure:
    def test_has_settingChanged_signal(self, panel):
        """AcquirePanel должна иметь атрибут settingChanged (Signal)."""
        assert hasattr(panel, "settingChanged")

    def test_has_load_from_scope(self, panel):
        assert callable(getattr(panel, "load_from_scope", None))

    def test_type_combo_has_all_modes(self, panel):
        items = [panel._type.itemData(i) for i in range(panel._type.count())]
        assert set(items) == {"NORMal", "AVERage", "PEAK", "HRESolution"}

    def test_count_combo_has_all_values(self, panel):
        items = [panel._count.itemData(i) for i in range(panel._count.count())]
        assert set(items) == {4, 8, 16, 32, 64, 128}

    def test_points_combo_has_all_values(self, panel):
        items = [panel._points.itemData(i) for i in range(panel._points.count())]
        assert set(items) == {4000, 40000, 400000, 4000000, 8000000}

    def test_points_combo_labels(self, panel):
        """Комбо глубины должен отображать удобочитаемые метки."""
        texts = [panel._points.itemText(i) for i in range(panel._points.count())]
        assert "4K" in texts
        assert "40K" in texts
        assert "400K" in texts
        assert "4M" in texts
        assert "8M" in texts
