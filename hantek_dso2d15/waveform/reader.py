"""Chunked waveform frame reader — Task W4.

Collects a complete waveform frame from the oscilloscope by issuing
repeated ``:WAVeform:DATA:ALL?`` queries and assembling the response
packets into a :class:`RawFrame`.

Frame structure (hardware-verified, 2026-06-27):
  - HEADER packet (128 bytes): oscilloscope metadata.
  - DATA packets (one per enabled channel, in CH1→CH2 order).

The reader is transport-agnostic: it accepts any object with
``write(cmd: str)`` and ``read_raw() -> bytes`` methods.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from hantek_dso2d15.waveform.packet import parse_packet, is_header
from hantek_dso2d15.waveform.header import parse_header, WaveHeader

#: SCPI query that triggers packet delivery.
_QUERY: str = ":WAVeform:DATA:ALL?"


@dataclass
class RawFrame:
    """A complete waveform frame as returned by the oscilloscope.

    Attributes
    ----------
    header:
        Parsed oscilloscope metadata (channels, srate, trigger state …).
    data_payloads:
        Raw signed-int8 sample bytes, one entry per enabled channel,
        in the same order as ``header.enabled_channels``.
    """

    header: WaveHeader
    data_payloads: list[bytes] = field(default_factory=list)


class WaveformReader:
    """Chunked reader for ``:WAVeform:DATA:ALL?`` waveform frames.

    Parameters
    ----------
    transport:
        An open transport object that provides ``write(cmd: str)`` and
        ``read_raw() -> bytes``.  Must already be open when
        :meth:`read_frame` is called.
    """

    def __init__(self, transport) -> None:
        self._transport = transport

    def read_frame(self, max_packets: int = 64) -> RawFrame:
        """Read one complete waveform frame from the oscilloscope.

        **Phase 1 — synchronisation:** sends ``:WAVeform:DATA:ALL?`` and
        reads packets, skipping non-header packets, until a header packet
        arrives.

        **Phase 2 — data collection:** sends ``:WAVeform:DATA:ALL?`` for
        each DATA packet, accumulating payloads until the ``uploaded``
        accounting reaches ``total`` (as reported in the header packet).

        Parameters
        ----------
        max_packets:
            Hard upper limit on the total number of packets read (header
            + data combined).  Raises :exc:`RuntimeError` if exceeded,
            preventing infinite loops on a misbehaving instrument.

        Returns
        -------
        RawFrame
            Parsed header and raw data payloads.

        Raises
        ------
        RuntimeError
            If ``max_packets`` is exhausted before a header is found, or
            before all data payloads are collected.
        """
        transport = self._transport
        iterations: int = 0

        # ------------------------------------------------------------------
        # Phase 1: synchronise — find the HEADER packet.
        # Non-header (DATA) packets that arrive before the header are
        # silently discarded.
        # ------------------------------------------------------------------
        header: WaveHeader | None = None
        total: int = 0

        while iterations < max_packets:
            transport.write(_QUERY)
            raw = transport.read_raw()
            iterations += 1

            if is_header(raw):
                header = parse_header(raw)
                total = parse_packet(raw).total
                break
        else:
            raise RuntimeError(
                f"WaveformReader: header packet not found within "
                f"{max_packets} packets (max_packets={max_packets})."
            )

        # ------------------------------------------------------------------
        # Phase 2: collect DATA packets until uploaded + len(payload) >= total.
        #
        # ``total = N_channels × points + 99`` (99 = header payload size).
        # Each DATA packet carries one channel's samples.  The ``uploaded``
        # field of a packet records how many bytes had already been
        # transferred before that packet.  We stop when:
        #   pkt.uploaded + len(pkt.payload) >= total
        # which means no more data will follow.
        # ------------------------------------------------------------------
        data_payloads: list[bytes] = []

        while iterations < max_packets:
            transport.write(_QUERY)
            raw = transport.read_raw()
            iterations += 1

            if is_header(raw):
                # Unexpected header mid-stream — skip it.
                continue

            pkt = parse_packet(raw)
            data_payloads.append(bytes(pkt.payload))

            if pkt.uploaded + len(pkt.payload) >= total:
                break  # all channel data received
        else:
            raise RuntimeError(
                f"WaveformReader: frame data incomplete after "
                f"{max_packets} packets (max_packets={max_packets})."
            )

        return RawFrame(header=header, data_payloads=data_payloads)
