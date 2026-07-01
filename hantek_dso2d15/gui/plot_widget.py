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

from types import SimpleNamespace

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel

from hantek_dso2d15.gui.cursor_overlay import CursorOverlay
from hantek_dso2d15.gui.decode_overlay import DecodeOverlay
from hantek_dso2d15.gui.theme import (
    CH_COLORS, MATH as MATH_COLOR, GRATICULE_BG, CURSOR,
    OK_GREEN, ERR_RED, WARN_AMBER,
)
from hantek_dso2d15.waveform.math_compute import compute_math
from hantek_dso2d15.waveform.display_window import compute_window

# CH_COLORS / MATH_COLOR / GRATICULE_BG — из дизайн-токенов (см. импорт выше)
HDIV = 14   # горизонтальных делений
VDIV = 8    # вертикальных делений


def _vdiv_label(v: float) -> str:
    """Компактная подпись V/дел: '500mV' / '1V' / '100V'."""
    return f"{v * 1000:g}mV" if v < 1.0 else f"{v:g}V"


def _time_label(s: float) -> str:
    """Компактная подпись времени: 'ns'/'µs'/'ms'/'s'."""
    a = abs(s)
    if a < 1e-6:
        return f"{s * 1e9:.3g}ns"
    if a < 1e-3:
        return f"{s * 1e6:.3g}µs"
    if a < 1.0:
        return f"{s * 1e3:.3g}ms"
    return f"{s:.3g}s"


def _volt_label(v: float) -> str:
    """Подпись напряжения со знаком: '+1.2V' / '-500mV' / '+0mV'."""
    a = abs(v)
    if a < 1.0:
        return f"{v * 1000:+.3g}mV"
    return f"{v:+.3g}V"


def _freq_label(f: float) -> str:
    """Компактная подпись частоты: 'Hz'/'kHz'/'MHz'/'GHz'."""
    a = abs(f)
    if a >= 1e9:
        return f"{f / 1e9:.3g}GHz"
    if a >= 1e6:
        return f"{f / 1e6:.3g}MHz"
    if a >= 1e3:
        return f"{f / 1e3:.3g}kHz"
    return f"{f:.3g}Hz"


# Символы алгебраических операций math для подписи в бейдже
_MATH_OP_SYM = {"ADD": "+", "SUBtract": "−", "MULTiply": "×", "DIVision": "÷"}


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


