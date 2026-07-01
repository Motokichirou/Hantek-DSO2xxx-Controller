"""Тесты накопителя статистики измерений MeasurementStats (чистая логика, без Qt).

Прибор отдаёт только текущее значение измерения; статистику cur/avg/max/min/std/count
копим на нашей стороне по потоку кадров. Запуск:
    .venv/Scripts/python.exe -m pytest tests/test_measure_stats.py -q
"""
from __future__ import annotations

import math

import pytest

from hantek_dso2d15.measure_stats import MeasurementStats


def _payload(*triples):
    """Хелпер: список dict'ов {channel,item,value} из троек (ch, item, value)."""
    return [{"channel": c, "item": i, "value": v} for c, i, v in triples]


class TestSingleSample:
    def test_one_value_cur_equals_value(self):
        st = MeasurementStats()
        st.update(_payload((1, "VMAX", 1.5)))
        s = st.stats_for(1, "VMAX")
        assert s["cur"] == pytest.approx(1.5)

    def test_one_value_avg_min_max_equal(self):
        st = MeasurementStats()
        st.update(_payload((1, "VMAX", 1.5)))
        s = st.stats_for(1, "VMAX")
        assert s["avg"] == pytest.approx(1.5)
        assert s["min"] == pytest.approx(1.5)
        assert s["max"] == pytest.approx(1.5)

    def test_one_value_std_zero(self):
        st = MeasurementStats()
        st.update(_payload((1, "VMAX", 1.5)))
        assert st.stats_for(1, "VMAX")["std"] == pytest.approx(0.0)

    def test_one_value_count_one(self):
        st = MeasurementStats()
        st.update(_payload((1, "VMAX", 1.5)))
        assert st.stats_for(1, "VMAX")["count"] == 1


class TestAccumulation:
    def test_avg_of_several(self):
        st = MeasurementStats()
        for v in (1.0, 2.0, 3.0):
            st.update(_payload((1, "VMAX", v)))
        s = st.stats_for(1, "VMAX")
        assert s["avg"] == pytest.approx(2.0)
        assert s["count"] == 3

    def test_min_max_track_extremes(self):
        st = MeasurementStats()
        for v in (2.0, 5.0, 1.0, 4.0):
            st.update(_payload((1, "VMAX", v)))
        s = st.stats_for(1, "VMAX")
        assert s["min"] == pytest.approx(1.0)
        assert s["max"] == pytest.approx(5.0)

    def test_cur_is_latest(self):
        st = MeasurementStats()
        for v in (2.0, 5.0, 1.0):
            st.update(_payload((1, "VMAX", v)))
        assert st.stats_for(1, "VMAX")["cur"] == pytest.approx(1.0)

    def test_std_population(self):
        """std — популяционное СКО (ddof=0)."""
        st = MeasurementStats()
        for v in (1.0, 2.0, 3.0):
            st.update(_payload((1, "VMAX", v)))
        # mean=2, var=((1)+(0)+(1))/3=2/3, std=sqrt(2/3)
        assert st.stats_for(1, "VMAX")["std"] == pytest.approx(math.sqrt(2.0 / 3.0))

    def test_rms_of_values(self):
        """rms — среднеквадратичное самих значений √(Σv²/n)."""
        st = MeasurementStats()
        for v in (1.0, 2.0, 3.0):
            st.update(_payload((1, "VMAX", v)))
        # √((1+4+9)/3) = √(14/3)
        assert st.stats_for(1, "VMAX")["rms"] == pytest.approx(math.sqrt(14.0 / 3.0))

    def test_rms_single_value_is_abs(self):
        st = MeasurementStats()
        st.update(_payload((1, "VMAX", -2.5)))
        assert st.stats_for(1, "VMAX")["rms"] == pytest.approx(2.5)


class TestMultipleKeys:
    def test_keys_independent(self):
        st = MeasurementStats()
        st.update(_payload((1, "VMAX", 1.0), (2, "FREQuency", 1000.0)))
        st.update(_payload((1, "VMAX", 3.0), (2, "FREQuency", 1000.0)))
        assert st.stats_for(1, "VMAX")["avg"] == pytest.approx(2.0)
        assert st.stats_for(2, "FREQuency")["avg"] == pytest.approx(1000.0)

    def test_same_item_different_channel_independent(self):
        st = MeasurementStats()
        st.update(_payload((1, "VMAX", 1.0), (2, "VMAX", 5.0)))
        assert st.stats_for(1, "VMAX")["cur"] == pytest.approx(1.0)
        assert st.stats_for(2, "VMAX")["cur"] == pytest.approx(5.0)


class TestNoneAndMissing:
    def test_none_value_skipped(self):
        st = MeasurementStats()
        st.update(_payload((1, "VMAX", 1.0)))
        st.update(_payload((1, "VMAX", None)))   # None не должен попасть в статистику
        s = st.stats_for(1, "VMAX")
        assert s["count"] == 1
        assert s["cur"] == pytest.approx(1.0)

    def test_unknown_key_returns_none(self):
        st = MeasurementStats()
        assert st.stats_for(9, "NOPE") is None

    def test_malformed_entry_ignored(self):
        st = MeasurementStats()
        st.update([{"channel": 1}, {"item": "X"}, {"channel": 1, "item": "VMAX", "value": 2.0}])
        assert st.stats_for(1, "VMAX")["cur"] == pytest.approx(2.0)


class TestReset:
    def test_reset_clears_all(self):
        st = MeasurementStats()
        st.update(_payload((1, "VMAX", 1.0)))
        st.reset()
        assert st.stats_for(1, "VMAX") is None

    def test_count_restarts_after_reset(self):
        st = MeasurementStats()
        st.update(_payload((1, "VMAX", 1.0)))
        st.update(_payload((1, "VMAX", 2.0)))
        st.reset()
        st.update(_payload((1, "VMAX", 9.0)))
        s = st.stats_for(1, "VMAX")
        assert s["count"] == 1
        assert s["avg"] == pytest.approx(9.0)
