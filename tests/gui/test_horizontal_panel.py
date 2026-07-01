"""Headless-тесты панели HorizontalPanel.

QT_QPA_PLATFORM=offscreen гарантирует безголовый режим.
Запуск: .venv/Scripts/python.exe -m pytest tests/gui/test_horizontal_panel.py -q
"""
from __future__ import annotations

import os
import sys
import types

import pytest

# Безголовый Qt — должно быть установлено ДО создания QApplication
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication   # noqa: E402
from PySide6.QtWidgets import QApplication    # noqa: E402

from hantek_dso2d15.gui.panels.horizontal import HorizontalPanel  # noqa: E402


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
# Фейк-scope (SimpleNamespace — изолированные экземпляры)
# ---------------------------------------------------------------------------

def _make_scope(
    scale: float = 1e-3,
    position: float = 0.0,
    mode: str = "MAIN",
    win_enable: bool = False,
    win_scale: float = 1e-4,
    win_position: float = 0.0,
):
    window = types.SimpleNamespace(
        enable=win_enable, scale=win_scale, position=win_position
    )
    timebase = types.SimpleNamespace(
        scale=scale, position=position, mode=mode, window=window
    )
    return types.SimpleNamespace(timebase=timebase)


# ---------------------------------------------------------------------------
# Фикстура панели (function-scope — свежая для каждого теста)
# ---------------------------------------------------------------------------

@pytest.fixture
def panel(app):
    return HorizontalPanel()


# ---------------------------------------------------------------------------
# Тест 1: load_from_scope заполняет контролы и НЕ эмитирует settingChanged
# ---------------------------------------------------------------------------

class TestLoadFromScope:
    def test_load_does_not_emit(self, panel):
        """load_from_scope не должен эмитировать settingChanged."""
        received = []
        panel.settingChanged.connect(lambda path, val: received.append((path, val)))
        panel.load_from_scope(
            _make_scope(scale=5e-4, position=0.1, mode="ROLL",
                        win_enable=True, win_scale=1e-5, win_position=0.05)
        )
        assert received == [], f"load_from_scope эмитировал: {received}"

    def test_load_fills_position(self, panel):
        """После load _position отображает правильное значение."""
        panel.load_from_scope(_make_scope(position=1.5))
        assert panel._position.value() == pytest.approx(1.5)

    def test_load_fills_mode(self, panel):
        """После load _mode показывает правильный режим."""
        panel.load_from_scope(_make_scope(mode="XY"))
        assert panel._mode.value() == "XY"

    def test_load_fills_scale(self, panel):
        """После load _scale содержит правильный масштаб."""
        panel.load_from_scope(_make_scope(scale=2e-4))
        assert panel._scale.value() == pytest.approx(2e-4)

    def test_load_fills_win_enable_true(self, panel):
        """После load _win_enable отражает win_enable=True."""
        panel.load_from_scope(_make_scope(win_enable=True))
        assert panel._win_enable.isChecked() is True

    def test_load_fills_win_enable_false(self, panel):
        """После load _win_enable отражает win_enable=False."""
        panel.load_from_scope(_make_scope(win_enable=False))
        assert panel._win_enable.isChecked() is False

    def test_load_fills_win_scale(self, panel):
        """После load _win_scale содержит правильное значение."""
        panel.load_from_scope(_make_scope(win_scale=5e-5, win_enable=True))
        assert panel._win_scale.value() == pytest.approx(5e-5)

    def test_load_fills_win_position(self, panel):
        """После load _win_position содержит правильное значение."""
        panel.load_from_scope(_make_scope(win_position=0.05, win_enable=True))
        assert panel._win_position.value() == pytest.approx(0.05)


# ---------------------------------------------------------------------------
# Тест 2: смена режима → settingChanged("timebase.mode", literal)
# ---------------------------------------------------------------------------

class TestModeSignal:
    def test_change_to_xy_emits_canonical(self, panel):
        """Клик по сегменту XY → settingChanged('timebase.mode', 'XY')."""
        received = []
        panel.settingChanged.connect(lambda p, v: received.append((p, v)))
        panel._mode._button_map["XY"].click()
        assert len(received) == 1, f"Ожидался 1 сигнал, получено: {received}"
        assert received[0] == ("timebase.mode", "XY")

    def test_change_to_roll_emits_canonical(self, panel):
        """Клик по сегменту ROLL → settingChanged('timebase.mode', 'ROLL')."""
        received = []
        panel.settingChanged.connect(lambda p, v: received.append((p, v)))
        panel._mode._button_map["ROLL"].click()
        assert received == [("timebase.mode", "ROLL")]

    def test_mode_value_is_string(self, panel):
        """Значение в сигнале — строка, не None."""
        received = []
        panel.settingChanged.connect(lambda p, v: received.append((p, v)))
        panel._mode._button_map["XY"].click()
        assert received and isinstance(received[0][1], str)


# ---------------------------------------------------------------------------
# Тест 3: ввод масштаба + editingFinished → settingChanged("timebase.scale", float)
# ---------------------------------------------------------------------------

