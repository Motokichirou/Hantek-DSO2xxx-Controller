"""Слой waveform: декодер :WAVeform:DATA:ALL? (формат подтверждён на железе).

volts = sample_int8 × (Vдел / 25) − offset_volts;  t[i] = i / srate.
Подробности формата/калибровки — tests/fixtures/waveform/FIXTURES.md.
"""

from .packet import Packet, parse_packet, is_header, HEADER_LEN
from .header import WaveHeader, parse_header
from .convert import COUNTS_PER_DIV, counts_to_volts, time_axis
from .reader import RawFrame, WaveformReader
from .decode import DecodedFrame, decode_frame

__all__ = [
    "Packet",
    "parse_packet",
    "is_header",
    "HEADER_LEN",
    "WaveHeader",
    "parse_header",
    "COUNTS_PER_DIV",
    "counts_to_volts",
    "time_axis",
    "RawFrame",
    "WaveformReader",
    "DecodedFrame",
    "decode_frame",
]
