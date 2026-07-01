"""Интеграционный тест декод-оверлея на графике (offscreen).

Проверяет замкнутый путь: set_decode_config → update_frame → декод из сэмплов →
видимые прямоугольники символов на ScopePlot. Запуск:
    .venv/Scripts/python.exe -m pytest tests/gui/test_decode_overlay.py -q
"""
from __future__ import annotations

import os
import sys
from types import SimpleNamespace

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication  # noqa: E402
from PySide6.QtWidgets import QApplication   # noqa: E402

from hantek_dso2d15.gui.plot_widget import ScopePlot  # noqa: E402


@pytest.fixture(scope="module")
def app():
    existing = QCoreApplication.instance()
    if existing is not None:
        yield existing
    else:
        yield QApplication(sys.argv[:1])


def _make_uart(bytes_seq, baud=9600, sr=480000, vlo=0.0, vhi=3.3, lead=8, tail=8):
    spb = int(round(sr / baud))
    levels = [1] * (lead * spb)
    for byte in bytes_seq:
        levels += [0] * spb
        for k in range(8):
            levels += [(byte >> k) & 1] * spb
        levels += [1] * spb
    levels += [1] * (tail * spb)
    arr = np.array(levels, dtype=float)
    samples = np.where(arr > 0.5, vhi, vlo)
    times = np.arange(samples.size) / sr
    return times, samples


def _frame(times, samples):
    return SimpleNamespace(
        time=times, channels={1: samples, 2: np.zeros_like(samples)},
        scales={1: 1.0, 2: 1.0}, offsets={1: -1.6, 2: 0.0},
        srate=480000.0, triggered=True, timebase=None,
        trigger_level=None, trigger_source=None)


def _visible_rects(plot):
    return [r for r in plot._decode_overlay._rects if r.isVisible()]


def test_uart_overlay_renders_symbols(app):
    plot = ScopePlot()
    t, s = _make_uart([0x55, 0x3C, 0xA0])
    plot.set_decode_config({
        "protocol": "UART", "threshold": 1.5,
        "uart": {"source": 1, "baud": 9600, "bits": 8, "parity": "NONE",
                 "stop_bits": 1, "lsb_first": True}, "spi": {}, "i2c": {}})
    plot.update_frame(_frame(t, s))
    assert len(_visible_rects(plot)) >= 3, "три байта → минимум 3 символа на оверлее"


def test_off_clears_overlay(app):
    plot = ScopePlot()
    t, s = _make_uart([0x55])
    plot.set_decode_config({
        "protocol": "UART", "threshold": 1.5,
        "uart": {"source": 1, "baud": 9600, "bits": 8, "parity": "NONE",
                 "stop_bits": 1, "lsb_first": True}, "spi": {}, "i2c": {}})
    plot.update_frame(_frame(t, s))
    assert len(_visible_rects(plot)) >= 1
    # выключение протокола очищает ленту
    plot.set_decode_config({"protocol": "OFF"})
    plot.update_frame(_frame(t, s))
    assert len(_visible_rects(plot)) == 0


def test_bad_config_does_not_crash(app):
    plot = ScopePlot()
    t, s = _make_uart([0x55])
    plot.set_decode_config({"protocol": "UART"})  # без секции uart → безопасно
    plot.update_frame(_frame(t, s))  # не должно бросить
    assert True
