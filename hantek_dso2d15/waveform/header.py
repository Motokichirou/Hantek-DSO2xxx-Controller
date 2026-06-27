"""
hantek_dso2d15.waveform.header — метаданные meta-заголовка PRIVate:WAVeform:DATA:ALL?

Формат подтверждён на железе (2026-06-27) и сверен с эталонной реализацией
phmarek/hantek-dso2000 (тот же VID/PID 0x049F/0x505E). Команда чтения —
``PRIVate:WAVeform:DATA:ALL?``: каждый пакет несёт 128-байтовый meta-заголовок,
затем кусок сэмплов (с байта 128).

Абсолютные индексы meta-полей в первых 128 байтах пакета:
  [0:2]   '#9'
  [2:11]  pkt_len  (9 цифр ASCII)
  [11:20] total    (9 цифр ASCII) — общее число байт сэмплов = N_каналов × points
  [20:29] uploaded (9 цифр ASCII) — позиция этого куска в общем буфере
  [29]    running  ('1'/'0')
  [30]    trig     ('1'/'0')
  [31:47] смещения каналов (в PRIVate-формате бинарны/не ASCII — НЕ используем;
          смещение берём запросом :CHANnel<n>:OFFSet?)
  [47:75] напряжения каналов (volts/count, не используется в декодере)
  [75:79] enable   ('1'/'0' для CH1..CH4)
  [79:88] srate    (float ASCII, 9 символов)

Калибровка (как в phmarek): ``volts = sample/25 × scale − offset`` (signed int8).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class WaveHeader:
    """Распарсенные метаданные meta-заголовка PRIVate:WAVeform:DATA:ALL?."""

    running: bool
    """True если прибор в режиме Run (не Stop)."""

    triggered: bool
    """True если последний захват завершился по триггеру."""

    enabled_channels: list[int]
    """Номера включённых каналов, по возрастанию: [1], [1,2], …"""

    srate: float
    """Частота дискретизации, Sa/s."""


def parse_header(raw: bytes) -> WaveHeader:
    """Распарсить 128-байтовый meta-заголовок в WaveHeader.

    Parameters
    ----------
    raw:
        Первые 128 байт первого пакета PRIVate:WAVeform:DATA:ALL?
        (включая 29-байтовый префикс '#9…').

    Returns
    -------
    WaveHeader

    Raises
    ------
    ValueError
        Если длина raw < 128 или префикс не '#9'.
    """
    if len(raw) < 128:
        raise ValueError(f"Meta-заголовок должен быть >= 128 байт, got {len(raw)}")
    if raw[:2] != b"#9":
        raise ValueError(f"Пакет должен начинаться с '#9', got {raw[:2]!r}")

    running: bool = raw[29:30] == b"1"
    triggered: bool = raw[30:31] == b"1"

    enable: str = raw[75:79].decode("latin1")
    enabled_channels: list[int] = [k + 1 for k, c in enumerate(enable) if c == "1"]

    srate: float = float(raw[79:88])

    return WaveHeader(
        running=running,
        triggered=triggered,
        enabled_channels=enabled_channels,
        srate=srate,
    )
