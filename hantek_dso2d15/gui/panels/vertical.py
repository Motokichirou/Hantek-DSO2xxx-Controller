"""Панель Vertical — поканальные вертикальные настройки (CH1, CH2).

Контролы: ON/OFF, V/дел, смещение, связь (coupling), щуп (probe), BW-limit, инверсия.
Изменения уходят сигналом ``channelChanged(n, attr, value)`` — главное окно
маршрутизирует их в поток воркера (весь VISA-I/O в одном потоке).
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QComboBox,
    QCheckBox, QFrame,
)

from hantek_dso2d15.gui.widgets import DecimalSpinBox
from hantek_dso2d15.gui.theme import CH_COLORS, rgba
from hantek_dso2d15.gui.segmented import SegmentedControl

# Стандартная последовательность V/дел (1-2-5), В
VDIV_VALUES = [
    1e-3, 2e-3, 5e-3, 1e-2, 2e-2, 5e-2,
    0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 10.0,
]
PROBE_VALUES = [1, 10, 100, 1000]
COUPLINGS = ["DC", "AC", "GND"]


def _vdiv_label(v: float) -> str:
    return f"{v * 1000:g} mV/дел" if v < 1.0 else f"{v:g} V/дел"


class _ChannelCard(QFrame):
    """Карточка одного канала."""

    changed = Signal(int, str, object)  # n, attr, value

    def __init__(self, n: int, parent=None):
        super().__init__(parent)
        self._n = n
        color = CH_COLORS.get(n, "#C5C9D1")
        self.setObjectName(f"chcard{n}")
        self.setStyleSheet(
            f"#chcard{n} {{ border: 1px solid {rgba(color, 0.35)}; border-radius: 6px; "
            f"background: {rgba(color, 0.07)}; }}"
            f"QLabel {{ color: #9AA0AC; }}"
        )
        lay = QGridLayout(self)
        lay.setContentsMargins(8, 6, 8, 8)
        lay.setHorizontalSpacing(8)
        lay.setVerticalSpacing(5)

        # заголовок: имя канала + ON/OFF
        head = QHBoxLayout()
        title = QLabel(f"CH{n}")
        title.setStyleSheet(f"color: {color}; font-weight: 700; font-size: 13px;")
        head.addWidget(title)
        head.addStretch(1)
        self._on = QCheckBox("ON")
        self._on.toggled.connect(lambda b: self.changed.emit(self._n, "display", bool(b)))
        head.addWidget(self._on)
        lay.addLayout(head, 0, 0, 1, 2)

        # V/дел (значения масштабируются коэффициентом щупа)
        lay.addWidget(QLabel("Масштаб"), 1, 0)
        self._probe_factor = 1
        self._scale = QComboBox()
        self._scale.currentIndexChanged.connect(
            lambda _i: self._scale.currentData() is not None
            and self.changed.emit(self._n, "scale", float(self._scale.currentData()))
        )
        self._rebuild_scale(1)
        lay.addWidget(self._scale, 1, 1)

        # смещение (применяется по Enter / снятии фокуса, не на каждый ввод)
        lay.addWidget(QLabel("Смещение, В"), 2, 0)
        self._offset = DecimalSpinBox()
        self._offset.setRange(-50.0, 50.0)
        self._offset.setDecimals(3)
        self._offset.setMinimumHeight(24)  # чтобы стрелки ↑↓ были кликабельны
        self._offset.editingFinished.connect(
            lambda: self.changed.emit(self._n, "offset", float(self._offset.value()))
        )
        lay.addWidget(self._offset, 2, 1)

        # связь (segmented DC/AC/GND, акцент — цвет канала)
        lay.addWidget(QLabel("Связь"), 3, 0)
        self._coupling = SegmentedControl(list(COUPLINGS), accent=color)
        self._coupling.valueChanged.connect(
            lambda s: self.changed.emit(self._n, "coupling", s)
        )
        lay.addWidget(self._coupling, 3, 1)

        # щуп
        lay.addWidget(QLabel("Щуп"), 4, 0)
        self._probe = QComboBox()
        for p in PROBE_VALUES:
            self._probe.addItem(f"{p}×", p)
        self._probe.currentIndexChanged.connect(
            lambda _i: self.changed.emit(self._n, "probe", int(self._probe.currentData()))
        )
        lay.addWidget(self._probe, 4, 1)

        # BW-limit / инверсия
        flags = QHBoxLayout()
        self._bw = QCheckBox("BW 20M")
        self._bw.toggled.connect(lambda b: self.changed.emit(self._n, "bwlimit", bool(b)))
        self._inv = QCheckBox("Инв.")
        self._inv.toggled.connect(lambda b: self.changed.emit(self._n, "invert", bool(b)))
        flags.addWidget(self._bw)
        flags.addWidget(self._inv)
        flags.addStretch(1)
        lay.addLayout(flags, 5, 0, 1, 2)

        self._widgets = [self._on, self._scale, self._offset, self._coupling,
                         self._probe, self._bw, self._inv]

    def _rebuild_scale(self, probe: int, select_scale: float | None = None) -> None:
        """Перестроить список V/дел под коэффициент щупа; выбрать ближайший к select_scale."""
        self._probe_factor = probe
        blocked = self._scale.blockSignals(True)
        try:
            self._scale.clear()
            for v in VDIV_VALUES:
                sv = v * probe
                self._scale.addItem(_vdiv_label(sv), sv)
            if select_scale is not None:
                values = [v * probe for v in VDIV_VALUES]
                self._set_combo_data(self._scale, _closest(values, float(select_scale)))
        finally:
            self._scale.blockSignals(blocked)

    def _apply_offset_step(self, vdiv: float) -> None:
        """Шаг смещения = V/дел ÷ 25 (= вольт/отсчёт прибора)."""
        self._offset.setSingleStep(max(float(vdiv) / 25.0, 0.001))

    def load(self, scope) -> None:
        """Заполнить контролы текущими значениями канала (сигналы заблокированы)."""
        ch = scope.channel[self._n]
        for w in self._widgets:
            w.blockSignals(True)
        try:
            self._on.setChecked(bool(ch.display))
            probe = int(ch.probe)
            self._set_combo_data(self._probe, probe)
            self._rebuild_scale(probe, float(ch.scale))
            self._apply_offset_step(float(ch.scale))
            self._offset.setValue(float(ch.offset))
            self._coupling.set_value(str(ch.coupling))
            self._bw.setChecked(bool(ch.bwlimit))
            self._inv.setChecked(bool(ch.invert))
        finally:
            for w in self._widgets:
                w.blockSignals(False)

    def update_readback(self, scale: float, offset: float, probe: int) -> None:
        """Синхронизировать контролы с фактическими значениями прибора (после изменения)."""
        for w in self._widgets:
            w.blockSignals(True)
        try:
            self._set_combo_data(self._probe, int(probe))
            self._rebuild_scale(int(probe), float(scale))
            self._apply_offset_step(float(scale))
            self._offset.setValue(float(offset))
        finally:
            for w in self._widgets:
                w.blockSignals(False)

    @staticmethod
    def _set_combo_data(combo: QComboBox, data) -> None:
        idx = combo.findData(data)
        if idx >= 0:
            combo.setCurrentIndex(idx)


def _closest(values, target):
    return min(values, key=lambda v: abs(v - target))


class VerticalPanel(QWidget):
    """Панель Vertical: карточки каналов CH1/CH2.

    Сигнал ``settingChanged(path, value)`` — единый для всех панелей; путь вида
    ``"channel.<n>.<attr>"`` (напр. ``"channel.1.scale"``).
    """

    settingChanged = Signal(str, object)

    def __init__(self, channels=(1, 2), parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(8)
        self._cards: dict[int, _ChannelCard] = {}
        for n in channels:
            card = _ChannelCard(n)
            card.changed.connect(
                lambda ch, attr, val: self.settingChanged.emit(f"channel.{ch}.{attr}", val)
            )
            self._cards[n] = card
            lay.addWidget(card)
        lay.addStretch(1)

    def load_from_scope(self, scope) -> None:
        for card in self._cards.values():
            card.load(scope)

    def update_readback(self, n: int, scale: float, offset: float, probe: int) -> None:
        """Обновить карточку канала фактическими значениями прибора."""
        card = self._cards.get(n)
        if card is not None:
            card.update_readback(scale, offset, probe)
