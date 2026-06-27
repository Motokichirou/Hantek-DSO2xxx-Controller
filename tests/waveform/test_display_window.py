"""Тесты чистой функции окна отображения развёртки (display_window)."""
from __future__ import annotations

from hantek_dso2d15.waveform.display_window import compute_window


class TestComputeWindow:
    def test_window_smaller_than_memory_centered(self):
        # 4000 точек @ 1 ГСа/с, развёртка 2 нс/дел -> окно 14*2ns=28ns -> 28 сэмплов
        start, end = compute_window(4000, 1e9, 2e-9)
        assert end - start == 28
        # центрировано вокруг середины (2000)
        assert start == 2000 - 14
        assert end == 2000 + 14

    def test_window_larger_than_memory_returns_all(self):
        # медленная развёртка: окно больше памяти -> показываем всё
        start, end = compute_window(4000, 1e9, 1.0)
        assert (start, end) == (0, 4000)

    def test_window_equal_memory_returns_all(self):
        # 4000 @ 1e9, tb такой что 14*tb*srate == 4000 -> всё
        tb = 4000 / (14 * 1e9)
        start, end = compute_window(4000, 1e9, tb)
        assert (start, end) == (0, 4000)

    def test_none_timebase_returns_all(self):
        assert compute_window(4000, 1e9, None) == (0, 4000)

    def test_zero_srate_returns_all(self):
        assert compute_window(4000, 0.0, 2e-9) == (0, 4000)

    def test_clamp_does_not_exceed_bounds(self):
        start, end = compute_window(100, 1e9, 2e-9)  # окно 28 в 100 точках
        assert 0 <= start
        assert end <= 100
        assert end - start == 28

    def test_minimum_two_points(self):
        # экстремально быстрый/короткий случай не должен дать <2 точек
        start, end = compute_window(4000, 1e9, 1e-12)
        assert end - start >= 2

    def test_custom_divisions(self):
        start, end = compute_window(4000, 1e9, 2e-9, n_divs=10)
        assert end - start == 20  # 10*2ns*1e9
