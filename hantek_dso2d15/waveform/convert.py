"""counts-to-volts conversion and time-axis helpers for DSO2D15 waveform data.

All calibration constants are hardware-verified (DDS loop, 2026-06-27).
See tests/fixtures/waveform/FIXTURES.md for the measurement protocol.
"""
from __future__ import annotations

import numpy as np

# Hardware-verified: 25 counts = 1 V/div on DSO2D15.
COUNTS_PER_DIV: float = 25.0


def counts_to_volts(
    samples: bytes | bytearray | np.ndarray,
    vdiv: float,
    offset_volts: float = 0.0,
) -> np.ndarray:
    """Convert raw sample counts to voltage values.

    Parameters
    ----------
    samples:
        Raw waveform data. Accepted forms:
        - ``bytes`` or ``bytearray``: interpreted as signed int8 samples
          (as delivered in a DATA packet payload by DSO2D15).
        - ``numpy.ndarray``: used as-is (dtype need not be int8, but the
          values must be in signed-int8 count space).
    vdiv:
        Volts per division, from ``:CHANnel<n>:SCALe?``.
    offset_volts:
        Channel vertical offset in volts, from ``:CHANnel<n>:OFFSet?``.
        Defaults to 0.0.

    Returns
    -------
    numpy.ndarray
        float64 array of voltage values with the formula::

            volts = sample × (vdiv / COUNTS_PER_DIV) − offset_volts
    """
    if isinstance(samples, (bytes, bytearray)):
        arr: np.ndarray = np.frombuffer(samples, dtype=np.int8)
    else:
        arr = samples

    return arr.astype(np.float64) * (vdiv / COUNTS_PER_DIV) - offset_volts


def time_axis(n: int, srate: float) -> np.ndarray:
    """Build a time axis for ``n`` samples at sample-rate ``srate``.

    Parameters
    ----------
    n:
        Number of samples.
    srate:
        Sample rate in Sa/s (from ``:ACQuire:SRATe?`` or the header field).

    Returns
    -------
    numpy.ndarray
        float64 array ``[0, 1/srate, 2/srate, ..., (n-1)/srate]``.
    """
    return np.arange(n) / srate
