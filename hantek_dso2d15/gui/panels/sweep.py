"""Панель Sweep / Multi-capture.

Позволяет задать параметрический свип (например, по частоте или амплитуде
генератора), установить шаг, выдержку и формат сохранения.

Панель только эмитирует конфиг-словарь на старт — фактическое выполнение
свипа (worker-цикл) — ответственность внешнего компонента (engine).
QFileDialog НЕ открывается внутри панели — вызывается снаружи по сигналу
folderRequested, что позволяет тестировать в headless-режиме offscreen.
"""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QHBoxLayout,
    QLabel, QComboBox, QLineEdit, QPushButton, QProgressBar,
)

from hantek_dso2d15.gui.widgets import DecimalSpinBox

# Параметры, доступные для свипа: (человекочитаемая метка, путь-параметр)
_PARAMETERS = [
    ("Частота генератора",   "dds.freq"),
    ("Амплитуда генератора", "dds.amplitude"),
]

# Форматы сохранения: currentData → строка
_FORMATS = ["CSV", "NPY", "HDF5"]


class SweepPanel(QWidget):
    """Панель Sweep / Multi-capture.

    Сигналы
    -------
    startRequested(object)
        Эмитируется при нажатии «Старт»; payload — dict, совпадающий с
        возвратом :py:meth:`config`.
    stopRequested()
        Эмитируется при нажатии «Стоп».
    folderRequested()
        Эмитируется при нажатии кнопки «…» выбора папки. Диалог открывает
        внешний код; затем вызывает :py:meth:`set_folder`.
    """

    startRequested = Signal(object)
    stopRequested = Signal()
    folderRequested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        # ── Заголовок ──────────────────────────────────────────────────────
        title = QLabel("SWEEP / MULTI-CAPTURE")
        root.addWidget(title)

        # ── Основная сетка параметров ──────────────────────────────────────
        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(6)

        row = 0

        # Параметр
        grid.addWidget(QLabel("Параметр"), row, 0)
        self._parameter = QComboBox()
        for label, path in _PARAMETERS:
            self._parameter.addItem(label, path)
        grid.addWidget(self._parameter, row, 1)
        row += 1

        # Start
        grid.addWidget(QLabel("Начало"), row, 0)
        self._start = DecimalSpinBox()
        self._start.setRange(0.0, 1e9)
        self._start.setDecimals(3)
        grid.addWidget(self._start, row, 1)
        row += 1

        # Stop
        grid.addWidget(QLabel("Конец"), row, 0)
        self._stop = DecimalSpinBox()
        self._stop.setRange(0.0, 1e9)
        self._stop.setDecimals(3)
        self._stop.setValue(1000.0)
        grid.addWidget(self._stop, row, 1)
        row += 1

        # Step
        grid.addWidget(QLabel("Шаг"), row, 0)
        self._step = DecimalSpinBox()
        self._step.setRange(0.0, 1e9)
        self._step.setDecimals(3)
        self._step.setValue(100.0)
        grid.addWidget(self._step, row, 1)
        row += 1

        # Dwell (мс)
        grid.addWidget(QLabel("Выдержка, мс"), row, 0)
        self._dwell_ms = DecimalSpinBox()
        self._dwell_ms.setRange(0.0, 600_000.0)
        self._dwell_ms.setDecimals(1)
        self._dwell_ms.setValue(200.0)
        grid.addWidget(self._dwell_ms, row, 1)
        row += 1

        # Формат
        grid.addWidget(QLabel("Формат"), row, 0)
        self._fmt = QComboBox()
        for fmt in _FORMATS:
            self._fmt.addItem(fmt, fmt)
        # Дефолт — CSV (первый пункт, уже выбран)
        grid.addWidget(self._fmt, row, 1)
        row += 1

        root.addLayout(grid)

        # ── Папка вывода ───────────────────────────────────────────────────
        folder_layout = QHBoxLayout()
        folder_layout.setSpacing(4)
        self._folder_edit = QLineEdit()
        self._folder_edit.setPlaceholderText("Папка для сохранения...")
        folder_layout.addWidget(self._folder_edit)
        self._btn_folder = QPushButton("…")
        self._btn_folder.setFixedWidth(32)
        self._btn_folder.clicked.connect(self.folderRequested)
        folder_layout.addWidget(self._btn_folder)
        root.addLayout(folder_layout)

        # ── Прогресс ───────────────────────────────────────────────────────
        self._progress_label = QLabel("Прогресс 0 / 0")
        root.addWidget(self._progress_label)

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        root.addWidget(self._progress_bar)

        # ── Кнопки Старт / Стоп ────────────────────────────────────────────
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self._btn_start = QPushButton("Старт")
        self._btn_start.clicked.connect(self._on_start_clicked)
        btn_layout.addWidget(self._btn_start)

        self._btn_stop = QPushButton("Стоп")
        self._btn_stop.setEnabled(False)
        self._btn_stop.clicked.connect(self.stopRequested)
        btn_layout.addWidget(self._btn_stop)

        root.addLayout(btn_layout)
        root.addStretch(1)

        # Список контролов конфигурации (блокируются при set_running(True))
        self._config_widgets = [
            self._parameter,
            self._start,
            self._stop,
            self._step,
            self._dwell_ms,
            self._fmt,
        ]

    # ------------------------------------------------------------------
    # Внутренние обработчики
    # ------------------------------------------------------------------

    def _on_start_clicked(self) -> None:
        self.startRequested.emit(self.config())

    # ------------------------------------------------------------------
    # Публичный API
    # ------------------------------------------------------------------

    def config(self) -> dict:
        """Собрать текущий конфиг свипа из контролов.

        Returns
        -------
        dict
            Ключи: ``parameter`` (str-путь), ``start`` (float),
            ``stop`` (float), ``step`` (float),
            ``dwell_s`` (float, = dwell_ms / 1000),
            ``fmt`` (str), ``folder`` (str).
        """
        return {
            "parameter": str(self._parameter.currentData()),
            "start":     float(self._start.value()),
            "stop":      float(self._stop.value()),
            "step":      float(self._step.value()),
            "dwell_s":   float(self._dwell_ms.value()) / 1000.0,
            "fmt":       str(self._fmt.currentData()),
            "folder":    self._folder_edit.text(),
        }

    def set_folder(self, path: str) -> None:
        """Выставить текст поля папки (без эмиссии сигналов)."""
        self._folder_edit.blockSignals(True)
        try:
            self._folder_edit.setText(path)
        finally:
            self._folder_edit.blockSignals(False)

    def set_progress(self, done: int, total: int) -> None:
        """Обновить прогресс-бар и лейбл.

        Parameters
        ----------
        done:
            Количество выполненных точек.
        total:
            Общее количество точек. При total == 0 бар устанавливается в 0.
        """
        if total > 0:
            value = int(round(done / total * 100))
        else:
            value = 0
        self._progress_bar.setValue(value)
        self._progress_label.setText(f"Прогресс {done} / {total}")

    def set_running(self, running: bool) -> None:
        """Переключить состояние панели: свип запущен / остановлен.

        При ``running=True``: «Старт» и контролы конфигурации disabled,
        «Стоп» enabled.  При ``running=False`` — наоборот.
        """
        self._btn_start.setEnabled(not running)
        self._btn_stop.setEnabled(running)
        for w in self._config_widgets:
            w.setEnabled(not running)
