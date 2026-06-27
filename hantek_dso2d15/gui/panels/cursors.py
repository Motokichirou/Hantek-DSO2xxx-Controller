"""Панель Cursors — управление режимом курсоров и читаут Δt / ΔV / частота.

Контролы:
  - Режим (QComboBox): OFF / X / Y / XY / TRACk
  - Источник (QComboBox): CH1 / CH2

Читаут (QLabel × 7): Ax, Bx, ΔX, 1/ΔX, Ay, By, ΔY.
None-значения отображаются как «—». Числа форматируются с SI-префиксами
(s/ms/µs/ns · Hz/kHz/MHz/GHz · V/mV/µV).

Сигналы:
    cursorModeChanged(str)   — "OFF"/"X"/"Y"/"XY"/"TRACk"
    cursorSourceChanged(int) — номер канала (1 или 2)
"""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QLabel,
    QWidget,
)

_MODES = ["OFF", "X", "Y", "XY", "TRACk"]
_SOURCES = [(1, "CH1"), (2, "CH2")]


# ---------------------------------------------------------------------------
# Форматирование SI
# ---------------------------------------------------------------------------


def _fmt_time(t: float | None) -> str:
    """Форматировать интервал/момент времени с SI-префиксами."""
    if t is None:
        return "—"
    a = abs(t)
    if a == 0.0:
        return "0 s"
    if a >= 1.0:
        return f"{t:.4g} s"
    if a >= 1e-3:
        return f"{t * 1e3:.4g} ms"
    if a >= 1e-6:
        return f"{t * 1e6:.4g} µs"
    if a >= 1e-9:
        return f"{t * 1e9:.4g} ns"
    return f"{t:.4g} s"


def _fmt_freq(f: float | None) -> str:
    """Форматировать частоту с SI-префиксами."""
    if f is None:
        return "—"
    if f == 0.0:
        return "0 Hz"
    if f >= 1e9:
        return f"{f / 1e9:.4g} GHz"
    if f >= 1e6:
        return f"{f / 1e6:.4g} MHz"
    if f >= 1e3:
        return f"{f / 1e3:.4g} kHz"
    return f"{f:.4g} Hz"


def _fmt_volt(v: float | None) -> str:
    """Форматировать напряжение с SI-префиксами."""
    if v is None:
        return "—"
    a = abs(v)
    if a == 0.0:
        return "0 V"
    if a >= 1.0:
        return f"{v:.4g} V"
    if a >= 1e-3:
        return f"{v * 1e3:.4g} mV"
    if a >= 1e-6:
        return f"{v * 1e6:.4g} µV"
    return f"{v:.4g} V"


# ---------------------------------------------------------------------------
# Панель
# ---------------------------------------------------------------------------


class CursorsPanel(QWidget):
    """Панель управления курсорами и отображения читаута.

    Подключение::

        panel = CursorsPanel()
        panel.cursorModeChanged.connect(overlay.set_mode)
        panel.cursorSourceChanged.connect(overlay.set_source)
        overlay.valuesChanged.connect(panel.update_readout)
    """

    cursorModeChanged   = Signal(str)   # "OFF"/"X"/"Y"/"XY"/"TRACk"
    cursorSourceChanged = Signal(int)   # 1 или 2

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        lay = QGridLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setHorizontalSpacing(8)
        lay.setVerticalSpacing(4)

        # --- Режим ---
        lay.addWidget(QLabel("Режим"), 0, 0)
        self._mode_combo = QComboBox()
        for m in _MODES:
            self._mode_combo.addItem(m, m)
        self._mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        lay.addWidget(self._mode_combo, 0, 1)

        # --- Источник ---
        lay.addWidget(QLabel("Источник"), 1, 0)
        self._source_combo = QComboBox()
        for n, lbl in _SOURCES:
            self._source_combo.addItem(lbl, n)
        self._source_combo.currentIndexChanged.connect(self._on_source_changed)
        lay.addWidget(self._source_combo, 1, 1)

        # --- Читаут ---
        #  (заголовок, атрибут-метки, строка в сетке)
        _readout_rows = [
            ("Ax",   "_ax_label",   2),
            ("Bx",   "_bx_label",   3),
            ("ΔX",   "_dt_label",   4),
            ("1/ΔX", "_freq_label", 5),
            ("Ay",   "_ay_label",   6),
            ("By",   "_by_label",   7),
            ("ΔY",   "_dv_label",   8),
        ]
        for header, attr, row in _readout_rows:
            lay.addWidget(QLabel(header), row, 0)
            lbl = QLabel("—")
            setattr(self, attr, lbl)
            lay.addWidget(lbl, row, 1)

    # ------------------------------------------------------------------
    # Обработчики комбо-боксов
    # ------------------------------------------------------------------

    def _on_mode_changed(self, _index: int) -> None:
        data = self._mode_combo.currentData()
        if data is not None:
            self.cursorModeChanged.emit(str(data))

    def _on_source_changed(self, _index: int) -> None:
        data = self._source_combo.currentData()
        if data is not None:
            self.cursorSourceChanged.emit(int(data))

    # ------------------------------------------------------------------
    # Публичный API
    # ------------------------------------------------------------------

    def update_readout(self, values: dict) -> None:
        """Обновить все метки читаута из dict, эмитируемого CursorOverlay."""
        self._ax_label.setText(_fmt_time(values.get("ax_t")))
        self._bx_label.setText(_fmt_time(values.get("bx_t")))
        self._dt_label.setText(_fmt_time(values.get("dt")))
        self._freq_label.setText(_fmt_freq(values.get("freq")))
        self._ay_label.setText(_fmt_volt(values.get("ay_v")))
        self._by_label.setText(_fmt_volt(values.get("by_v")))
        self._dv_label.setText(_fmt_volt(values.get("dv")))
