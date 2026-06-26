"""Tests for hantek_dso2d15.waveform.decode — Task W5.

TDD: tests written before implementation. All tests should FAIL before
decode.py exists, then PASS after implementation.

Fixtures (hardware-verified, 2026-06-27):
  frame_dc_p1v0_ch1.pkt0.bin  — header, CH1 only, DDS DC +1.0V
  frame_dc_p1v0_ch1.pkt1.bin  — data, CH1, ~4000 samples ≈ +25 counts (+1.0V)
  frame_dc_p1v0_ch1ch2.pkt0.bin/.pkt1.bin/.pkt2.bin — header + 2 data pkts
"""
from __future__ import annotations

import pathlib
import numpy as np
import pytest

from hantek_dso2d15.waveform.decode import DecodedFrame, decode_frame
from hantek_dso2d15.waveform.reader import RawFrame, WaveformReader
from hantek_dso2d15.transport.fake_transport import FakeTransport

FIXTURE_DIR = pathlib.Path(__file__).parent.parent / "fixtures" / "waveform"


def _load(*names: str) -> list[bytes]:
    """Load fixture binary files in order."""
    return [(FIXTURE_DIR / name).read_bytes() for name in names]


# ---------------------------------------------------------------------------
# Helpers: build RawFrame via WaveformReader + FakeTransport
# ---------------------------------------------------------------------------

def _make_frame_ch1() -> RawFrame:
    pkt0, pkt1 = _load(
        "frame_dc_p1v0_ch1.pkt0.bin",
        "frame_dc_p1v0_ch1.pkt1.bin",
    )
    transport = FakeTransport()
    transport.open()
    # Queue enough packets for the reader: header + data
    # The reader may retry, so supply the sequence twice to be safe.
    transport.set_raw(pkt0, pkt1, pkt0, pkt1)
    reader = WaveformReader(transport)
    return reader.read_frame()


def _make_frame_ch1ch2() -> RawFrame:
    pkt0, pkt1, pkt2 = _load(
        "frame_dc_p1v0_ch1ch2.pkt0.bin",
        "frame_dc_p1v0_ch1ch2.pkt1.bin",
        "frame_dc_p1v0_ch1ch2.pkt2.bin",
    )
    transport = FakeTransport()
    transport.open()
    transport.set_raw(pkt0, pkt1, pkt2, pkt0, pkt1, pkt2)
    reader = WaveformReader(transport)
    return reader.read_frame()


# ---------------------------------------------------------------------------
# Synthetic RawFrame helpers (for deterministic unit tests)
# ---------------------------------------------------------------------------

def _make_synthetic_frame(
    enabled_channels: list[int],
    payloads: list[bytes],
    srate: float = 1.25e6,
    triggered: bool = False,
) -> RawFrame:
    """Build a RawFrame synthetically without touching the transport."""
    from hantek_dso2d15.waveform.header import WaveHeader

    header = WaveHeader(
        running=True,
        triggered=triggered,
        offsets_counts=[0, 0, 0, 0],
        enabled_channels=enabled_channels,
        srate=srate,
    )
    return RawFrame(header=header, data_payloads=payloads)


# ---------------------------------------------------------------------------
# Test: DecodedFrame is a dataclass with expected fields
# ---------------------------------------------------------------------------

class TestDecodedFrameStructure:
    def test_has_required_fields(self) -> None:
        """DecodedFrame must expose time, channels, srate, triggered."""
        frame = _make_frame_ch1()
        result = decode_frame(frame, {1: 1.0})

        assert hasattr(result, "time")
        assert hasattr(result, "channels")
        assert hasattr(result, "srate")
        assert hasattr(result, "triggered")

    def test_is_decoded_frame_instance(self) -> None:
        frame = _make_frame_ch1()
        result = decode_frame(frame, {1: 1.0})
        assert isinstance(result, DecodedFrame)


# ---------------------------------------------------------------------------
# Test: single-channel DC +1.0V frame (real fixture)
# ---------------------------------------------------------------------------