class TestScaleSignal:
    def test_editing_finished_emits_float(self, panel):
        """editingFinished на _scale → settingChanged('timebase.scale', float)."""
        panel._scale.blockSignals(True)
        panel._scale.setValue(5e-3)
        panel._scale.blockSignals(False)

        received = []
        panel.settingChanged.connect(lambda p, v: received.append((p, v)))
        panel._scale.editingFinished.emit()

        assert len(received) == 1, f"Ожидался 1 сигнал, получено: {received}"
        path, val = received[0]
        assert path == "timebase.scale"
        assert isinstance(val, float), f"Ожидался float, получен {type(val)}"
        assert val == pytest.approx(5e-3)

    def test_editing_finished_small_value(self, panel):
        """editingFinished с 2e-9 → ('timebase.scale', 2e-9)."""
        panel._scale.blockSignals(True)
        panel._scale.setValue(2e-9)
        panel._scale.blockSignals(False)

        received = []
        panel.settingChanged.connect(lambda p, v: received.append((p, v)))
        panel._scale.editingFinished.emit()

        assert received and received[0][0] == "timebase.scale"
        assert received[0][1] == pytest.approx(2e-9)


# ---------------------------------------------------------------------------
# Тест 4: позиция + editingFinished → settingChanged("timebase.position", float)
# ---------------------------------------------------------------------------

class TestPositionSignal:
    def test_editing_finished_emits_float(self, panel):
        """editingFinished на _position → settingChanged('timebase.position', float)."""
        panel._position.blockSignals(True)
        panel._position.setValue(-0.5)
        panel._position.blockSignals(False)

        received = []
        panel.settingChanged.connect(lambda p, v: received.append((p, v)))
        panel._position.editingFinished.emit()

        assert len(received) == 1
        path, val = received[0]
        assert path == "timebase.position"
        assert isinstance(val, float)
        assert val == pytest.approx(-0.5)


# ---------------------------------------------------------------------------
# Тест 5: чекбокс окна → settingChanged("timebase.window.enable", bool)
# ---------------------------------------------------------------------------

class TestWindowEnableSignal:
    def test_check_emits_true(self, panel):
        """Включение чекбокса → settingChanged('timebase.window.enable', True)."""
        panel._win_enable.blockSignals(True)
        panel._win_enable.setChecked(False)
        panel._win_enable.blockSignals(False)

        received = []
        panel.settingChanged.connect(lambda p, v: received.append((p, v)))
        panel._win_enable.setChecked(True)
        assert received == [("timebase.window.enable", True)]

    def test_uncheck_emits_false(self, panel):
        """Выключение чекбокса → settingChanged('timebase.window.enable', False)."""
        panel._win_enable.blockSignals(True)
        panel._win_enable.setChecked(True)
        panel._win_enable.blockSignals(False)

        received = []
        panel.settingChanged.connect(lambda p, v: received.append((p, v)))
        panel._win_enable.setChecked(False)
        assert received == [("timebase.window.enable", False)]


# ---------------------------------------------------------------------------
# Тест 6: масштаб окна + editingFinished → settingChanged("timebase.window.scale", float)
# ---------------------------------------------------------------------------

class TestWindowScaleSignal:
    def test_editing_finished_emits_float(self, panel):
        """editingFinished на _win_scale → settingChanged('timebase.window.scale', float)."""
        panel._win_scale.blockSignals(True)
        panel._win_scale.setValue(1e-4)
        panel._win_scale.blockSignals(False)

        received = []
        panel.settingChanged.connect(lambda p, v: received.append((p, v)))
        panel._win_scale.editingFinished.emit()

        assert len(received) == 1
        path, val = received[0]
        assert path == "timebase.window.scale"
        assert isinstance(val, float)
        assert val == pytest.approx(1e-4)


# ---------------------------------------------------------------------------
# Тест 7: позиция окна + editingFinished → settingChanged("timebase.window.position", float)
# ---------------------------------------------------------------------------

class TestWindowPositionSignal:
    def test_editing_finished_emits_float(self, panel):
        """editingFinished на _win_position → settingChanged('timebase.window.position', float)."""
        panel._win_position.blockSignals(True)
        panel._win_position.setValue(0.05)
        panel._win_position.blockSignals(False)

        received = []
        panel.settingChanged.connect(lambda p, v: received.append((p, v)))
        panel._win_position.editingFinished.emit()

        assert len(received) == 1
        path, val = received[0]
        assert path == "timebase.window.position"
        assert isinstance(val, float)
        assert val == pytest.approx(0.05)


# ---------------------------------------------------------------------------
# Тест 8: структура панели
# ---------------------------------------------------------------------------

class TestPanelStructure:
    def test_has_setting_changed_signal(self, panel):
        assert hasattr(panel, "settingChanged")

    def test_has_load_from_scope(self, panel):
        assert callable(getattr(panel, "load_from_scope", None))

    def test_mode_combo_has_all_modes(self, panel):
        assert set(panel._mode._button_map.keys()) == {"MAIN", "XY", "ROLL"}

    def test_has_win_enable_checkbox(self, panel):
        assert hasattr(panel, "_win_enable")

    def test_has_win_scale_spinbox(self, panel):
        assert hasattr(panel, "_win_scale")

    def test_has_win_position_spinbox(self, panel):
        assert hasattr(panel, "_win_position")

    def test_scale_range_min(self, panel):
        """Минимум масштаба 2e-9 с/дел."""
        assert panel._scale.minimum() == pytest.approx(2e-9)

    def test_scale_range_max(self, panel):
        """Максимум масштаба 50 с/дел."""
        assert panel._scale.maximum() == pytest.approx(50.0)
