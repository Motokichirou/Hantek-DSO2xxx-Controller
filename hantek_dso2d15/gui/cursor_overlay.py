"""Оверлей клиентских курсоров на pg.PlotItem.

Два вертикальных курсора (AX, BX) измеряют время; два горизонтальных
(AY, BY) — напряжение. В режиме TRACk вертикальные курсоры «следят» за
трассой источника (интерполяция по кадру).

Единицы: X — деления [0 … HDIV], Y — деления [-VDIV/2 … VDIV/2].
Конвертация в секунды/вольты — строго по формулам мануала:

    total_t  = decoded.time[-1] - decoded.time[0]   (>1 точки; иначе 0)
    t(x_div) = decoded.time[0] + (x_div / HDIV) * total_t
    dt        = abs(bx_div - ax_div) / HDIV * total_t
    freq      = 1/dt  если dt > 0 иначе 0

    volts(y_div, n) = y_div * vdiv - off      (vdiv=scales[n], off=offsets[n])
    ΔV              = abs(ay_div - by_div) * vdiv   (офсет сокращается)

В режиме TRACk:
    ay_v = np.interp(ax_div, linspace(0, HDIV, N), channels[n])
    by_v = np.interp(bx_div, linspace(0, HDIV, N), channels[n])
"""
from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import QObject, Signal

# Константы сетки (должны совпадать с plot_widget.py)
HDIV: int = 14   # горизонтальных делений
VDIV: int = 8    # вертикальных делений

# Видимость (AX, BX, AY, BY) для каждого режима
_MODES_VIS: dict[str, tuple[bool, bool, bool, bool]] = {
    "OFF":   (False, False, False, False),
    "X":     (True,  True,  False, False),
    "Y":     (False, False, True,  True),
    "XY":    (True,  True,  True,  True),
    "TRACk": (True,  True,  False, False),
}

_ALL_MODES = list(_MODES_VIS.keys())


def _pen(color: str) -> object:
    from PySide6.QtCore import Qt
    return pg.mkPen(color=color, width=1, style=Qt.PenStyle.DashLine)


class CursorOverlay(QObject):
    """Перетаскиваемые курсоры поверх PlotItem.

    Использование::

        overlay = CursorOverlay(scope_plot.plot_item)
        overlay.valuesChanged.connect(cursor_panel.update_readout)
        # при каждом новом кадре:
        overlay.update_frame(decoded)
        # при смене режима панелью:
        overlay.set_mode("X")
    """

    #: Эмитируется при каждом изменении позиции курсора или кадра.
    #: Аргумент — dict с ключами mode/ax_t/bx_t/dt/freq/ay_v/by_v/dv.
    valuesChanged = Signal(object)

    def __init__(self, plot_item: pg.PlotItem) -> None:
        super().__init__()
        self._pi = plot_item
        self._mode: str = "OFF"
        self._source: int = 1
        self._decoded = None

        pen_x = _pen("#00E5FF")   # вертикальные (время): голубой
        pen_y = _pen("#FF8C00")   # горизонтальные (напряжение): оранжевый

        # Вертикальные курсоры (постоянный X)
        self._ax = pg.InfiniteLine(
            pos=HDIV / 3, angle=90, movable=True, pen=pen_x, label="A",
        )
        self._bx = pg.InfiniteLine(
            pos=2 * HDIV / 3, angle=90, movable=True, pen=pen_x, label="B",
        )
        # Горизонтальные курсоры (постоянный Y)
        self._ay = pg.InfiniteLine(
            pos=1.0, angle=0, movable=True, pen=pen_y, label="A",
        )
        self._by = pg.InfiniteLine(
            pos=-1.0, angle=0, movable=True, pen=pen_y, label="B",
        )

        for line in (self._ax, self._bx, self._ay, self._by):
            plot_item.addItem(line)
            line.setVisible(False)
            line.sigPositionChanged.connect(lambda _: self._emit())

    # ------------------------------------------------------------------
    # Публичный API
    # ------------------------------------------------------------------

    def set_mode(self, mode: str) -> None:
        """Установить режим; показать/скрыть нужные линии."""
        self._mode = mode
        vis = _MODES_VIS.get(mode, (False, False, False, False))
        self._ax.setVisible(vis[0])
        self._bx.setVisible(vis[1])
        self._ay.setVisible(vis[2])
        self._by.setVisible(vis[3])
        self._emit()

    def set_source(self, n: int) -> None:
        """Установить канал-источник для расчёта напряжения и трекинга."""
        self._source = n
        self._emit()

    def update_frame(self, decoded) -> None:
        """Сохранить декодированный кадр и пересчитать читаут."""
        self._decoded = decoded
        self._emit()

    # ------------------------------------------------------------------
    # Внутреннее
    # ------------------------------------------------------------------

    def _emit(self) -> None:
        self.valuesChanged.emit(self._values())

    def _values(self) -> dict:
        """Вычислить читаут по позициям линий и сохранённому кадру.

        Правило видимости:
          - dt/freq   : только если AX и BX видимы; иначе None.
          - ay_v/by_v : из AY/BY (режимы Y/XY) или из трассы (TRACk); иначе None.
          - dv        : abs(ay_v - by_v) когда ay_v/by_v не None; иначе None.
        """
        mode = self._mode
        dec = self._decoded
        n = self._source

        ax_div = float(self._ax.value())
        bx_div = float(self._bx.value())
        ay_div = float(self._ay.value())
        by_div = float(self._by.value())

        ax_vis = self._ax.isVisible()
        bx_vis = self._bx.isVisible()
        ay_vis = self._ay.isVisible()
        by_vis = self._by.isVisible()

        # ---- Временны́е курсоры ----
        ax_t: float | None = None
        bx_t: float | None = None
        dt:   float | None = None
        freq: float | None = None

        if ax_vis and bx_vis and dec is not None and len(dec.time) > 0:
            t0 = float(dec.time[0])
            total_t = float(dec.time[-1] - dec.time[0]) if len(dec.time) > 1 else 0.0
            ax_t = t0 + (ax_div / HDIV) * total_t
            bx_t = t0 + (bx_div / HDIV) * total_t
            dt   = abs(bx_div - ax_div) / HDIV * total_t
            freq = 1.0 / dt if dt > 0.0 else 0.0

        # ---- Напряжение ----
        ay_v: float | None = None
        by_v: float | None = None
        dv:   float | None = None

        if mode == "TRACk" and ax_vis and bx_vis and dec is not None:
            chan = dec.channels.get(n) if dec is not None else None
            if chan is not None:
                arr = np.asarray(chan)
                if len(arr) > 1:
                    xs = np.linspace(0.0, float(HDIV), len(arr))
                    ay_v = float(np.interp(ax_div, xs, arr))
                    by_v = float(np.interp(bx_div, xs, arr))
                    dv   = float(abs(ay_v - by_v))
        elif ay_vis and by_vis and dec is not None:
            if n in dec.scales:
                vdiv = float(dec.scales[n])
                off  = float(dec.offsets.get(n, 0.0))
                ay_v = ay_div * vdiv - off
                by_v = by_div * vdiv - off
                dv   = abs(ay_div - by_div) * vdiv

        return {
            "mode":  mode,
            "ax_t":  ax_t,
            "bx_t":  bx_t,
            "dt":    dt,
            "freq":  freq,
            "ay_v":  ay_v,
            "by_v":  by_v,
            "dv":    dv,
        }