class TestDecodeSingleChannelDcP1V0:
    def test_channel_key_is_1(self) -> None:
        frame = _make_frame_ch1()
        result = decode_frame(frame, {1: 1.0})
        assert set(result.channels.keys()) == {1}

    def test_mean_voltage_approx_1v(self) -> None:
        """CH1 DDS DC +1.0V → decoded mean must be within ±0.1V of 1.0V."""
        frame = _make_frame_ch1()
        result = decode_frame(frame, {1: 1.0})
        mean_v = float(np.mean(result.channels[1]))
        assert abs(mean_v - 1.0) < 0.1, f"mean={mean_v:.4f}, expected ≈1.0V"

    def test_time_length_equals_4000(self) -> None:
        frame = _make_frame_ch1()
        result = decode_frame(frame, {1: 1.0})
        assert len(result.time) == 4000

    def test_time_step_equals_1_over_srate(self) -> None:
        """time[1] must equal 1/1.25e6 = 8e-7 seconds."""
        frame = _make_frame_ch1()
        result = decode_frame(frame, {1: 1.0})
        expected_step = 1.0 / 1.25e6
        assert abs(result.time[1] - expected_step) < 1e-15, (
            f"time[1]={result.time[1]}, expected {expected_step}"
        )

    def test_triggered_is_false(self) -> None:
        """Fixture was captured without trigger → triggered must be False."""
        frame = _make_frame_ch1()
        result = decode_frame(frame, {1: 1.0})
        assert result.triggered is False

    def test_srate_is_1p25mhz(self) -> None:
        frame = _make_frame_ch1()
        result = decode_frame(frame, {1: 1.0})
        assert result.srate == pytest.approx(1.25e6)

    def test_channels_are_float64_arrays(self) -> None:
        frame = _make_frame_ch1()
        result = decode_frame(frame, {1: 1.0})
        assert result.channels[1].dtype == np.float64


# ---------------------------------------------------------------------------
# Test: two-channel frame (real fixture)
# ---------------------------------------------------------------------------

class TestDecodeTwoChannels:
    def test_channel_keys_are_1_and_2(self) -> None:
        frame = _make_frame_ch1ch2()
        result = decode_frame(frame, {1: 1.0, 2: 1.0})
        assert set(result.channels.keys()) == {1, 2}

    def test_ch1_mean_approx_1v(self) -> None:
        frame = _make_frame_ch1ch2()
        result = decode_frame(frame, {1: 1.0, 2: 1.0})
        mean_v = float(np.mean(result.channels[1]))
        assert abs(mean_v - 1.0) < 0.1, f"CH1 mean={mean_v:.4f}, expected ≈1.0V"

    def test_time_length_equals_4000(self) -> None:
        frame = _make_frame_ch1ch2()
        result = decode_frame(frame, {1: 1.0, 2: 1.0})
        assert len(result.time) == 4000

    def test_both_channels_same_length(self) -> None:
        frame = _make_frame_ch1ch2()
        result = decode_frame(frame, {1: 1.0, 2: 1.0})
        assert len(result.channels[1]) == len(result.channels[2])


# ---------------------------------------------------------------------------
# Test: offset shifts the mean
# ---------------------------------------------------------------------------

class TestDecodeOffset:
    def test_offset_shifts_mean_by_minus_0p5(self) -> None:
        """offsets={1: 0.5} should subtract 0.5V from every sample."""
        frame = _make_frame_ch1()

        # Baseline: no offset
        result_no_offset = decode_frame(frame, {1: 1.0})
        mean_no_offset = float(np.mean(result_no_offset.channels[1]))

        # With offset=0.5V → mean should decrease by 0.5V
        result_with_offset = decode_frame(frame, {1: 1.0}, offsets={1: 0.5})
        mean_with_offset = float(np.mean(result_with_offset.channels[1]))

        delta = mean_no_offset - mean_with_offset
        assert abs(delta - 0.5) < 0.01, (
            f"Expected mean shift of 0.5V, got {delta:.4f}V"
        )

    def test_offset_none_equivalent_to_zero(self) -> None:
        """decode_frame with offsets=None should equal offsets={}."""
        frame = _make_frame_ch1()
        r_none = decode_frame(frame, {1: 1.0}, offsets=None)
        r_empty = decode_frame(frame, {1: 1.0}, offsets={})
        np.testing.assert_array_equal(r_none.channels[1], r_empty.channels[1])

    def test_missing_channel_in_offsets_defaults_to_zero(self) -> None:
        """If a channel is not in offsets dict, offset defaults to 0.0."""
        frame = _make_frame_ch1()
        result = decode_frame(frame, {1: 1.0}, offsets={})
        mean_v = float(np.mean(result.channels[1]))
        assert abs(mean_v - 1.0) < 0.1


