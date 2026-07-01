"""Панель Decode — клиентское декодирование шин (UART / SPI / I²C).

Прибор декодированные данные шин по SCPI не отдаёт — декодируем из сэмплов на
нашей стороне (см. ``waveform/decode_*.py``). Панель только собирает конфиг и
эмитит его сигналом ``decodeConfigChanged(dict)``; сам декод и оверлей символов
на графике — в ``plot_widget`` (по аналогии с Math/Cursors, без прибора).

Прибор 2-канальный, поэтому источники — CH1/CH2 (SPI: SCLK+DATA; I²C: SDA+SCL).
"""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QLabel, QComboBox, QCheckBox,
    QStackedWidget, QSpinBox,
)

from hantek_dso2d15.gui.widgets import DecimalSpinBox
from hantek_dso2d15.gui.segmented import SegmentedControl

# Frozen-совместимые перечисления (из docs/scpi-command-reference.md, TRIGger:UART/SPI)
BAUDS = (110, 300, 600, 1200, 2400, 4800, 9600, 14400, 19200, 38400,
         57600, 115200, 230400, 460800, 921600)
PARITIES = ("NONE", "ODD", "EVEN")
CLOCK_EDGES = (("Rising", "Rising"), ("Falling", "Falling"))
PROTOCOLS = (("Off", "OFF"), ("UART", "UART"), ("SPI", "SPI"), ("I²C", "I2C"))


def _channel_combo() -> QComboBox:
    c = QComboBox()
    c.addItem("CH1", 1)
    c.addItem("CH2", 2)
    return c


