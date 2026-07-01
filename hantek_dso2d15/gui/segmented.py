"""Переиспользуемый виджет SegmentedControl — горизонтальный ряд сегментов.

Заменяет QComboBox для коротких фиксированных наборов опций
(Coupling: AC/DC/GND, Slope: POS/NEG, Trigger mode: NORM/AUTO/SINGLE и т.д.).
Визуал по дизайн-макету design/design_handoff_dso2d15_ui.
"""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QButtonGroup, QSizePolicy,
)

from hantek_dso2d15.gui.theme import rgba


def _normalize(options: list) -> list[tuple[str, str]]:
    """Нормализовать список опций в список пар (label, value).

    Элемент str   → (s, s)
    Элемент tuple → (label, value)
    """
    result = []
    for item in options:
        if isinstance(item, str):
            result.append((item, item))
        else:
            label, value = item
            result.append((str(label), str(value)))
    return result


class SegmentedControl(QWidget):
    """Горизонтальный ряд сегментов-кнопок с эксклюзивным выбором.

    Parameters
    ----------
    options:
        Список строк (label==value) или список пар (label, value).
    accent:
        Hex-цвет (#RRGGBB) активного сегмента (тинт фона + текст + рамка).
    parent:
        Родительский виджет Qt.

    Signals
    -------
    valueChanged(str):
        Эмитируется только при выборе сегмента **пользователем**.
        Не эмитируется при __init__ и при вызове set_value().
    """

    valueChanged = Signal(str)

    def __init__(
        self,
        options: list,
        accent: str = "#37D67A",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._accent = accent
        self._pairs = _normalize(options)          # [(label, value), ...]
        self._value_map: dict[int, str] = {}       # button_id → value
        self._button_map: dict[str, QPushButton] = {}  # value → button

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        n = len(self._pairs)
        for i, (label, value) in enumerate(self._pairs):
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.setFixedHeight(26)

            # Скругление: только у крайних кнопок
            if n == 1:
                position = "only"
            elif i == 0:
                position = "left"
            elif i == n - 1:
                position = "right"
            else:
                position = "middle"

            btn.setProperty("segPosition", position)
            btn.setProperty("segAccent", accent)
            self._apply_button_style(btn, position, accent, checked=False)

            self._group.addButton(btn, i)
            self._value_map[i] = value
            self._button_map[value] = btn
            layout.addWidget(btn)

        # Выбрать первый сегмент БЕЗ эмиссии
        if self._pairs:
            first_btn = self._group.button(0)
            first_btn.blockSignals(True)
            first_btn.setChecked(True)
            first_btn.blockSignals(False)
            self._apply_button_style(
                first_btn,
                first_btn.property("segPosition"),
                accent,
                checked=True,
            )

        # Подключить сигнал после инициализации
        self._group.idClicked.connect(self._on_button_clicked)

    # ------------------------------------------------------------------
    # Внутренние методы
    # ------------------------------------------------------------------

    def _apply_button_style(
        self,
        btn: QPushButton,
        position: str,
        accent: str,
        *,
        checked: bool,
    ) -> None:
        """Задать QSS для одной кнопки по позиции и состоянию."""
        # Радиусы скруглений: left=4px left-corners, right=4px right-corners, middle/only=4px all
        if position == "left":
            radius = "border-radius: 0; border-top-left-radius: 4px; border-bottom-left-radius: 4px;"
            border = "border-right: none;"
        elif position == "right":
            radius = "border-radius: 0; border-top-right-radius: 4px; border-bottom-right-radius: 4px;"
            border = ""
        elif position == "only":
            radius = "border-radius: 4px;"
            border = ""
        else:  # middle
            radius = "border-radius: 0;"
            border = "border-right: none;"

        if checked:
            bg = rgba(accent, 0.16)
            color = accent
            border_color = accent
        else:
            bg = "#16181D"
            color = "#7A808C"
            border_color = "#2A2D34"

        style = (
            f"QPushButton {{"
            f"  background: {bg};"
            f"  color: {color};"
            f"  border: 1px solid {border_color};"
            f"  {border}"
            f"  {radius}"
            f"  font-size: 11px;"
            f"  font-weight: 600;"
            f"  padding: 0 8px;"
            f"  min-height: 26px;"
            f"  max-height: 26px;"
            f"}}"
        )
        btn.setStyleSheet(style)

    def _on_button_clicked(self, btn_id: int) -> None:
        """Обработчик клика пользователя — обновляет стили, эмитирует сигнал."""
        value = self._value_map.get(btn_id)
        if value is None:
            return

        # Перекрасить все кнопки
        for bid, btn in enumerate(self._group.buttons()):
            is_checked = (bid == btn_id)
            # найти индекс кнопки в group по id
            # _group.buttons() возвращает в порядке добавления (соответствует индексу)
            pass

        # Перекрасить все по факту checked-состояния
        for bid in range(len(self._pairs)):
            btn = self._group.button(bid)
            if btn is None:
                continue
            is_checked = (bid == btn_id)
            self._apply_button_style(
                btn,
                btn.property("segPosition"),
                self._accent,
                checked=is_checked,
            )

        self.valueChanged.emit(value)

    # ------------------------------------------------------------------
    # Публичный API
    # ------------------------------------------------------------------

    def value(self) -> str | None:
        """Вернуть value текущего выбранного сегмента, или None если нет."""
        checked = self._group.checkedButton()
        if checked is None:
            return None
        btn_id = self._group.id(checked)
        return self._value_map.get(btn_id)

    def set_value(self, value: str) -> None:
        """Выбрать сегмент с данным value. Не эмитирует valueChanged.

        Если value не найден — ничего не делает.
        """
        btn = self._button_map.get(value)
        if btn is None:
            return  # неизвестное value — игнорируем

        # Заблокировать сигналы группы на время программного выбора
        self._group.blockSignals(True)
        btn.blockSignals(True)
        try:
            btn.setChecked(True)
        finally:
            btn.blockSignals(False)
            self._group.blockSignals(False)

        # Перекрасить все кнопки
        for bid in range(len(self._pairs)):
            b = self._group.button(bid)
            if b is None:
                continue
            self._apply_button_style(
                b,
                b.property("segPosition"),
                self._accent,
                checked=(b is btn),
            )
