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
