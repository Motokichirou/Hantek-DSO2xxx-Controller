"""Чанковый чтец осциллограммы — ``PRIVate:WAVeform:DATA:ALL?``.

Формат подтверждён на железе (2026-06-27) и сверен с phmarek/hantek-dso2000:
  - Команда ``PRIVate:WAVeform:DATA:ALL?`` (с префиксом PRIVate!) отдаёт ВСЕ
    включённые каналы; обычный ``WAVeform:DATA:ALL?`` отдаёт только CH1.
  - Каждый пакет: ``#9`` + pkt_len(9) + total(9) + uploaded(9) + meta-хвост до
    байта 128, затем кусок сэмплов с байта 128.
  - ``total`` = N_каналов × points (байты сэмплов). Кусок пишется в общий буфер
    по позиции ``uploaded``. Читаем пока не собрали ``total`` байт.
  - Сэмплы каналов ИНТЕРЛИВНЫ блоками по 2000 байт:
    ``|CH1_0|CH2_0|CH1_1|CH2_1|…`` — де-интерлив по индексу включённого канала.

Чтец транспортно-агностичен: нужен объект с ``write(cmd)`` и ``read_raw()->bytes``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from hantek_dso2d15.waveform.packet import parse_packet
from hantek_dso2d15.waveform.header import parse_header, WaveHeader

#: SCPI-запрос, отдающий данные ВСЕХ включённых каналов (с префиксом PRIVate).
_QUERY: str = "PRIVate:WAVeform:DATA:ALL?"
#: Сэмплы начинаются после 128-байтового meta-заголовка пакета.
_META_END: int = 128
#: Размер блока интерлива каналов (байт).
_BLOCK: int = 2000


@dataclass
class RawFrame:
    """Полный кадр осциллограммы.

    Attributes
    ----------
    header:
        Распарсенные метаданные (включённые каналы, srate, статус триггера).
    data_payloads:
        Сырые signed-int8 байты сэмплов, по одному элементу на включённый канал,
        в порядке ``header.enabled_channels`` (уже де-интерливленные).
    """

    header: WaveHeader
    data_payloads: list[bytes] = field(default_factory=list)


class WaveformReader:
    """Чтец кадров ``PRIVate:WAVeform:DATA:ALL?``.

    Parameters
    ----------
    transport:
        Открытый транспорт с ``write(cmd: str)`` и ``read_raw() -> bytes``.
    """

    def __init__(self, transport) -> None:
        self._transport = transport

    def read_frame(self, max_packets: int = 64) -> RawFrame:
        """Прочитать один полный кадр осциллограммы (все включённые каналы).

        Шлёт ``PRIVate:WAVeform:DATA:ALL?`` повторно, собирая куски сэмплов в
        общий буфер по позиции ``uploaded``, пока не наберётся ``total`` байт.
        Затем парсит meta-заголовок и де-интерливит буфер по каналам.

        Raises
        ------
        RuntimeError
            Если за ``max_packets`` итераций не собрался полный кадр.
        """
        transport = self._transport
        total: int = -1
        got: int = 0
        buffer: bytearray | None = None
        meta: bytes | None = None
        iterations: int = 0

        while iterations < max_packets:
            transport.write(_QUERY)
            raw = transport.read_raw()
            iterations += 1

            # Защита от коротких/битых пакетов (десинк при быстром опросе).
            if len(raw) < _META_END or raw[:2] != b"#9":
                continue

            pkt = parse_packet(raw)
            if pkt.pkt_len == 0:
                continue  # пустой пакет — данных нет

            chunk = raw[_META_END:]
            if total == -1:
                total = pkt.total
                buffer = bytearray(total)
                meta = bytes(raw[:_META_END])

            end = pkt.uploaded + len(chunk)
            buffer[pkt.uploaded:end] = chunk
            got += len(chunk)

            if got >= total:
                break
        else:
            raise RuntimeError(
                f"WaveformReader: кадр не собран за {max_packets} пакетов "
                f"(max_packets={max_packets})."
            )

        header = parse_header(meta)
        channel_count = len(header.enabled_channels)
        data = bytes(buffer)
        payloads = [
            self._deinterleave(data, k, channel_count)
            for k in range(channel_count)
        ]
        return RawFrame(header=header, data_payloads=payloads)

    @staticmethod
    def _deinterleave(buffer: bytes, index: int, channel_count: int,
                      block: int = _BLOCK) -> bytes:
        """Извлечь сэмплы канала по его индексу среди включённых.

        Сэмплы лежат блоками по ``block`` байт, чередуясь по каналам:
        ``|ch0_0|ch1_0|ch0_1|ch1_1|…``. Канал с индексом ``index`` — это блоки на
        позициях ``index*block``, ``index*block + block*channel_count``, …
        """
        if channel_count <= 0:
            return b""
        out = bytearray()
        pos = index * block
        stride = block * channel_count
        while pos < len(buffer):
            out += buffer[pos:pos + block]
            pos += stride
        return bytes(out)
