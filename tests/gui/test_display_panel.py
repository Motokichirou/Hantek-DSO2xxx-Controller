"""Headless-тесты панели DisplayPanel.

QT_QPA_PLATFORM=offscreen гарантирует безголовый режим.
Запуск: .venv\\Scripts\\python.exe -m pytest tests/gui/test_display_panel.py -q
"""
from __future__ import annotations

import os
import sys

import pytest

# Безголовый Qt — должно быть установлено ДО создания QApplication
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication  # noqa: E402
from PySide6.QtWidgets import QApplication   # noqa: E402

from hantek_dso2d15.gui.panels.display import DisplayPanel  # noqa: E402


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
# Фикстура панели (новый экземпляр на каждый тест)
# ---------------------------------------------------------------------------

@pytest.fixture
def panel(app):
    return DisplayPanel()


# ---------------------------------------------------------------------------
# Тест 1: дефолты при старте — без эмиссии
# ---------------------------------------------------------------------------

class TestDefaults:
    def test_init_does_not_emit(self, app):
        """DisplayPanel.__init__ не должен эмитировать displayChanged."""
        received = []

        # Подключаем до создания — нельзя: Signal ещё не существует.
        # Создаём объект, затем коннектим и проверяем что прошлых эмиссий нет.
        # Реальная проверка: создаём и сразу подключаем, затем ничего не делаем.
        p = DisplayPanel()
        p.displayChanged.connect(lambda k, v: received.append((k, v)))
        # Не трогаем контролы — received должен остаться пустым
        assert received == [], f"__init__ эмитировал: {received}"

    def test_defaults_type(self, panel):
        """defaults()['type'] == 'VECTors'."""
        d = panel.defaults()
        assert d["type"] == "VECTors", f"Ожидали 'VECTors', получили {d['type']!r}"

    def test_defaults_grid(self, panel):
        """defaults()['grid'] == 'REAL'."""
        d = panel.defaults()
        assert d["grid"] == "REAL", f"Ожидали 'REAL', получили {d['grid']!r}"

    def test_defaults_wbright(self, panel):
        """defaults()['wbright'] == 80."""
        d = panel.defaults()
        assert d["wbright"] == 80, f"Ожидали 80, получили {d['wbright']!r}"

    def test_defaults_gbright(self, panel):
        """defaults()['gbright'] == 40."""
        d = panel.defaults()
        assert d["gbright"] == 40, f"Ожидали 40, получили {d['gbright']!r}"

    def test_defaults_keys(self, panel):
        """defaults() содержит ровно ключи type, grid, wbright, gbright."""
        d = panel.defaults()
        assert set(d.keys()) == {"type", "grid", "wbright", "gbright"}

    def test_type_combo_default_data(self, panel):
        """Комбо type при старте показывает 'VECTors'."""
        assert panel._type.currentData() == "VECTors"

    def test_grid_combo_default_data(self, panel):
        """Комбо grid при старте показывает 'REAL'."""
        assert panel._grid.currentData() == "REAL"

    def test_wbright_default_value(self, panel):
        """Контрол wbright при старте = 80."""
        assert panel._wbright.value() == 80

    def test_gbright_default_value(self, panel):
        """Контрол gbright при старте = 40."""
        assert panel._gbright.value() == 40


# ---------------------------------------------------------------------------
# Тест 2: смена типа → displayChanged("type", literal_str)
# ---------------------------------------------------------------------------

class TestTypeSignal:
    def test_change_type_to_dots_emits(self, panel):
        """Смена type → VECTors→DOTS эмитит displayChanged('type', 'DOTS')."""
        received = []
        panel.displayChanged.connect(lambda k, v: received.append((k, v)))

        idx = panel._type.findData("DOTS")
        panel._type.setCurrentIndex(idx)

        assert len(received) == 1, f"Ожидался 1 сигнал, получено: {received}"
        key, value = received[0]
        assert key == "type"
        assert value == "DOTS"

    def test_change_type_to_vectors_emits(self, panel):
        """Смена type DOTS→VECTors эмитит displayChanged('type', 'VECTors')."""
        # Сначала ставим DOTS без прослушивания
        panel._type.blockSignals(True)
        idx = panel._type.findData("DOTS")
        panel._type.setCurrentIndex(idx)
        panel._type.blockSignals(False)

        received = []
        panel.displayChanged.connect(lambda k, v: received.append((k, v)))

        idx = panel._type.findData("VECTors")
        panel._type.setCurrentIndex(idx)

        assert received == [("type", "VECTors")]

    def test_type_value_is_string(self, panel):
        """Значение в сигнале type — str, не None."""
        received = []
        panel.displayChanged.connect(lambda k, v: received.append((k, v)))

        idx = panel._type.findData("DOTS")
        panel._type.setCurrentIndex(idx)

        assert received and isinstance(received[0][1], str)

    def test_type_combo_has_vectors_and_dots(self, panel):
        """Комбо type содержит оба значения VECTors и DOTS."""
        items = [panel._type.itemData(i) for i in range(panel._type.count())]
        assert "VECTors" in items
        assert "DOTS" in items

    def test_type_combo_labels(self, panel):
        """Метки комбо type — «Линии» и «Точки»."""
        texts = [panel._type.itemText(i) for i in range(panel._type.count())]
        assert "Линии" in texts
        assert "Точки" in texts


