"""Панель Display — клиентское управление рендером графика.

Контролы не отправляют SCPI-команды на прибор; они управляют только
отображением на стороне хоста. Изменения уходят сигналом ``displayChanged(key,
value)``.

Ключи и значения:
  "type"    → str  "VECTors" | "DOTS"   (литералы по frozen SCPI reference)
  "grid"    → str  "DOTTed"  | "REAL"
  "wbright" → int  0..100  (яркость осциллограммы)
  "gbright" → int  0..100  (яркость сетки)
"""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QGridLayout, QLabel, QComboBox, QSpinBox,
)

# Типы рендера: (data_literal, display_label)
_TYPES = [
    ("VECTors", "Линии"),
    ("DOTS",    "Точки"),
]

# Типы сетки: (data_literal, display_label)
_GRIDS = [
    ("REAL",   "Сплошная"),
    ("DOTTed", "Точечная"),
]

_WBRIGHT_DEFAULT = 80
_GBRIGHT_DEFAULT = 40


class DisplayPanel(QWidget):
    """Панель настроек отображения (клиентская, без SCPI).

    Сигнал ``displayChanged(key, value)`` — единый для всех контролов.
    Ключи:
        "type"    → str  "VECTors" | "DOTS"
        "grid"    → str  "DOTTed"  | "REAL"
        "wbright" → int  0..100
        "gbright" → int  0..100

    При инициализации выставляет дефолты **без** эмиссии сигнала.
    """

    displayChanged = Signal(str, object)  # (key, value)

    def __init__(self, parent=None):
        super().__init__(parent)

        lay = QGridLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setHorizontalSpacing(8)
        lay.setVerticalSpacing(6)

        # --- Тип рендера ---
        lay.addWidget(QLabel("Тип"), 0, 0)
        self._type = QComboBox()
        for literal, label in _TYPES:
            self._type.addItem(label, literal)
        lay.addWidget(self._type, 0, 1)

        # --- Тип сетки ---
        lay.addWidget(QLabel("Сетка"), 1, 0)
        self._grid = QComboBox()
        for literal, label in _GRIDS:
            self._grid.addItem(label, literal)
        lay.addWidget(self._grid, 1, 1)

        # --- Яркость осциллограммы ---
        lay.addWidget(QLabel("Яркость сигнала"), 2, 0)
        self._wbright = QSpinBox()
        self._wbright.setRange(0, 100)
        lay.addWidget(self._wbright, 2, 1)

        # --- Яркость сетки ---
        lay.addWidget(QLabel("Яркость сетки"), 3, 0)
        self._gbright = QSpinBox()
        self._gbright.setRange(0, 100)
        lay.addWidget(self._gbright, 3, 1)

        # Выставить дефолты БЕЗ эмиссии
        self._set_defaults_silent()

        # Подключить обработчики ПОСЛЕ выставления дефолтов
        self._type.currentIndexChanged.connect(self._on_type_changed)
        self._grid.currentIndexChanged.connect(self._on_grid_changed)
        self._wbright.valueChanged.connect(self._on_wbright_changed)
        self._gbright.valueChanged.connect(self._on_gbright_changed)

    # ------------------------------------------------------------------
    # Установка дефолтов (без эмиссии)
    # ------------------------------------------------------------------

    def _set_defaults_silent(self) -> None:
        """Выставить начальные значения без эмиссии displayChanged."""
        # type = VECTors
        idx = self._type.findData("VECTors")
        if idx >= 0:
            self._type.setCurrentIndex(idx)

        # grid = REAL
        idx = self._grid.findData("REAL")
        if idx >= 0:
            self._grid.setCurrentIndex(idx)

        # яркости
        self._wbright.setValue(_WBRIGHT_DEFAULT)
        self._gbright.setValue(_GBRIGHT_DEFAULT)

    # ------------------------------------------------------------------
    # Обработчики сигналов контролов
    # ------------------------------------------------------------------

    def _on_type_changed(self, _index: int) -> None:
        data = self._type.currentData()
        if data is not None:
            self.displayChanged.emit("type", data)

    def _on_grid_changed(self, _index: int) -> None:
        data = self._grid.currentData()
        if data is not None:
            self.displayChanged.emit("grid", data)

    def _on_wbright_changed(self, value: int) -> None:
        self.displayChanged.emit("wbright", int(value))

    def _on_gbright_changed(self, value: int) -> None:
        self.displayChanged.emit("gbright", int(value))

    # ------------------------------------------------------------------
    # Публичный API
    # ------------------------------------------------------------------

    def defaults(self) -> dict:
        """Вернуть снапшот текущих значений всех контролов.

        Используется оркестратором для начальной синхронизации графика.
        Вызов не эмитирует сигналов.

        Returns:
            dict с ключами "type", "grid", "wbright", "gbright".
        """
        return {
            "type":    self._type.currentData(),
            "grid":    self._grid.currentData(),
            "wbright": int(self._wbright.value()),
            "gbright": int(self._gbright.value()),
        }
