"""Панель Measure — автоизмерения DSO2D15.

Пользователь выбирает канал (CH1/CH2) из Source-выпадашки, затем добавляет
измерения через сгруппированное меню. Таблица отображает тип, источник в цвете
канала и живое значение. Любое изменение набора строк эмитирует
``measurementsChanged(list[tuple[int, str]])``.

MATH-источник добавляется вместе с math-панелью; в Source пока только CH1/CH2.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QHBoxLayout,
    QMenu,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

# Цветокод каналов (совпадает с vertical.py и plot_widget)
CH_COLORS: dict[int, str] = {1: "#F2C300", 2: "#3FE03F"}

# Группы измерений со SCPI-элементами (frozen, из docs/scpi-command-reference.md)
GROUPS: dict[str, list[str]] = {
    "Voltage": [
        "VMAX", "VMIN", "VPP", "VTOP", "VBASe", "VAMP", "VAVG", "VRMS",
        "OVERshoot", "PREShoot", "VUPper", "VMID", "VLOWer", "VARIance",
        "PVRMS", "MARea", "MPARea",
    ],
    "Time": [
        "PERiod", "FREQuency", "RTIMe", "FTIMe", "PWIDth", "NWIDth",
        "PDUTy", "NDUTy", "RDELay", "FDELay", "RPHase", "FPHase",
        "TVMAX", "TVMIN", "PSLEWrate", "NSLEWrate",
    ],
    "Count": ["PPULses", "NPULses", "PEDGes", "NEDGes"],
}

# Человекочитаемые метки для отображения в таблице
LABELS: dict[str, str] = {
    "VMAX": "Vmax",         "VMIN": "Vmin",         "VPP": "Vpp",
    "VTOP": "Vtop",         "VBASe": "Vbase",        "VAMP": "Vamp",
    "VAVG": "Vavg",         "VRMS": "Vrms",          "OVERshoot": "Overshoot",
    "PREShoot": "Preshoot", "VUPper": "Vupper",      "VMID": "Vmid",
    "VLOWer": "Vlower",     "VARIance": "Variance",  "PVRMS": "Period Vrms",
    "MARea": "Area",        "MPARea": "Period Area",
    "PERiod": "Period",     "FREQuency": "Freq",
    "RTIMe": "Rise",        "FTIMe": "Fall",
    "PWIDth": "+Width",     "NWIDth": "-Width",
    "PDUTy": "+Duty",       "NDUTy": "-Duty",
    "RDELay": "Rise Delay", "FDELay": "Fall Delay",
    "RPHase": "Rise Phase", "FPHase": "Fall Phase",
    "TVMAX": "Time@Vmax",   "TVMIN": "Time@Vmin",
    "PSLEWrate": "+SlewRate", "NSLEWrate": "-SlewRate",
    "PPULses": "+Pulses",   "NPULses": "-Pulses",
    "PEDGes": "+Edges",     "NEDGes": "-Edges",
}

# Маппинг SCPI source-строки → номер канала
_SOURCE_TO_CH: dict[str, int] = {"CHANnel1": 1, "CHANnel2": 2}

# Наборы для определения единицы измерения
_VOLTAGE_ITEMS: frozenset[str] = frozenset(GROUPS["Voltage"])
_TIME_ITEMS: frozenset[str] = frozenset(GROUPS["Time"])
_COUNT_ITEMS: frozenset[str] = frozenset(GROUPS["Count"])
_DUTY_ITEMS: frozenset[str] = frozenset({"PDUTy", "NDUTy"})
_PHASE_ITEMS: frozenset[str] = frozenset({"RPHase", "FPHase"})


# ---------------------------------------------------------------------------
# Вспомогательные функции форматирования
# ---------------------------------------------------------------------------

def _si_prefix(value: float, unit: str) -> str:
    """Форматировать число с SI-префиксом и единицей (ASCII-префиксы)."""
    if value == 0.0:
        return f"0 {unit}"
    abs_v = abs(value)
    if abs_v >= 1e9:
        return f"{value / 1e9:.4g} G{unit}"
    if abs_v >= 1e6:
        return f"{value / 1e6:.4g} M{unit}"
    if abs_v >= 1e3:
        return f"{value / 1e3:.4g} k{unit}"
    if abs_v >= 1.0:
        return f"{value:.4g} {unit}"
    if abs_v >= 1e-3:
        return f"{value * 1e3:.4g} m{unit}"
    if abs_v >= 1e-6:
        return f"{value * 1e6:.4g} µ{unit}"
    if abs_v >= 1e-9:
        return f"{value * 1e9:.4g} n{unit}"
    return f"{value:.4g} {unit}"


def _fmt_value(item: str, value: float) -> str:
    """Форматировать числовое значение по типу SCPI-измерения.

    Правила:
      PDUTy / NDUTy           → % (скважность)
      RPHase / FPHase         → ° (фаза)
      Voltage-группа          → В с SI-префиксом
      FREQuency               → Гц с SI-префиксом
      Count-группа (PPULses…) → целое без единицы
      остальное (Time-группа) → с с SI-префиксом
    """
    if item in _DUTY_ITEMS:
        return f"{value:.2f}%"
    if item in _PHASE_ITEMS:
        return f"{value:.2f}°"   # °
    if item in _VOLTAGE_ITEMS:
        return _si_prefix(value, "В")   # В
    if item == "FREQuency":
        return _si_prefix(value, "Гц")  # Гц
    if item in _COUNT_ITEMS:
        return f"{value:g}"
    # Всё остальное (Time-группа, PSLEWrate и т.д.) — секунды
    return _si_prefix(value, "с")   # с


# ---------------------------------------------------------------------------
# MeasurePanel
# ---------------------------------------------------------------------------

class MeasurePanel(QWidget):
    """Панель автоизмерений DSO2D15.

    Сигнал:
        measurementsChanged(object) — payload: list[tuple[int, str]]
            список (channel, item) в порядке таблицы; эмитируется при любом
            изменении набора строк (добавление / удаление).
            НЕ эмитируется из load_from_scope или update_values.
    """

    measurementsChanged = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)

        # Внутренний список активных строк в порядке таблицы
        self._rows: list[tuple[int, str]] = []

        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(6)

        # ---- Заголовок: Source-выпадашка + кнопка «+ Добавить» ------------
        header = QHBoxLayout()
        header.setSpacing(6)

        from PySide6.QtWidgets import QComboBox  # локальный импорт для наглядности
        self._source_combo = QComboBox()
        # MATH-источник добавляется вместе с math-панелью; пока только CH1/CH2.
        self._source_combo.addItem("CH1", 1)
        self._source_combo.addItem("CH2", 2)
        self._source_combo.setToolTip(
            "Канал для добавляемых измерений (MATH — добавляется с math-панелью)"
        )
        self._source_combo.currentIndexChanged.connect(self._update_source_color)
        header.addWidget(self._source_combo)

        self._add_btn = QPushButton("+ Добавить измерение")
        self._add_btn.clicked.connect(self._show_add_menu)
        header.addWidget(self._add_btn, stretch=1)

        lay.addLayout(header)

        # ---- Таблица: Тип | Источник | Значение | [✕] ----------------------
        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(["Тип", "Источник", "Значение", ""])
        hh = self._table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(3, 28)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self._table.verticalHeader().setVisible(False)
        lay.addWidget(self._table)

        # Начальный цвет Source
        self._update_source_color()

    # ------------------------------------------------------------------
    # Внутренние обработчики
    # ------------------------------------------------------------------

    def _update_source_color(self) -> None:
        """Подкрасить Source-выпадашку цветом текущего канала."""
        channel = self._source_combo.currentData()
        color = CH_COLORS.get(channel, "#C5C9D1")
        self._source_combo.setStyleSheet(f"color: {color};")

    def _show_add_menu(self) -> None:
        """Показать сгруппированное меню выбора измерения и добавить выбранное."""
        channel = self._source_combo.currentData()
        if channel is None:
            return

        menu = QMenu(self)
        for group_name, items in GROUPS.items():
            sub = menu.addMenu(group_name)
            for item in items:
                action = sub.addAction(LABELS.get(item, item))
                action.setData((channel, item))

        triggered = menu.exec(
            self._add_btn.mapToGlobal(self._add_btn.rect().bottomLeft())
        )
        if triggered is not None:
            ch, it = triggered.data()
            self._add_row(ch, it)

    # ------------------------------------------------------------------
    # Управление строками
    # ------------------------------------------------------------------

    def _add_row(self, channel: int, item: str) -> None:
        """Добавить строку (channel, item) если ещё нет дубликата.

        Дубликат (тот же channel + item) игнорируется без эмиссии сигнала.
        При успешном добавлении эмитирует measurementsChanged.
        """
        if (channel, item) in self._rows:
            return

        row_idx = self._table.rowCount()
        self._rows.append((channel, item))
        self._table.insertRow(row_idx)

        # Колонка 0: тип (человекочитаемый ярлык)
        type_cell = QTableWidgetItem(LABELS.get(item, item))
        type_cell.setFlags(Qt.ItemFlag.ItemIsEnabled)
        self._table.setItem(row_idx, 0, type_cell)

        # Колонка 1: источник (метка канала, в цвете канала)
        color = CH_COLORS.get(channel, "#C5C9D1")
        src_cell = QTableWidgetItem(f"CH{channel}")
        src_cell.setForeground(QColor(color))
        src_cell.setFlags(Qt.ItemFlag.ItemIsEnabled)
        self._table.setItem(row_idx, 1, src_cell)

        # Колонка 2: значение (моноширинный, изначально "—")
        val_cell = QTableWidgetItem("—")   # —
        val_cell.setFlags(Qt.ItemFlag.ItemIsEnabled)
        mono = QFont("Courier New")
        mono.setPointSize(9)
        val_cell.setFont(mono)
        self._table.setItem(row_idx, 2, val_cell)

        # Колонка 3: кнопка удаления ✕
        # Захватываем (channel, item), а не row_idx, чтобы не устаревало после удалений
        btn = QPushButton("✕")   # ✕
        btn.setFixedSize(24, 22)
        btn.clicked.connect(
            lambda _checked, ch=channel, it=item: self._remove_row_by_pair(ch, it)
        )
        self._table.setCellWidget(row_idx, 3, btn)

        self.measurementsChanged.emit(list(self._rows))

    def _remove_row_by_pair(self, channel: int, item: str) -> None:
        """Найти строку по (channel, item) и удалить её.

        Если пара не найдена — молча ничего не делает (защита от гонок).
        """
        try:
            idx = self._rows.index((channel, item))
        except ValueError:
            return
        self._remove_row(idx)

    def _remove_row(self, index: int) -> None:
        """Удалить строку по индексу и эмитировать measurementsChanged."""
        self._rows.pop(index)
        self._table.removeRow(index)
        self.measurementsChanged.emit(list(self._rows))

    # ------------------------------------------------------------------
    # Публичный API
    # ------------------------------------------------------------------

    def load_from_scope(self, scope) -> None:
        """Прочитать scope.measure.source и выставить Source-выпадашку.

        Сигналы заблокированы во время загрузки —
        measurementsChanged НЕ эмитируется.
        """
        source_str = str(scope.measure.source)
        channel = _SOURCE_TO_CH.get(source_str, 1)

        self._source_combo.blockSignals(True)
        try:
            idx = self._source_combo.findData(channel)
            if idx >= 0:
                self._source_combo.setCurrentIndex(idx)
        finally:
            self._source_combo.blockSignals(False)

    def update_values(self, payload) -> None:
        """Обновить колонку Value по payload.

        payload — list[dict]:
            {"channel": int, "item": str, "value": float | None}

        Строки без совпадения в таблице игнорируются мягко.
        value=None (или отсутствующий ключ) → "—".
        Этот метод НЕ эмитирует measurementsChanged.
        """
        # Построить lookup по (channel, item) → value
        lookup: dict[tuple[int, str], float | None] = {}
        for entry in payload:
            try:
                ch = int(entry["channel"])
                it = str(entry["item"])
                val = entry.get("value")
                lookup[(ch, it)] = val
            except (KeyError, TypeError, ValueError):
                continue

        for row_idx, (channel, item) in enumerate(self._rows):
            key = (channel, item)
            if key not in lookup:
                continue
            val = lookup[key]
            cell = self._table.item(row_idx, 2)
            if cell is None:
                continue
            if val is None:
                cell.setText("—")   # —
            else:
                try:
                    cell.setText(_fmt_value(item, float(val)))
                except (TypeError, ValueError):
                    cell.setText("—")
