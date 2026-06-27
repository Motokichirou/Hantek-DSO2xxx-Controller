"""Headless-тесты TriggerPanel (QT_QPA_PLATFORM=offscreen).

Запуск: .venv/Scripts/python.exe -m pytest tests/gui/test_trigger_panel.py -q
"""
from __future__ import annotations

import os
import sys

import pytest

# Безголовый Qt — должно быть установлено ДО создания QApplication
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from hantek_dso2d15.gui.panels.trigger import TriggerPanel  # noqa: E402


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
# Фейк-scope: SimpleNamespace-образный объект с нужными атрибутами
# ---------------------------------------------------------------------------

class _FakeEdge:
    def __init__(self, source="CHANnel1", slope="RISIng", level=0.0):
        self.source = source
        self.slope = slope
        self.level = level


class _FakeTrigger:
    def __init__(self, mode="EDGE", sweep="AUTO", holdoff=1e-6,
                 source="CHANnel1", slope="RISIng", level=0.0):
        self.mode = mode
        self.sweep = sweep
        self.holdoff = holdoff
        self.edge = _FakeEdge(source=source, slope=slope, level=level)


class _FakeScope:
    def __init__(self, **kwargs):
        self.trigger = _FakeTrigger(**kwargs)


# ---------------------------------------------------------------------------
# Фикстура панели
# ---------------------------------------------------------------------------

@pytest.fixture
def panel(app):
    return TriggerPanel()


# ---------------------------------------------------------------------------
# Тест 1: load_from_scope заполняет контролы и НЕ эмитирует settingChanged
# ---------------------------------------------------------------------------

class TestLoadFromScope:
    def test_load_does_not_emit(self, panel):
        """load_from_scope не должен эмитировать settingChanged."""
        received = []
        panel.settingChanged.connect(lambda path, val: received.append((path, val)))

        scope = _FakeScope(
            mode="EDGE", sweep="NORMal", holdoff=1e-6,
            source="CHANnel2", slope="FALLing", level=1.5,
        )
        panel.load_from_scope(scope)

        assert received == [], f"load_from_scope эмитировал: {received}"

    def test_load_sets_mode(self, panel):
        """После load текущий режим должен совпадать с загруженным."""
        scope = _FakeScope(mode="PULSe")
        panel.load_from_scope(scope)
        assert panel._mode.currentText() == "PULSe"

    def test_load_sets_sweep(self, panel):
        scope = _FakeScope(sweep="NORMal")
        panel.load_from_scope(scope)
        assert panel._sweep.value() == "NORMal"

    def test_load_sets_source(self, panel):
        scope = _FakeScope(source="CHANnel2")
        panel.load_from_scope(scope)
        assert panel._source.currentText() == "CHANnel2"

    def test_load_sets_slope(self, panel):
        scope = _FakeScope(slope="FALLing")
        panel.load_from_scope(scope)
        assert panel._slope.value() == "FALLing"

    def test_load_sets_level(self, panel):
        scope = _FakeScope(level=1.5)
        panel.load_from_scope(scope)
        assert panel._level.value() == pytest.approx(1.5)

    def test_load_sets_holdoff(self, panel):
        scope = _FakeScope(holdoff=1e-6)
        panel.load_from_scope(scope)
        assert panel._holdoff.value() == pytest.approx(1e-6)


# ---------------------------------------------------------------------------
# Тест 2: смена развёртки → settingChanged("trigger.sweep", "NORMal")
# ---------------------------------------------------------------------------

class TestSweepSignal:
    def test_sweep_normal_emits(self, panel):
        """Клик по сегменту NORMal испускает settingChanged('trigger.sweep','NORMal')."""
        panel._sweep.set_value("AUTO")  # стартуем с AUTO (без эмиссии)
        received = []
        panel.settingChanged.connect(lambda p, v: received.append((p, v)))

        panel._sweep._button_map["NORMal"].click()  # клик пользователя по сегменту

        assert len(received) == 1, f"Ожидался 1 сигнал, получено: {received}"
        assert received[0] == ("trigger.sweep", "NORMal")

    def test_sweep_single_emits(self, panel):
        panel._sweep.set_value("AUTO")
        received = []
        panel.settingChanged.connect(lambda p, v: received.append((p, v)))

        panel._sweep._button_map["SINGle"].click()

        assert received == [("trigger.sweep", "SINGle")]

    def test_sweep_value_is_string(self, panel):
        """Значение в сигнале — строка-литерал, не None."""
        received = []
        panel.settingChanged.connect(lambda p, v: received.append((p, v)))

        panel._sweep.set_value("AUTO")
        panel._sweep._button_map["NORMal"].click()

        assert received and isinstance(received[0][1], str)


# ---------------------------------------------------------------------------
# Тест 3: ввод уровня + editingFinished → settingChanged("trigger.edge.level", float)
# ---------------------------------------------------------------------------

