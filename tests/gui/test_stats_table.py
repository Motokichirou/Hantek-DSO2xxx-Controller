"""Тесты моноширинного паддинга жёсткой таблицы статистики (MainWindow._pad).

_pad — статик-метод; инстанс окна не нужен. Гарантия: ≥1 пробел-разделитель между
колонками (иначе при полной ширине ячейки слипаются). Запуск:
    .venv/Scripts/python.exe -m pytest tests/gui/test_stats_table.py -q
"""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from hantek_dso2d15.gui.main_window import MainWindow  # noqa: E402


class TestPadSeparator:
    def test_exact_width_keeps_separator_right(self):
        """Значение длиной = width всё равно оставляет ведущий пробел (right-justify)."""
        out = MainWindow._pad("123456789012", 11, right=True)
        assert len(out) == 11
        assert out.startswith(" "), "right-justify: должен остаться ≥1 ведущий пробел"

    def test_exact_width_keeps_separator_left(self):
        """Левое выравнивание оставляет хвостовой пробел."""
        out = MainWindow._pad("123456789012", 11, right=False)
        assert len(out) == 11
        assert out.endswith(" "), "left-justify: должен остаться ≥1 хвостовой пробел"

    def test_overlong_truncated_with_ellipsis(self):
        out = MainWindow._pad("ABCDEFGHIJKLMNOP", 11, right=True)
        assert len(out) == 11
        assert "…" in out
        assert out.startswith(" ")

    def test_short_value_padded(self):
        out = MainWindow._pad("1.6V", 11, right=True)
        assert len(out) == 11
        assert out.strip() == "1.6V"

    def test_label_left_aligned(self):
        out = MainWindow._pad("CH1 VMAX", 13, right=False)
        assert len(out) == 13
        assert out.startswith("CH1 VMAX")
        assert out.endswith(" ")
