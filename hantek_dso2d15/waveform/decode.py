"""Waveform decode facade — Task W5.

Combines a :class:`~hantek_dso2d15.waveform.reader.RawFrame` (raw signed-int8
sample payloads + parsed header) with per-channel vertical scale/offset
information to produce a fully decoded :class:`DecodedFrame` containing
NumPy voltage arrays and a calibrated time axis.

This module is deliberately free of SCPI logic: scale, offset, and srate are
all supplied by the caller (the engine layer reads them from the instrument).

Hardware-verified calibration (2026-06-27, DDS loop):
  ``volts = sample_int8 × (vdiv / COUNTS_PER_DIV) − offset_volts``
  ``COUNTS_PER_DIV = 25``
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from hantek_dso2d15.waveform.convert import counts_to_volts, time_axis
from hantek_dso2d15.waveform.reader import RawFrame


@dataclass
class DecodedFrame:
    """A fully decoded waveform frame with voltage arrays and time axis.

    Attributes
    ----------
    time:
        1-D float64 array of sample timestamps in seconds,
        ``t[i] = i / srate`` starting at ``t[0] = 0``.
    channels:
        Mapping from channel number (1-based) to a float64 voltage array.
        Contains one entry per enabled channel in the source frame.
    srate:
        Sample rate in Sa/s, taken directly from the frame header.
    triggered:
        ``True`` if the oscilloscope confirmed a trigger event for this
        frame; ``False`` for free-run / untriggered captures.
    scales:
        Per-channel volts-per-division used to decode this frame, keyed by
        channel number. Позволяет потребителю (GUI-графикуль) показывать
        сигнал в делениях без отдельного учёта масштабов.
    offsets:
        Per-channel смещение в вольтах, использованное при декодировании.
        Для экранной позиции в делениях: ``y_div = (volts + offset) / scale``
        (= raw_count/25) — так смещение двигает трассу, как на приборе.
    """

    time: np.ndarray
    channels: dict[int, np.ndarray] = field(default_factory=dict)
    srate: float = 0.0
    triggered: bool = False
    scales: dict[int, float] = field(default_factory=dict)
    offsets: dict[int, float] = field(default_factory=dict)


def decode_frame(
    frame: RawFrame,
    scales: dict[int, float],
    offsets: dict[int, float] | None = None,
) -> DecodedFrame:
    """Decode a raw waveform frame into voltage arrays and a time axis.

    Parameters
    ----------
    frame:
        A :class:`~hantek_dso2d15.waveform.reader.RawFrame` as returned by
        :class:`~hantek_dso2d15.waveform.reader.WaveformReader`.  Its
        ``header.enabled_channels`` list determines which channels are
        decoded and their order relative to ``data_payloads``.
    scales:
        Per-channel volts-per-division values, keyed by channel number
        (1-based).  Typically obtained from ``:CHANnel<n>:SCALe?``.
    offsets:
        Per-channel vertical offset in volts, keyed by channel number.
        Typically obtained from ``:CHANnel<n>:OFFSet?``.  Channels absent
        from this mapping default to ``0.0``.  ``None`` is treated as an
        empty dict (all offsets zero).

    Returns
    -------
    DecodedFrame
        - ``channels[ch]`` — float64 voltage array for each enabled channel.
        - ``time`` — time axis built from the length of the first channel.
        - ``srate``, ``triggered`` — taken directly from ``frame.header``.
    """
    _offsets: dict[int, float] = offsets if offsets is not None else {}

    channels: dict[int, np.ndarray] = {}
    used_scales: dict[int, float] = {}
    used_offsets: dict[int, float] = {}
    for i, ch in enumerate(frame.header.enabled_channels):
        vdiv = scales[ch]
        offset_v = _offsets.get(ch, 0.0)
        channels[ch] = counts_to_volts(frame.data_payloads[i], vdiv, offset_v)
        used_scales[ch] = vdiv
        used_offsets[ch] = offset_v

    # Build the time axis from the length of the first decoded channel.
    first_ch = frame.header.enabled_channels[0]
    n_samples = len(channels[first_ch])
    t = time_axis(n_samples, frame.header.srate)

    return DecodedFrame(
        time=t,
        channels=channels,
        srate=frame.header.srate,
        triggered=frame.header.triggered,
        scales=used_scales,
        offsets=used_offsets,
    )