class TestLevelSignal:
    def test_level_editing_finished_emits(self, panel):
        """setValue + editingFinished.emit() → settingChanged('trigger.edge.level', 2.5)."""
        received = []
        panel.settingChanged.connect(lambda p, v: received.append((p, v)))

        panel._level.setValue(2.5)
        panel._level.editingFinished.emit()

        assert len(received) == 1, f"Ожидался 1 сигнал, получено: {received}"
        path, val = received[0]
        assert path == "trigger.edge.level"
        assert val == pytest.approx(2.5)
        assert isinstance(val, float)

    def test_level_negative_emits(self, panel):
        received = []
        panel.settingChanged.connect(lambda p, v: received.append((p, v)))

        panel._level.setValue(-1.2)
        panel._level.editingFinished.emit()

        assert len(received) == 1
        path, val = received[0]
        assert path == "trigger.edge.level"
        assert val == pytest.approx(-1.2)

    def test_level_zero_emits_float(self, panel):
        received = []
        panel.settingChanged.connect(lambda p, v: received.append((p, v)))

        panel._level.setValue(0.0)
        panel._level.editingFinished.emit()

        assert received and isinstance(received[0][1], float)


# ---------------------------------------------------------------------------
# Тест 4: ввод holdoff + editingFinished → settingChanged("trigger.holdoff", float)
# ---------------------------------------------------------------------------

class TestHoldoffSignal:
    def test_holdoff_editing_finished_emits(self, panel):
        """setValue(1e-6) + editingFinished.emit() → settingChanged('trigger.holdoff', 1e-6)."""
        received = []
        panel.settingChanged.connect(lambda p, v: received.append((p, v)))

        panel._holdoff.setValue(1e-6)
        panel._holdoff.editingFinished.emit()

        assert len(received) == 1, f"Ожидался 1 сигнал, получено: {received}"
        path, val = received[0]
        assert path == "trigger.holdoff"
        assert val == pytest.approx(1e-6)
        assert isinstance(val, float)

    def test_holdoff_value_is_float_not_int(self, panel):
        received = []
        panel.settingChanged.connect(lambda p, v: received.append((p, v)))

        panel._holdoff.setValue(0.001)
        panel._holdoff.editingFinished.emit()

        assert received and isinstance(received[0][1], float)


# ---------------------------------------------------------------------------
# Тест 5: канонические литералы — EDGE, RISIng
# ---------------------------------------------------------------------------

class TestCanonicalLiterals:
    def test_mode_edge_literal(self, panel):
        """Выбор EDGE → settingChanged('trigger.mode', 'EDGE') — точный литерал."""
        # Стартуем с PULSe, чтобы переход в EDGE точно дал сигнал
        panel._mode.blockSignals(True)
        panel._mode.setCurrentText("PULSe")
        panel._mode.blockSignals(False)

        received = []
        panel.settingChanged.connect(lambda p, v: received.append((p, v)))

        panel._mode.setCurrentText("EDGE")

        assert len(received) == 1
        assert received[0] == ("trigger.mode", "EDGE")

    def test_slope_rising_literal(self, panel):
        """Клик по RISIng → settingChanged('trigger.edge.slope', 'RISIng') — точный литерал."""
        panel._slope.set_value("FALLing")
        received = []
        panel.settingChanged.connect(lambda p, v: received.append((p, v)))

        panel._slope._button_map["RISIng"].click()

        assert len(received) == 1
        assert received[0] == ("trigger.edge.slope", "RISIng")

    def test_source_channel1_literal(self, panel):
        """Выбор CHANnel1 → settingChanged('trigger.edge.source', 'CHANnel1')."""
        panel._source.blockSignals(True)
        panel._source.setCurrentText("CHANnel2")
        panel._source.blockSignals(False)

        received = []
        panel.settingChanged.connect(lambda p, v: received.append((p, v)))

        panel._source.setCurrentText("CHANnel1")

        assert len(received) == 1
        assert received[0] == ("trigger.edge.source", "CHANnel1")

    def test_all_modes_present(self, panel):
        """Все 14 режимов из Trigger.MODES доступны в комбо."""
        from hantek_dso2d15.scpi.trigger import Trigger
        texts = [panel._mode.itemText(i) for i in range(panel._mode.count())]
        for m in Trigger.MODES:
            assert m in texts, f"Режим {m!r} отсутствует в комбо"

    def test_edge_sources_correct(self, panel):
        """Комбо источников содержит ровно CHANnel1, CHANnel2, EXT/10."""
        texts = {panel._source.itemText(i) for i in range(panel._source.count())}
        assert texts == {"CHANnel1", "CHANnel2", "EXT/10"}

    def test_slopes_present(self, panel):
        """Все три фронта присутствуют в segmented-контроле."""
        assert set(panel._slope._button_map.keys()) == {"RISIng", "FALLing", "EITHer"}


# ---------------------------------------------------------------------------
# Тест 6: структура — наличие сигнала и метода
# ---------------------------------------------------------------------------

class TestPanelStructure:
    def test_has_settingChanged_signal(self, panel):
        assert hasattr(panel, "settingChanged")

    def test_has_load_from_scope(self, panel):
        assert callable(getattr(panel, "load_from_scope", None))
