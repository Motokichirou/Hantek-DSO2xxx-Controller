"""Tests for EngineWorker (Task E3).

Tests use a lightweight stub controller — no real instrument or threads needed.
QCoreApplication is created once at module scope.
"""
from __future__ import annotations

import pytest
from PySide6.QtCore import QCoreApplication

from hantek_dso2d15.engine.states import RunState
from hantek_dso2d15.engine.worker import EngineWorker


# ---------------------------------------------------------------------------
# Module-scoped QCoreApplication (one per process)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def qapp():
    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication([])
    return app


# ---------------------------------------------------------------------------
# Stub controllers
# ---------------------------------------------------------------------------

class _OkController:
    """Returns the same marker object every call."""

    def __init__(self, marker):
        self._marker = marker

    def read_decoded_frame(self):
        return self._marker


class _ErrorController:
    """Always raises the given exception."""

    def __init__(self, message: str = "boom"):
        self._message = message

    def read_decoded_frame(self):
        raise RuntimeError(self._message)


# ---------------------------------------------------------------------------
# Test 1 — capture_once() with successful stub emits frameReady exactly once
# ---------------------------------------------------------------------------

def test_capture_once_emits_frame_ready(qapp):
    marker = object()
    worker = EngineWorker(_OkController(marker))

    captured_frames = []
    captured_errors = []
    worker.frameReady.connect(captured_frames.append)
    worker.errorOccurred.connect(captured_errors.append)

    worker.capture_once()

    assert len(captured_frames) == 1, "frameReady должен быть испущен ровно один раз"
    assert captured_frames[0] is marker, "frameReady должен нести именно маркер"
    assert len(captured_errors) == 0, "errorOccurred не должен быть испущен"


# ---------------------------------------------------------------------------
# Test 2 — single() yields exactly one frame, then state=STOPPED + stateChanged
# ---------------------------------------------------------------------------

def test_single_emits_one_frame_then_stops(qapp):
    marker = object()
    worker = EngineWorker(_OkController(marker))

    captured_frames = []
    state_changes = []
    worker.frameReady.connect(captured_frames.append)
    worker.stateChanged.connect(state_changes.append)

    worker.single()

    assert len(captured_frames) == 1, "single() должен дать ровно один кадр"
    assert captured_frames[0] is marker
    assert worker.state is RunState.STOPPED, "после single() state должен быть STOPPED"
    # stateChanged должен быть испущен хотя бы дважды: SINGLE → STOPPED
    assert RunState.SINGLE in state_changes, "stateChanged(SINGLE) должен быть испущен"
    assert RunState.STOPPED in state_changes, "stateChanged(STOPPED) должен быть испущен"


# ---------------------------------------------------------------------------
# Test 3 — error in controller: errorOccurred emitted, frameReady NOT emitted
# ---------------------------------------------------------------------------

def test_capture_once_error_emits_error_occurred(qapp):
    worker = EngineWorker(_ErrorController("boom"))

    captured_frames = []
    captured_errors = []
    worker.frameReady.connect(captured_frames.append)
    worker.errorOccurred.connect(captured_errors.append)

    worker.capture_once()

    assert len(captured_frames) == 0, "frameReady НЕ должен быть испущен при ошибке"
    assert len(captured_errors) == 1, "errorOccurred должен быть испущен ровно один раз"
    assert captured_errors[0] == "boom", "errorOccurred должен нести текст исключения"


# ---------------------------------------------------------------------------
# Test 4 — start() → RUNNING; stop() → STOPPED (no real timer needed)
# ---------------------------------------------------------------------------

def test_start_stop_state_transitions(qapp):
    worker = EngineWorker(_OkController(object()))

    state_changes = []
    worker.stateChanged.connect(state_changes.append)

    assert worker.state is RunState.STOPPED, "начальное состояние должно быть STOPPED"

    worker.start()
    assert worker.state is RunState.RUNNING, "после start() state должен быть RUNNING"
    assert RunState.RUNNING in state_changes

    worker.stop()
    assert worker.state is RunState.STOPPED, "после stop() state должен быть STOPPED"
    assert RunState.STOPPED in state_changes


# ---------------------------------------------------------------------------
# Test 5 — single() + ошибка контроллера: НЕ залипает в SINGLE, уходит в STOPPED
# ---------------------------------------------------------------------------

