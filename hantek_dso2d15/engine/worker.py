"""EngineWorker — тонкий Qt-слой поверх AcquisitionController (Task E3).

Переносится в QThread слоем GUI. Управление кадентностью опроса — host-side:
  - Run  → таймер тикает с interval_ms, каждый тик вызывает capture_once().
  - Stop → таймер остановлен.
  - Single → один synchronous захват, затем автоматически STOPPED.

Не блокирует UI-поток: вся VISA-I/O происходит в том потоке, куда перемещён worker.
"""
from __future__ import annotations

import os
import threading
import time

from PySide6.QtCore import QObject, QTimer, Signal, Slot

from hantek_dso2d15.engine.states import RunState
from hantek_dso2d15.engine.sweep import SweepConfig, SweepRunner
from hantek_dso2d15.io.export import export_frame, capture_filename
from hantek_dso2d15.io.presets import capture_preset, apply_preset, save_preset


class EngineWorker(QObject):
    """Qt-обёртка вокруг AcquisitionController.

    Сигналы
    -------
    frameReady(object)
        Испускается при успешном получении декодированного кадра.
        Передаёт объект :class:`~hantek_dso2d15.waveform.decode.DecodedFrame`.
    errorOccurred(str)
        Испускается при любом исключении в ``capture_once()``.
        Передаёт строку ``str(exception)``.
    stateChanged(object)
        Испускается при каждом изменении состояния. Передаёт
        значение :class:`~hantek_dso2d15.engine.states.RunState`.

    Parameters
    ----------
    controller:
        Объект с методом ``read_decoded_frame() -> DecodedFrame``.
        Обычно :class:`~hantek_dso2d15.engine.controller.AcquisitionController`.
    interval_ms:
        Интервал таймера непрерывного сбора в миллисекундах. По умолчанию 50 мс
        (~20 fps).
    parent:
        Родительский QObject (опционально).
    """

    frameReady = Signal(object)
    errorOccurred = Signal(str)
    stateChanged = Signal(object)
    #: диагностика кадра: (мс чтения осциллограммы, мс опроса измерений, число USB-пакетов).
    diagTiming = Signal(float, float, int)
    #: после вертикального изменения канала — фактические значения с прибора
    #: (n, scale, offset, probe) для синхронизации панели (прибор = источник истины).
    channelReadback = Signal(int, float, float, int)
    #: список dict {"channel", "item", "value"} — результат опроса автоизмерений
    #: после каждого успешного кадра (только если активны запросы).
    measurementsReady = Signal(object)
    #: прогресс свипа (done, total).
    sweepProgress = Signal(int, int)
    #: свип завершён — dict результата {"done","total","cancelled"}.
    sweepFinished = Signal(object)
    #: ошибка свипа (строка).
    sweepError = Signal(str)
    #: пресет сохранён в файл (путь).
    presetSaved = Signal(str)
    #: пресет применён к прибору; payload = список путей-ошибок (пустой = всё ок).
    presetApplied = Signal(object)
    #: ошибка операции с пресетом (строка).
    presetError = Signal(str)
    #: результат сырой SCPI-команды терминала: (команда, ответ, is_error).
    commandResult = Signal(str, str, bool)

    def __init__(self, controller, interval_ms: int = 50, parent=None) -> None:
        super().__init__(parent)
        self._controller = controller
        self._state: RunState = RunState.STOPPED
        # Список активных запросов автоизмерений. Пуст → измерения не опрашиваются.
        # Заполняется через set_measurements(); элементы: tuple(int, str).
        self._measure_requests: list = []
        # --- Измерения: round-robin + кэш + троттлинг UI ---------------------
        # Каждое измерение — отдельный синхронный VISA round-trip. Опрашивать ВЕСЬ
        # набор за один кадр = надолго застопорить поток сбора (и спровоцировать
        # десинк USBTMC → «кадр не собран»). Поэтому на каждый кадр опрашиваем лишь
        # _measure_batch измерений по кругу, накапливая значения в кэш; в UI отдаём
        # полный снимок кэша не чаще _emit_period (чтобы не перестраивать таблицу
        # каждый кадр). Так поток сбора не стопорится, а измерения обновляются «волной».
        self._measure_cache: dict[tuple[int, str], float | None] = {}
        self._measure_rr: int = 0              # указатель round-robin по _measure_requests
        self._measure_batch: int = 2           # измерений за один опрос (bounded стоимость)
        # Каденция опроса: измерения опрашиваются НЕ каждый кадр, а не чаще
        # _measure_poll_period. Между опросами кадры читаются и рисуются свободно —
        # поэтому FPS дисплея не зависит от стоимости (возможно медленных) measure-запросов.
        self._measure_poll_period: float = 0.2  # с (≈5 опросов/сек)
        self._last_poll_t: float | None = None
        self._force_full_measure: bool = False  # single(): опросить ВЕСЬ набор за раз
        # Флаг отмены свипа (потокобезопасен; выставляется из GUI-потока).
        self._sweep_cancel = threading.Event()

        self._timer = QTimer(self)
        self._timer.setInterval(interval_ms)
        self._timer.timeout.connect(self.capture_once)

    # ------------------------------------------------------------------
    # Public property
    # ------------------------------------------------------------------

    @property
    def state(self) -> RunState:
        """Текущее состояние цикла сбора."""
        return self._state

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    @Slot()
    def start(self) -> None:
        """Перевести в режим непрерывного сбора (RUNNING) и запустить таймер."""
        self._state = RunState.RUNNING
        self._last_poll_t = None   # первый кадр прогона сразу опрашивает измерения
        self._timer.start()
        self.stateChanged.emit(self._state)

    @Slot()
    def stop(self) -> None:
        """Остановить сбор (STOPPED) и остановить таймер."""
        self._state = RunState.STOPPED
        self._timer.stop()
        self.stateChanged.emit(self._state)

    @Slot()
    def single(self) -> None:
        """Одиночный захват: SINGLE → capture_once() → STOPPED."""
        self._state = RunState.SINGLE
        self._force_full_measure = True   # одиночный захват меряет ВЕСЬ набор
        self._last_poll_t = None          # и сразу опрашивает (минуя каденцию)
        self.stateChanged.emit(self._state)
        self.capture_once()

    @Slot(object)
    def set_measurements(self, requests) -> None:
        """Установить список активных запросов автоизмерений.

        После установки непустого списка активирует ``scope.measure.enable = True``.
        Вызывать из потока воркера (через queued-сигнал) — не из UI-потока.

        Parameters
        ----------
        requests:
            Итерируемый объект из пар ``(channel, item)``. Элементы нормализуются
            к ``tuple(int, str)``. Пустой список — отключает опрос измерений.
        """
        self._measure_requests = [(int(ch), str(item)) for ch, item in requests]
        # новый набор → сбросить round-robin и кэш (старые ключи неактуальны)
        self._measure_cache = {}
        self._measure_rr = 0
        self._last_poll_t = None
        if self._measure_requests:
            try:
                self._controller.scope.measure.enable = True
            except Exception as exc:  # noqa: BLE001
                self.errorOccurred.emit(f"set_measurements: {exc}")

    def _poll_measure_batch(self) -> None:
        """Опросить очередную порцию измерений (round-robin) и обновить кэш.

        Обычный кадр: _measure_batch измерений по кругу. После single() (флаг
        _force_full_measure) — весь набор за раз (одиночный захват меряет всё).
        """
        reqs = self._measure_requests
        n = len(reqs)
        if n == 0:
            return
        if self._force_full_measure:
            batch = list(reqs)
            self._force_full_measure = False
            self._measure_rr = 0
        else:
            k = min(self._measure_batch, n)
            batch = [reqs[(self._measure_rr + i) % n] for i in range(k)]
            self._measure_rr = (self._measure_rr + k) % n
        for d in self._controller.read_measurements(batch):
            self._measure_cache[(int(d["channel"]), str(d["item"]))] = d.get("value")

    def _should_poll_measures(self) -> bool:
        """True, если пора опросить порцию измерений (каденция _measure_poll_period).

        Первый раз после старта/single (_last_poll_t is None) — всегда.
        """
        if self._last_poll_t is None:
            return True
        return (time.monotonic() - self._last_poll_t) >= self._measure_poll_period

    def _measure_snapshot(self) -> list:
        """Полный снимок кэша в порядке _measure_requests (неопрошенные → value None)."""
        return [
            {"channel": ch, "item": item, "value": self._measure_cache.get((ch, item))}
            for (ch, item) in self._measure_requests
        ]

    @Slot()
    def capture_once(self) -> None:
        """Тянет один кадр с контроллера и испускает frameReady или errorOccurred.

        После захвата (успешного ИЛИ ошибочного), если текущее состояние SINGLE,
        автоматически вызывает :meth:`stop` — чтобы одиночный режим не залипал в
        SINGLE при ошибке контроллера.

        Если активны запросы измерений (``_measure_requests`` непуст) — после
        успешного ``frameReady.emit`` опрашивает ``controller.read_measurements()``
        и испускает ``measurementsReady``. Ошибка измерений не останавливает цикл.
        """
        try:
            t0 = time.monotonic()
            frame = self._controller.read_decoded_frame()
            read_ms = (time.monotonic() - t0) * 1000.0
            self.frameReady.emit(frame)
            # Автоизмерения после успешного кадра: round-robin порция в кэш (bounded
            # стоимость на кадр), снимок в UI — троттлинг _emit_period. Это не даёт
            # потоку сбора стопориться на залпе из N запросов (и рвать осциллограмму).
            meas_ms = 0.0
            if self._measure_requests and self._should_poll_measures():
                try:
                    tm = time.monotonic()
                    self._poll_measure_batch()
                    self._last_poll_t = time.monotonic()   # ПОСЛЕ опроса (без back-to-back)
                    meas_ms = (self._last_poll_t - tm) * 1000.0
                    self.measurementsReady.emit(self._measure_snapshot())
                except Exception as exc:  # noqa: BLE001
                    self.errorOccurred.emit(str(exc))
            packets = int(getattr(self._controller, "last_read_packets", 0))
            self.diagTiming.emit(read_ms, meas_ms, packets)
        except Exception as exc:  # noqa: BLE001
            self.errorOccurred.emit(str(exc))
        finally:
            # Одиночный режим всегда завершается в STOPPED, даже после ошибки.
            if self._state is RunState.SINGLE:
                self.stop()

    @Slot(str, object)
    def apply_setting(self, path: str, value) -> None:
        """Применить настройку прибора из потока воркера (VISA-I/O не на UI-потоке).

        Универсальный механизм для всех панелей. Выполняется в потоке воркера
        через queued-сигнал — сериализуется с захватом кадров, поэтому транспорта
        касается только один поток.

        ``path`` — точечный путь по объектному графу драйвера, числовые токены =
        индексы. Примеры:
          - ``"channel.1.scale"``   → ``scope.channel[1].scale = value``
          - ``"timebase.scale"``    → ``scope.timebase.scale = value``
          - ``"trigger.edge.level"``→ ``scope.trigger.edge.level = value``
          - ``"trigger.sweep"``     → ``scope.trigger.sweep = value``

        После смены ``channel.N.scale|offset`` обновляет кэш масштабов контроллера.
        """
        try:
            # Действия (не setattr): одиночный запуск пакета генератора.
            if path == "dds.burst_trigger":
                self._controller.scope.dds.burst_trigger()
                return

            parts = path.split(".")
            obj = self._controller.scope
            for token in parts[:-1]:
                obj = obj[int(token)] if token.isdigit() else getattr(obj, token)
            setattr(obj, parts[-1], value)

            # после вертикального изменения канала: пересчитать кэш масштабов и
            # вернуть панели фактические значения (прибор мог авто-сменить scale
            # вслед за probe или зажать offset).
            if len(parts) == 3 and parts[0] == "channel" and parts[2] in ("scale", "offset", "probe"):
                n = int(parts[1])
                self._controller.refresh_scaling([n])
                ch = self._controller.scope.channel[n]
                self.channelReadback.emit(n, float(ch.scale), float(ch.offset), int(ch.probe))
            # смена развёртки → обновить кэш timebase (кадры зумятся под s/дел)
            elif path == "timebase.scale":
                self._controller.refresh_timebase()
            # смена триггера → обновить кэш уровня/источника (маркеры триггера)
            elif path.startswith("trigger."):
                self._controller.refresh_trigger()
        except Exception as exc:  # noqa: BLE001
            self.errorOccurred.emit(f"apply_setting({path}={value!r}): {exc}")

    # ------------------------------------------------------------------
    # Свип / multi-capture (выполняется в потоке воркера; блокирует его на
    # время свипа — это нормально, отмена идёт через потокобезопасный Event).
    # ------------------------------------------------------------------

    def cancel_sweep(self) -> None:
        """Запросить отмену свипа. Потокобезопасно — зовётся из GUI-потока."""
        self._sweep_cancel.set()

    def _sweep_sleep(self, seconds: float) -> None:
        """Выдержка с проверкой отмены (чанками по 50 мс)."""
        remaining = float(seconds)
        while remaining > 0.0 and not self._sweep_cancel.is_set():
            chunk = 0.05 if remaining > 0.05 else remaining
            time.sleep(chunk)
            remaining -= chunk

    @Slot(object)
    def run_sweep(self, config_dict) -> None:
        """Запустить свип/multi-capture. Останавливает обычный сбор на время свипа.

        ``config_dict`` — словарь от SweepPanel (parameter-путь, start/stop/step,
        dwell_s, fmt, folder). Прогресс/итог/ошибка идут сигналами.
        """
        self.stop()                      # остановить обычный сбор
        self._sweep_cancel.clear()
        try:
            cfg = SweepConfig(
                parameter=str(config_dict["parameter"]),
                start=float(config_dict["start"]),
                stop=float(config_dict["stop"]),
                step=float(config_dict["step"]),
                dwell_s=float(config_dict["dwell_s"]),
                fmt=str(config_dict["fmt"]),
                folder=str(config_dict["folder"]),
            )
            if cfg.folder:
                os.makedirs(cfg.folder, exist_ok=True)

            scope = self._controller.scope
            parts = cfg.parameter.split(".")

            def set_param(value) -> None:
                obj = scope
                for token in parts[:-1]:
                    obj = obj[int(token)] if token.isdigit() else getattr(obj, token)
                setattr(obj, parts[-1], value)

            def save(frame, i: int) -> None:
                path = capture_filename(cfg.folder, i + 1, cfg.fmt)
                export_frame(frame, path, cfg.fmt)

            result = SweepRunner().run(
                cfg,
                set_param=set_param,
                capture=self._controller.read_decoded_frame,
                save=save,
                sleep=self._sweep_sleep,
                on_progress=lambda done, total: self.sweepProgress.emit(done, total),
                should_cancel=self._sweep_cancel.is_set,
            )
            self.sweepFinished.emit(result)
        except Exception as exc:  # noqa: BLE001
            self.sweepError.emit(f"sweep: {exc}")

    # ------------------------------------------------------------------
    # Пресеты (device-I/O в потоке воркера; одноразовые операции)
    # ------------------------------------------------------------------

    @Slot(str)
    def capture_preset_to(self, path: str) -> None:
        """Снять настройки прибора и сохранить пресет в JSON-файл."""
        try:
            preset = capture_preset(self._controller.scope)
            save_preset(preset, path)
            self.presetSaved.emit(path)
        except Exception as exc:  # noqa: BLE001
            self.presetError.emit(f"save preset: {exc}")

    @Slot(object)
    def apply_preset_dict(self, preset) -> None:
        """Применить пресет (dict путь→значение) к прибору."""
        try:
            errors = apply_preset(self._controller.scope, preset)
            self.presetApplied.emit(errors)
        except Exception as exc:  # noqa: BLE001
            self.presetError.emit(f"apply preset: {exc}")

    @Slot(str)
    def send_command(self, command: str) -> None:
        """Отправить сырую SCPI-команду из терминала (в потоке воркера).

        Запрос (оканчивается на ``?``) → query; иначе write и ответ ``OK``.
        Результат — сигналом ``commandResult(команда, ответ, is_error)``.
        """
        try:
            transport = self._controller.scope.transport
            stripped = command.strip()
            if stripped.endswith("?"):
                resp = transport.query(stripped)
            else:
                transport.write(stripped)
                resp = "OK"
            self.commandResult.emit(command, str(resp), False)
        except Exception as exc:  # noqa: BLE001
            self.commandResult.emit(command, str(exc), True)
