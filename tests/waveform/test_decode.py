"""Tests for hantek_dso2d15.waveform.decode — using hardware-verified fixtures.

Фикстуры сняты на железе 2026-06-27, формат подтверждён FIXTURES.md.
Реальные fixtures: priv_sq_ch1.pkt0.bin, priv_sq_ch1_off_ch2.pkt0/1.bin.
"""
from __future__ import annotations

import pathlib

import numpy as np
import pytest

from hantek_dso2d15.waveform.decode import DecodedFrame, decode_frame
from hantek_dso2d15.waveform.header import WaveHeader
from hantek_dso2d15.waveform.reader import RawFrame, WaveformReader
from hantek_dso2d15.transport.fake_transport import FakeTransport

FIXTURE_DIR = pathlib.Path(__file__).parent.parent / "fixtures" / "waveform"


# ---------------------------------------------------------------------------
# Helpers: RawFrame via WaveformReader + FakeTransport on real fixtures
# ---------------------------------------------------------------------------

def _make_frame_ch1() -> RawFrame:
    """Load priv_sq_ch1 (1 packet, CH1 only, square wave 2Vpp)."""
    pkt0 = (FIXTURE_DIR / "priv_sq_ch1.pkt0.bin").read_bytes()
    transport = FakeTransport()
    transport.open()
    transport.set_raw(pkt0)
    return WaveformReader(transport).read_frame()


def _make_frame_ch1ch2() -> RawFrame:
    """Load priv_sq_ch1_off_ch2 (2 packets, CH1+CH2)."""
    pkt0 = (FIXTURE_DIR / "priv_sq_ch1_off_ch2.pkt0.bin").read_bytes()
    pkt1 = (FIXTURE_DIR / "priv_sq_ch1_off_ch2.pkt1.bin").read_bytes()
    transport = FakeTransport()
    transport.open()
    transport.set_raw(pkt0, pkt1)
    return WaveformReader(transport).read_frame()


def _make_synthetic_frame(
    enabled_channels: list[int],
    payloads: list[bytes],
    srate: float = 1.25e6,
    triggered: bool = False,
    running: bool = False,
) -> RawFrame:
    """Construct a RawFrame synthetically without touching transport."""
    header = WaveHeader(
        running=running,
        triggered=triggered,
        enabled_channels=enabled_channels,
        srate=srate,
    )
    return RawFrame(header=header, data_payloads=payloads)


def _vpp_p90_p10(arr: np.ndarray) -> float:
    """Peak-to-peak estimate using 90th–10th percentile (noise-robust)."""
    return float(np.percentile(arr, 90) - np.percentile(arr, 10))


# ---------------------------------------------------------------------------
# Test: DecodedFrame return type
# ---------------------------------------------------------------------------

class TestDecodedFrameStructure:
    def test_returns_decoded_frame_instance(self) -> None:
        frame = _make_frame_ch1()
        result = decode_frame(frame, {1: 1.0})
        assert isinstance(result, DecodedFrame)

    def test_has_required_fields(self) -> None:
        frame = _make_frame_ch1()
        result = decode_frame(frame, {1: 1.0})
        assert hasattr(result, "time")
        assert hasattr(result, "channels")
        assert hasattr(result, "srate")
        assert hasattr(result, "triggered")


# ---------------------------------------------------------------------------
# Test: single-channel square wave fixture (priv_sq_ch1)
# ---------------------------------------------------------------------------

class TestDecodeSingleChannel:
    """priv_sq_ch1: CH1 меандр 2Vpp, 1В/дел, srate=1.25MHz."""

    def test_channel_set_is_ch1_only(self) -> None:
        result = decode_frame(_make_frame_ch1(), {1: 1.0})
        assert set(result.channels.keys()) == {1}

    def test_time_length_equals_4000(self) -> None:
        result = decode_frame(_make_frame_ch1(), {1: 1.0})
        assert len(result.time) == 4000

    def test_time_step_equals_1_over_srate(self) -> None:
        """time[1] must equal 1/1.25e6 (hardware-verified srate)."""
        result = decode_frame(_make_frame_ch1(), {1: 1.0})
        assert result.time[1] == pytest.approx(1 / 1.25e6, rel=1e-9)

    def test_time_starts_at_zero(self) -> None:
        result = decode_frame(_make_frame_ch1(), {1: 1.0})
        assert result.time[0] == pytest.approx(0.0)

    def test_srate_is_1p25mhz(self) -> None:
        result = decode_frame(_make_frame_ch1(), {1: 1.0})
        assert result.srate == pytest.approx(1.25e6)

    def test_triggered_is_false(self) -> None:
        result = decode_frame(_make_frame_ch1(), {1: 1.0})
        assert result.triggered is False

    def test_channels_are_float64(self) -> None:
        result = decode_frame(_make_frame_ch1(), {1: 1.0})
        assert result.channels[1].dtype == np.float64

    def test_ch1_vpp_approx_2v(self) -> None:
        """Square wave ±25 counts @ 1V/div → Vpp ≈ 2.0V (±0.15V)."""
        result = decode_frame(_make_frame_ch1(), {1: 1.0})
        vpp = _vpp_p90_p10(result.channels[1])
        assert abs(vpp - 2.0) < 0.15, f"CH1 Vpp={vpp:.4f}V, expected ≈2.0V"

    def test_channel_length_equals_time_length(self) -> None:
        result = decode_frame(_make_frame_ch1(), {1: 1.0})
        assert len(result.channels[1]) == len(result.time)