class DecodePanel(QWidget):
    """Панель настройки декодирования шины.

    Сигнал ``decodeConfigChanged(dict)`` эмитится при любом изменении; конфиг:
        {
          "protocol": "OFF"|"UART"|"SPI"|"I2C",
          "threshold": float,          # порог логического уровня, В
          "uart": {"source","baud","bits","parity","stop_bits","lsb_first"},
          "spi":  {"sclk","data","clock_edge","bits","msb_first"},
          "i2c":  {"sda","scl"},
        }
    Ключи протокол-специфичных секций всегда присутствуют (значения по контролам).
    """

    decodeConfigChanged = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setSpacing(8)

        top = QGridLayout()
        top.setHorizontalSpacing(8)
        top.setVerticalSpacing(6)

        # Протокол
        top.addWidget(QLabel("Протокол"), 0, 0)
        self._protocol = SegmentedControl(list(PROTOCOLS), accent="#37D67A")
        self._protocol.valueChanged.connect(self._on_protocol_changed)
        top.addWidget(self._protocol, 0, 1)

        # Порог
        top.addWidget(QLabel("Порог, В"), 1, 0)
        self._threshold = DecimalSpinBox()
        self._threshold.setRange(-50.0, 50.0)
        self._threshold.setDecimals(3)
        self._threshold.setValue(1.5)
        self._threshold.setMinimumHeight(24)
        self._threshold.editingFinished.connect(self._emit)
        top.addWidget(self._threshold, 1, 1)
        outer.addLayout(top)

        # Стек параметров по протоколу (Off = пустая страница)
        self._stack = QStackedWidget()
        self._stack.addWidget(QWidget())            # 0: OFF
        self._stack.addWidget(self._build_uart())   # 1: UART
        self._stack.addWidget(self._build_spi())    # 2: SPI
        self._stack.addWidget(self._build_i2c())    # 3: I2C
        outer.addWidget(self._stack)
        outer.addStretch(1)

        self._proto_index = {"OFF": 0, "UART": 1, "SPI": 2, "I2C": 3}

    # ------------------------------------------------------------------
    # Построение секций параметров
    # ------------------------------------------------------------------

    def _build_uart(self) -> QWidget:
        w = QWidget()
        g = QGridLayout(w)
        g.setContentsMargins(0, 0, 0, 0)
        g.setHorizontalSpacing(8)
        g.setVerticalSpacing(6)
        g.addWidget(QLabel("Источник"), 0, 0)
        self._u_source = _channel_combo()
        self._u_source.currentIndexChanged.connect(self._emit)
        g.addWidget(self._u_source, 0, 1)
        g.addWidget(QLabel("Бод"), 1, 0)
        self._u_baud = QComboBox()
        for b in BAUDS:
            self._u_baud.addItem(str(b), b)
        self._u_baud.setCurrentText("9600")
        self._u_baud.currentIndexChanged.connect(self._emit)
        g.addWidget(self._u_baud, 1, 1)
        g.addWidget(QLabel("Бит данных"), 2, 0)
        self._u_bits = QSpinBox()
        self._u_bits.setRange(5, 8)
        self._u_bits.setValue(8)
        self._u_bits.valueChanged.connect(self._emit)
        g.addWidget(self._u_bits, 2, 1)
        g.addWidget(QLabel("Чётность"), 3, 0)
        self._u_parity = SegmentedControl(list(PARITIES))
        self._u_parity.valueChanged.connect(lambda _v: self._emit())
        g.addWidget(self._u_parity, 3, 1)
        g.addWidget(QLabel("Стоп-бит"), 4, 0)
        self._u_stop = QSpinBox()
        self._u_stop.setRange(1, 2)
        self._u_stop.setValue(1)
        self._u_stop.valueChanged.connect(self._emit)
        g.addWidget(self._u_stop, 4, 1)
        self._u_lsb = QCheckBox("LSB-first")
        self._u_lsb.setChecked(True)
        self._u_lsb.toggled.connect(self._emit)
        g.addWidget(self._u_lsb, 5, 0, 1, 2)
        return w

    def _build_spi(self) -> QWidget:
        w = QWidget()
        g = QGridLayout(w)
        g.setContentsMargins(0, 0, 0, 0)
        g.setHorizontalSpacing(8)
        g.setVerticalSpacing(6)
        g.addWidget(QLabel("SCLK"), 0, 0)
        self._s_sclk = _channel_combo()
        self._s_sclk.currentIndexChanged.connect(self._emit)
        g.addWidget(self._s_sclk, 0, 1)
        g.addWidget(QLabel("DATA"), 1, 0)
        self._s_data = _channel_combo()
        self._s_data.setCurrentIndex(1)  # по умолчанию CH2
        self._s_data.currentIndexChanged.connect(self._emit)
        g.addWidget(self._s_data, 1, 1)
        g.addWidget(QLabel("Фронт SCLK"), 2, 0)
        self._s_edge = SegmentedControl(list(CLOCK_EDGES))
        self._s_edge.valueChanged.connect(lambda _v: self._emit())
        g.addWidget(self._s_edge, 2, 1)
        g.addWidget(QLabel("Бит в слове"), 3, 0)
        self._s_bits = QSpinBox()
        self._s_bits.setRange(4, 32)
        self._s_bits.setValue(8)
        self._s_bits.valueChanged.connect(self._emit)
        g.addWidget(self._s_bits, 3, 1)
        self._s_msb = QCheckBox("MSB-first")
        self._s_msb.setChecked(True)
        self._s_msb.toggled.connect(self._emit)
        g.addWidget(self._s_msb, 4, 0, 1, 2)
        return w

    def _build_i2c(self) -> QWidget:
        w = QWidget()
        g = QGridLayout(w)
        g.setContentsMargins(0, 0, 0, 0)
        g.setHorizontalSpacing(8)
        g.setVerticalSpacing(6)
        g.addWidget(QLabel("SDA"), 0, 0)
        self._i_sda = _channel_combo()
        self._i_sda.currentIndexChanged.connect(self._emit)
        g.addWidget(self._i_sda, 0, 1)
        g.addWidget(QLabel("SCL"), 1, 0)
        self._i_scl = _channel_combo()
        self._i_scl.setCurrentIndex(1)  # по умолчанию CH2
        self._i_scl.currentIndexChanged.connect(self._emit)
        g.addWidget(self._i_scl, 1, 1)
        return w

    # ------------------------------------------------------------------
    # Обработчики
    # ------------------------------------------------------------------

    def _on_protocol_changed(self, value: str) -> None:
        self._stack.setCurrentIndex(self._proto_index.get(value, 0))
        self._emit()

    def _emit(self, *_args) -> None:
        self.decodeConfigChanged.emit(self.config())

    # ------------------------------------------------------------------
    # Публичный API
    # ------------------------------------------------------------------

    def config(self) -> dict:
        """Собрать текущий конфиг декодирования (см. docstring класса)."""
        return {
            "protocol": self._protocol.value() or "OFF",
            "threshold": float(self._threshold.value()),
            "uart": {
                "source": int(self._u_source.currentData()),
                "baud": float(self._u_baud.currentData()),
                "bits": int(self._u_bits.value()),
                "parity": self._u_parity.value() or "NONE",
                "stop_bits": int(self._u_stop.value()),
                "lsb_first": bool(self._u_lsb.isChecked()),
            },
            "spi": {
                "sclk": int(self._s_sclk.currentData()),
                "data": int(self._s_data.currentData()),
                "clock_edge": self._s_edge.value() or "Rising",
                "bits": int(self._s_bits.value()),
                "msb_first": bool(self._s_msb.isChecked()),
            },
            "i2c": {
                "sda": int(self._i_sda.currentData()),
                "scl": int(self._i_scl.currentData()),
            },
        }
