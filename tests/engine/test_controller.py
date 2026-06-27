"""Tests for hantek_dso2d15.engine.controller.

TDD: rewritten to use hardware-verified PRIVate fixtures (2026-06-27).
All tests run through FakeTransport — no real instrument needed.

Fixtures used:
  priv_sq_ch1.pkt0.bin           — 1 channel, CH1 square 2Vpp @ 1V/div, off=0
  priv_sq_ch1_off_ch2.pkt0.bin   — 2 channels, packet 0 (uploaded=0)
  priv_sq_ch1_off_ch2.pkt1.bin   — 2 channels, packet 1 (uploaded=4000)
"""
from __future__ import annotations

import pathlib

import numpy as np
import pytest

from hantek_dso2d15.transport.fake_transport import FakeTransport
from hantek_dso2d15.scpi.scope import Scope
from hantek_dso2d15.waveform.reader import WaveformReader
from hantek_dso2d15.waveform.decode import DecodedFrame
from hantek_dso2d15.engine.controller import AcquisitionController

FIXTURE_DIR = pathlib.Path(__file__).parent.parent / "fixtures" / "waveform"


def _load(*names: str) -> list[bytes]:
    return [(FIXTURE_DIR / name).read_bytes() for name in names]


# ---------------------------------------------------------------------------
# Helpers to build controller with FakeTransport
# ---------------------------------------------------------------------------

def _make_controller_ch1():
    """1-channel controller: CH1 square wave 2Vpp, 1V/div, offset=0."""
    (pkt0,) = _load("priv_sq_ch1.pkt0.bin")
    transport = FakeTransport()
    # Two copies: enough for tests that call read_decoded_frame() twice.
    transport.set_raw(pkt0, pkt0)
    transport.set_response(":CHANnel1:SCALe?", "1.000000e+00")
    transport.set_response(":CHANnel1:OFFSet?", "0.000000e+00")
    transport.open()
    scope = Scope(transport)
    reader = WaveformReader(transport)
    controller = AcquisitionController(scope, reader)
    return controller, transport


def _make_controller_ch1ch2():
    """2-channel controller using priv_sq_ch1_off_ch2 fixture.

    CH1: square 2Vpp @ 1V/div, off=0  → Vpp ≈ 2.0V.
    CH2: flat ≈+50 count @ 5V/div, off=+10V → decoded ≈ 0V.
    Each frame needs two packets (pkt0 + pkt1); queue holds two frames.
    """
    pkt0, pkt1 = _load(
        "priv_sq_ch1_off_ch2.pkt0.bin",
        "priv_sq_ch1_off_ch2.pkt1.bin",
    )
    transport = FakeTransport()
    # Two full frames: pkt0+pkt1 twice.
    transport.set_raw(pkt0, pkt1, pkt0, pkt1)
    transport.set_response(":CHANnel1:SCALe?", "1.000000e+00")
    transport.set_response(":CHANnel1:OFFSet?", "0.000000e+00")
    transport.set_response(":CHANnel2:SCALe?", "5.000000e+00")
    transport.set_response(":CHANnel2:OFFSet?", "1.000000e+01")
    transport.open()
    scope = Scope(transport)
    reader = WaveformReader(transport)
    controller = AcquisitionController(scope, reader)
    return controller, transport


# ---------------------------------------------------------------------------
# Test: read_decoded_frame — single channel CH1
# ---------------------------------------------------------------------------

class TestReadDecodedFrameSingleChannel:
    def test_returns_decoded_frame_instance(self):
        """read_decoded_frame() must return a DecodedFrame."""
        controller, _ = _make_controller_ch1()
        result = controller.read_decoded_frame()
        assert isinstance(result, DecodedFrame)

    def test_channels_set_is_ch1_only(self):
        """enable='1000' → only CH1 present; channels keys must be {1}."""
        controller, _ = _make_controller_ch1()
        result = controller.read_decoded_frame()
        assert set(result.channels.keys()) == {1}

    def test_ch1_vpp_approx_2v(self):
        """Square wave ±25 count @ 1V/div → Vpp ≈ 2.0V (within ±0.15V).

        Hardware fixture has min=-26, max=27 (53 counts = 2.12V with noise).
        """
        controller, _ = _make_controller_ch1()
        result = controller.read_decoded_frame()
        ch1 = result.channels[1]
        vpp = float(np.max(ch1) - np.min(ch1))
        assert abs(vpp - 2.0) < 0.15, f"CH1 Vpp={vpp:.4f}V, expected ≈2.0V (±0.15V)"