# ---------------------------------------------------------------------------
# Test: two-channel fixture with offset (priv_sq_ch1_off_ch2)
# ---------------------------------------------------------------------------

class TestDecodeTwoChannels:
    """priv_sq_ch1_off_ch2: CH1 меандр 2Vpp@1В/дел; CH2 ≈+50 count, 5В/дел, offset 10В."""

    def test_channel_set_is_ch1_and_ch2(self) -> None:
        result = decode_frame(_make_frame_ch1ch2(), {1: 1.0, 2: 5.0}, offsets={1: 0.0, 2: 10.0})
        assert set(result.channels.keys()) == {1, 2}

    def test_ch1_vpp_approx_2v(self) -> None:
        """CH1 square wave Vpp ≈ 2.0V (±0.15V)."""
        result = decode_frame(_make_frame_ch1ch2(), {1: 1.0, 2: 5.0}, offsets={1: 0.0, 2: 10.0})
        vpp = _vpp_p90_p10(result.channels[1])
        assert abs(vpp - 2.0) < 0.15, f"CH1 Vpp={vpp:.4f}V, expected ≈2.0V"

    def test_ch2_mean_approx_zero(self) -> None:
        """CH2: ≈+50 count × (5.0/25) − 10.0 = 0.0V (±0.2V).

        De-interleave sanity: if channels swapped, CH2 would look like a square
        wave (mean≠0) rather than a flat DC ≈0V line.
        """
        result = decode_frame(_make_frame_ch1ch2(), {1: 1.0, 2: 5.0}, offsets={1: 0.0, 2: 10.0})
        ch2_mean = float(np.mean(result.channels[2]))
        assert abs(ch2_mean - 0.0) < 0.2, f"CH2 mean={ch2_mean:.4f}V, expected ≈0.0V"

    def test_ch1_not_equal_ch2(self) -> None:
        """De-interleave guard: CH1 (square wave) must differ from CH2 (DC flat)."""
        result = decode_frame(_make_frame_ch1ch2(), {1: 1.0, 2: 5.0}, offsets={1: 0.0, 2: 10.0})
        vpp_ch1 = _vpp_p90_p10(result.channels[1])
        vpp_ch2 = _vpp_p90_p10(result.channels[2])
        # CH1 square wave Vpp ≈ 2V, CH2 DC Vpp ≈ 0V; difference must be > 1V
        assert (vpp_ch1 - vpp_ch2) > 1.0, (
            f"CH1 Vpp={vpp_ch1:.3f}V, CH2 Vpp={vpp_ch2:.3f}V — channels appear swapped"
        )

    def test_time_length_equals_4000(self) -> None:
        """Each channel has 4000 samples (total=8000 / 2 channels)."""
        result = decode_frame(_make_frame_ch1ch2(), {1: 1.0, 2: 5.0}, offsets={1: 0.0, 2: 10.0})
        assert len(result.time) == 4000

    def test_both_channels_same_length(self) -> None:
        result = decode_frame(_make_frame_ch1ch2(), {1: 1.0, 2: 5.0}, offsets={1: 0.0, 2: 10.0})
        assert len(result.channels[1]) == len(result.channels[2])


# ---------------------------------------------------------------------------
# Test: synthetic exact values (deterministic, no fixture noise)
# ---------------------------------------------------------------------------