def test_single_with_error_returns_to_stopped(qapp):
    worker = EngineWorker(_ErrorController("boom"))

    captured_frames = []
    captured_errors = []
    worker.frameReady.connect(captured_frames.append)
    worker.errorOccurred.connect(captured_errors.append)

    worker.single()

    assert len(captured_frames) == 0, "frameReady не должен испускаться при ошибке"
    assert captured_errors == ["boom"], "errorOccurred должен нести текст исключения"
    assert worker.state is RunState.STOPPED, (
        "single() при ошибке не должен залипать в SINGLE — должен уйти в STOPPED"
    )


# ---------------------------------------------------------------------------
# Test 6 — apply_setting(path, value): навигация по графу драйвера
# ---------------------------------------------------------------------------

class _FakeChannel:
    def __init__(self):
        self.scale = 1.0
        self.offset = 0.0
        self.probe = 1
        self.coupling = None


class _FakeTimebase:
    def __init__(self):
        self.scale = None


class _FakeScope:
    def __init__(self):
        self._ch = {1: _FakeChannel(), 2: _FakeChannel()}
        self.timebase = _FakeTimebase()

    @property
    def channel(self):
        return self._ch


class _ScopeController:
    """Stub-контроллер с .scope и refresh_scaling для apply_setting."""
    def __init__(self):
        self.scope = _FakeScope()
        self.refreshed = []

    def refresh_scaling(self, channels):
        self.refreshed.append(list(channels))

    def read_decoded_frame(self):
        return object()


def test_apply_setting_channel_scale(qapp):
    c = _ScopeController()
    worker = EngineWorker(c)
    worker.apply_setting("channel.1.scale", 0.5)
    assert c.scope.channel[1].scale == 0.5
    # смена scale канала -> refresh_scaling([1])
    assert c.refreshed == [[1]]


def test_apply_setting_nested_and_no_refresh(qapp):
    c = _ScopeController()
    worker = EngineWorker(c)
    worker.apply_setting("timebase.scale", 1e-3)
    worker.apply_setting("channel.2.coupling", "AC")
    assert c.scope.timebase.scale == 1e-3
    assert c.scope.channel[2].coupling == "AC"
    # coupling/timebase не триггерят refresh_scaling
    assert c.refreshed == []


def test_apply_setting_error_emits_error(qapp):
    c = _ScopeController()
    worker = EngineWorker(c)
    errors = []
    worker.errorOccurred.connect(errors.append)
    worker.apply_setting("channel.9.scale", 1.0)  # нет канала 9
    assert len(errors) == 1 and "apply_setting" in errors[0]


def test_apply_setting_emits_channel_readback(qapp):
    """После вертикального изменения воркер возвращает фактические scale/offset/probe."""
    c = _ScopeController()
    c.scope.channel[1].scale = 2.0
    c.scope.channel[1].offset = 0.5
    c.scope.channel[1].probe = 10
    worker = EngineWorker(c)
    seen = []
    worker.channelReadback.connect(lambda n, s, o, p: seen.append((n, s, o, p)))
    worker.apply_setting("channel.1.probe", 10)
    assert seen == [(1, 2.0, 0.5, 10)]


# ---------------------------------------------------------------------------
# Фейки для тестирования set_measurements / measurementsReady
# ---------------------------------------------------------------------------

class _FakeMeasureW:
    """Фейк scope.measure для тестов воркера — имитирует MeasurementDriver.enable."""

    def __init__(self):
        self.enable: bool = False

    def read_item(self, channel: int, item: str) -> float:
        raise NotImplementedError("_FakeMeasureW.read_item не используется в этих тестах")


class _FakeScopeW:
    """Фейк scope с поддержкой .measure для тестов воркера."""

    def __init__(self):
        self.measure = _FakeMeasureW()
        self._channels: dict = {}

    @property
    def channel(self):
        return self._channels


class _ControllerWithMeasure:
    """Stub-контроллер для тестирования измерительного пути воркера.

    Всегда возвращает успешный кадр. read_measurements() возвращает фиктивный
    payload или бросает исключение (если raise_measurements=True).
    """

    def __init__(
        self,
        marker=None,
        raise_measurements: bool = False,
    ):
        self._marker = marker or object()
        self.scope = _FakeScopeW()
        self._raise_measurements = raise_measurements
        self.measurement_calls: list = []  # журнал вызовов read_measurements

    def read_decoded_frame(self):
        return self._marker

    def read_measurements(self, requests: list) -> list:
        self.measurement_calls.append(list(requests))
        if self._raise_measurements:
            raise RuntimeError("measurement error")
        return [
            {"channel": int(ch), "item": str(item), "value": 1.0}
            for ch, item in requests
        ]

    def refresh_scaling(self, channels):
        pass