# ---------------------------------------------------------------------------
# Test: read_decoded_frame — two channels CH1 + CH2
# ---------------------------------------------------------------------------

class TestReadDecodedFrameTwoChannels:
    def test_returns_decoded_frame_instance(self):
        controller, _ = _make_controller_ch1ch2()
        result = controller.read_decoded_frame()
        assert isinstance(result, DecodedFrame)

    def test_channels_set_is_ch1_and_ch2(self):
        """enable='1100' → both channels present; channels keys must be {1, 2}.

        The old dedup quirk (collapsing identical payloads to CH1 only) has been
        removed; distinct hardware channels must yield distinct keys.
        """
        controller, _ = _make_controller_ch1ch2()
        result = controller.read_decoded_frame()
        assert set(result.channels.keys()) == {1, 2}

    def test_ch1_vpp_approx_2v(self):
        """CH1 de-interleaved square wave must decode to Vpp ≈ 2.0V (within ±0.15V)."""
        controller, _ = _make_controller_ch1ch2()
        result = controller.read_decoded_frame()
        ch1 = result.channels[1]
        vpp = float(np.max(ch1) - np.min(ch1))
        assert abs(vpp - 2.0) < 0.15, f"CH1 Vpp={vpp:.4f}V, expected ≈2.0V (±0.15V)"

    def test_ch2_mean_approx_0v(self):
        """CH2 de-interleaved flat ≈+50 count @ 5V/div, off=+10V → mean ≈ 0V.

        Calibration: 50/25 * 5.0 − 10.0 = 10.0 − 10.0 = 0.0V.
        Verifies de-interleave correctness: CH1≠CH2 (square vs flat).
        """
        controller, _ = _make_controller_ch1ch2()
        result = controller.read_decoded_frame()
        ch2 = result.channels[2]
        mean_v = float(np.mean(ch2))
        assert abs(mean_v - 0.0) < 0.2, f"CH2 mean={mean_v:.4f}V, expected ≈0V (±0.2V)"


# ---------------------------------------------------------------------------
# Test: force() — sends :TRIGger:FORCe
# ---------------------------------------------------------------------------

class TestForce:
    def test_force_sends_trigger_force(self):
        """`force()` must write ':TRIGger:FORCe' to the transport."""
        controller, transport = _make_controller_ch1()
        transport.reset()
        controller.force()
        assert ":TRIGger:FORCe" in transport.writes

    def test_force_only_writes_one_command(self):
        """force() must write exactly one command."""
        controller, transport = _make_controller_ch1()
        transport.reset()
        controller.force()
        assert len(transport.writes) == 1


# ---------------------------------------------------------------------------
# Test: set_sweep(mode) — sends :TRIGger:SWEep {mode}
# ---------------------------------------------------------------------------

class TestSetSweep:
    def test_set_sweep_normal(self):
        """`set_sweep('NORMal')` must write ':TRIGger:SWEep NORMal'."""
        controller, transport = _make_controller_ch1()
        transport.reset()
        controller.set_sweep("NORMal")
        assert ":TRIGger:SWEep NORMal" in transport.writes

    def test_set_sweep_auto(self):
        """`set_sweep('AUTO')` must write ':TRIGger:SWEep AUTO'."""
        controller, transport = _make_controller_ch1()
        transport.reset()
        controller.set_sweep("AUTO")
        assert ":TRIGger:SWEep AUTO" in transport.writes

    def test_set_sweep_single(self):
        """`set_sweep('SINGle')` must write ':TRIGger:SWEep SINGle'."""
        controller, transport = _make_controller_ch1()
        transport.reset()
        controller.set_sweep("SINGle")
        assert ":TRIGger:SWEep SINGle" in transport.writes

    def test_set_sweep_invalid_raises(self):
        """Invalid sweep mode must raise ValueError (from Trigger.sweep setter)."""
        controller, _ = _make_controller_ch1()
        with pytest.raises(ValueError):
            controller.set_sweep("BOGUS")