class TestDecodeSynthetic:
    def test_single_sample_25_counts_at_1v_per_div(self) -> None:
        """25 counts × (1.0/25) − 0 = 1.0V exactly."""
        payload = bytes([25])
        frame = _make_synthetic_frame([1], [payload], srate=1.0e6)
        result = decode_frame(frame, {1: 1.0})
        assert result.channels[1][0] == pytest.approx(1.0)

    def test_negative_sample_minus25_counts(self) -> None:
        """int8 -25 (byte 231) × (1.0/25) = -1.0V exactly."""
        payload = bytes([256 - 25])  # 231 → signed int8 -25
        frame = _make_synthetic_frame([1], [payload], srate=1.0e6)
        result = decode_frame(frame, {1: 1.0})
        assert result.channels[1][0] == pytest.approx(-1.0)

    def test_vdiv_scaling_2v_per_div(self) -> None:
        """25 counts × (2.0/25) = 2.0V."""
        payload = bytes([25])
        frame = _make_synthetic_frame([1], [payload], srate=1.0e6)
        result = decode_frame(frame, {1: 2.0})
        assert result.channels[1][0] == pytest.approx(2.0)

    def test_offset_subtracted(self) -> None:
        """25 counts × (1.0/25) − 0.5 = 0.5V."""
        payload = bytes([25])
        frame = _make_synthetic_frame([1], [payload], srate=1.0e6)
        result = decode_frame(frame, {1: 1.0}, offsets={1: 0.5})
        assert result.channels[1][0] == pytest.approx(0.5)

    def test_offsets_none_treated_as_zero(self) -> None:
        """offsets=None → no offset applied (same as offsets={})."""
        payload = bytes([25])
        frame = _make_synthetic_frame([1], [payload], srate=1.0e6)
        result_none = decode_frame(frame, {1: 1.0}, offsets=None)
        result_empty = decode_frame(frame, {1: 1.0}, offsets={})
        np.testing.assert_array_equal(result_none.channels[1], result_empty.channels[1])

    def test_missing_channel_offset_defaults_zero(self) -> None:
        """Channel absent from offsets dict → offset=0.0 (no shift)."""
        payload = bytes([25])
        frame = _make_synthetic_frame([1], [payload], srate=1.0e6)
        result = decode_frame(frame, {1: 1.0}, offsets={})  # CH1 not in offsets
        assert result.channels[1][0] == pytest.approx(1.0)

    def test_time_axis_starts_at_zero(self) -> None:
        payload = bytes([0, 0, 0, 0])
        frame = _make_synthetic_frame([1], [payload], srate=4.0)
        result = decode_frame(frame, {1: 1.0})
        assert result.time[0] == pytest.approx(0.0)

    def test_time_axis_step_correct(self) -> None:
        payload = bytes([0, 0, 0, 0])
        frame = _make_synthetic_frame([1], [payload], srate=4.0)
        result = decode_frame(frame, {1: 1.0})
        np.testing.assert_allclose(result.time, [0.0, 0.25, 0.5, 0.75])

    def test_triggered_true_propagated(self) -> None:
        payload = bytes([0])
        frame = _make_synthetic_frame([1], [payload], triggered=True)
        result = decode_frame(frame, {1: 1.0})
        assert result.triggered is True

    def test_triggered_false_propagated(self) -> None:
        payload = bytes([0])
        frame = _make_synthetic_frame([1], [payload], triggered=False)
        result = decode_frame(frame, {1: 1.0})
        assert result.triggered is False

    def test_srate_propagated(self) -> None:
        payload = bytes([0])
        frame = _make_synthetic_frame([1], [payload], srate=5.0e6)
        result = decode_frame(frame, {1: 1.0})
        assert result.srate == pytest.approx(5.0e6)

    def test_two_channel_different_scales(self) -> None:
        """CH1: 25 counts @1V/div =1.0V; CH2: 50 counts @2V/div =4.0V."""
        frame = _make_synthetic_frame([1, 2], [bytes([25]), bytes([50])], srate=1.0e6)
        result = decode_frame(frame, {1: 1.0, 2: 2.0})
        assert result.channels[1][0] == pytest.approx(1.0)   # 25*(1.0/25)=1.0
        assert result.channels[2][0] == pytest.approx(4.0)   # 50*(2.0/25)=4.0

    def test_ch2_offset_50counts_at_5v_per_div_minus_10v(self) -> None:
        """Exact calibration check matching the hardware fixture formula.

        50 counts × (5.0/25) − 10.0 = 10.0 − 10.0 = 0.0V.
        """
        payload = bytes([50])
        frame = _make_synthetic_frame([2], [payload], srate=1.25e6)
        result = decode_frame(frame, {2: 5.0}, offsets={2: 10.0})
        assert result.channels[2][0] == pytest.approx(0.0)

    def test_output_dtype_is_float64(self) -> None:
        payload = bytes([0])
        frame = _make_synthetic_frame([1], [payload], srate=1.0e6)
        result = decode_frame(frame, {1: 1.0})
        assert result.channels[1].dtype == np.float64