class ScopePlot(QWidget):
    """Графикуль 14×8 делений; кривые каналов в единицах делений."""

    #: уровень триггера перетащен мышью (вольты) — главное окно шлёт в прибор.
    triggerLevelChanged = Signal(float)

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
        self._ticks = None            # PlotCurveItem субделений (5/дел)
        self._draw_graticule()

        self._curves: dict[int, pg.PlotDataItem] = {}
        for n in CH_COLORS:
            self._curves[n] = self._pi.plot()
        # math-трасса (поверх каналов)
        self._math_curve = self._pi.plot()
        self._math_config: dict | None = None
        self._apply_curve_style()

        # --- маркеры триггера: пунктир уровня (перетаскиваемый) + треугольник + T-маркер ---
        # состояние для конвертации позиция↔вольты при drag
        self._trig_src: int | None = None
        self._trig_vdiv: float | None = None
        self._trig_offset: float = 0.0
        self._trig_dragging: bool = False
        self._trig_settle: int = 0   # счётчик кадров «не трогать линию» после drag
        self._trig_level_line = pg.InfiniteLine(
            angle=0, movable=True,
            pen=pg.mkPen(color=(255, 255, 255, 90), width=1, style=Qt.PenStyle.DashLine),
            hoverPen=pg.mkPen(color=(255, 255, 255, 200), width=2, style=Qt.PenStyle.DashLine))
        self._trig_level_line.sigDragged.connect(self._on_trig_dragged)
        self._trig_level_line.sigPositionChangeFinished.connect(self._on_trig_drag_done)
        self._pi.addItem(self._trig_level_line)
        self._trig_level_line.hide()
        self._trig_level_arrow = pg.ArrowItem(  # на левом краю, остриём внутрь
            angle=180, headLen=12, headWidth=11, tailLen=0, pen=None, brush=pg.mkBrush(CH_COLORS[1]))
        self._pi.addItem(self._trig_level_arrow)
        self._trig_level_arrow.hide()
        self._trig_pos_arrow = pg.ArrowItem(  # сверху, остриём вниз (позиция триггера по X)
            angle=90, headLen=10, headWidth=10, tailLen=0, pen=None, brush=pg.mkBrush(CURSOR))
        self._pi.addItem(self._trig_pos_arrow)
        self._trig_pos_arrow.hide()

        # оверлей курсоров (привязка панели — в main_window)
        self.cursors = CursorOverlay(self._pi)
        self.cursors.valuesChanged.connect(self._on_cursor_values)

        # оверлей декодера шин (символы поверх осциллограммы; декод — из сэмплов окна)
        self._decode_overlay = DecodeOverlay(self._pi)
        self._decode_config: dict | None = None

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
        self._meas_readout = ""   # строка активных измерений (пушит main_window)
        self._line_cursors = ""   # строка курсоров (ΔX/1ΔX/ΔY)
        self._line_math = ""      # строка math (операция + скаляр)

        # бейдж статуса триггера (top-center): Stop/Auto/Trig'd/Ready
        self._trig_badge = QLabel(self._pw)
        self._trig_badge.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._trig_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.set_trigger_badge("Stop", ERR_RED)

    def resizeEvent(self, event):  # noqa: N802
        super().resizeEvent(event)
        self._position_trig_badge()

    def _position_trig_badge(self) -> None:
        self._trig_badge.adjustSize()
        x = (self._pw.width() - self._trig_badge.width()) // 2
        self._trig_badge.move(max(0, x), 8)

    def set_trigger_badge(self, text: str, color: str) -> None:
        """Бейдж статуса триггера сверху по центру (текст + цвет рамки/текста)."""
        r, g, b = _hex_to_rgb(color)
        self._trig_badge.setStyleSheet(
            f"background: rgba(8,9,11,0.78); border: 1px solid rgba({r},{g},{b},0.5);"
            f"border-radius: 3px; padding: 2px 9px; color: {color};"
            "font-family: 'JetBrains Mono','Consolas',monospace; font-size: 12px; font-weight: 700;"
        )
        self._trig_badge.setText(text)
        self._position_trig_badge()

    # ------------------------------------------------------------------
    # Сетка
    # ------------------------------------------------------------------

    def _draw_graticule(self) -> None:
        # Альфы по ролям (×255), по эталону standalone-прототипа:
        #   мажорные линии делений 0.05 · центр-крест 0.16 · border 0.12 · тики 0.28
        BORDER_A, CENTER_A, MINOR_A = 31, 41, 13
        specs = []
        for i in range(HDIV + 1):
            base = BORDER_A if i in (0, HDIV) else (CENTER_A if i == HDIV // 2 else MINOR_A)
            specs.append(("x", i, base))
        for j in range(VDIV + 1):
            y = j - VDIV // 2
            base = BORDER_A if j in (0, VDIV) else (CENTER_A if y == 0 else MINOR_A)
            specs.append(("y", y, base))
        for axis, pos, base in specs:
            line = self._pi.addLine(**({"x": pos} if axis == "x" else {"y": pos}),
                                    pen=pg.mkPen(color=(255, 255, 255, base), width=1))
            self._grat.append({"line": line, "base_alpha": base})

        # Субделения (5 на деление) — короткие тики по центральным осям («мм»).
        cx, cy = HDIV / 2.0, 0.0
        tx, ty = 0.06, 0.05   # полудлина тика по X / Y (в делениях ≈ 4px)
        xs: list[float] = []
        ys: list[float] = []
        x = 0.0
        while x <= HDIV + 1e-9:          # вертикальные тики на гориз. центр-оси (время)
            xs += [x, x, float("nan")]
            ys += [cy - ty, cy + ty, float("nan")]
            x += HDIV / 14 / 5           # = 0.2 деления
        y = -VDIV / 2.0
        while y <= VDIV / 2.0 + 1e-9:    # горизонтальные тики на верт. центр-оси (напряжение)
            xs += [cx - tx, cx + tx, float("nan")]
            ys += [y, y, float("nan")]
            y += VDIV / 8 / 5            # = 0.2 деления
        self._ticks = self._pi.plot(xs, ys, connect="finite",
                                    pen=pg.mkPen(color=(255, 255, 255, 71), width=1))
        self._apply_grid_style()

    def _apply_grid_style(self) -> None:
        style = Qt.PenStyle.DotLine if self._grid_style == "DOTTed" else Qt.PenStyle.SolidLine
        mult = self._gbright / 40.0  # 40 = базовый вид (множитель 1.0)
        for item in self._grat:
            alpha = max(0, min(255, int(item["base_alpha"] * mult)))
            item["line"].setPen(pg.mkPen(color=(255, 255, 255, alpha), width=1, style=style))
        if self._ticks is not None:
            ta = max(0, min(255, int(71 * mult)))
            self._ticks.setPen(pg.mkPen(color=(255, 255, 255, ta), width=1))

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

    # ------------------------------------------------------------------
    # Decode API (декодирование шин из сэмплов окна — клиентское)
    # ------------------------------------------------------------------

    def set_decode_config(self, config: dict) -> None:
        self._decode_config = config

    def _render_decode(self, view) -> None:
        """Декодировать шину из сэмплов видимого окна и нарисовать оверлей символов."""
        cfg = self._decode_config
        proto = (cfg or {}).get("protocol", "OFF")
        t = np.asarray(getattr(view, "time", []), dtype=float)
        if not cfg or proto == "OFF" or t.size < 2:
            self._decode_overlay.clear()
            return
        t0 = float(t[0])
        span = float(t[-1] - t[0]) or 1.0

        def _t2x(tv: float) -> float:
            return (float(tv) - t0) / span * HDIV

        chans = getattr(view, "channels", {})
        thr = float(cfg.get("threshold", 1.5))
        items: list[dict] = []
        try:
            if proto == "UART":
                from hantek_dso2d15.waveform.decode_uart import decode_uart
                u = cfg.get("uart", {})
                src = chans.get(int(u.get("source", 1)))
                if src is None:
                    self._decode_overlay.clear()
                    return
                syms = decode_uart(
                    t, src, threshold=thr, baud=float(u.get("baud", 9600)),
                    bits=int(u.get("bits", 8)), parity=str(u.get("parity", "NONE")),
                    stop_bits=int(u.get("stop_bits", 1)),
                    lsb_first=bool(u.get("lsb_first", True)))
                for s in syms:
                    col = ERR_RED if s.error else OK_GREEN
                    lbl = f"{s.value:02X}" + ("!" if s.error else "")
                    items.append({"x0": _t2x(s.start), "x1": _t2x(s.end), "label": lbl, "color": col})
            elif proto == "SPI":
                from hantek_dso2d15.waveform.decode_spi import decode_spi
                sp = cfg.get("spi", {})
                sclk = chans.get(int(sp.get("sclk", 1)))
                data = chans.get(int(sp.get("data", 2)))
                if sclk is None or data is None:
                    self._decode_overlay.clear()
                    return
                words = decode_spi(
                    t, sclk, data, threshold=thr,
                    clock_edge=str(sp.get("clock_edge", "Rising")),
                    bits=int(sp.get("bits", 8)), msb_first=bool(sp.get("msb_first", True)))
                for w in words:
                    items.append({"x0": _t2x(w.start), "x1": _t2x(w.end),
                                  "label": f"{w.value:X}", "color": OK_GREEN})
            elif proto == "I2C":
                from hantek_dso2d15.waveform.decode_i2c import decode_i2c
                ic = cfg.get("i2c", {})
                sda = chans.get(int(ic.get("sda", 1)))
                scl = chans.get(int(ic.get("scl", 2)))
                if sda is None or scl is None:
                    self._decode_overlay.clear()
                    return
                for s in decode_i2c(t, sda, scl, threshold=thr):
                    if s.kind == "start":
                        items.append({"x0": _t2x(s.start), "x1": _t2x(s.start) + 0.4,
                                      "label": "S", "color": WARN_AMBER})
                    elif s.kind == "stop":
                        items.append({"x0": _t2x(s.start) - 0.4, "x1": _t2x(s.start),
                                      "label": "P", "color": WARN_AMBER})
                    else:  # address / data
                        col = OK_GREEN if s.ack else ERR_RED
                        pfx = "" if s.kind == "data" else "@"
                        items.append({"x0": _t2x(s.start), "x1": _t2x(s.end),
                                      "label": f"{pfx}{s.value:02X}", "color": col})
        except Exception:  # noqa: BLE001 — битый конфиг/кадр не должен ронять рендер
            self._decode_overlay.clear()
            return
        self._decode_overlay.render(items)

    def _render_math(self, decoded) -> None:
        cfg = self._math_config
        if not cfg or not cfg.get("display"):
            self._math_curve.setData([], [])
            self._line_math = ""
            return
        try:
            res = compute_math(decoded, cfg)
        except Exception:  # noqa: BLE001 — мусорный конфиг не должен ронять рендер
            res = None
        if res is None or len(res.y) == 0:
            self._math_curve.setData([], [])
            self._line_math = ""
            return
        L = len(res.y)
        x = np.linspace(0.0, HDIV, L)
        if res.kind == "algebraic":
            scale = float(cfg.get("scale", 1.0)) or 1.0
            off = float(cfg.get("offset", 0.0))
            self._math_curve.setData(x, (np.asarray(res.y) + off) / scale)
            self._line_math = self._build_math_line(cfg, res)
        else:  # fft — авто-вписать спектр в графикуль (точная ось частот — дизайн-пасс)
            y = np.asarray(res.y, dtype=float)
            ymin = float(y.min())
            span = float(y.max()) - ymin or 1.0
            self._math_curve.setData(x, (y - ymin) / span * VDIV - VDIV / 2.0)
            self._line_math = self._build_math_line(cfg, res)

    @staticmethod
    def _build_math_line(cfg: dict, res) -> str:
        """HTML-строка math для бейджа: операция + скаляр (Vpp / пик-частота)."""
        if res.kind == "algebraic":
            op = _MATH_OP_SYM.get(str(cfg.get("operator", "")), "?")
            s1, s2 = cfg.get("source1", 1), cfg.get("source2", 2)
            y = np.asarray(res.y, dtype=float)
            vpp = float(y.max() - y.min()) if y.size else 0.0
            label = f"Math CH{s1}{op}CH{s2}&nbsp;&nbsp;Vpp={_volt_label(vpp)}"
        else:  # fft
            src = cfg.get("fft_source", 1)
            xf = np.asarray(res.x, dtype=float)
            yf = np.asarray(res.y, dtype=float)
            peak = f"&nbsp;&nbsp;peak {_freq_label(float(xf[int(np.argmax(yf))]))}" if yf.size else ""
            label = f"FFT CH{src}{peak}"
        return f"<span style='color:{MATH_COLOR}'>{label}</span>"

    # ------------------------------------------------------------------
    # Кадр
    # ------------------------------------------------------------------

    def update_frame(self, decoded) -> None:
        """Обновить кривые. Показываем окно ``14×s/дел`` (зум как на приборе).

        V/дел берётся из ``decoded.scales``. Развёртка ``decoded.timebase`` (с/дел)
        задаёт зум: рисуем центральный срез памяти шириной ``14×s/дел``. Полный
        буфер не теряется — math/курсоры получают тот же срез (``view``), поэтому их
        единицы соответствуют видимому окну; измерения/сохранение берут полный кадр.
        """
        n_pts = len(decoded.time)
        if n_pts == 0:
            return
        start, end = compute_window(n_pts, decoded.srate, getattr(decoded, "timebase", None))
        view = self._window_view(decoded, start, end)
        m = end - start
        x = np.linspace(0.0, HDIV, m)
        for n, curve in self._curves.items():
            v = view.channels.get(n)
            vdiv = view.scales.get(n)
            if v is not None and vdiv:
                # экранная позиция в делениях = (вольты + смещение)/Vдел = count/25,
                # так смещение двигает трассу, как на приборе
                off = view.offsets.get(n, 0.0)
                curve.setData(x, (np.asarray(v) + off) / vdiv)
            else:
                curve.setData([], [])

        self._render_math(view)
        self.cursors.update_frame(view)
        self._render_decode(view)
        self._update_trigger_markers(decoded)
        self._update_readout(view)
        if decoded.triggered:
            self.set_trigger_badge("Trig'd", OK_GREEN)
        else:
            self.set_trigger_badge("Auto", WARN_AMBER)

    def _update_trigger_markers(self, decoded) -> None:
        """Маркеры триггера: пунктир уровня + треугольник уровня (цвет источника)
        на левом краю + T-маркер позиции сверху. Скрыты, если источник не виден."""
        src = getattr(decoded, "trigger_source", None)
        lvl = getattr(decoded, "trigger_level", None)
        vdiv = decoded.scales.get(src) if src is not None else None
        if src is not None and lvl is not None and vdiv:
            off = decoded.offsets.get(src, 0.0)
            # запомнить для конвертации позиция↔вольты при перетаскивании
            self._trig_src, self._trig_vdiv, self._trig_offset = src, float(vdiv), float(off)
            r, g, b = _hex_to_rgb(CH_COLORS.get(src, CURSOR))
            self._trig_level_line.setPen(pg.mkPen(color=(r, g, b, 110), width=1,
                                                  style=Qt.PenStyle.DashLine))
            if not self._trig_dragging:            # не перебивать активный drag
                if self._trig_settle > 0:
                    # после отпускания держим позицию, пока прибор не догонит
                    # (иначе старые кадры дёргают линию назад — «bounce»)
                    self._trig_settle -= 1
                else:
                    y = (float(lvl) + off) / vdiv  # уровень в делениях
                    self._trig_level_line.setValue(y)
                    self._place_trig_arrow(y, (r, g, b))
            self._trig_level_line.show()
            self._trig_level_arrow.show()
            self._trig_pos_arrow.setPos(HDIV / 2.0, VDIV / 2.0)  # позиция по центру (по X)
            self._trig_pos_arrow.show()
        else:
            self._trig_src = self._trig_vdiv = None
            self._trig_level_line.hide()
            self._trig_level_arrow.hide()
            self._trig_pos_arrow.hide()

    def _place_trig_arrow(self, y_div: float, rgb) -> None:
        """Поставить треугольник уровня у левого края на уровне y_div."""
        self._trig_level_arrow.setStyle(brush=pg.mkBrush(*rgb))
        self._trig_level_arrow.setPos(0.22, max(-VDIV / 2.0, min(VDIV / 2.0, y_div)))

    def _on_trig_dragged(self) -> None:
        """Идёт перетаскивание линии уровня — двигаем треугольник за ней."""
        self._trig_dragging = True
        if self._trig_src is not None:
            rgb = _hex_to_rgb(CH_COLORS.get(self._trig_src, CURSOR))
            self._place_trig_arrow(self._trig_level_line.value(), rgb)

    def _on_trig_drag_done(self) -> None:
        """Перетаскивание завершено — конвертируем в вольты и шлём в прибор."""
        if not self._trig_dragging:
            return
        self._trig_dragging = False
        if self._trig_vdiv:
            y = self._trig_level_line.value()
            volts = y * self._trig_vdiv - self._trig_offset
            self._trig_settle = 4   # держать позицию, пока прибор догонит (без bounce)
            self.triggerLevelChanged.emit(float(volts))

    @staticmethod
    def _window_view(decoded, start: int, end: int):
        """Лёгкий «вид» кадра — срез [start:end] по времени/каналам.

        Масштабы/смещения/срейт/триггер/развёртка не меняются. Используется для
        рисовки, math и курсоров, чтобы их временные единицы шли по видимому окну.
        """
        return SimpleNamespace(
            time=decoded.time[start:end],
            channels={n: np.asarray(v)[start:end] for n, v in decoded.channels.items()},
            scales=decoded.scales,
            offsets=decoded.offsets,
            srate=decoded.srate,
            triggered=decoded.triggered,
            timebase=getattr(decoded, "timebase", None),
            trigger_level=getattr(decoded, "trigger_level", None),
            trigger_source=getattr(decoded, "trigger_source", None),
        )

    def _on_cursor_values(self, values: dict) -> None:
        """Курсоры изменились → собрать строку бейджа (ΔX · 1/ΔX · ΔY)."""
        if not values or values.get("mode", "OFF") == "OFF":
            self._line_cursors = ""
            self._render_readout()
            return
        parts = []
        dt = values.get("dt")
        if dt is not None:
            parts.append(f"ΔX={_time_label(dt)}")
            freq = values.get("freq")
            if freq is not None:
                parts.append(f"1/ΔX={_freq_label(freq)}")
        dv = values.get("dv")
        if dv is not None:
            parts.append(f"ΔY={_volt_label(dv)}")
        if parts:
            inner = "&nbsp;&nbsp;".join(parts)
            self._line_cursors = f"<span style='color:{CURSOR}'>Curs {inner}</span>"
        else:
            self._line_cursors = ""
        self._render_readout()

    def set_measurements_readout(self, html: str) -> None:
        """Принять готовую HTML-строку активных измерений (пушит main_window).

        Пустая строка убирает строку измерений из бейджа. Перерисовки кадра не
        требуется — текст обновится при следующем ``update_frame``; но для
        мгновенного отклика дёргаем перерисовку самого лейбла.
        """
        self._meas_readout = html or ""
        self._render_readout()

    def _update_readout(self, decoded) -> None:
        """Собрать строки бейджа из кадра и перерисовать.

        Строка 1 — каналы: ``CHn V/дел ⎓смещение`` (в цвете канала).
        Строка 2 — триггер: ``Trig CHn уровень`` (в цвете источника).
        Строка 3 — развёртка · срейт · статус.
        Строка 4 — активные измерения (``self._meas_readout``, если задана).
        """
        # --- строка 1: каналы (V/дел + смещение) ---
        ch_parts = []
        for n in sorted(decoded.channels):
            color = CH_COLORS.get(n, "#C5C9D1")
            vdiv = decoded.scales.get(n)
            if not vdiv:
                continue
            off = decoded.offsets.get(n, 0.0)
            off_txt = f" <span style='color:#7A808C'>⎓{_volt_label(off)}</span>" if off else ""
            ch_parts.append(
                f"<span style='color:{color}'>CH{n} {_vdiv_label(vdiv)}</span>{off_txt}"
            )
        self._line_channels = "&nbsp;&nbsp;".join(ch_parts)

        # --- строка 2: уровень триггера (цвет источника) ---
        src = getattr(decoded, "trigger_source", None)
        lvl = getattr(decoded, "trigger_level", None)
        if src is not None and lvl is not None:
            tcolor = CH_COLORS.get(src, "#C5C9D1")
            self._line_trigger = (
                f"<span style='color:{tcolor}'>Trig CH{src} {_volt_label(float(lvl))}</span>"
            )
        else:
            self._line_trigger = ""

        # --- строка 3: время/дел · срейт · статус ---
        tb_parts = []
        n_shown = len(decoded.time)
        sr = decoded.srate
        if n_shown > 1 and sr > 0:
            tdiv = (n_shown / sr) / HDIV
            tb_parts.append(f"<span style='color:#C5C9D1'>{_time_label(tdiv)}/дел</span>")
        if sr > 0:
            sr_txt = (f"{sr/1e9:g} GSa/s" if sr >= 1e9
                      else (f"{sr/1e6:g} MSa/s" if sr >= 1e6 else f"{sr/1e3:g} kSa/s"))
            tb_parts.append(f"<span style='color:#9AA0AC'>{sr_txt}</span>")
        trig = "Trig'd" if decoded.triggered else "Auto"
        tcol = "#37D67A" if decoded.triggered else "#F5A623"
        tb_parts.append(f"<span style='color:{tcol}'>{trig}</span>")
        self._line_timebase = "&nbsp;·&nbsp;".join(tb_parts)

        self._render_readout()

    def _render_readout(self) -> None:
        """Склеить непустые строки бейджа и обновить лейбл.

        Дедуп: ``setText``/``adjustSize`` (релейаут rich-text, дорого) только при
        реальном изменении содержимого. Бейдж зовётся каждый кадр, но строки
        каналов/развёртки/таблицы между кадрами обычно совпадают — лишний релейаут
        под нагрузкой режет FPS.
        """
        lines = [
            getattr(self, "_line_channels", ""),
            getattr(self, "_line_trigger", ""),
            getattr(self, "_line_timebase", ""),
            getattr(self, "_line_math", ""),
            getattr(self, "_line_cursors", ""),
            self._meas_readout,
        ]
        html = "<br>".join(s for s in lines if s)
        if html == getattr(self, "_readout_html_cache", None):
            return
        self._readout_html_cache = html
        self._readout.setText(html)
        self._readout.adjustSize()

    def clear(self) -> None:
        for curve in self._curves.values():
            curve.setData([], [])
        self._math_curve.setData([], [])
