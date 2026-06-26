"""IEEE-обёртка пакета :WAVeform:DATA:ALL? — парсинг prefixed блоков.

Формат (hardware-verified, 2026-06-27):
  raw[:2]   == b"#9"           (литерал)
  raw[2:11]  = pkt_len         (9 ASCII-цифр)
  raw[11:20] = total           (9 ASCII-цифр)
  raw[20:29] = uploaded        (9 ASCII-цифр)
  raw[29:]   = payload         (байты данных или метаданных)

HEADER-пакет: len(raw) == 128.
DATA-пакет:   len(raw) >  128.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["HEADER_LEN", "Packet", "parse_packet", "is_header"]

HEADER_LEN: int = 128


@dataclass
class Packet:
    """Разобранный пакет :WAVeform:DATA:ALL?."""

    pkt_len: int
    total: int
    uploaded: int
    payload: bytes


def parse_packet(raw: bytes) -> Packet:
    """Разобрать один пакет из сырых байт.

    Args:
        raw: Байты пакета, начинающиеся с ``#9``.

    Returns:
        Packet с полями pkt_len, total, uploaded, payload.

    Raises:
        ValueError: Если первые два байта не равны ``b"#9"``.
    """
    if raw[:2] != b"#9":
        raise ValueError(f"Invalid packet prefix: {raw[:2]!r}; expected b'#9'")

    pkt_len = int(raw[2:11])
    total = int(raw[11:20])
    uploaded = int(raw[20:29])
    payload = raw[29:]

    return Packet(pkt_len=pkt_len, total=total, uploaded=uploaded, payload=payload)


def is_header(raw: bytes) -> bool:
    """Вернуть True, если ``raw`` является header-пакетом (длина == HEADER_LEN)."""
    return len(raw) == HEADER_LEN
