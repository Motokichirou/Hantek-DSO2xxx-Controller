"""ScopePlot — центральный графикуль на pyqtgraph (сетка 14×8 делений).

Рисует декодированные кадры в ЕДИНИЦАХ ДЕЛЕНИЙ: y = вольты / (V/дел), так что
1 деление по вертикали = текущий масштаб канала (как на приборе). Горизонталь —
запись растянута на 14 делений. Цветокод: CH1 жёлтый, CH2 зелёный.

Клиентские надстройки (всё считается/рисуется у нас, не в приборе):
  - Display: режим рисовки (линии/точки), стиль и яркость сетки, яркость трасс.
  - Math: третья трасса (ADD/SUB/MUL/DIV — в делениях по math-масштабу; FFT —
    спектр, авто-вписанный в графикуль; см. ``set_math_config``).
  - Cursors: оверлей перетаскиваемых линий (``self.cursors``), читаут — снаружи.
"""
from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel

from hantek_dso2d15.gui.cursor_overlay import CursorOverlay
from hantek_dso2d15.waveform.math_compute import compute_math

# Цветокод каналов (CH1 жёлтый, CH2 зелёный — как на приборе)
CH_COLORS = {1: "#F2C300", 2: "#3FE03F", 3: "#C77DFF", 4: "#FF7DD8"}
MATH_COLOR = "#C77DFF"
GRATICULE_BG = "#08090B"
HDIV = 14   # горизонтальных делений
VDIV = 8    # вертикальных делений


