"""
hantek_dso2d15.waveform.header — метаданные header-пакета WAVeform:DATA:ALL?

Индексы выверены на железе (2026-06-27); расхождение с frozen reference §7:
voltage-поля занимают 4×8=32 байта (не 28), enable/srate сдвинуты на +4.

Абсолютные индексы в raw (128-байтовый header-пакет):
  [0:2]   '#9'
  [2:11]  pkt_len (9 цифр ASCII)
  [11:20] total (9 цифр ASCII)
  [20:29] uploaded (9 цифр ASCII)
  [29]    running  ('1'/'0')
  [30]    trig     ('1'/'0')
  [31:35] ch1off, [35:39] ch2off, [39:43] ch3off, [43:47] ch4off  (4 байта, signed ASCII int)
  [47:79] ch1volt..ch4volt (4×8 символов, не используется в декодере)
  [79:83] enable   ('1'/'0' для CH1..CH4)
  [83:92] srate    (float ASCII, 9 символов)
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class WaveHeader:
    """Распарсенные метаданные header-пакета WAVeform:DATA:ALL?."""

    running: bool
    """True если прибор в режиме Run (не Stop)."""

    triggered: bool
    """True если последний захват завершился по триггеру."""

    offsets_counts: list[int]
    """Смещения каналов CH1..CH4 в counts (знаковые, COUNTS_PER_DIV=25)."""

    enabled_channels: list[int]
    """Номера включённых каналов, по возрастанию: [1], [1,2], …"""

    srate: float
    """Частота дискретизации, Sa/s."""


def parse_header(raw: bytes) -> WaveHeader:
    """Распарсить header-пакет (128 байт) в WaveHeader.

    Parameters
    ----------
    raw:
        Полный 128-байтовый header-пакет, включая 29-байтовый префикс '#9…'.

    Returns
    -------
    WaveHeader

    Raises
    ------
    ValueError
        Если длина raw != 128 или префикс не '#9'.
    """
    if len(raw) != 128:
        raise ValueError(f"Header packet must be 128 bytes, got {len(raw)}")
    if raw[:2] != b"#9":
        raise ValueError(f"Header packet must start with '#9', got {raw[:2]!r}")

    running: bool = raw[29:30] == b"1"
    triggered: bool = raw[30:31] == b"1"

    offsets_counts: list[int] = [
        int(raw[31 + 4 * k : 35 + 4 * k])
        for k in range(4)
    ]

    enable: str = raw[79:83].decode("latin1")
    enabled_channels: list[int] = [k + 1 for k, c in enumerate(enable) if c == "1"]

    srate: float = float(raw[83:92])

    return WaveHeader(
        running=running,
        triggered=triggered,
        offsets_counts=offsets_counts,
        enabled_channels=enabled_channels,
        srate=srate,
    )
