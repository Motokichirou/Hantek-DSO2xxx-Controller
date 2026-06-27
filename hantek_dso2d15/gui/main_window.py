"""MainWindow — минимальное главное окно клиента DSO2D15.

Тулбар (connection + RUN/STOP/SINGLE), центральный график, статус-бар.
Сбор данных в фоновом QThread (EngineWorker); кадры приходят сигналом
frameReady и рисуются на графике. VISA-I/O не блокирует UI-поток.
"""
from __future__ import annotations

import os
from datetime import datetime

from PySide6.QtCore import Qt, QThread, QMetaObject, QElapsedTimer, Slot
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QToolBar, QComboBox, QPushButton, QLabel, QSizePolicy,
    QDockWidget, QTabWidget, QScrollArea, QVBoxLayout, QFileDialog,
)

from hantek_dso2d15.transport.visa_transport import VisaTransport
from hantek_dso2d15.transport.scpi_log import ScpiLogger
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

STYLE = """
QMainWindow, QWidget { background: #0E0F12; color: #C5C9D1; }
QToolBar { background: #16181D; border: none; spacing: 8px; padding: 6px; }
QComboBox { background: #0E0F12; border: 1px solid #2A2D34; border-radius: 5px;
            padding: 4px 8px; color: #E6E9EF; }
QComboBox#resources { min-width: 320px; }
QDoubleSpinBox { background: #0E0F12; border: 1px solid #2A2D34; border-radius: 4px;
                 padding: 3px 18px 3px 6px; color: #E6E9EF; }
QDoubleSpinBox::up-button { subcontrol-origin: border; subcontrol-position: top right;
                 width: 16px; border-left: 1px solid #2A2D34; background: #1B1E24;
                 border-top-right-radius: 4px; }
QDoubleSpinBox::down-button { subcontrol-origin: border; subcontrol-position: bottom right;
                 width: 16px; border-left: 1px solid #2A2D34; background: #1B1E24;
                 border-bottom-right-radius: 4px; }
QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover { background: #2A2D34; }
QDoubleSpinBox::up-arrow { width: 0; height: 0; border-left: 4px solid transparent;
                 border-right: 4px solid transparent; border-bottom: 5px solid #9AA0AC; }
QDoubleSpinBox::down-arrow { width: 0; height: 0; border-left: 4px solid transparent;
                 border-right: 4px solid transparent; border-top: 5px solid #9AA0AC; }
QCheckBox { color: #9AA0AC; }
QPushButton { background: #1B1E24; border: 1px solid #2A2D34; border-radius: 5px;
              padding: 6px 14px; color: #C5C9D1; font-weight: 600; }
QPushButton:hover { border-color: #3A3F49; }
QPushButton#run { background: rgba(55,214,122,0.16); border-color: #2F4A3C; color: #37D67A; }
QPushButton#stop { background: rgba(229,72,77,0.16); border-color: #5A2A2C; color: #E5484D; }
QPushButton#single { color: #F5A623; border-color: #6A521E; }
QPushButton#log:checked { background: rgba(229,72,77,0.20); border-color: #5A2A2C; color: #E5484D; }
QPushButton:disabled { color: #5A606C; }
QStatusBar { background: #16181D; color: #6E747F; }
QLabel { color: #9AA0AC; }
QDockWidget { color: #AEB4BF; }
QTabWidget::pane { border: none; background: #13151A; }
QTabBar::tab { background: #16181D; color: #7A808C; padding: 8px 14px; border: none; }
QTabBar::tab:selected { color: #E6E9EF; border-bottom: 2px solid #37D67A; }
QLabel#section { background: #1B1E24; color: #AEB4BF; font-weight: 600;
                 padding: 5px 10px; letter-spacing: 0.7px; }
"""


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Hantek DSO2D15")
        self.resize(1280, 720)
        self.setStyleSheet(STYLE)

        # --- движок/соединение ---
        self._transport = None
        self._scope = None
        self._controller = None
        self._worker = None
        self._thread = None
        self._fps_timer = QElapsedTimer()
        self._frame_count = 0

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

        scope_body = QWidget()
        sl = QVBoxLayout(scope_body)
        sl.setContentsMargins(0, 0, 0, 0)
        sl.setSpacing(0)
        for title, panel in (("ВЕРТИКАЛЬ", self._vertical), ("ГОРИЗОНТАЛЬ", self._horizontal),
                             ("ТРИГГЕР", self._trigger), ("ИЗМЕРЕНИЯ", self._measure),
                             ("ACQUIRE", self._acquire), ("MATH / FFT", self._math),
                             ("КУРСОРЫ", self._cursors), ("ДИСПЛЕЙ", self._display)):
            hdr = QLabel(title)
            hdr.setObjectName("section")
            sl.addWidget(hdr)
            if panel in self._panels or panel is self._measure:
                panel.setEnabled(False)  # device-панели включаются при connect
            sl.addWidget(panel)
        sl.addStretch(1)

        # --- проводка клиентских панелей к графику (без прибора) ---
        self._display.displayChanged.connect(
            lambda key, val: self._plot.apply_display({key: val})
        )
        self._plot.apply_display(self._display.defaults())
        self._math.mathConfigChanged.connect(self._plot.set_math_config)
        self._cursors.cursorModeChanged.connect(self._plot.cursors.set_mode)
        self._cursors.cursorSourceChanged.connect(self._plot.cursors.set_source)
        self._plot.cursors.valuesChanged.connect(self._cursors.update_readout)

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

    def _connect(self):
        resource = self._resources.currentText().strip()
        if not resource:
            self._lbl_idn.setText("Нет VISA-ресурса. Подключи прибор и нажми ⟳.")
            return
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
            self._scope = None
            return

        # worker в фоновом потоке
        self._worker = EngineWorker(self._controller, interval_ms=5)
        self._thread = QThread(self)
        self._worker.moveToThread(self._thread)
        self._worker.frameReady.connect(self._on_frame)
        self._worker.errorOccurred.connect(self._on_error)
        self._worker.stateChanged.connect(self._on_state)
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
        self._thread.start()

        self._btn_connect.setText("Disconnect")
        self._btn_run.setEnabled(True)
        self._btn_single.setEnabled(True)
        for panel in self._panels:
            panel.setEnabled(True)
        self._measure.setEnabled(True)
        self._sweep.setEnabled(True)
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
            QMetaObject.invokeMethod(self._worker, "start", Qt.ConnectionType.QueuedConnection)

    def _single(self):
        if self._worker is None:
            return
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
    # Слоты сигналов worker (выполняются в UI-потоке)
    # ------------------------------------------------------------------

    @Slot(object)
    def _on_frame(self, decoded):
        self._plot.update_frame(decoded)
        self._frame_count += 1
        fps = ""
        if self._fps_timer.isValid():
            el = self._fps_timer.elapsed() / 1000.0
            if el > 0:
                fps = f" · {self._frame_count / el:.1f} fps"
        trig = "Trig'd" if decoded.triggered else "Auto"
        self._lbl_metrics.setText(
            f"{decoded.srate/1e6:.3f} MSa/s · {trig} · {len(decoded.channels)} ch{fps}"
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

    def closeEvent(self, event):
        self._disconnect()
        super().closeEvent(event)
