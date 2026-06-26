"""Tests for hantek_dso2d15.engine.controller — Task E2.

TDD: tests written before implementation. Tests use real fixture packets
(hardware-verified 2026-06-27) through FakeTransport — no real instrument needed.
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
    """Single-channel controller: CH1 DC +1.0V fixture."""
    pkt0, pkt1 = _load(
        "frame_dc_p1v0_ch1.pkt0.bin",
        "frame_dc_p1v0_ch1.pkt1.bin",
    )
    transport = FakeTransport()
    # Queue packets twice to be safe (reader may consume header + data)
    transport.set_raw(pkt0, pkt1, pkt0, pkt1)
    transport.set_response(":CHANnel1:SCALe?", "1.000000e+00")
    transport.set_response(":CHANnel1:OFFSet?", "0.000000e+00")
    transport.open()
    scope = Scope(transport)
    reader = WaveformReader(transport)
    controller = AcquisitionController(scope, reader)
    return controller, transport


def _make_controller_ch1ch2():
    """Two-channel controller: CH1+CH2 DC +1.0V fixture."""
    pkt0, pkt1, pkt2 = _load(
        "frame_dc_p1v0_ch1ch2.pkt0.bin",
        "frame_dc_p1v0_ch1ch2.pkt1.bin",
        "frame_dc_p1v0_ch1ch2.pkt2.bin",
    )
    transport = FakeTransport()
    transport.set_raw(pkt0, pkt1, pkt2, pkt0, pkt1, pkt2)
    transport.set_response(":CHANnel1:SCALe?", "1.000000e+00")
    transport.set_response(":CHANnel1:OFFSet?", "0.000000e+00")
    transport.set_response(":CHANnel2:SCALe?", "1.000000e+00")
    transport.set_response(":CHANnel2:OFFSet?", "0.000000e+00")
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
        """enabled_channels for single-CH fixture must be {1}."""
        controller, _ = _make_controller_ch1()
        result = controller.read_decoded_frame()
        assert set(result.channels.keys()) == {1}

    def test_ch1_mean_approx_1v(self):
        """DDS DC +1.0V → CH1 mean must be within ±0.1V of 1.0V."""
        controller, _ = _make_controller_ch1()
        result = controller.read_decoded_frame()
        mean_v = float(np.mean(result.channels[1]))
        assert abs(mean_v - 1.0) < 0.1, f"mean={mean_v:.4f}, expected ≈1.0V"


# ---------------------------------------------------------------------------
# Test: read_decoded_frame — two channels CH1 + CH2
# ---------------------------------------------------------------------------

class TestReadDecodedFrameTwoChannels:
    def test_returns_decoded_frame_instance(self):
        controller, _ = _make_controller_ch1ch2()
        result = controller.read_decoded_frame()
        assert isinstance(result, DecodedFrame)

    def test_channels_set_is_ch1_and_ch2(self):
        """Two-channel fixture must decode channels {1, 2}."""
        controller, _ = _make_controller_ch1ch2()
        result = controller.read_decoded_frame()
        assert set(result.channels.keys()) == {1, 2}

    def test_ch1_mean_approx_1v(self):
        controller, _ = _make_controller_ch1ch2()
        result = controller.read_decoded_frame()
        mean_v = float(np.mean(result.channels[1]))
        assert abs(mean_v - 1.0) < 0.1, f"CH1 mean={mean_v:.4f}, expected ≈1.0V"


# ---------------------------------------------------------------------------
# Test: force() — sends :TRIGger:FORCe
# ---------------------------------------------------------------------------

class TestForce:
    def test_force_sends_trigger_force(self):
        """`force()` must write ':TRIGger:FORCe' to the transport."""
        controller, transport = _make_controller_ch1()
        transport.reset()  # clear any prior writes
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
        controller, transport = _make_controller_ch1()
        with pytest.raises(ValueError):
            controller.set_sweep("BOGUS")


# ---------------------------------------------------------------------------
# Test: constructor accepts custom decoder
# ---------------------------------------------------------------------------

class TestCustomDecoder:
    def test_custom_decoder_is_called(self):
        """AcquisitionController must accept an injected decoder callable."""
        pkt0, pkt1 = _load(
            "frame_dc_p1v0_ch1.pkt0.bin",
            "frame_dc_p1v0_ch1.pkt1.bin",
        )
        transport = FakeTransport()
        transport.set_raw(pkt0, pkt1, pkt0, pkt1)
        transport.set_response(":CHANnel1:SCALe?", "1.000000e+00")
        transport.set_response(":CHANnel1:OFFSet?", "0.000000e+00")
        transport.open()
        scope = Scope(transport)
        reader = WaveformReader(transport)

        sentinel = object()
        calls = []

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