def _vdiv_label(v: float) -> str:
    """Компактная подпись V/дел: '500mV' / '1V' / '100V'."""
    return f"{v * 1000:g}mV" if v < 1.0 else f"{v:g}V"


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


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

        # --- параметры рендера (Display); дефолты совпадают с DisplayPanel ---
        self._draw_mode = "VECTors"   # VECTors | DOTS
        self._wbright = 80            # яркость трасс 0..100
        self._grid_style = "REAL"     # REAL | DOTTed
        self._gbright = 40            # яркость сетки 0..100 (40 = базовый вид)

        self._grat: list[dict] = []   # элементы сетки: {"line", "base_alpha"}
        self._draw_graticule()

        self._curves: dict[int, pg.PlotDataItem] = {}
        for n in CH_COLORS:
            self._curves[n] = self._pi.plot()
        # math-трасса (поверх каналов)
        self._math_curve = self._pi.plot()
        self._math_config: dict | None = None
        self._apply_curve_style()

        # оверлей курсоров (привязка панели — в main_window)
        self.cursors = CursorOverlay(self._pi)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._pw)

        # ридаут-бейджи (V/дел по каналам, срейт, триггер) поверх графикуля
        self._readout = QLabel(self._pw)
        self._readout.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._readout.setStyleSheet(
            "background: rgba(8,9,11,0.78); border-radius: 3px; padding: 3px 6px;"
            "font-family: 'JetBrains Mono','Consolas',monospace; font-size: 11px;"
        )
        self._readout.move(10, 8)
        self._readout.setText("")

    # ------------------------------------------------------------------
    # Сетка
    # ------------------------------------------------------------------

    def _draw_graticule(self) -> None:
        # базовые альфы по ролям линий; яркость/стиль применяются позже
        specs = []
        for i in range(HDIV + 1):
            base = 90 if i in (0, HDIV) else (70 if i == HDIV // 2 else 28)
            specs.append(("x", i, base))
        for j in range(VDIV + 1):
            y = j - VDIV // 2
            base = 90 if j in (0, VDIV) else (70 if y == 0 else 28)
            specs.append(("y", y, base))
        for axis, pos, base in specs:
            line = self._pi.addLine(**({"x": pos} if axis == "x" else {"y": pos}),
                                    pen=pg.mkPen(color=(255, 255, 255, base), width=1))
            self._grat.append({"line": line, "base_alpha": base})
        self._apply_grid_style()

    def _apply_grid_style(self) -> None:
        style = Qt.PenStyle.DotLine if self._grid_style == "DOTTed" else Qt.PenStyle.SolidLine
        mult = self._gbright / 40.0  # 40 = базовый вид (множитель 1.0)
        for item in self._grat:
            alpha = max(0, min(255, int(item["base_alpha"] * mult)))
            item["line"].setPen(pg.mkPen(color=(255, 255, 255, alpha), width=1, style=style))

    # ------------------------------------------------------------------
    # Трассы (стиль рисовки + яркость)
    # ------------------------------------------------------------------

    def _apply_curve_style(self) -> None:
        alpha = max(0, min(255, int(255 * self._wbright / 100.0)))
        for n, curve in self._curves.items():
            self._style_one(curve, CH_COLORS[n], alpha)
        self._style_one(self._math_curve, MATH_COLOR, alpha)

    def _style_one(self, curve: pg.PlotDataItem, color: str, alpha: int) -> None:
        r, g, b = _hex_to_rgb(color)
        if self._draw_mode == "DOTS":
            curve.setPen(None)
            curve.setSymbol("o")
            curve.setSymbolSize(2)
            curve.setSymbolPen(None)
            curve.setSymbolBrush(pg.mkBrush(r, g, b, alpha))
        else:  # VECTors
            curve.setSymbol(None)
            curve.setPen(pg.mkPen(color=(r, g, b, alpha), width=1.6))

    # ------------------------------------------------------------------
    # Display API (вызывается из main_window по сигналам DisplayPanel)
    # ------------------------------------------------------------------

    def set_draw_mode(self, mode: str) -> None:
        self._draw_mode = "DOTS" if mode == "DOTS" else "VECTors"
        self._apply_curve_style()

    def set_waveform_brightness(self, value: int) -> None:
        self._wbright = int(value)
        self._apply_curve_style()

    def set_grid_style(self, style: str) -> None:
        self._grid_style = "DOTTed" if style == "DOTTed" else "REAL"
        self._apply_grid_style()

    def set_grid_brightness(self, value: int) -> None:
        self._gbright = int(value)
        self._apply_grid_style()

    def apply_display(self, settings: dict) -> None:
        """Применить снапшот настроек Display (key->value) разом."""
        if "type" in settings:
            self.set_draw_mode(settings["type"])
        if "grid" in settings:
            self.set_grid_style(settings["grid"])
        if "wbright" in settings:
            self.set_waveform_brightness(settings["wbright"])
        if "gbright" in settings:
            self.set_grid_brightness(settings["gbright"])

    # ------------------------------------------------------------------
    # Math API
    # ------------------------------------------------------------------

    def set_math_config(self, config: dict) -> None:
        self._math_config = config

    def _render_math(self, decoded) -> None:
        cfg = self._math_config
        if not cfg or not cfg.get("display"):
            self._math_curve.setData([], [])
            return
        try:
            res = compute_math(decoded, cfg)
        except Exception:  # noqa: BLE001 — мусорный конфиг не должен ронять рендер
            res = None
        if res is None or len(res.y) == 0:
            self._math_curve.setData([], [])
            return
        L = len(res.y)
        x = np.linspace(0.0, HDIV, L)
        if res.kind == "algebraic":
            scale = float(cfg.get("scale", 1.0)) or 1.0
            off = float(cfg.get("offset", 0.0))
            self._math_curve.setData(x, (np.asarray(res.y) + off) / scale)
        else:  # fft — авто-вписать спектр в графикуль (точная ось частот — дизайн-пасс)
            y = np.asarray(res.y, dtype=float)
            ymin = float(y.min())
            span = float(y.max()) - ymin or 1.0
            self._math_curve.setData(x, (y - ymin) / span * VDIV - VDIV / 2.0)

    # ------------------------------------------------------------------
    # Кадр
    # ------------------------------------------------------------------

    def update_frame(self, decoded) -> None:
        """Обновить кривые. V/дел берётся из ``decoded.scales`` (перевод вольт в деления)."""
        n_pts = len(decoded.time)
        if n_pts == 0:
            return
        x = np.linspace(0.0, HDIV, n_pts)
        for n, curve in self._curves.items():
            v = decoded.channels.get(n)
            vdiv = decoded.scales.get(n)
            if v is not None and vdiv:
                # экранная позиция в делениях = (вольты + смещение)/Vдел = count/25,
                # так смещение двигает трассу, как на приборе
                off = decoded.offsets.get(n, 0.0)
                curve.setData(x, (np.asarray(v) + off) / vdiv)
            else:
                curve.setData([], [])

        self._render_math(decoded)
        self.cursors.update_frame(decoded)
        self._update_readout(decoded)

    def _update_readout(self, decoded) -> None:
        """Бейджи: V/дел по каналам (в цвете) + срейт + статус триггера."""
        parts = []
        for n in sorted(decoded.channels):
            color = CH_COLORS.get(n, "#C5C9D1")
            vdiv = decoded.scales.get(n)
            if vdiv:
                parts.append(f"<span style='color:{color}'>CH{n} {_vdiv_label(vdiv)}</span>")
        sr = decoded.srate
        sr_txt = f"{sr/1e9:g} GSa/s" if sr >= 1e9 else (f"{sr/1e6:g} MSa/s" if sr >= 1e6 else f"{sr/1e3:g} kSa/s")
        trig = "Trig'd" if decoded.triggered else "Auto"
        parts.append(f"<span style='color:#9AA0AC'>{sr_txt}</span>")
        parts.append(f"<span style='color:{'#37D67A' if decoded.triggered else '#F5A623'}'>{trig}</span>")
        self._readout.setText("&nbsp;&nbsp;".join(parts))
        self._readout.adjustSize()

    def clear(self) -> None:
        for curve in self._curves.values():
            curve.setData([], [])
        self._math_curve.setData([], [])
