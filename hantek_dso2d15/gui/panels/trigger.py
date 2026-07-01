"""Панель Trigger — настройки триггера DSO2D15.

Контролы: тип триггера, источник (edge), развёртка, фронт (edge), уровень (edge), holdoff.
Сигнал ``settingChanged(path, value)`` — единый для всех панелей; путь вида
``"trigger.<attr>"`` или ``"trigger.edge.<attr>"``.
"""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QGridLayout, QLabel, QComboBox,
)

from hantek_dso2d15.gui.widgets import DecimalSpinBox
from hantek_dso2d15.gui.segmented import SegmentedControl
from hantek_dso2d15.gui.theme import WARN_AMBER
from hantek_dso2d15.scpi.trigger import Trigger, TriggerEdge

# Только каналы, доступные в типовой конфигурации DSO2D15 (2-канальный прибор + EXT)
_EDGE_SOURCES = ("CHANnel1", "CHANnel2", "EXT/10")


class TriggerPanel(QWidget):
    """Панель Trigger: тип, источник, развёртка, фронт, уровень, holdoff.

    Сигнал ``settingChanged(path, value)`` — единый для всех панелей.
    Пути: ``"trigger.mode"``, ``"trigger.sweep"``, ``"trigger.holdoff"``,
    ``"trigger.edge.source"``, ``"trigger.edge.slope"``, ``"trigger.edge.level"``.
    """

    settingChanged = Signal(str, object)

    def __init__(self, parent=None):
        super().__init__(parent)

        lay = QGridLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setHorizontalSpacing(8)
        lay.setVerticalSpacing(6)

        # ---- Тип триггера ------------------------------------------------
        lay.addWidget(QLabel("Тип"), 0, 0)
        self._mode = QComboBox()
        self._mode.addItems(list(Trigger.MODES))
        self._mode.currentTextChanged.connect(
            lambda s: self.settingChanged.emit("trigger.mode", s)
        )
        lay.addWidget(self._mode, 0, 1)

        # ---- Источник (edge) ----------------------------------------------
        lay.addWidget(QLabel("Источник"), 1, 0)
        self._source = QComboBox()
        self._source.addItems(list(_EDGE_SOURCES))
        self._source.currentTextChanged.connect(
            lambda s: self.settingChanged.emit("trigger.edge.source", s)
        )
        lay.addWidget(self._source, 1, 1)

        # ---- Развёртка (segmented) ----------------------------------------
        lay.addWidget(QLabel("Развёртка"), 2, 0)
        self._sweep = SegmentedControl(
            [("Auto", "AUTO"), ("Normal", "NORMal"), ("Single", "SINGle")], accent=WARN_AMBER)
        self._sweep.valueChanged.connect(
            lambda v: self.settingChanged.emit("trigger.sweep", v)
        )
        lay.addWidget(self._sweep, 2, 1)

        # ---- Фронт (segmented) --------------------------------------------
        lay.addWidget(QLabel("Фронт"), 3, 0)
        self._slope = SegmentedControl(
            [("Rising", "RISIng"), ("Falling", "FALLing"), ("Either", "EITHer")])
        self._slope.valueChanged.connect(
            lambda v: self.settingChanged.emit("trigger.edge.slope", v)
        )
        lay.addWidget(self._slope, 3, 1)

        # ---- Уровень (edge) -----------------------------------------------
        lay.addWidget(QLabel("Уровень, В"), 4, 0)
        self._level = DecimalSpinBox()
        self._level.setRange(-50.0, 50.0)
        self._level.setDecimals(3)
        self._level.setMinimumHeight(24)
        self._level.editingFinished.connect(
            lambda: self.settingChanged.emit("trigger.edge.level", float(self._level.value()))
        )
        lay.addWidget(self._level, 4, 1)

        # ---- Holdoff -------------------------------------------------------
        lay.addWidget(QLabel("Holdoff, s"), 5, 0)
        self._holdoff = DecimalSpinBox()
        self._holdoff.setRange(0.0, 10.0)
        self._holdoff.setDecimals(9)
        self._holdoff.setMinimumHeight(24)
        self._holdoff.editingFinished.connect(
            lambda: self.settingChanged.emit("trigger.holdoff", float(self._holdoff.value()))
        )
        lay.addWidget(self._holdoff, 5, 1)

        self._all_widgets = [
            self._mode, self._source, self._sweep,
            self._slope, self._level, self._holdoff,
        ]

    def update_level(self, volts: float) -> None:
        """Синхронизировать спинбокс уровня (напр. после drag на графике), без эмиссии."""
        blocked = self._level.blockSignals(True)
        try:
            self._level.setValue(float(volts))
        finally:
            self._level.blockSignals(blocked)

    def load_from_scope(self, scope) -> None:
        """Загрузить текущие значения триггера с прибора (сигналы заблокированы)."""
        for w in self._all_widgets:
            w.blockSignals(True)
        try:
            self._mode.setCurrentText(str(scope.trigger.mode))
            self._source.setCurrentText(str(scope.trigger.edge.source))
            self._sweep.set_value(str(scope.trigger.sweep))
            self._slope.set_value(str(scope.trigger.edge.slope))
            self._level.setValue(float(scope.trigger.edge.level))
            self._holdoff.setValue(float(scope.trigger.holdoff))
        finally:
            for w in self._all_widgets:
                w.blockSignals(False)