# ---------------------------------------------------------------------------
# Test: synthetic exact values (deterministic)
# ---------------------------------------------------------------------------

class TestDecodeSynthetic:
    def test_single_sample_exact_conversion(self) -> None:
        """25 counts at 1V/div = 1.0V exactly."""
        payload = bytes([25])  # int8 +25 = 1V at 1V/div
        frame = _make_synthetic_frame([1], [payload], srate=1.0e6)
        result = decode_frame(frame, {1: 1.0})
        assert result.channels[1][0] == pytest.approx(1.0)

    def test_negative_sample_exact_conversion(self) -> None:
        """int8 -25 (byte 231) at 1V/div = -1.0V exactly."""
        payload = bytes([256 - 25])  # 231 → int8 -25
        frame = _make_synthetic_frame([1], [payload], srate=1.0e6)
        result = decode_frame(frame, {1: 1.0})
        assert result.channels[1][0] == pytest.approx(-1.0)

    def test_vdiv_scaling(self) -> None:
        """25 counts at 2V/div = 2.0V."""
        payload = bytes([25])
        frame = _make_synthetic_frame([1], [payload], srate=1.0e6)
        result = decode_frame(frame, {1: 2.0})
        assert result.channels[1][0] == pytest.approx(2.0)

    def test_offset_applied_exactly(self) -> None:
        """25 counts at 1V/div with offset=0.5V → 1.0 - 0.5 = 0.5V."""
        payload = bytes([25])
        frame = _make_synthetic_frame([1], [payload], srate=1.0e6)
        result = decode_frame(frame, {1: 1.0}, offsets={1: 0.5})
        assert result.channels[1][0] == pytest.approx(0.5)

    def test_time_axis_starts_at_zero(self) -> None:
        payload = bytes([0, 0, 0, 0])
        frame = _make_synthetic_frame([1], [payload], srate=4.0)
        result = decode_frame(frame, {1: 1.0})
        assert result.time[0] == pytest.approx(0.0)

    def test_time_axis_step(self) -> None:
        payload = bytes([0, 0, 0, 0])
        frame = _make_synthetic_frame([1], [payload], srate=4.0)
        result = decode_frame(frame, {1: 1.0})
        np.testing.assert_allclose(result.time, [0.0, 0.25, 0.5, 0.75])

    def test_triggered_propagated(self) -> None:
        payload = bytes([0])
        frame = _make_synthetic_frame([1], [payload], triggered=True)
        result = decode_frame(frame, {1: 1.0})
        assert result.triggered is True

    def test_srate_propagated(self) -> None:
        payload = bytes([0])
        frame = _make_synthetic_frame([1], [payload], srate=5.0e6)
        result = decode_frame(frame, {1: 1.0})
        assert result.srate == pytest.approx(5.0e6)

    def test_two_channel_synthetic(self) -> None:
        """Two channels with different scales decoded independently."""
        payload1 = bytes([25])   # CH1: +25 counts
        payload2 = bytes([50])   # CH2: +50 counts (but int8: 50 is fine)
        frame = _make_synthetic_frame([1, 2], [payload1, payload2], srate=1.0e6)
        result = decode_frame(frame, {1: 1.0, 2: 2.0})
        assert result.channels[1][0] == pytest.approx(1.0)   # 25*(1.0/25)
        assert result.channels[2][0] == pytest.approx(4.0)   # 50*(2.0/25)

    def test_offsets_none_means_zero_offset(self) -> None:
        payload = bytes([25])
        frame = _make_synthetic_frame([1], [payload], srate=1.0e6)
        result_none = decode_frame(frame, {1: 1.0}, offsets=None)
        result_zero = decode_frame(frame, {1: 1.0}, offsets={1: 0.0})
        assert result_none.channels[1][0] == pytest.approx(result_zero.channels[1][0])
