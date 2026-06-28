"""WaveformPicker — сетка плиток выбора формы сигнала генератора.

Замена QComboBox для типа DDS-волны: каждая плитка несёт нарисованный глиф формы
(синус/прямоугольник/пила/экспонента/шум/DC) + подпись. Эксклюзивный выбор.

API намеренно совпадает с :class:`SegmentedControl` (``valueChanged``/``set_value``/
``value``/``_button_map``) — чтобы привязка панели и тесты были единообразны.
"""
from __future__ import annotations

import math

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QPixmap, QPainter, QPen, QColor, QIcon
from PySide6.QtWidgets import (
    QWidget, QGridLayout, QToolButton, QButtonGroup, QSizePolicy,
)

# Фиксированный «шум» для глифа NOISe — детерминированно (одинаковая иконка всегда).
_NOISE = [0.2, -0.6, 0.5, -0.3, 0.8, -0.5, 0.1, -0.8, 0.4, -0.2,
          0.7, -0.4, 0.3, -0.7, 0.6, -0.1]


def _wave_points(kind: str, n: int = 72) -> list[tuple[float, float]]:
    """Нормализованные точки глифа (x,y ∈ [0..1], y: 0=верх, 1=низ)."""
    pts: list[tuple[float, float]] = []
    for i in range(n + 1):
        t = i / n
        if kind == "SINE":
            y = 0.5 - 0.4 * math.sin(2 * math.pi * t)
        elif kind == "SQUAre":
            y = 0.12 if (t * 2) % 1.0 < 0.5 else 0.88
        elif kind == "RAMP":
            y = 0.9 - 0.8 * (2 * t if t < 0.5 else 2 * (1 - t))   # треугольник
        elif kind == "EXP":
            y = 0.88 - 0.78 * math.exp(-3.2 * t)
        elif kind == "NOISe":
            y = 0.5 - 0.36 * _NOISE[i % len(_NOISE)]
        elif kind == "DC":
            y = 0.4
        else:  # ARB* и прочее — мягкая «произвольная» волна
            y = 0.5 - 0.32 * math.sin(2 * math.pi * t) * math.sin(math.pi * t)
        pts.append((t, y))
    return pts


def waveform_icon(kind: str, size: int = 30, color: str = "#C5C9D1") -> QIcon:
    """Нарисовать глиф формы сигнала и вернуть QIcon (для плиток/легенды)."""
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    pen = QPen(QColor(color))
    pen.setWidthF(1.6)
    p.setPen(pen)
    m = 4.0
    span = size - 2 * m
    pts = _wave_points(kind)
    prev = None
    for t, y in pts:
        x = m + t * span
        yy = m + y * (size - 2 * m)
        if prev is not None:
            p.drawLine(int(prev[0]), int(prev[1]), int(x), int(yy))
        prev = (x, yy)
    p.end()
    return QIcon(pm)


class WaveformPicker(QWidget):
    """Сетка плиток выбора формы DDS-сигнала.

    Parameters
    ----------
    options:
        Список пар ``(value, label)`` — value = frozen SCPI-литерал, label = подпись.
    columns:
        Число колонок сетки.
    accent:
        Hex-цвет активной плитки и глифа.

    Signals
    -------
    valueChanged(str):
        Только при выборе плитки пользователем (не из __init__/set_value).
    """

    valueChanged = Signal(str)

    def __init__(
        self,
        options: list[tuple[str, str]],
        columns: int = 5,
        accent: str = "#37D67A",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._accent = accent
        self._value_map: dict[int, str] = {}
        self._button_map: dict[str, QToolButton] = {}

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)

        lay = QGridLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)

        for i, (value, label) in enumerate(options):
            btn = QToolButton()
            btn.setCheckable(True)
            btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            btn.setIcon(waveform_icon(value, color="#9AA0AC"))
            btn.setIconSize(QSize(30, 22))
            btn.setText(label)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.setToolTip(value)
            self._apply_style(btn, checked=False)
            self._group.addButton(btn, i)
            self._value_map[i] = value
            self._button_map[value] = btn
            lay.addWidget(btn, i // columns, i % columns)

        if options:
            first = self._group.button(0)
            first.blockSignals(True)
            first.setChecked(True)
            first.blockSignals(False)
            self._apply_style(first, checked=True)

        self._group.idClicked.connect(self._on_clicked)

    # ------------------------------------------------------------------
    def _apply_style(self, btn: QToolButton, *, checked: bool) -> None:
        if checked:
            bg, fg, border = self._rgba(self._accent, 0.16), self._accent, self._accent
            btn.setIcon(waveform_icon(btn.toolTip(), color=self._accent))
        else:
            bg, fg, border = "#16181D", "#7A808C", "#2A2D34"
            btn.setIcon(waveform_icon(btn.toolTip(), color="#9AA0AC"))
        btn.setStyleSheet(
            f"QToolButton {{ background: {bg}; color: {fg};"
            f" border: 1px solid {border}; border-radius: 5px;"
            f" font-size: 10px; font-weight: 600; padding: 3px 2px; }}"
        )

    @staticmethod
    def _rgba(hex_color: str, alpha: float) -> str:
        h = hex_color.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f"rgba({r},{g},{b},{alpha})"

    def _on_clicked(self, bid: int) -> None:
        value = self._value_map.get(bid)
        if value is None:
            return
        for i in range(len(self._value_map)):
            b = self._group.button(i)
            if b is not None:
                self._apply_style(b, checked=(i == bid))
        self.valueChanged.emit(value)

    # ------------------------------------------------------------------
    # Публичный API (как у SegmentedControl)
    # ------------------------------------------------------------------
    def value(self) -> str | None:
        checked = self._group.checkedButton()
        if checked is None:
            return None
        return self._value_map.get(self._group.id(checked))

    def set_value(self, value: str) -> None:
        """Выбрать плитку без эмиссии valueChanged. Неизвестное value — игнор."""
        btn = self._button_map.get(value)
        if btn is None:
            return
        self._group.blockSignals(True)
        btn.blockSignals(True)
        try:
            btn.setChecked(True)
        finally:
            btn.blockSignals(False)
            self._group.blockSignals(False)
        for i in range(len(self._value_map)):
            b = self._group.button(i)
            if b is not None:
                self._apply_style(b, checked=(b is btn))
