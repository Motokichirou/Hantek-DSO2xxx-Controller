"""Переиспользуемые виджеты GUI."""
from __future__ import annotations

from PySide6.QtCore import QLocale
from PySide6.QtWidgets import QDoubleSpinBox


class DecimalSpinBox(QDoubleSpinBox):
    """QDoubleSpinBox, принимающий И точку, И запятую как десятичный разделитель.

    Удобно на нумпаде: в русской/английской раскладке разделитель разный — оба
    варианта работают без лишних телодвижений. Запятая на лету заменяется точкой.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # точка как «родной» разделитель отображения/парсинга
        self.setLocale(QLocale(QLocale.Language.C))

    def validate(self, text, pos):  # type: ignore[override]
        return super().validate(text.replace(",", "."), pos)

    def valueFromText(self, text):  # type: ignore[override]
        return super().valueFromText(text.replace(",", "."))