class _ControllerErrorFrame:
    """Stub-контроллер, который всегда падает на read_decoded_frame."""

    def __init__(self):
        self.scope = _FakeScopeW()
        self.measurement_calls: list = []

    def read_decoded_frame(self):
        raise RuntimeError("frame error")

    def read_measurements(self, requests: list) -> list:
        self.measurement_calls.append(list(requests))
        return []

    def refresh_scaling(self, channels):
        pass


# ---------------------------------------------------------------------------
# Test 7 — set_measurements: хранение и нормализация запросов
# ---------------------------------------------------------------------------

def test_set_measurements_default_empty(qapp):
    """По умолчанию _measure_requests пуст — измерения не активны."""
    c = _ControllerWithMeasure()
    worker = EngineWorker(c)
    assert worker._measure_requests == []


def test_set_measurements_stores_requests(qapp):
    """set_measurements сохраняет список запросов."""
    c = _ControllerWithMeasure()
    worker = EngineWorker(c)
    worker.set_measurements([(1, "FREQ"), (2, "VPP")])
    assert worker._measure_requests == [(1, "FREQ"), (2, "VPP")]


def test_set_measurements_normalizes_to_tuple(qapp):
    """Элементы нормализуются к tuple(int, str) — список вместо кортежа тоже принимается."""
    c = _ControllerWithMeasure()
    worker = EngineWorker(c)
    worker.set_measurements([[1, "FREQ"]])  # список вместо кортежа
    assert worker._measure_requests == [(1, "FREQ")]
    assert isinstance(worker._measure_requests[0], tuple)


def test_set_measurements_non_empty_enables_measure(qapp):
    """Непустой список запросов → measure.enable выставляется в True."""
    c = _ControllerWithMeasure()
    worker = EngineWorker(c)
    assert c.scope.measure.enable is False
    worker.set_measurements([(1, "FREQ")])
    assert c.scope.measure.enable is True


def test_set_measurements_empty_does_not_enable_measure(qapp):
    """Пустой список запросов → measure.enable не трогается (остаётся False)."""
    c = _ControllerWithMeasure()
    worker = EngineWorker(c)
    worker.set_measurements([])
    assert c.scope.measure.enable is False


def test_set_measurements_replaces_previous(qapp):
    """Повторный вызов set_measurements заменяет предыдущие запросы."""
    c = _ControllerWithMeasure()
    worker = EngineWorker(c)
    worker.set_measurements([(1, "FREQ"), (2, "VPP")])
    worker.set_measurements([(1, "MEAN")])
    assert worker._measure_requests == [(1, "MEAN")]


# ---------------------------------------------------------------------------
# Test 8 — measurementsReady: эмиссия после успешного кадра
# ---------------------------------------------------------------------------

def test_measurements_not_emitted_when_no_requests(qapp):
    """Пустой _measure_requests → measurementsReady НЕ эмитится."""
    c = _ControllerWithMeasure()
    worker = EngineWorker(c)

    payloads = []
    worker.measurementsReady.connect(payloads.append)

    worker.capture_once()

    assert payloads == [], "measurementsReady не должен эмитится без активных запросов"


def test_measurements_emitted_after_successful_frame(qapp):
    """После успешного кадра measurementsReady эмитится с корректным payload."""
    marker = object()
    c = _ControllerWithMeasure(marker=marker)
    worker = EngineWorker(c)
    worker.set_measurements([(1, "FREQ")])

    frames = []
    payloads = []
    worker.frameReady.connect(frames.append)
    worker.measurementsReady.connect(payloads.append)

    worker.capture_once()

    assert len(frames) == 1, "frameReady должен быть испущен"
    assert len(payloads) == 1, "measurementsReady должен быть испущен ровно один раз"
    payload = payloads[0]
    assert isinstance(payload, list)
    assert len(payload) == 1
    assert payload[0] == {"channel": 1, "item": "FREQ", "value": 1.0}


def test_measurements_payload_structure(qapp):
    """Каждый элемент payload содержит ровно три ключа: channel, item, value."""
    c = _ControllerWithMeasure()
    worker = EngineWorker(c)
    worker.set_measurements([(1, "FREQ"), (2, "VPP")])

    payloads = []
    worker.measurementsReady.connect(payloads.append)

    worker.capture_once()

    assert len(payloads) == 1
    payload = payloads[0]
    assert len(payload) == 2
    for item in payload:
        assert set(item.keys()) == {"channel", "item", "value"}


