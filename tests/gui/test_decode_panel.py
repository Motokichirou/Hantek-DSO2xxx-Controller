"""Headless-тесты DecodePanel (QT_QPA_PLATFORM=offscreen).

Запуск: .venv/Scripts/python.exe -m pytest tests/gui/test_decode_panel.py -q
"""
from __future__ import annotations

import os
import sys

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication  # noqa: E402
from PySide6.QtWidgets import QApplication   # noqa: E402

from hantek_dso2d15.gui.panels.decode import DecodePanel  # noqa: E402


@pytest.fixture(scope="module")
def app():
    existing = QCoreApplication.instance()
    if existing is not None:
        yield existing
    else:
        yield QApplication(sys.argv[:1])


@pytest.fixture
def panel(app):
    return DecodePanel()


class TestDefaults:
    def test_default_protocol_off(self, panel):
        assert panel.config()["protocol"] == "OFF"

    def test_default_threshold(self, panel):
        assert panel.config()["threshold"] == pytest.approx(1.5)

    def test_config_has_all_sections(self, panel):
        cfg = panel.config()
        assert set(cfg) >= {"protocol", "threshold", "uart", "spi", "i2c"}


class TestProtocolSwitch:
    def test_switch_emits(self, panel):
        received = []
        panel.decodeConfigChanged.connect(received.append)
        panel._protocol._button_map["UART"].click()
        assert received and received[-1]["protocol"] == "UART"

    def test_switch_changes_stack(self, panel):
        panel._protocol._button_map["SPI"].click()
        assert panel._stack.currentIndex() == 3 - 1  # SPI = индекс 2

    def test_i2c_selected(self, panel):
        panel._protocol._button_map["I2C"].click()   # ключ = value, не label
        assert panel.config()["protocol"] == "I2C"
        assert panel._stack.currentIndex() == 3


class TestUartConfig:
    def test_uart_params(self, panel):
        panel._protocol._button_map["UART"].click()
        panel._u_baud.setCurrentText("115200")
        panel._u_bits.setValue(7)
        panel._u_parity._button_map["EVEN"].click()
        cfg = panel.config()["uart"]
        assert cfg["baud"] == pytest.approx(115200.0)
        assert cfg["bits"] == 7
        assert cfg["parity"] == "EVEN"
        assert cfg["source"] in (1, 2)


class TestSpiConfig:
    def test_spi_params(self, panel):
        panel._protocol._button_map["SPI"].click()
        panel._s_edge._button_map["Falling"].click()
        panel._s_bits.setValue(16)
        cfg = panel.config()["spi"]
        assert cfg["clock_edge"] == "Falling"
        assert cfg["bits"] == 16
        assert cfg["sclk"] in (1, 2) and cfg["data"] in (1, 2)


class TestI2cConfig:
    def test_i2c_sources(self, panel):
        cfg = panel.config()["i2c"]
        assert cfg["sda"] in (1, 2)
        assert cfg["scl"] in (1, 2)


class TestStructure:
    def test_has_signal(self, panel):
        assert hasattr(panel, "decodeConfigChanged")

    def test_has_config(self, panel):
        assert callable(getattr(panel, "config", None))