# ---------------------------------------------------------------------------
# Test: constructor accepts custom decoder
# ---------------------------------------------------------------------------

class TestCustomDecoder:
    def test_custom_decoder_is_called(self):
        """AcquisitionController must forward (frame, scales, offsets) to injected decoder."""
        (pkt0,) = _load("priv_sq_ch1.pkt0.bin")
        transport = FakeTransport()
        transport.set_raw(pkt0)
        transport.set_response(":CHANnel1:SCALe?", "1.000000e+00")
        transport.set_response(":CHANnel1:OFFSet?", "0.000000e+00")
        transport.open()
        scope = Scope(transport)
        reader = WaveformReader(transport)

        sentinel = object()
        calls: list = []

        def fake_decoder(frame, scales, offsets):
            calls.append((frame, scales, offsets))
            return sentinel  # type: ignore[return-value]

        controller = AcquisitionController(scope, reader, decoder=fake_decoder)
        result = controller.read_decoded_frame()

        assert result is sentinel
        assert len(calls) == 1
        _, scales, offsets = calls[0]
        assert scales == {1: 1.0}
        assert offsets == {1: 0.0}


# ---------------------------------------------------------------------------
# Test: refresh_scaling caches scale/offset (fps-optimisation)
# ---------------------------------------------------------------------------

def test_refresh_scaling_caches_values():
    """After refresh_scaling([1]), read_decoded_frame() must not re-query :CHANnel1:SCALe?."""
    controller, transport = _make_controller_ch1()
    controller.refresh_scaling([1])
    before = sum(1 for q in transport.queries if q == ":CHANnel1:SCALe?")
    # Frame read must use cache — no additional :SCALe? queries.
    controller.read_decoded_frame()
    after = sum(1 for q in transport.queries if q == ":CHANnel1:SCALe?")
    assert after == before, (
        f"После refresh_scaling кадр не должен повторно запрашивать :CHANnel1:SCALe? "
        f"(before={before}, after={after})"
    )


def test_clear_scaling_cache_re_enables_scale_query():
    """After clear_scaling_cache(), the next read_decoded_frame() must re-query :CHANnel1:SCALe?."""
    controller, transport = _make_controller_ch1()
    controller.refresh_scaling([1])
    controller.clear_scaling_cache()
    before = sum(1 for q in transport.queries if q == ":CHANnel1:SCALe?")
    controller.read_decoded_frame()
    after = sum(1 for q in transport.queries if q == ":CHANnel1:SCALe?")
    assert after > before, (
        "После clear_scaling_cache() следующий кадр должен запросить :CHANnel1:SCALe? "
        f"(before={before}, after={after})"
    )


# ---------------------------------------------------------------------------
# Test: timebase кэш попадает в DecodedFrame (для зума окна графиком)
# ---------------------------------------------------------------------------

def test_refresh_timebase_populates_frame():
    """refresh_timebase() кэширует :TIMebase:SCALe? и кадр получает .timebase."""
    controller, transport = _make_controller_ch1()
    transport.set_response(":TIMebase:SCALe?", "5.000000e-08")
    controller.refresh_timebase()
    frame = controller.read_decoded_frame()
    assert frame.timebase == 5e-8


def test_read_decoded_frame_lazy_timebase():
    """Без явного refresh первый кадр лениво запрашивает развёртку."""
    controller, transport = _make_controller_ch1()
    transport.set_response(":TIMebase:SCALe?", "2.000000e-09")
    frame = controller.read_decoded_frame()
    assert frame.timebase == 2e-9


# ---------------------------------------------------------------------------
# Фейки для тестирования read_measurements (без реального прибора)
# ---------------------------------------------------------------------------

class _FakeMeasure:
    """Фейк scope.measure — имитирует интерфейс MeasurementDriver.

    Параметры
    ---------
    responses:
        dict[(channel, item)] -> float — возвращаемые значения.
    raises:
        dict[(channel, item)] -> Exception — исключения для конкретных пар.
    """

    def __init__(self, responses: dict | None = None, raises: dict | None = None):
        self.enable: bool = False
        self._responses: dict = responses or {}
        self._raises: dict = raises or {}

    def read_item(self, channel: int, item: str) -> float:
        key = (channel, item)
        if key in self._raises:
            raise self._raises[key]
        return self._responses[key]


