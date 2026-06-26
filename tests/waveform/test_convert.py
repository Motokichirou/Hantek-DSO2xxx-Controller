"""Tests for hantek_dso2d15.waveform.convert — counts-to-volts and time axis.

TDD: run this file BEFORE convert.py exists to confirm FAIL, then after to confirm PASS.
"""
import pathlib

import numpy as np
import pytest

# ---------------------------------------------------------------------------
# Module under test
# ---------------------------------------------------------------------------
from hantek_dso2d15.waveform.convert import (
    COUNTS_PER_DIV,
    counts_to_volts,
    time_axis,
)

FIXTURES = pathlib.Path(__file__).parent.parent / "fixtures" / "waveform"


# ---------------------------------------------------------------------------
# COUNTS_PER_DIV constant
# ---------------------------------------------------------------------------

def test_counts_per_div_value():
    assert COUNTS_PER_DIV == 25.0


# ---------------------------------------------------------------------------
# counts_to_volts — NumPy array inputs
# ---------------------------------------------------------------------------

def test_basic_positive_negative_zero():
    """[25, -25, 0] @ 1 V/div, off=0 → [1.0, -1.0, 0.0] exactly."""
    samples = np.array([25, -25, 0], dtype=np.int8)
    result = counts_to_volts(samples, vdiv=1.0, offset_volts=0.0)
    expected = np.array([1.0, -1.0, 0.0])
    np.testing.assert_array_almost_equal(result, expected, decimal=10)


def test_vdiv_2v():
    """[25] @ 2 V/div, off=0 → [2.0] exactly."""
    samples = np.array([25], dtype=np.int8)
    result = counts_to_volts(samples, vdiv=2.0, offset_volts=0.0)
    np.testing.assert_array_almost_equal(result, np.array([2.0]), decimal=10)


def test_offset_subtracted():
    """[38] @ 2 V/div, off=2.0 → [38*2/25 - 2] = [1.04] exactly."""
    samples = np.array([38], dtype=np.int8)
    result = counts_to_volts(samples, vdiv=2.0, offset_volts=2.0)
    expected = np.array([38 * 2.0 / 25 - 2.0])  # 1.04
    np.testing.assert_array_almost_equal(result, expected, decimal=10)


def test_offset_default_is_zero():
    """offset_volts should default to 0.0."""
    samples = np.array([25], dtype=np.int8)
    r1 = counts_to_volts(samples, vdiv=1.0)
    r2 = counts_to_volts(samples, vdiv=1.0, offset_volts=0.0)
    np.testing.assert_array_equal(r1, r2)


# ---------------------------------------------------------------------------
# counts_to_volts — bytes / bytearray inputs
# ---------------------------------------------------------------------------

def test_bytes_input():
    """bytes([25, 231]) → signed int8 [25, -25] @ 1 V/div → [1.0, -1.0]."""
    raw = bytes([25, 256 - 25])  # 231 unsigned → -25 as int8
    result = counts_to_volts(raw, vdiv=1.0)
    np.testing.assert_array_almost_equal(result, np.array([1.0, -1.0]), decimal=10)


def test_bytearray_input():
    """bytearray input should work identically to bytes."""
    raw = bytearray([25, 256 - 25])
    result = counts_to_volts(raw, vdiv=1.0)
    np.testing.assert_array_almost_equal(result, np.array([1.0, -1.0]), decimal=10)


def test_return_type_is_float64():
    """Return dtype must be float64 regardless of input type."""
    samples = np.array([10, 20], dtype=np.int8)
    result = counts_to_volts(samples, vdiv=1.0)
    assert result.dtype == np.float64

    result_bytes = counts_to_volts(bytes([10, 20]), vdiv=1.0)
    assert result_bytes.dtype == np.float64


# ---------------------------------------------------------------------------
# time_axis
# ---------------------------------------------------------------------------

def test_time_axis_length():
    t = time_axis(4, 1.25e6)
    assert len(t) == 4


def test_time_axis_first_element_zero():
    t = time_axis(4, 1.25e6)
    assert t[0] == 0.0


def test_time_axis_second_element():
    """time_axis(4, 1.25e6)[1] == 8e-7 exactly."""
    t = time_axis(4, 1.25e6)
    assert abs(t[1] - 8e-7) < 1e-15


def test_time_axis_values():
    """time_axis(4, 1.25e6) → [0, 8e-7, 1.6e-6, 2.4e-6]."""
    t = time_axis(4, 1.25e6)
    expected = np.array([0.0, 8e-7, 1.6e-6, 2.4e-6])
    np.testing.assert_array_almost_equal(t, expected, decimal=15)


def test_time_axis_dtype_is_float():
    t = time_axis(5, 1e6)
    assert np.issubdtype(t.dtype, np.floating)


# ---------------------------------------------------------------------------
# Real fixture — DC +1.0 V on CH1
# ---------------------------------------------------------------------------

def test_real_fixture_dc_p1v0_ch1_mean():
    """
    Real capture: DDS DC +1.0 V → CH1 at 1 V/div, offset=0.
    payload = raw[29:] (skipping 29-byte ASCII prefix).
    mean(counts_to_volts(payload, 1.0)) should be within ±0.1 V of 1.0 V.
    """
    pkt1_path = FIXTURES / "frame_dc_p1v0_ch1.pkt1.bin"
    raw = pkt1_path.read_bytes()
    assert len(raw) == 4029, f"Unexpected fixture size: {len(raw)}"

    payload = raw[29:]  # 4000 bytes of signed int8 samples
    assert len(payload) == 4000

    volts = counts_to_volts(payload, vdiv=1.0)
    mean_v = float(np.mean(volts))
    assert abs(mean_v - 1.0) < 0.1, (
        f"Mean voltage {mean_v:.4f} V deviates more than 0.1 V from expected 1.0 V"
    )
