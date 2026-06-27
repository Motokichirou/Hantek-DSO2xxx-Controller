"""Панель Horizontal — горизонтальная развёртка (timebase).

Контролы:
  - Масштаб (с/дел): DecimalSpinBox 2e-9 … 50, путь "timebase.scale", float
  - Позиция (с):     DecimalSpinBox, путь "timebase.position", float
  - Режим:           ComboBox (MAIN | XY | ROLL), путь "timebase.mode", str
  - Zoom-окно:
      * Включить:              QCheckBox, путь "timebase.window.enable", bool
      * Масштаб окна (с/дел): DecimalSpinBox 2e-9 … 50, путь "timebase.window.scale", float
      * Позиция окна (с):     DecimalSpinBox, путь "timebase.window.position", float

Сигнал ``settingChanged(path, value)`` — единый для всех панелей; путь по
графу драйвера, значение — float / str / bool.
"""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QGroupBox, QLabel, QComboBox, QCheckBox,
)

from hantek_dso2d15.gui.widgets import DecimalSpinBox

# Каноничные SCPI-литералы режима развёртки (frozen, из docs/scpi-command-reference.md)
MODES: tuple[str, ...] = ("MAIN", "XY", "ROLL")


class HorizontalPanel(QWidget):
    """Панель горизонтальной развёртки (timebase).

    Сигнал ``settingChanged(path, value)`` — единый для всех панелей.
    Пути:
        "timebase.scale"           → float  (с/дел)
        "timebase.position"        → float  (с)
        "timebase.mode"            → str    (SCPI-каноничный: MAIN|XY|ROLL)
        "timebase.window.enable"   → bool
        "timebase.window.scale"    → float  (с/дел)
        "timebase.window.position" → float  (с)
    """

    settingChanged = Signal(str, object)

    def __init__(self, parent=None):
        super().__init__(parent)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setSpacing(8)

        # ------------------------------------------------------------------ #
        # Основные настройки развёртки
        # ------------------------------------------------------------------ #
        main_grid = QGridLayout()
        main_grid.setHorizontalSpacing(8)
        main_grid.setVerticalSpacing(5)

        # Масштаб (с/дел)
        main_grid.addWidget(QLabel("Масштаб, с/дел"), 0, 0)
        self._scale = DecimalSpinBox()
        self._scale.setRange(2e-9, 50.0)
        self._scale.setDecimals(9)
        self._scale.setSingleStep(1e-9)
        self._scale.setValue(1e-3)
        self._scale.setMinimumHeight(24)
        self._scale.editingFinished.connect(self._on_scale_finished)
        main_grid.addWidget(self._scale, 0, 1)

        # Позиция (с)
        main_grid.addWidget(QLabel("Позиция, с"), 1, 0)
        self._position = DecimalSpinBox()
        self._position.setRange(-1000.0, 1000.0)
        self._position.setDecimals(6)
        self._position.setValue(0.0)
        self._position.setMinimumHeight(24)
        self._position.editingFinished.connect(self._on_position_finished)
        main_grid.addWidget(self._position, 1, 1)

        # Режим
        main_grid.addWidget(QLabel("Режим"), 2, 0)
        self._mode = QComboBox()
        for m in MODES:
            self._mode.addItem(m, m)
        self._mode.currentIndexChanged.connect(self._on_mode_changed)
        main_grid.addWidget(self._mode, 2, 1)

        outer.addLayout(main_grid)

        # ------------------------------------------------------------------ #
        # Zoom-окно
        # ------------------------------------------------------------------ #
        win_group = QGroupBox("Zoom-окно")
        win_lay = QGridLayout(win_group)
        win_lay.setHorizontalSpacing(8)
        win_lay.setVerticalSpacing(5)

        self._win_enable = QCheckBox("Включить")
        self._win_enable.toggled.connect(self._on_win_enable_toggled)
        win_lay.addWidget(self._win_enable, 0, 0, 1, 2)

        win_lay.addWidget(QLabel("Масштаб, с/дел"), 1, 0)
        self._win_scale = DecimalSpinBox()
        self._win_scale.setRange(2e-9, 50.0)
        self._win_scale.setDecimals(9)
        self._win_scale.setSingleStep(1e-9)
        self._win_scale.setValue(1e-4)
        self._win_scale.setMinimumHeight(24)
        self._win_scale.editingFinished.connect(self._on_win_scale_finished)
        self._win_scale.setEnabled(False)
        win_lay.addWidget(self._win_scale, 1, 1)

        win_lay.addWidget(QLabel("Позиция, с"), 2, 0)
        self._win_position = DecimalSpinBox()
        self._win_position.setRange(-1000.0, 1000.0)
        self._win_position.setDecimals(6)
        self._win_position.setValue(0.0)
        self._win_position.setMinimumHeight(24)
        self._win_position.editingFinished.connect(self._on_win_position_finished)
        self._win_position.setEnabled(False)
        win_lay.addWidget(self._win_position, 2, 1)

        outer.addWidget(win_group)
        outer.addStretch(1)

        # Все управляемые виджеты — для blockSignals в load_from_scope
        self._all_widgets = [
            self._scale, self._position, self._mode,
            self._win_enable, self._win_scale, self._win_position,
        ]

    # ------------------------------------------------------------------ #
    # Обработчики сигналов
    # ------------------------------------------------------------------ #

    def _on_scale_finished(self) -> None:
        self.settingChanged.emit("timebase.scale", float(self._scale.value()))

    def _on_position_finished(self) -> None:
        self.settingChanged.emit("timebase.position", float(self._position.value()))

    def _on_mode_changed(self, _index: int) -> None:
        data = self._mode.currentData()
        if data is not None:
            self.settingChanged.emit("timebase.mode", str(data))

    def _on_win_enable_toggled(self, enabled: bool) -> None:
        self._win_scale.setEnabled(enabled)
        self._win_position.setEnabled(enabled)
        self.settingChanged.emit("timebase.window.enable", bool(enabled))

    def _on_win_scale_finished(self) -> None:
        self.settingChanged.emit("timebase.window.scale", float(self._win_scale.value()))

    def _on_win_position_finished(self) -> None:
        self.settingChanged.emit("timebase.window.position", float(self._win_position.value()))

    # ------------------------------------------------------------------ #
    # Публичный API
    # ------------------------------------------------------------------ #

    def load_from_scope(self, scope) -> None:
        """Прочитать текущие настройки с прибора и выставить контролы.

        Во время загрузки сигналы всех виджетов заблокированы — команды
        прибору не отправляются.
        """
        tb = scope.timebase
        for w in self._all_widgets:
            w.blockSignals(True)
        try:
            self._scale.setValue(float(tb.scale))
            self._position.setValue(float(tb.position))
            idx = self._mode.findData(str(tb.mode))
            if idx >= 0:
                self._mode.setCurrentIndex(idx)
            win = tb.window
            enabled = bool(win.enable)
            self._win_enable.setChecked(enabled)
            self._win_scale.setValue(float(win.scale))
            self._win_position.setValue(float(win.position))
            # Обновить enabled-состояние напрямую (toggled заблокирован)
            self._win_scale.setEnabled(enabled)
            self._win_position.setEnabled(enabled)
        finally:
            for w in self._all_widgets:
                w.blockSignals(False)
