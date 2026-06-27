"""MainWindow — минимальное главное окно клиента DSO2D15.

Тулбар (connection + RUN/STOP/SINGLE), центральный график, статус-бар.
Сбор данных в фоновом QThread (EngineWorker); кадры приходят сигналом
frameReady и рисуются на графике. VISA-I/O не блокирует UI-поток.
"""
from __future__ import annotations

import os
from datetime import datetime

from PySide6.QtCore import Qt, QThread, QMetaObject, QElapsedTimer, Slot, Signal
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QToolBar, QComboBox, QPushButton, QLabel, QSizePolicy,
    QDockWidget, QTabWidget, QScrollArea, QVBoxLayout, QFileDialog, QMenu, QSplitter,
)

from hantek_dso2d15.transport.visa_transport import VisaTransport
from hantek_dso2d15.transport.scpi_log import ScpiLogger
from hantek_dso2d15.io.export import export_frame
from hantek_dso2d15.io.presets import load_preset, SnapshotScope
from hantek_dso2d15.scpi.scope import Scope
from hantek_dso2d15.waveform.reader import WaveformReader
from hantek_dso2d15.engine.controller import AcquisitionController
from hantek_dso2d15.engine.worker import EngineWorker
from hantek_dso2d15.engine.states import RunState
from hantek_dso2d15.gui.plot_widget import ScopePlot
from hantek_dso2d15.gui.panels.vertical import VerticalPanel
from hantek_dso2d15.gui.panels.horizontal import HorizontalPanel
from hantek_dso2d15.gui.panels.trigger import TriggerPanel
from hantek_dso2d15.gui.panels.acquire import AcquirePanel
from hantek_dso2d15.gui.panels.measure import MeasurePanel
from hantek_dso2d15.gui.panels.math import MathPanel
from hantek_dso2d15.gui.panels.cursors import CursorsPanel
from hantek_dso2d15.gui.panels.display import DisplayPanel
from hantek_dso2d15.gui.panels.generator import GeneratorPanel
from hantek_dso2d15.gui.panels.sweep import SweepPanel
from hantek_dso2d15.gui.scpi_terminal import ScpiTerminal
from hantek_dso2d15.gui.accordion import CollapsibleSection
from hantek_dso2d15.measure_stats import MeasurementStats
from hantek_dso2d15.gui.theme import STYLESHEET


