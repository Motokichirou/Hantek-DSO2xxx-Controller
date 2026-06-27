"""Панель Acquire — настройки режима сбора данных.

Контролы:
  - Режим сбора (NORMal / AVERage / PEAK / HRESolution)
  - Усреднения (4 / 8 / 16 / 32 / 64 / 128)
  - Глубина памяти (4K / 40K / 400K / 4M / 8M)
  - Частота дискретизации (только отображение, QLabel)

Изменения уходят сигналом ``settingChanged(path, value)``; путь — точечный
по графу драйвера, значение — каноничный SCPI-литерал (строка) или int.
"""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QGridLayout, QLabel, QComboBox,
)

# Допустимые типы сбора (каноничные SCPI-литералы)
_TYPES = ["NORMal", "AVERage", "PEAK", "HRESolution"]

# Допустимые числа усреднений
_COUNTS = [4, 8, 16, 32, 64, 128]

# Глубина памяти: (int_value, human_label)
_POINTS = [
    (4_000,     "4K"),
    (40_000,    "40K"),
    (400_000,   "400K"),
    (4_000_000, "4M"),
    (8_000_000, "8M"),
]


def _fmt_srate(hz: float) -> str:
    """Форматировать частоту дискретизации в удобочитаемом виде."""
    if hz >= 1e9:
        return f"{hz / 1e9:g} GSa/s"
    if hz >= 1e6:
        return f"{hz / 1e6:g} MSa/s"
    if hz >= 1e3:
        return f"{hz / 1e3:g} kSa/s"
    return f"{hz:g} Sa/s"


class AcquirePanel(QWidget):
    """Панель настроек подсистемы Acquire.

    Сигнал ``settingChanged(path, value)`` — единый для всех панелей.
    Пути:
        "acquire.type"   → str (SCPI-канонический литерал)
        "acquire.count"  → int
        "acquire.points" → int
    Частота дискретизации: только отображение, сигнал не эмитируется.
    """

    settingChanged = Signal(str, object)

    def __init__(self, parent=None):
        super().__init__(parent)

        lay = QGridLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setHorizontalSpacing(8)
        lay.setVerticalSpacing(6)

        # --- Режим сбора ---
        lay.addWidget(QLabel("Режим"), 0, 0)
        self._type = QComboBox()
        for t in _TYPES:
            self._type.addItem(t, t)
        self._type.currentIndexChanged.connect(self._on_type_changed)
        lay.addWidget(self._type, 0, 1)

        # --- Усреднения ---
        lay.addWidget(QLabel("Усреднения"), 1, 0)
        self._count = QComboBox()
        for c in _COUNTS:
            self._count.addItem(str(c), c)
        self._count.currentIndexChanged.connect(self._on_count_changed)
        lay.addWidget(self._count, 1, 1)

        # --- Глубина памяти ---
        lay.addWidget(QLabel("Глубина"), 2, 0)
        self._points = QComboBox()
        for pts, lbl in _POINTS:
            self._points.addItem(lbl, pts)
        self._points.currentIndexChanged.connect(self._on_points_changed)
        lay.addWidget(self._points, 2, 1)

        # --- Частота дискретизации (только чтение) ---
        lay.addWidget(QLabel("Sa/s"), 3, 0)
        self._srate_label = QLabel("—")
        lay.addWidget(self._srate_label, 3, 1)

        self._combos = [self._type, self._count, self._points]

    # ------------------------------------------------------------------
    # Обработчики сигналов комбо-боксов
    # ------------------------------------------------------------------

    def _on_type_changed(self, _index: int) -> None:
        data = self._type.currentData()
        if data is not None:
            self.settingChanged.emit("acquire.type", data)

    def _on_count_changed(self, _index: int) -> None:
        data = self._count.currentData()
        if data is not None:
            self.settingChanged.emit("acquire.count", int(data))

    def _on_points_changed(self, _index: int) -> None:
        data = self._points.currentData()
        if data is not None:
            self.settingChanged.emit("acquire.points", int(data))

    # ------------------------------------------------------------------
    # Публичный API
    # ------------------------------------------------------------------

    def load_from_scope(self, scope) -> None:
        """Прочитать текущие настройки с прибора и выставить контролы.

        Во время загрузки сигналы заблокированы — команды приборам не
        отправляются.
        """
        acq = scope.acquire

        for combo in self._combos:
            combo.blockSignals(True)
        try:
            # type
            idx = self._type.findData(str(acq.type))
            if idx >= 0:
                self._type.setCurrentIndex(idx)

            # count
            idx = self._count.findData(int(acq.count))
            if idx >= 0:
                self._count.setCurrentIndex(idx)

            # points
            idx = self._points.findData(int(acq.points))
            if idx >= 0:
                self._points.setCurrentIndex(idx)
        finally:
            for combo in self._combos:
                combo.blockSignals(False)

        # srate — просто метка, сигналов нет
        try:
            self._srate_label.setText(_fmt_srate(float(acq.srate)))
        except Exception:
            self._srate_label.setText("—")
