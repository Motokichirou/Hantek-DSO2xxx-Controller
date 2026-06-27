"""Панель Math — настройки математики осциллограмм.

Вычисляет math-трассу клиентски из наших сэмпл-буферов.

Поддерживаемые операторы (frozen SCPI-reference §6):
  Алгебра : ADD / SUBtract / MULTiply / DIVision
  Спектр  : FFT

Контролы:
  display    — QCheckBox «Включить»
  operator   — QComboBox  ADD / SUBtract / MULTiply / DIVision / FFT
  source1    — QComboBox  CH1 / CH2  (алгебра, источник A)
  source2    — QComboBox  CH1 / CH2  (алгебра, источник B)
  scale      — DecimalSpinBox  В/дел  (используется рендером, не compute_math)
  offset     — DecimalSpinBox  В      (используется рендером, не compute_math)
  fft_source — QComboBox  CH1 / CH2
  fft_window — QComboBox  RECTangle / HANNing / HAMMing / BLACkman / TRIangle / FLATtop
  fft_unit   — QComboBox  VRMS / DB

Сигнал ``mathConfigChanged(dict)`` несёт полный снапшот config() при любом
изменении.  Рендер math-трассы подключается к этому сигналу и вызывает
compute_math() сам.
"""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGridLayout,
    QLabel,
    QWidget,
)

from hantek_dso2d15.gui.widgets import DecimalSpinBox

# Допустимые значения (frozen SCPI-reference §6 — не менять без hardware-verify)
_OPERATORS = ["ADD", "SUBtract", "MULTiply", "DIVision", "FFT"]
_SOURCES = [(1, "CH1"), (2, "CH2")]
_FFT_WINDOWS = ["RECTangle", "HANNing", "HAMMing", "BLACkman", "TRIangle", "FLATtop"]
_FFT_UNITS = ["VRMS", "DB"]


class MathPanel(QWidget):
    """Панель настроек математики осциллограмм.

    Сигнал ``mathConfigChanged(object)`` эмитируется при любом изменении
    контролов; аргумент — полный dict из ``config()``.

    Инициализируется с дефолтами без эмиссии:
        display=False, operator="ADD", source1=1, source2=2,
        scale=1.0, offset=0.0, fft_source=1, fft_window="HANNing", fft_unit="VRMS"
    """

    mathConfigChanged = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)

        lay = QGridLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setHorizontalSpacing(8)
        lay.setVerticalSpacing(6)

        # --- Включить ---
        self._display = QCheckBox("Включить")
        lay.addWidget(self._display, 0, 0, 1, 2)

        # --- Оператор ---
        lay.addWidget(QLabel("Оператор"), 1, 0)
        self._operator = QComboBox()
        for op in _OPERATORS:
            self._operator.addItem(op, op)
        lay.addWidget(self._operator, 1, 1)

        # --- Источник 1 (алгебра) ---
        lay.addWidget(QLabel("Источник 1"), 2, 0)
        self._source1 = QComboBox()
        for ch, label in _SOURCES:
            self._source1.addItem(label, ch)
        lay.addWidget(self._source1, 2, 1)

        # --- Источник 2 (алгебра) ---
        lay.addWidget(QLabel("Источник 2"), 3, 0)
        self._source2 = QComboBox()
        for ch, label in _SOURCES:
            self._source2.addItem(label, ch)
        lay.addWidget(self._source2, 3, 1)

        # --- Масштаб В/дел ---
        lay.addWidget(QLabel("Масштаб, В/дел"), 4, 0)
        self._scale = DecimalSpinBox()
        self._scale.setRange(0.001, 1000.0)
        self._scale.setSingleStep(0.1)
        lay.addWidget(self._scale, 4, 1)

        # --- Смещение ---
        lay.addWidget(QLabel("Смещение, В"), 5, 0)
        self._offset = DecimalSpinBox()
        self._offset.setRange(-1000.0, 1000.0)
        self._offset.setSingleStep(0.1)
        lay.addWidget(self._offset, 5, 1)

        # --- FFT: источник ---
        lay.addWidget(QLabel("FFT источник"), 6, 0)
        self._fft_source = QComboBox()
        for ch, label in _SOURCES:
            self._fft_source.addItem(label, ch)
        lay.addWidget(self._fft_source, 6, 1)

        # --- FFT: окно ---
        lay.addWidget(QLabel("FFT окно"), 7, 0)
        self._fft_window = QComboBox()
        for w in _FFT_WINDOWS:
            self._fft_window.addItem(w, w)
        lay.addWidget(self._fft_window, 7, 1)

        # --- FFT: единица ---
        lay.addWidget(QLabel("FFT единица"), 8, 0)
        self._fft_unit = QComboBox()
        for u in _FFT_UNITS:
            self._fft_unit.addItem(u, u)
        lay.addWidget(self._fft_unit, 8, 1)

        # --- Установить дефолты ДО подключения сигналов ---
        # display: QCheckBox unchecked по умолчанию (display=False) — OK
        # operator: index 0 = "ADD"  — OK
        # source1:  index 0 = CH1    — OK
        # source2:  index 1 = CH2    — нужно явно выставить
        self._source2.setCurrentIndex(1)
        # scale: setValue вызывать здесь, чтобы было точно 1.0 (конструктор даёт 0.0)
        self._scale.setValue(1.0)
        # offset: 0.0 по умолчанию — OK
        # fft_source: index 0 = CH1  — OK
        # fft_window: index 1 = HANNing — нужно явно выставить
        self._fft_window.setCurrentIndex(1)
        # fft_unit: index 0 = VRMS   — OK

        # --- Подключить сигналы ПОСЛЕ установки дефолтов ---
        self._display.toggled.connect(self._emit)
        self._operator.currentIndexChanged.connect(self._emit)
        self._source1.currentIndexChanged.connect(self._emit)
        self._source2.currentIndexChanged.connect(self._emit)
        self._scale.valueChanged.connect(self._emit)
        self._offset.valueChanged.connect(self._emit)
        self._fft_source.currentIndexChanged.connect(self._emit)
        self._fft_window.currentIndexChanged.connect(self._emit)
        self._fft_unit.currentIndexChanged.connect(self._emit)

    # ------------------------------------------------------------------
    # Внутренний обработчик
    # ------------------------------------------------------------------

    def _emit(self, *_args) -> None:
        """Эмитировать mathConfigChanged с текущим снапшотом конфига."""
        self.mathConfigChanged.emit(self.config())

    # ------------------------------------------------------------------
    # Публичный API
    # ------------------------------------------------------------------

    def config(self) -> dict:
        """Вернуть полный снапшот конфигурации Math-панели.

        Returns
        -------
        dict
            Все ключи контракта::

                display, operator, source1, source2, scale, offset,
                fft_source, fft_window, fft_unit
        """
        return {
            "display":    self._display.isChecked(),
            "operator":   self._operator.currentData(),
            "source1":    self._source1.currentData(),
            "source2":    self._source2.currentData(),
            "scale":      float(self._scale.value()),
            "offset":     float(self._offset.value()),
            "fft_source": self._fft_source.currentData(),
            "fft_window": self._fft_window.currentData(),
            "fft_unit":   self._fft_unit.currentData(),
        }
