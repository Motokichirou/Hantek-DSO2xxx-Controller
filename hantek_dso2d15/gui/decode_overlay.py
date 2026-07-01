"""DecodeOverlay — оверлей декодированных символов шины на графике.

Рисует горизонтальную ленту прямоугольников с подписями (hex-значения) вдоль
временной оси в нижней части графикуля. Протокол-агностичен: принимает уже
готовые элементы ``{x0, x1, label, color}`` в координатах делений (0..HDIV по X);
преобразование время→X и выбор цвета — на стороне ``plot_widget`` (декод-раннер).

Пул графических элементов переиспользуется между кадрами (без пересоздания).
"""
from __future__ import annotations

import pyqtgraph as pg
from PySide6.QtGui import QColor, QPen, QBrush
from PySide6.QtWidgets import QGraphicsRectItem


class DecodeOverlay:
    """Лента символов декодера на графике (нижняя полоса)."""

    def __init__(self, plot_item, y0: float = -3.9, y1: float = -3.1) -> None:
        self._vb = plot_item.getViewBox()
        self._y0 = y0
        self._y1 = y1
        self._rects: list[QGraphicsRectItem] = []
        self._texts: list[pg.TextItem] = []

    # ------------------------------------------------------------------
    def _ensure(self, n: int) -> None:
        """Дорастить пулы прямоугольников/подписей до n элементов."""
        while len(self._rects) < n:
            r = QGraphicsRectItem()
            r.setZValue(20)
            r.hide()
            self._vb.addItem(r, ignoreBounds=True)
            self._rects.append(r)
            t = pg.TextItem(anchor=(0.5, 0.5))
            t.setZValue(21)
            t.hide()
            self._vb.addItem(t, ignoreBounds=True)
            self._texts.append(t)

    def clear(self) -> None:
        """Скрыть все элементы оверлея."""
        for r in self._rects:
            r.hide()
        for t in self._texts:
            t.hide()

    def render(self, items: list[dict]) -> None:
        """Отрисовать символы.

        items — список ``{"x0": float, "x1": float, "label": str, "color": str}``
        в координатах делений (X: 0..HDIV). Пустой список — очищает ленту.
        """
        self.clear()
        if not items:
            return
        self._ensure(len(items))
        ymid = (self._y0 + self._y1) / 2.0
        h = self._y1 - self._y0
        for i, it in enumerate(items):
            x0 = float(it["x0"])
            x1 = float(it["x1"])
            if x1 < x0:
                x0, x1 = x1, x0
            w = max(x1 - x0, 1e-4)
            color = QColor(it.get("color", "#C5C9D1"))
            r = self._rects[i]
            r.setRect(x0, self._y0, w, h)
            fill = QColor(color)
            fill.setAlpha(60)
            r.setBrush(QBrush(fill))
            r.setPen(QPen(color, 0))
            r.show()
            t = self._texts[i]
            t.setColor(color)
            t.setText(str(it.get("label", "")))
            t.setPos((x0 + x1) / 2.0, ymid)
            # подпись прячем, если ячейка слишком узкая (визуальный мусор)
            t.setVisible(w >= 0.35)