def _html_escape(s: str) -> str:
    """Экранировать спецсимволы HTML (пробелы сохраняет <pre>)."""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class MainWindow(QMainWindow):
    # запросы пресета в поток воркера (Qt маршалит str/dict)
    _sigSavePreset = Signal(str)
    _sigApplyPreset = Signal(object)
    #: универсальная отправка настройки в поток воркера (напр. drag уровня триггера)
    _sigApplySetting = Signal(str, object)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Hantek DSO2D15")
        self.resize(1280, 720)
        self.setStyleSheet(STYLESHEET)

        # --- движок/соединение ---
        self._transport = None
        self._scope = None
        self._controller = None
        self._worker = None
        self._thread = None
        self._fps_timer = QElapsedTimer()
        self._frame_count = 0
        self._last_frame = None   # последний декодированный кадр (для Save)

        # --- центральный график ---
        self._plot = ScopePlot()
        self.setCentralWidget(self._plot)

        # --- тулбар ---
        tb = QToolBar()
        tb.setMovable(False)
        self.addToolBar(tb)

        self._resources = QComboBox()
        self._resources.setObjectName("resources")
        self._refresh_resources()
        tb.addWidget(self._resources)

        self._btn_refresh = QPushButton("⟳")
        self._btn_refresh.setToolTip("Обновить список приборов (пере-сканировать VISA)")
        self._btn_refresh.clicked.connect(self._refresh_resources)
        tb.addWidget(self._btn_refresh)

        self._btn_connect = QPushButton("Connect")
        self._btn_connect.clicked.connect(self._toggle_connect)
        tb.addWidget(self._btn_connect)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        tb.addWidget(spacer)

        self._btn_run = QPushButton("▶ RUN")
        self._btn_run.setObjectName("run")
        self._btn_run.clicked.connect(self._toggle_run)
        self._btn_run.setEnabled(False)
        tb.addWidget(self._btn_run)

        self._btn_single = QPushButton("SINGLE")
        self._btn_single.setObjectName("single")
        self._btn_single.clicked.connect(self._single)
        self._btn_single.setEnabled(False)
        tb.addWidget(self._btn_single)

        # Логгер SCPI-обмена в файл (отдельная кнопка, кап 10 МБ с ротацией)
        self._scpi_log = ScpiLogger()
        self._btn_log = QPushButton("● LOG")
        self._btn_log.setObjectName("log")
        self._btn_log.setCheckable(True)
        self._btn_log.setToolTip("Писать весь SCPI-обмен в файл (осциллограмма свёрнута; кап 10 МБ)")
        self._btn_log.toggled.connect(self._toggle_log)
        tb.addWidget(self._btn_log)

        # Файловые действия: сохранить кадр, скриншот графика, пресеты
        self._btn_save = QPushButton("Save")
        self._btn_save.setToolTip("Сохранить текущий кадр (CSV/NPY/HDF5)")
        self._btn_save.clicked.connect(self._save_waveform)
        self._btn_save.setEnabled(False)
        tb.addWidget(self._btn_save)

        self._btn_png = QPushButton("PNG")
        self._btn_png.setToolTip("Сохранить скриншот графика (PNG)")
        self._btn_png.clicked.connect(self._save_screenshot)
        tb.addWidget(self._btn_png)

        self._btn_preset = QPushButton("Presets")
        self._btn_preset.setToolTip("Сохранить/загрузить настройки прибора (JSON)")
        self._btn_preset.clicked.connect(self._presets_menu)
        self._btn_preset.setEnabled(False)
        tb.addWidget(self._btn_preset)

        self._btn_scpi = QPushButton("SCPI")
        self._btn_scpi.setObjectName("scpi")
        self._btn_scpi.setCheckable(True)
        self._btn_scpi.setToolTip("Показать/скрыть SCPI-терминал")
        self._btn_scpi.toggled.connect(self._toggle_terminal)
        tb.addWidget(self._btn_scpi)

        # --- правый док: табы Scope / Generator / Sweep ---
        self._dock = QDockWidget("", self)
        self._dock.setFeatures(QDockWidget.NoDockWidgetFeatures)
        self._dock.setTitleBarWidget(QWidget())  # без заголовка
        self._tabs = QTabWidget()
        self._tabs.setMinimumWidth(360)
        self._tabs.setMaximumWidth(420)

        # Scope-таб: стек панелей с заголовками секций.
        # settingChanged каждой панели подключается к слоту воркера (QueuedConnection)
        # в _connect — Qt сам маршалит (path, value) в поток воркера.
        self._vertical = VerticalPanel(channels=(1, 2))
        self._horizontal = HorizontalPanel()
        self._trigger = TriggerPanel()
        self._acquire = AcquirePanel()
        self._measure = MeasurePanel()
        self._meas_stats = MeasurementStats()   # клиентская статистика измерений
        self._math = MathPanel()
        self._cursors = CursorsPanel()
        self._display = DisplayPanel()
        self._generator = GeneratorPanel()
        self._sweep = SweepPanel()
        self._sweep.set_folder(os.path.abspath("captures"))
        # settingChanged-панели (маршрутизируются в apply_setting воркера).
        # Measure имеет иной поток данных (см. проводку в _connect), потому отдельно.
        # Generator — в своём табе, но тоже device-facing -> в _panels.
        self._panels = [self._vertical, self._horizontal, self._trigger, self._acquire,
                        self._generator]
        # Клиентские панели (Math/Cursors/Display) работают с НАШИМ графиком, а не с
        # прибором — проводка в __init__ (ниже), активны всегда.
        self._client_panels = [self._math, self._cursors, self._display]

        # аккордеон в вертикальном сплиттере: разделители между секциями можно
        # тянуть мышью, перераспределяя высоту (напр. увеличить таблицу измерений).
        scope_body = QSplitter(Qt.Vertical)
        scope_body.setObjectName("ScopeAccordion")
        scope_body.setChildrenCollapsible(False)
        scope_body.setHandleWidth(3)
        # по умолчанию развёрнуты Вертикаль/Горизонталь/Триггер/Измерения
        for title, panel, expanded in (
                ("ВЕРТИКАЛЬ", self._vertical, True), ("ГОРИЗОНТАЛЬ", self._horizontal, True),
                ("ТРИГГЕР", self._trigger, True), ("ИЗМЕРЕНИЯ", self._measure, True),
                ("ACQUIRE", self._acquire, False), ("MATH / FFT", self._math, False),
                ("КУРСОРЫ", self._cursors, False), ("ДИСПЛЕЙ", self._display, False)):
            if panel in self._panels or panel is self._measure:
                panel.setEnabled(False)  # device-панели включаются при connect
            scope_body.addWidget(CollapsibleSection(title, panel, expanded=expanded))

        # --- проводка клиентских панелей к графику (без прибора) ---
        self._display.displayChanged.connect(
            lambda key, val: self._plot.apply_display({key: val})
        )
        self._plot.apply_display(self._display.defaults())
        self._math.mathConfigChanged.connect(self._plot.set_math_config)
        self._cursors.cursorModeChanged.connect(self._plot.cursors.set_mode)
        self._cursors.cursorSourceChanged.connect(self._plot.cursors.set_source)
        self._plot.cursors.valuesChanged.connect(self._cursors.update_readout)
        # перетаскивание уровня триггера мышью на графике → прибор + панель
        self._plot.triggerLevelChanged.connect(self._on_trigger_level_dragged)

        scope_scroll = QScrollArea()
        scope_scroll.setWidgetResizable(True)
        scope_scroll.setFrameShape(QScrollArea.NoFrame)
        scope_scroll.setWidget(scope_body)

        self._tabs.addTab(scope_scroll, "Scope")

        gen_scroll = QScrollArea()
        gen_scroll.setWidgetResizable(True)
        gen_scroll.setFrameShape(QScrollArea.NoFrame)
        self._generator.setEnabled(False)  # включится при connect
        gen_scroll.setWidget(self._generator)
        self._tabs.addTab(gen_scroll, "Generator")

        sweep_scroll = QScrollArea()
        sweep_scroll.setWidgetResizable(True)
        sweep_scroll.setFrameShape(QScrollArea.NoFrame)
        self._sweep.setEnabled(False)  # включится при connect
        sweep_scroll.setWidget(self._sweep)
        self._tabs.addTab(sweep_scroll, "Sweep")

        # пикер папки свипа (диалог в главном потоке; панель остаётся headless)
        self._sweep.folderRequested.connect(self._pick_sweep_folder)

        self._dock.setWidget(self._tabs)
        self.addDockWidget(Qt.RightDockWidgetArea, self._dock)

        # --- нижний док: SCPI-терминал (скрыт; тумблер — кнопка SCPI) ---
        self._terminal = ScpiTerminal()
        self._terminal.setEnabled(False)  # активен при connect
        self._term_dock = QDockWidget("SCPI-терминал", self)
        self._term_dock.setFeatures(
            QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetMovable
        )
        self._term_dock.setWidget(self._terminal)
        self.addDockWidget(Qt.BottomDockWidgetArea, self._term_dock)
        self._term_dock.hide()
        # синхронизировать кнопку-тумблер с видимостью дока (напр. закрытие крестиком)
        self._term_dock.visibilityChanged.connect(self._btn_scpi.setChecked)

        # --- статус-бар ---
        self._lbl_conn = QLabel("● offline")
        self._lbl_idn = QLabel("")        # модель/IDN — постоянно, не перетирается кадрами
        self._lbl_metrics = QLabel("")    # srate · trig · ch · fps (обновляется кадрами)
        sb = self.statusBar()
        sb.addWidget(self._lbl_conn)
        sb.addWidget(self._lbl_idn, 1)
        sb.addPermanentWidget(self._lbl_metrics)

        self._running = False

    # ------------------------------------------------------------------
    # Соединение
    # ------------------------------------------------------------------

    def _refresh_resources(self):
        try:
            res = VisaTransport.list_resources()
        except Exception as exc:  # noqa: BLE001
            res = ()
            self._lbl_idn.setText(f"list_resources error: {exc}")
        self._resources.clear()
        usb = [r for r in res if r.upper().startswith("USB")]
        self._resources.addItems(usb + [r for r in res if r not in usb])

    def _toggle_connect(self):
        if self._scope is None:
            self._connect()
        else:
            self._disconnect()

    def _set_connecting_ui(self, busy: bool) -> None:
        """Лёгкая обратная связь на коннекте: открытие VISA блокирует UI-поток на
        3-5 с (анимация невозможна без потоков), поэтому хотя бы сразу показываем
        статус и принудительно перерисовываем кнопку/лейбл до фриза.
        """
        if busy:
            self._btn_connect.setEnabled(False)
            self._btn_connect.setText("⏳ Подключение…")
            self._lbl_conn.setText("● connecting…")
            self._lbl_conn.setStyleSheet("color: #F5A623;")
            # принудительная немедленная перерисовка (до блокирующего VISA-вызова)
            self._btn_connect.repaint()
            self._lbl_conn.repaint()
        else:
            self._btn_connect.setEnabled(True)
            self._btn_connect.setText("Connect")

    def _connect(self):
        resource = self._resources.currentText().strip()
        if not resource:
            self._lbl_idn.setText("Нет VISA-ресурса. Подключи прибор и нажми ⟳.")
            return
        self._set_connecting_ui(True)
        try:
            self._transport = VisaTransport(resource, timeout_ms=8000)
            if self._scpi_log.is_active:
                self._transport.set_io_logger(self._scpi_log.callback)
            self._scope = Scope(self._transport)
            self._scope.connect()
            idn = self._scope.idn()
            # гарантируем, что хотя бы CH1 отображается, развёртка AUTO
            self._scope.channel[1].display = True
            self._scope.trigger.sweep = "AUTO"
            self._controller = AcquisitionController(self._scope, WaveformReader(self._transport))
            self._controller.refresh_scaling([1, 2])
            # заполнить панели текущими настройками (главный поток, до старта воркера)
            for panel in self._panels:
                panel.load_from_scope(self._scope)
            self._measure.load_from_scope(self._scope)
        except Exception as exc:  # noqa: BLE001
            self._lbl_idn.setText(f"Ошибка подключения: {exc}")
            self._lbl_conn.setText("● offline")
            self._lbl_conn.setStyleSheet("color: #5A606C;")
            self._scope = None
            self._set_connecting_ui(False)
            return

        # worker в фоновом потоке
        # 50 мс (≈20 Гц): даёт USB-потоку osc передышку между кадрами. 5 мс (200 Гц)
        # провоцировал десинк USBTMC → «кадр не собран за 512 пакетов».
        self._worker = EngineWorker(self._controller, interval_ms=50)
        self._thread = QThread(self)
        self._worker.moveToThread(self._thread)
        self._worker.frameReady.connect(self._on_frame)
        self._worker.errorOccurred.connect(self._on_error)
        self._worker.stateChanged.connect(self._on_state)
        self._worker.diagTiming.connect(self._on_diag_timing)
        # контролы панелей → слот воркера в его потоке (Qt маршалит payload)
        for panel in self._panels:
            panel.settingChanged.connect(
                self._worker.apply_setting, Qt.ConnectionType.QueuedConnection
            )
        # readback с прибора → синхронизация панели Vertical (scale вслед за probe, кламп offset)
        self._worker.channelReadback.connect(self._vertical.update_readback)
        # Measure: набор активных строк → воркер (его поток); значения ← воркер в UI-поток
        self._measure.measurementsChanged.connect(
            self._worker.set_measurements, Qt.ConnectionType.QueuedConnection
        )
        self._worker.measurementsReady.connect(self._measure.update_values)
        self._worker.measurementsReady.connect(self._on_measurements_badge)
        self._measure.statsResetRequested.connect(self._reset_meas_stats)
        # Sweep: старт → worker.run_sweep (в его потоке); стоп → отмена (Event,
        # потокобезопасно, проходит даже пока run_sweep блокирует поток воркера).
        self._sweep.startRequested.connect(
            self._worker.run_sweep, Qt.ConnectionType.QueuedConnection
        )
        self._sweep.startRequested.connect(lambda _c: self._sweep.set_running(True))
        self._sweep.stopRequested.connect(
            self._worker.cancel_sweep, Qt.ConnectionType.DirectConnection
        )
        self._worker.sweepProgress.connect(self._sweep.set_progress)
        self._worker.sweepFinished.connect(self._on_sweep_finished)
        self._worker.sweepError.connect(self._on_sweep_error)
        # Пресеты: запросы в поток воркера; итоги — в статус-бар
        self._sigSavePreset.connect(
            self._worker.capture_preset_to, Qt.ConnectionType.QueuedConnection
        )
        self._sigApplyPreset.connect(
            self._worker.apply_preset_dict, Qt.ConnectionType.QueuedConnection
        )
        self._worker.presetSaved.connect(self._on_preset_saved)
        self._worker.presetApplied.connect(self._on_preset_applied)
        self._worker.presetError.connect(self._on_sweep_error)
        self._sigApplySetting.connect(
            self._worker.apply_setting, Qt.ConnectionType.QueuedConnection
        )
        # SCPI-терминал: команда → воркер; результат → журнал терминала
        self._terminal.commandEntered.connect(
            self._worker.send_command, Qt.ConnectionType.QueuedConnection
        )
        self._worker.commandResult.connect(self._on_command_result)
        self._thread.start()

        self._btn_connect.setEnabled(True)   # снять busy-disable коннекта
        self._btn_connect.setText("Disconnect")
        self._btn_run.setEnabled(True)
        self._btn_single.setEnabled(True)
        for panel in self._panels:
            panel.setEnabled(True)
        self._measure.setEnabled(True)
        self._sweep.setEnabled(True)
        self._btn_save.setEnabled(True)
        self._btn_preset.setEnabled(True)
        self._terminal.setEnabled(True)
        self._lbl_conn.setText("● connected")
        self._lbl_conn.setStyleSheet("color: #37D67A;")
        self._lbl_idn.setText(idn)

    def _disconnect(self):
        if self._worker is not None:
            for panel in self._panels:
                try:
                    panel.settingChanged.disconnect(self._worker.apply_setting)
                except (RuntimeError, TypeError):
                    pass
            QMetaObject.invokeMethod(self._worker, "stop", Qt.ConnectionType.QueuedConnection)
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait(3000)
        if self._scope is not None:
            try:
                self._scope.disconnect()
            except Exception:  # noqa: BLE001
                pass
        self._worker = self._thread = self._controller = self._scope = self._transport = None
        self._running = False
        self._plot.clear()
        for panel in self._panels:
            panel.setEnabled(False)
        self._measure.setEnabled(False)
        self._sweep.setEnabled(False)
        self._btn_save.setEnabled(False)
        self._btn_preset.setEnabled(False)
        self._terminal.setEnabled(False)
        self._last_frame = None
        self._btn_connect.setText("Connect")
        self._btn_run.setText("▶ RUN")
        self._btn_run.setObjectName("run")
        self._btn_run.setEnabled(False)
        self._btn_single.setEnabled(False)
        self._lbl_conn.setText("● offline")
        self._lbl_conn.setStyleSheet("color: #5A606C;")
        self._lbl_idn.setText("")
        self._lbl_metrics.setText("")


    # ------------------------------------------------------------------
    # Управление сбором (host-side, через worker в его потоке)
    # ------------------------------------------------------------------

    def _toggle_run(self):
        if self._worker is None:
            return
        if self._running:
            QMetaObject.invokeMethod(self._worker, "stop", Qt.ConnectionType.QueuedConnection)
        else:
            self._frame_count = 0
            self._fps_timer.restart()
            self._reset_meas_stats()   # новый прогон Run → статистика с нуля
            QMetaObject.invokeMethod(self._worker, "start", Qt.ConnectionType.QueuedConnection)

    def _single(self):
        if self._worker is None:
            return
        self._reset_meas_stats()       # Single → статистика с нуля
        QMetaObject.invokeMethod(self._worker, "single", Qt.ConnectionType.QueuedConnection)

    def _toggle_log(self, on: bool):
        """Включить/выключить файловый лог SCPI-обмена."""
        if on:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = os.path.abspath(f"scpi_{ts}.log")
            self._scpi_log.start(path)
            if self._transport is not None:
                self._transport.set_io_logger(self._scpi_log.callback)
            self._lbl_metrics.setText(f"⬤ SCPI-лог: {path}")
        else:
            if self._transport is not None:
                self._transport.set_io_logger(None)
            self._scpi_log.stop()
            self._lbl_metrics.setText("SCPI-лог остановлен")

    def _toggle_terminal(self, on: bool):
        """Показать/скрыть нижний SCPI-терминал."""
        self._term_dock.setVisible(on)

    @Slot(str, str, bool)
    def _on_command_result(self, cmd, response, is_error):
        self._terminal.append_response(response, is_error)

    @Slot(float)
    def _on_trigger_level_dragged(self, volts):
        """Уровень триггера перетащили на графике → в прибор + синхронизировать панель."""
        self._sigApplySetting.emit("trigger.edge.level", float(volts))
        self._trigger.update_level(float(volts))

    def _on_measurements_badge(self, payload):
        """Накопить статистику измерений и показать таблицу в бейдже графика.

        Прибор отдаёт только текущее значение; cur/avg/max/min/std/count копим у
        себя (``self._meas_stats``). Строим компактную HTML-таблицу по активному
        набору (порядок payload) и пушим в бейдж. Пустой набор — очищает таблицу.
        """
        self._meas_stats.update(payload)
        self._plot.set_measurements_readout(self._build_stats_table(payload))

    # Жёсткая таблица статистики: моноширинные колонки фиксированной ширины
    # (значения не «прыгают» при смене длины). Ширины в символах.
    _STATS_W_LABEL = 13     # столбец «CHn ITEM»
    _STATS_W_NUM = 11       # числовые столбцы (cur/avg/max/min/std/rms)
    _STATS_W_CNT = 6        # счётчик

    @staticmethod
    def _pad(text: str, width: int, *, right: bool) -> str:
        """Обрезать до width и выровнять моноширинно, ГАРАНТИРУЯ ≥1 пробел-разделитель.

        Содержимое ограничено ``width-1`` символами — поэтому при выравнивании всегда
        остаётся минимум один пробел (иначе соседние колонки слипаются).
        """
        s = str(text)
        maxc = max(1, width - 1)          # резерв ≥1 символа под разделитель
        if len(s) > maxc:
            s = s[: max(0, maxc - 1)] + "…"
        return s.rjust(width) if right else s.ljust(width)

    def _build_stats_table(self, payload) -> str:
        """Жёсткая моноширинная таблица статистики измерений (строки = активный набор).

        Колонки фиксированной ширины через ``<pre>``: Изм · Cur · Avg · Max · Min ·
        Std · RMS · Cnt. Строки окрашены по каналу; шапка серая.
        """
        from hantek_dso2d15.gui.panels.measure import _fmt_value
        from hantek_dso2d15.gui.theme import CH_COLORS

        wl, wn, wc = self._STATS_W_LABEL, self._STATS_W_NUM, self._STATS_W_CNT

        def _num(val, item):
            try:
                return _fmt_value(item, float(val))
            except (TypeError, ValueError):
                return "—"

        lines = []
        seen = set()
        for entry in payload or []:
            try:
                ch = int(entry["channel"])
                item = str(entry["item"])
            except (KeyError, TypeError, ValueError):
                continue
            key = (ch, item)
            if key in seen:
                continue
            seen.add(key)
            s = self._meas_stats.stats_for(ch, item)
            if s is None:
                continue
            color = CH_COLORS.get(ch, "#C5C9D1")
            row = (
                self._pad(f"CH{ch} {item}", wl, right=False)
                + self._pad(_num(s["cur"], item), wn, right=True)
                + self._pad(_num(s["avg"], item), wn, right=True)
                + self._pad(_num(s["max"], item), wn, right=True)
                + self._pad(_num(s["min"], item), wn, right=True)
                + self._pad(_num(s["std"], item), wn, right=True)
                + self._pad(_num(s["rms"], item), wn, right=True)
                + self._pad(str(s["count"]), wc, right=True)
            )
            lines.append(f"<span style='color:{color}'>{_html_escape(row)}</span>")
        if not lines:
            return ""
        header = (
            self._pad("Изм", wl, right=False)
            + self._pad("Cur", wn, right=True)
            + self._pad("Avg", wn, right=True)
            + self._pad("Max", wn, right=True)
            + self._pad("Min", wn, right=True)
            + self._pad("Std", wn, right=True)
            + self._pad("RMS", wn, right=True)
            + self._pad("Cnt", wc, right=True)
        )
        head_span = f"<span style='color:#7A808C'>{_html_escape(header)}</span>"
        body = "\n".join([head_span] + lines)
        return f"<pre style='margin:0;font-family:JetBrains Mono,Consolas,monospace'>{body}</pre>"

    def _reset_meas_stats(self):
        """Сбросить накопленную статистику измерений и очистить таблицу бейджа."""
        self._meas_stats.reset()
        self._plot.set_measurements_readout("")

    def _pick_sweep_folder(self):
        """Открыть диалог выбора папки для свипа (главный поток)."""
        start_dir = self._sweep.config().get("folder") or ""
        path = QFileDialog.getExistingDirectory(self, "Папка для свипа", start_dir)
        if path:
            self._sweep.set_folder(path)

    @Slot(object)
    def _on_sweep_finished(self, result):
        self._sweep.set_running(False)
        done, total = result.get("done", 0), result.get("total", 0)
        if result.get("cancelled"):
            self._lbl_metrics.setText(f"Свип отменён ({done}/{total})")
        else:
            self._lbl_metrics.setText(f"Свип завершён: сохранено {done}/{total}")

    @Slot(str)
    def _on_sweep_error(self, msg):
        self._sweep.set_running(False)
        self._lbl_metrics.setText(f"⚠ {msg}")

    # ------------------------------------------------------------------
    # Save / Screenshot / Presets
    # ------------------------------------------------------------------

    def _save_waveform(self):
        """Сохранить текущий кадр в CSV/NPY/HDF5."""
        if self._last_frame is None:
            self._lbl_metrics.setText("Нет кадра для сохранения (нажми RUN)")
            return
        path, _flt = QFileDialog.getSaveFileName(
            self, "Сохранить кадр", "waveform",
            "CSV (*.csv);;NumPy (*.npz);;HDF5 (*.h5)",
        )
        if not path:
            return
        low = path.lower()
        if low.endswith((".npz", ".npy")):
            fmt = "NPY"
        elif low.endswith((".h5", ".hdf5")):
            fmt = "HDF5"
        else:
            fmt = "CSV"
            if not low.endswith(".csv"):
                path += ".csv"
        try:
            export_frame(self._last_frame, path, fmt)
            self._lbl_metrics.setText(f"Кадр сохранён: {path}")
        except Exception as exc:  # noqa: BLE001
            self._lbl_metrics.setText(f"⚠ save: {exc}")

    def _save_screenshot(self):
        """Сохранить скриншот нашего графика в PNG."""
        path, _ = QFileDialog.getSaveFileName(self, "Скриншот графика", "scope.png", "PNG (*.png)")
        if not path:
            return
        if not path.lower().endswith(".png"):
            path += ".png"
        if self._plot.grab().save(path, "PNG"):
            self._lbl_metrics.setText(f"Скриншот сохранён: {path}")
        else:
            self._lbl_metrics.setText("⚠ не удалось сохранить PNG")

    def _presets_menu(self):
        """Меню пресетов под кнопкой."""
        menu = QMenu(self)
        menu.addAction("Сохранить пресет…", self._save_preset)
        menu.addAction("Загрузить пресет…", self._load_preset)
        menu.exec(self._btn_preset.mapToGlobal(self._btn_preset.rect().bottomLeft()))

    def _save_preset(self):
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить пресет", "preset.json", "JSON (*.json)")
        if not path:
            return
        if not path.lower().endswith(".json"):
            path += ".json"
        self._lbl_metrics.setText("Сохранение пресета…")
        self._sigSavePreset.emit(path)   # воркер снимет настройки и запишет файл

    def _load_preset(self):
        path, _ = QFileDialog.getOpenFileName(self, "Загрузить пресет", "", "JSON (*.json)")
        if not path:
            return
        try:
            preset = load_preset(path)
        except Exception as exc:  # noqa: BLE001
            self._lbl_metrics.setText(f"⚠ load preset: {exc}")
            return
        # ресинк панелей из снапшота (без I/O); затем применить к прибору в потоке воркера
        snap = SnapshotScope(preset)
        for panel in (self._vertical, self._horizontal, self._trigger,
                      self._acquire, self._generator):
            try:
                panel.load_from_scope(snap)
            except Exception:  # noqa: BLE001 — неполный пресет: панель не ресинкнется, но прибор применит
                pass
        self._sigApplyPreset.emit(preset)
        self._lbl_metrics.setText(f"Пресет загружается: {path}")

    @Slot(str)
    def _on_preset_saved(self, path):
        self._lbl_metrics.setText(f"Пресет сохранён: {path}")

    @Slot(object)
    def _on_preset_applied(self, errors):
        if errors:
            self._lbl_metrics.setText(f"Пресет применён (ошибок путей: {len(errors)})")
        else:
            self._lbl_metrics.setText("Пресет применён")

    # ------------------------------------------------------------------
    # Слоты сигналов worker (выполняются в UI-потоке)
    # ------------------------------------------------------------------

    @Slot(object)
    def _on_diag_timing(self, read_ms: float, meas_ms: float, packets: int) -> None:
        """Диагностика кадра: мс чтения · мс измерений · число USB-пакетов."""
        self._diag_read_ms = float(read_ms)
        self._diag_meas_ms = float(meas_ms)
        self._diag_packets = int(packets)

    def _on_frame(self, decoded):
        self._plot.update_frame(decoded)
        self._last_frame = decoded
        # FPS по скользящему окну ~1 с (истинная текущая скорость, а не среднее с
        # момента старта — иначе медленный разгон занижает цифру надолго).
        self._frame_count += 1
        if self._fps_timer.isValid():
            el = self._fps_timer.elapsed()
            if el >= 1000:
                self._fps_display = self._frame_count * 1000.0 / el
                self._frame_count = 0
                self._fps_timer.restart()
        fps_val = getattr(self, "_fps_display", 0.0)
        fps = f" · {fps_val:.1f} fps" if fps_val else ""
        trig = "Trig'd" if decoded.triggered else "Auto"
        diag = ""
        rd = getattr(self, "_diag_read_ms", None)
        if rd is not None:
            ms = getattr(self, "_diag_meas_ms", 0.0)
            pk = getattr(self, "_diag_packets", 0)
            diag = f" · rd {rd:.0f}ms/{pk}pk · ms {ms:.0f}ms"
        self._lbl_metrics.setText(
            f"{decoded.srate/1e6:.3f} MSa/s · {trig} · {len(decoded.channels)} ch{fps}{diag}"
        )

    @Slot(str)
    def _on_error(self, msg):
        self._lbl_metrics.setText(f"⚠ {msg}")

    @Slot(object)
    def _on_state(self, state):
        self._running = state is RunState.RUNNING
        if self._running:
            self._btn_run.setText("■ STOP")
            self._btn_run.setObjectName("stop")
        else:
            self._btn_run.setText("▶ RUN")
            self._btn_run.setObjectName("run")
        # переприменить стиль после смены objectName
        self._btn_run.setStyleSheet("")
        self.setStyleSheet(self.styleSheet())
        # бейдж триггера: STOP красный / SINGLE «Ready» cyan; RUN ведут кадры (Trig'd/Auto)
        if state is RunState.STOPPED:
            self._plot.set_trigger_badge("Stop", "#E5484D")
        elif state is RunState.SINGLE:
            self._plot.set_trigger_badge("Ready", "#23C8E6")

    def closeEvent(self, event):
        self._disconnect()
        super().closeEvent(event)