def test_measurements_emitted_in_single_mode(qapp):
    """measurementsReady эмитится и в режиме single() (не только в run-цикле)."""
    c = _ControllerWithMeasure()
    worker = EngineWorker(c)
    worker.set_measurements([(2, "VPP")])

    payloads = []
    worker.measurementsReady.connect(payloads.append)

    worker.single()

    assert len(payloads) == 1, "measurementsReady должен эмититься при single()"
    assert payloads[0][0]["channel"] == 2
    assert payloads[0][0]["item"] == "VPP"


def test_measurements_error_does_not_stop_cycle(qapp):
    """Исключение в read_measurements → errorOccurred, кадр всё равно испускается."""
    c = _ControllerWithMeasure(raise_measurements=True)
    worker = EngineWorker(c)
    worker.set_measurements([(1, "FREQ")])

    errors = []
    frames = []
    payloads = []
    worker.errorOccurred.connect(errors.append)
    worker.frameReady.connect(frames.append)
    worker.measurementsReady.connect(payloads.append)

    worker.capture_once()

    # Кадр должен быть испущен — ошибка измерений не ломает кадровый путь
    assert len(frames) == 1, "frameReady должен быть испущен несмотря на ошибку измерений"
    # Ошибка измерений должна быть эмитирована
    assert len(errors) == 1, "errorOccurred должен быть испущен при ошибке read_measurements"
    assert "measurement error" in errors[0]
    # measurementsReady не эмитируется при ошибке
    assert payloads == []


def test_measurements_not_called_when_frame_fails(qapp):
    """Если read_decoded_frame падает — read_measurements не вызывается."""
    c = _ControllerErrorFrame()
    worker = EngineWorker(c)
    worker._measure_requests = [(1, "FREQ")]  # напрямую, минуя set_measurements (нет measure.enable)

    errors = []
    payloads = []
    worker.errorOccurred.connect(errors.append)
    worker.measurementsReady.connect(payloads.append)

    worker.capture_once()

    assert "frame error" in errors[0], "errorOccurred должен нести текст ошибки кадра"
    assert payloads == [], "measurementsReady не должен эмититься при ошибке кадра"
    assert c.measurement_calls == [], "read_measurements не должен вызываться при ошибке кадра"


# ---------------------------------------------------------------------------
# send_command — сырой SCPI из терминала
# ---------------------------------------------------------------------------

class _FakeTransportT:
    def __init__(self, response="RESP"):
        self.writes = []
        self.queries = []
        self._response = response
        self.fail = False

    def write(self, cmd):
        if self.fail:
            raise RuntimeError("io fail")
        self.writes.append(cmd)

    def query(self, cmd):
        if self.fail:
            raise RuntimeError("io fail")
        self.queries.append(cmd)
        return self._response


class _ScopeT:
    def __init__(self, transport):
        self.transport = transport


class _ControllerT:
    def __init__(self, transport):
        self.scope = _ScopeT(transport)


def _make_cmd_worker(response="RESP"):
    t = _FakeTransportT(response)
    return EngineWorker(_ControllerT(t)), t


def test_send_command_query(qapp):
    """Команда с '?' идёт через query; результат — (cmd, ответ, False)."""
    worker, t = _make_cmd_worker("undefined,DSO2D15")
    results = []
    worker.commandResult.connect(lambda c, r, e: results.append((c, r, e)))
    worker.send_command("*IDN?")
    assert t.queries == ["*IDN?"]
    assert t.writes == []
    assert results == [("*IDN?", "undefined,DSO2D15", False)]


def test_send_command_write_returns_ok(qapp):
    """Команда без '?' идёт через write; ответ 'OK'."""
    worker, t = _make_cmd_worker()
    results = []
    worker.commandResult.connect(lambda c, r, e: results.append((c, r, e)))
    worker.send_command(":DDS:SWITch ON")
    assert t.writes == [":DDS:SWITch ON"]
    assert t.queries == []
    assert results == [(":DDS:SWITch ON", "OK", False)]


def test_send_command_error_flagged(qapp):
    """Исключение транспорта -> commandResult с is_error=True."""
    worker, t = _make_cmd_worker()
    t.fail = True
    results = []
    worker.commandResult.connect(lambda c, r, e: results.append((c, r, e)))
    worker.send_command("*IDN?")
    assert len(results) == 1
    assert results[0][0] == "*IDN?"
    assert results[0][2] is True  # is_error
