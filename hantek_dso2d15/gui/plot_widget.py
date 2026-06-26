"""ScopePlot — центральный графикуль на pyqtgraph (сетка 14×8 делений).

Рисует декодированные кадры в ЕДИНИЦАХ ДЕЛЕНИЙ: y = вольты / (V/дел), так что
1 деление по вертикали = текущий масштаб канала (как на приборе). Горизонталь —
запись растянута на 14 делений. Цветокод: CH1 жёлтый, CH2 зелёный.
"""
from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PySide6.QtWidgets import QWidget, QVBoxLayout

# Цветокод каналов (CH1 жёлтый, CH2 зелёный — как на приборе)
CH_COLORS = {1: "#F2C300", 2: "#3FE03F", 3: "#C77DFF", 4: "#FF7DD8"}
GRATICULE_BG = "#08090B"
HDIV = 14   # горизонтальных делений
VDIV = 8    # вертикальных делений


class ScopePlot(QWidget):
    """Графикуль 14×8 делений; кривые каналов в единицах делений."""

    def __init__(self, parent=None):
        super().__init__(parent)
        pg.setConfigOptions(antialias=True)
        self._pw = pg.PlotWidget(background=GRATICULE_BG)
        self._pi = self._pw.getPlotItem()
        self._pi.setMouseEnabled(False, False)
        self._pi.setMenuEnabled(False)
        self._pi.hideButtons()
        self._pi.showAxis("left", False)
        self._pi.showAxis("bottom", False)
        self._pi.setXRange(0, HDIV, padding=0)
        self._pi.setYRange(-VDIV / 2, VDIV / 2, padding=0)

        self._draw_graticule()

        self._curves: dict[int, pg.PlotDataItem] = {}
        for n, color in CH_COLORS.items():
            self._curves[n] = self._pi.plot(pen=pg.mkPen(color=color, width=1.6))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._pw)

    def _draw_graticule(self) -> None:
        minor = pg.mkPen(color=(255, 255, 255, 28), width=1)
        center = pg.mkPen(color=(255, 255, 255, 70), width=1)
        border = pg.mkPen(color=(255, 255, 255, 90), width=1)
        for i in range(HDIV + 1):
            pen = border if i in (0, HDIV) else (center if i == HDIV // 2 else minor)
            self._pi.addLine(x=i, pen=pen)
        for j in range(VDIV + 1):
            y = j - VDIV // 2
            pen = border if j in (0, VDIV) else (center if y == 0 else minor)
            self._pi.addLine(y=y, pen=pen)

    def update_frame(self, decoded, scales: dict) -> None:
        """Обновить кривые. ``scales`` — {канал: V/дел} для перевода вольт в деления."""
        n_pts = len(decoded.time)
        if n_pts == 0:
            return
        x = np.linspace(0.0, HDIV, n_pts)
        for n, curve in self._curves.items():
            v = decoded.channels.get(n)
            vdiv = scales.get(n)
            if v is not None and vdiv:
                curve.setData(x, np.asarray(v) / vdiv)
            else:
                curve.setData([], [])

    def clear(self) -> None:
        for curve in self._curves.values():
            curve.setData([], [])
