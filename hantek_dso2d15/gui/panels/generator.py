"""Панель Generator — встроенный DDS-генератор Hantek DSO2D15.

Контролы: выход ON/OFF, тип волны, частота, амплитуда, смещение, скважность;
подгруппа модуляции (AM/FM); подгруппа Burst.

Изменения уходят сигналом ``settingChanged(path, value)``; путь вида
``"dds.<attr>"``, значение — Python-тип (bool / str / float / int).

Числовые контролы (DecimalSpinBox, QSpinBox) эмитят по ``editingFinished``
(Enter / потеря фокуса), не на каждый вводимый символ.
"""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QLabel, QComboBox,
    QCheckBox, QPushButton, QSpinBox, QGroupBox,
)

from hantek_dso2d15.gui.widgets import DecimalSpinBox
from hantek_dso2d15.gui.waveform_tiles import WaveformPicker


class GeneratorPanel(QWidget):
    """Панель управления встроенным DDS-генератором.

    Сигнал ``settingChanged(path, value)`` — единый для всех панелей.
    Пути:
        "dds.output"        → bool
        "dds.type"          → str  (SCPI-литерал из TYPES)
        "dds.freq"          → float  Гц
        "dds.amplitude"     → float  Vpp
        "dds.offset"        → float  В
        "dds.duty"          → float  %
        "dds.mod_enable"    → bool
        "dds.mod_type"      → str  (AM | FM)
        "dds.mod_wave"      → str  (SINE | SQUAre | RAMP)
        "dds.mod_freq"      → float  Гц
        "dds.mod_depth"     → float  (% для AM; Гц для FM)
        "dds.burst_enable"  → bool
        "dds.burst_type"    → str  (N_CYCLE | INFInit)
        "dds.burst_count"   → int
        "dds.burst_trigger" → True  (action, не persist-настройка)
    """

    settingChanged = Signal(str, object)

    # Frozen-литералы (из docs/scpi-command-reference.md)
    TYPES = ("SINE", "SQUAre", "RAMP", "EXP", "NOISe", "DC", "ARB1", "ARB2", "ARB3", "ARB4")
    MOD_TYPES = ("AM", "FM")
    MOD_WAVES = ("SINE", "SQUAre", "RAMP")
    BURST_TYPES = ("N_CYCLE", "INFInit")

    # Человекочитаемые подписи для типов волны
    _TYPE_LABELS = {
        "SINE":   "Синус",
        "SQUAre": "Прямоугольник",
        "RAMP":   "Пила",
        "EXP":    "Экспонента",
        "NOISe":  "Шум",
        "DC":     "Постоянный",
        "ARB1":   "ARB 1",
        "ARB2":   "ARB 2",
        "ARB3":   "ARB 3",
        "ARB4":   "ARB 4",
    }

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        # ── Основные параметры ──────────────────────────────────────────────
        main_grid = QGridLayout()
        main_grid.setHorizontalSpacing(8)
        main_grid.setVerticalSpacing(6)

        row = 0

        # Выход ON/OFF
        self._output = QCheckBox("Выход ON")
        self._output.toggled.connect(
            lambda b: self.settingChanged.emit("dds.output", bool(b))
        )
        main_grid.addWidget(self._output, row, 0, 1, 2)
        row += 1

        # Тип волны — плитки с глифами форм (полная ширина)
        main_grid.addWidget(QLabel("Тип"), row, 0, 1, 2)
        row += 1
        self._type = WaveformPicker(
            [(v, self._TYPE_LABELS.get(v, v)) for v in self.TYPES], columns=5
        )
        self._type.valueChanged.connect(
            lambda v: self.settingChanged.emit("dds.type", v)
        )
        main_grid.addWidget(self._type, row, 0, 1, 2)
        row += 1

        # Частота
        main_grid.addWidget(QLabel("Частота, Гц"), row, 0)
        self._freq = DecimalSpinBox()
        self._freq.setRange(1.0, 25e6)
        self._freq.setDecimals(3)
        self._freq.editingFinished.connect(
            lambda: self.settingChanged.emit("dds.freq", float(self._freq.value()))
        )
        main_grid.addWidget(self._freq, row, 1)
        row += 1

        # Амплитуда
        main_grid.addWidget(QLabel("Амплитуда, Vpp"), row, 0)
        self._amplitude = DecimalSpinBox()
        self._amplitude.setRange(0.001, 7.0)
        self._amplitude.setDecimals(3)
        self._amplitude.editingFinished.connect(
            lambda: self.settingChanged.emit("dds.amplitude", float(self._amplitude.value()))
        )
        main_grid.addWidget(self._amplitude, row, 1)
        row += 1

        # Смещение
        main_grid.addWidget(QLabel("Смещение, В"), row, 0)
        self._offset = DecimalSpinBox()
        self._offset.setRange(-2.5, 2.5)
        self._offset.setDecimals(3)
        self._offset.editingFinished.connect(
            lambda: self.settingChanged.emit("dds.offset", float(self._offset.value()))
        )
        main_grid.addWidget(self._offset, row, 1)
        row += 1

        # Скважность
        main_grid.addWidget(QLabel("Скважность, %"), row, 0)
        self._duty = DecimalSpinBox()
        self._duty.setRange(0.0, 99.0)
        self._duty.setDecimals(1)
        self._duty.editingFinished.connect(
            lambda: self.settingChanged.emit("dds.duty", float(self._duty.value()))
        )
        main_grid.addWidget(self._duty, row, 1)

        root.addLayout(main_grid)

        # ── Подгруппа: Модуляция ────────────────────────────────────────────
        mod_box = QGroupBox("Модуляция")
        mod_grid = QGridLayout(mod_box)
        mod_grid.setHorizontalSpacing(8)
        mod_grid.setVerticalSpacing(6)

        mrow = 0

        self._mod_enable = QCheckBox("Вкл.")
        self._mod_enable.toggled.connect(
            lambda b: self.settingChanged.emit("dds.mod_enable", bool(b))
        )
        mod_grid.addWidget(self._mod_enable, mrow, 0, 1, 2)
        mrow += 1

        mod_grid.addWidget(QLabel("Тип мод."), mrow, 0)
        self._mod_type = QComboBox()
        for literal in self.MOD_TYPES:
            self._mod_type.addItem(literal, literal)
        self._mod_type.currentIndexChanged.connect(self._on_mod_type_changed)
        mod_grid.addWidget(self._mod_type, mrow, 1)
        mrow += 1

        mod_grid.addWidget(QLabel("Форма"), mrow, 0)
        self._mod_wave = QComboBox()
        for literal in self.MOD_WAVES:
            self._mod_wave.addItem(literal, literal)
        self._mod_wave.currentIndexChanged.connect(self._on_mod_wave_changed)
        mod_grid.addWidget(self._mod_wave, mrow, 1)
        mrow += 1

        mod_grid.addWidget(QLabel("Частота мод., Гц"), mrow, 0)
        self._mod_freq = DecimalSpinBox()
        self._mod_freq.setRange(1.0, 1e6)
        self._mod_freq.setDecimals(3)
        self._mod_freq.editingFinished.connect(
            lambda: self.settingChanged.emit("dds.mod_freq", float(self._mod_freq.value()))
        )
        mod_grid.addWidget(self._mod_freq, mrow, 1)
        mrow += 1

        # Подпись «Глубина, %» / «Девиация, Гц» меняется при смене mod_type
        self._mod_depth_label = QLabel("Глубина, %")
        mod_grid.addWidget(self._mod_depth_label, mrow, 0)
        self._mod_depth = DecimalSpinBox()
        self._mod_depth.setRange(0.0, 1e6)
        self._mod_depth.setDecimals(3)
        self._mod_depth.editingFinished.connect(
            lambda: self.settingChanged.emit("dds.mod_depth", float(self._mod_depth.value()))
        )
        mod_grid.addWidget(self._mod_depth, mrow, 1)

        root.addWidget(mod_box)

        # ── Подгруппа: Burst ────────────────────────────────────────────────
        burst_box = QGroupBox("Пакет (Burst)")
        burst_grid = QGridLayout(burst_box)
        burst_grid.setHorizontalSpacing(8)
        burst_grid.setVerticalSpacing(6)

        brow = 0

        self._burst_enable = QCheckBox("Вкл.")
        self._burst_enable.toggled.connect(
            lambda b: self.settingChanged.emit("dds.burst_enable", bool(b))
        )
        burst_grid.addWidget(self._burst_enable, brow, 0, 1, 2)
        brow += 1

        burst_grid.addWidget(QLabel("Тип"), brow, 0)
        self._burst_type = QComboBox()
        for literal in self.BURST_TYPES:
            self._burst_type.addItem(literal, literal)
        self._burst_type.currentIndexChanged.connect(self._on_burst_type_changed)
        burst_grid.addWidget(self._burst_type, brow, 1)
        brow += 1

        burst_grid.addWidget(QLabel("Число циклов"), brow, 0)
        self._burst_count = QSpinBox()
        self._burst_count.setRange(1, 1_000_000)
        self._burst_count.editingFinished.connect(
            lambda: self.settingChanged.emit("dds.burst_count", int(self._burst_count.value()))
        )
        burst_grid.addWidget(self._burst_count, brow, 1)
        brow += 1

        self._burst_trigger_btn = QPushButton("Запустить пакет")
        self._burst_trigger_btn.clicked.connect(
            lambda: self.settingChanged.emit("dds.burst_trigger", True)
        )
        burst_grid.addWidget(self._burst_trigger_btn, brow, 0, 1, 2)

        root.addWidget(burst_box)
        root.addStretch(1)

        # Список всех виджетов для blockSignals в load_from_scope
        self._all_widgets = [
            self._output, self._type, self._freq, self._amplitude,
            self._offset, self._duty,
            self._mod_enable, self._mod_type, self._mod_wave,
            self._mod_freq, self._mod_depth,
            self._burst_enable, self._burst_type, self._burst_count,
        ]

    # ------------------------------------------------------------------
    # Внутренние обработчики
    # ------------------------------------------------------------------

    def _on_mod_type_changed(self, _index: int) -> None:
        data = self._mod_type.currentData()
        if data is not None:
            self._update_depth_label(str(data))
            self.settingChanged.emit("dds.mod_type", data)

    def _on_mod_wave_changed(self, _index: int) -> None:
        data = self._mod_wave.currentData()
        if data is not None:
            self.settingChanged.emit("dds.mod_wave", data)

    def _on_burst_type_changed(self, _index: int) -> None:
        data = self._burst_type.currentData()
        if data is not None:
            self.settingChanged.emit("dds.burst_type", data)

    def _update_depth_label(self, mod_type: str) -> None:
        """Обновить подпись поля глубины/девиации в зависимости от типа модуляции."""
        if mod_type == "FM":
            self._mod_depth_label.setText("Девиация, Гц")
        else:
            self._mod_depth_label.setText("Глубина, %")

    # ------------------------------------------------------------------
    # Публичный API
    # ------------------------------------------------------------------

    def load_from_scope(self, scope) -> None:
        """Прочитать текущие настройки DDS из scope и выставить контролы.

        Во время загрузки сигналы заблокированы — команды приборам не
        отправляются.
        """
        dds = scope.dds

        for w in self._all_widgets:
            w.blockSignals(True)
        try:
            # Основные
            self._output.setChecked(bool(dds.output))

            self._type.set_value(str(dds.type))

            self._freq.setValue(float(dds.freq))
            self._amplitude.setValue(float(dds.amplitude))
            self._offset.setValue(float(dds.offset))
            self._duty.setValue(float(dds.duty))

            # Модуляция
            self._mod_enable.setChecked(bool(dds.mod_enable))

            idx = self._mod_type.findData(str(dds.mod_type))
            if idx >= 0:
                self._mod_type.setCurrentIndex(idx)

            # Обновляем подпись явно (сигнал заблокирован)
            self._update_depth_label(str(dds.mod_type))

            idx = self._mod_wave.findData(str(dds.mod_wave))
            if idx >= 0:
                self._mod_wave.setCurrentIndex(idx)

            self._mod_freq.setValue(float(dds.mod_freq))
            self._mod_depth.setValue(float(dds.mod_depth))

            # Burst
            self._burst_enable.setChecked(bool(dds.burst_enable))

            idx = self._burst_type.findData(str(dds.burst_type))
            if idx >= 0:
                self._burst_type.setCurrentIndex(idx)

            self._burst_count.setValue(int(dds.burst_count))

        finally:
            for w in self._all_widgets:
                w.blockSignals(False)