class _FakeScopeWithMeasure:
    """Минимальный фейк scope с поддержкой .measure для read_measurements."""

    def __init__(self, measure: _FakeMeasure):
        self.measure = measure
        self._channels: dict = {}

    @property
    def channel(self):
        return self._channels


class _FakeReaderStub:
    """Заглушка reader — не используется в тестах read_measurements."""

    def read_frame(self):
        raise RuntimeError("_FakeReaderStub.read_frame не используется в этих тестах")


# ---------------------------------------------------------------------------
# Test: read_measurements — опрос автоизмерений
# ---------------------------------------------------------------------------

class TestReadMeasurements:
    """Тесты AcquisitionController.read_measurements()."""

    def _make_controller(
        self,
        responses: dict | None = None,
        raises: dict | None = None,
    ) -> tuple:
        """Собрать контроллер с фейк-scope и фейк-measure."""
        measure = _FakeMeasure(responses, raises)
        scope = _FakeScopeWithMeasure(measure)
        reader = _FakeReaderStub()
        controller = AcquisitionController(scope, reader)
        return controller, measure

    def test_empty_requests_returns_empty_list(self):
        """Пустой список requests → пустой список в ответ."""
        controller, _ = self._make_controller()
        result = controller.read_measurements([])
        assert result == []

    def test_single_successful_item(self):
        """Один запрос — один словарь с корректными channel/item/value."""
        controller, _ = self._make_controller(responses={(1, "FREQ"): 1000.0})
        result = controller.read_measurements([(1, "FREQ")])
        assert result == [{"channel": 1, "item": "FREQ", "value": 1000.0}]

    def test_exception_yields_none_value(self):
        """I/O-ошибка в read_item → value = None, исключение не пробрасывается."""
        controller, _ = self._make_controller(
            raises={(1, "FREQ"): RuntimeError("transport error")}
        )
        result = controller.read_measurements([(1, "FREQ")])
        assert result == [{"channel": 1, "item": "FREQ", "value": None}]

    def test_multiple_requests_preserves_order(self):
        """Порядок результата совпадает с порядком requests."""
        controller, _ = self._make_controller(
            responses={(1, "FREQ"): 500.0, (2, "VPP"): 3.14, (1, "MEAN"): 0.0}
        )
        requests = [(1, "FREQ"), (2, "VPP"), (1, "MEAN")]
        result = controller.read_measurements(requests)
        assert result == [
            {"channel": 1, "item": "FREQ", "value": 500.0},
            {"channel": 2, "item": "VPP", "value": 3.14},
            {"channel": 1, "item": "MEAN", "value": 0.0},
        ]

    def test_mixed_success_and_failure(self):
        """Часть успешна, часть бросает — упавшие получают value=None."""
        controller, _ = self._make_controller(
            responses={(1, "FREQ"): 1000.0},
            raises={(2, "VPP"): IOError("read error")},
        )
        requests = [(1, "FREQ"), (2, "VPP")]
        result = controller.read_measurements(requests)
        assert result == [
            {"channel": 1, "item": "FREQ", "value": 1000.0},
            {"channel": 2, "item": "VPP", "value": None},
        ]

    def test_does_not_modify_scaling_cache(self):
        """read_measurements не должен трогать кэш масштабов."""
        controller, _ = self._make_controller(responses={(1, "FREQ"): 42.0})
        controller._scale_cache[1] = 99.0
        controller._offset_cache[1] = -5.0
        controller.read_measurements([(1, "FREQ")])
        # Кэш должен остаться без изменений
        assert controller._scale_cache[1] == 99.0
        assert controller._offset_cache[1] == -5.0

    def test_result_keys_are_channel_item_value(self):
        """Каждый элемент результата содержит ровно три ключа: channel, item, value."""
        controller, _ = self._make_controller(responses={(1, "RMS"): 0.707})
        result = controller.read_measurements([(1, "RMS")])
        assert len(result) == 1
        assert set(result[0].keys()) == {"channel", "item", "value"}