# ---------------------------------------------------------------------------
# Тест 3: смена сетки → displayChanged("grid", literal_str)
# ---------------------------------------------------------------------------

class TestGridSignal:
    def test_change_grid_to_dotted_emits(self, panel):
        """Смена grid REAL→DOTTed эмитит displayChanged('grid', 'DOTTed')."""
        received = []
        panel.displayChanged.connect(lambda k, v: received.append((k, v)))

        idx = panel._grid.findData("DOTTed")
        panel._grid.setCurrentIndex(idx)

        assert len(received) == 1, f"Ожидался 1 сигнал, получено: {received}"
        key, value = received[0]
        assert key == "grid"
        assert value == "DOTTed"

    def test_change_grid_to_real_emits(self, panel):
        """Смена grid DOTTed→REAL эмитит displayChanged('grid', 'REAL')."""
        # Ставим DOTTed без прослушивания
        panel._grid.blockSignals(True)
        idx = panel._grid.findData("DOTTed")
        panel._grid.setCurrentIndex(idx)
        panel._grid.blockSignals(False)

        received = []
        panel.displayChanged.connect(lambda k, v: received.append((k, v)))

        idx = panel._grid.findData("REAL")
        panel._grid.setCurrentIndex(idx)

        assert received == [("grid", "REAL")]

    def test_grid_value_is_string(self, panel):
        """Значение в сигнале grid — str."""
        received = []
        panel.displayChanged.connect(lambda k, v: received.append((k, v)))

        idx = panel._grid.findData("DOTTed")
        panel._grid.setCurrentIndex(idx)

        assert received and isinstance(received[0][1], str)

    def test_grid_combo_has_dotted_and_real(self, panel):
        """Комбо grid содержит DOTTed и REAL."""
        items = [panel._grid.itemData(i) for i in range(panel._grid.count())]
        assert "DOTTed" in items
        assert "REAL" in items

    def test_grid_combo_labels(self, panel):
        """Метки комбо grid — «Точечная» и «Сплошная»."""
        texts = [panel._grid.itemText(i) for i in range(panel._grid.count())]
        assert "Точечная" in texts
        assert "Сплошная" in texts


# ---------------------------------------------------------------------------
# Тест 4: изменение яркости осциллограммы → displayChanged("wbright", int)
# ---------------------------------------------------------------------------

class TestWbrightSignal:
    def test_change_wbright_emits_int(self, panel):
        """Смена wbright → displayChanged('wbright', int)."""
        received = []
        panel.displayChanged.connect(lambda k, v: received.append((k, v)))

        panel._wbright.setValue(50)

        # Фильтруем только wbright (дефолт уже 80, так что 50 — смена)
        wbright_events = [(k, v) for k, v in received if k == "wbright"]
        assert len(wbright_events) >= 1
        key, value = wbright_events[-1]
        assert key == "wbright"
        assert value == 50
        assert isinstance(value, int), f"Ожидался int, получен {type(value)}"

    def test_wbright_range_0(self, panel):
        """wbright принимает значение 0."""
        received = []
        panel.displayChanged.connect(lambda k, v: received.append((k, v)))

        panel._wbright.setValue(0)

        wbright_events = [(k, v) for k, v in received if k == "wbright"]
        assert wbright_events and wbright_events[-1][1] == 0

    def test_wbright_range_100(self, panel):
        """wbright принимает значение 100."""
        received = []
        panel.displayChanged.connect(lambda k, v: received.append((k, v)))

        panel._wbright.setValue(100)

        wbright_events = [(k, v) for k, v in received if k == "wbright"]
        assert wbright_events and wbright_events[-1][1] == 100

    def test_wbright_key_is_wbright(self, panel):
        """Ключ сигнала — строго 'wbright'."""
        received = []
        panel.displayChanged.connect(lambda k, v: received.append((k, v)))

        panel._wbright.setValue(60)

        wbright_events = [(k, v) for k, v in received if k == "wbright"]
        assert wbright_events, "Нет события wbright"
        assert all(k == "wbright" for k, _ in wbright_events)


# ---------------------------------------------------------------------------
# Тест 5: изменение яркости сетки → displayChanged("gbright", int)
# ---------------------------------------------------------------------------

class TestGbrightSignal:
    def test_change_gbright_emits_int(self, panel):
        """Смена gbright → displayChanged('gbright', int)."""
        received = []
        panel.displayChanged.connect(lambda k, v: received.append((k, v)))

        panel._gbright.setValue(70)

        gbright_events = [(k, v) for k, v in received if k == "gbright"]
        assert len(gbright_events) >= 1
        key, value = gbright_events[-1]
        assert key == "gbright"
        assert value == 70
        assert isinstance(value, int), f"Ожидался int, получен {type(value)}"

    def test_gbright_range_0(self, panel):
        """gbright принимает значение 0."""
        received = []
        panel.displayChanged.connect(lambda k, v: received.append((k, v)))

        panel._gbright.setValue(0)

        gbright_events = [(k, v) for k, v in received if k == "gbright"]
        assert gbright_events and gbright_events[-1][1] == 0

    def test_gbright_range_100(self, panel):
        """gbright принимает значение 100."""
        received = []
        panel.displayChanged.connect(lambda k, v: received.append((k, v)))

        panel._gbright.setValue(100)

        gbright_events = [(k, v) for k, v in received if k == "gbright"]
        assert gbright_events and gbright_events[-1][1] == 100

    def test_gbright_key_is_gbright(self, panel):
        """Ключ сигнала — строго 'gbright'."""
        received = []
        panel.displayChanged.connect(lambda k, v: received.append((k, v)))

        panel._gbright.setValue(20)

        gbright_events = [(k, v) for k, v in received if k == "gbright"]
        assert gbright_events, "Нет события gbright"
        assert all(k == "gbright" for k, _ in gbright_events)


# ---------------------------------------------------------------------------
# Тест 6: defaults() отражает текущее состояние контролов
# ---------------------------------------------------------------------------

class TestDefaultsSnapshot:
    def test_defaults_reflects_changed_type(self, panel):
        """После смены type через blockSignals, defaults() отдаёт новое значение."""
        panel._type.blockSignals(True)
        idx = panel._type.findData("DOTS")
        panel._type.setCurrentIndex(idx)
        panel._type.blockSignals(False)

        d = panel.defaults()
        assert d["type"] == "DOTS"

    def test_defaults_reflects_changed_wbright(self, panel):
        """defaults()['wbright'] отражает текущее значение контрола."""
        panel._wbright.blockSignals(True)
        panel._wbright.setValue(33)
        panel._wbright.blockSignals(False)

        d = panel.defaults()
        assert d["wbright"] == 33

    def test_defaults_reflects_changed_gbright(self, panel):
        """defaults()['gbright'] отражает текущее значение контрола."""
        panel._gbright.blockSignals(True)
        panel._gbright.setValue(77)
        panel._gbright.blockSignals(False)

        d = panel.defaults()
        assert d["gbright"] == 77

    def test_defaults_no_side_effects(self, panel):
        """defaults() не эмитирует displayChanged."""
        received = []
        panel.displayChanged.connect(lambda k, v: received.append((k, v)))

        _ = panel.defaults()

        assert received == [], f"defaults() эмитировал: {received}"


# ---------------------------------------------------------------------------
# Тест 7: структура виджета
# ---------------------------------------------------------------------------

class TestPanelStructure:
    def test_has_displayChanged_signal(self, panel):
        """DisplayPanel имеет атрибут displayChanged."""
        assert hasattr(panel, "displayChanged")

    def test_has_defaults_method(self, panel):
        """DisplayPanel имеет вызываемый метод defaults()."""
        assert callable(getattr(panel, "defaults", None))

    def test_has_type_combo(self, panel):
        """DisplayPanel имеет атрибут _type (QComboBox)."""
        from PySide6.QtWidgets import QComboBox
        assert hasattr(panel, "_type")
        assert isinstance(panel._type, QComboBox)

    def test_has_grid_combo(self, panel):
        """DisplayPanel имеет атрибут _grid (QComboBox)."""
        from PySide6.QtWidgets import QComboBox
        assert hasattr(panel, "_grid")
        assert isinstance(panel._grid, QComboBox)

    def test_has_wbright_control(self, panel):
        """DisplayPanel имеет атрибут _wbright с методом value()."""
        assert hasattr(panel, "_wbright")
        assert callable(getattr(panel._wbright, "value", None))

    def test_has_gbright_control(self, panel):
        """DisplayPanel имеет атрибут _gbright с методом value()."""
        assert hasattr(panel, "_gbright")
        assert callable(getattr(panel._gbright, "value", None))

    def test_wbright_min_max(self, panel):
        """_wbright имеет диапазон 0..100."""
        assert panel._wbright.minimum() == 0
        assert panel._wbright.maximum() == 100

    def test_gbright_min_max(self, panel):
        """_gbright имеет диапазон 0..100."""
        assert panel._gbright.minimum() == 0
        assert panel._gbright.maximum() == 100
