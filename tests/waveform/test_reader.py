"""Tests for hantek_dso2d15.waveform.reader.

Uses real hardware-captured fixtures from tests/fixtures/waveform/:
  priv_sq_ch1.pkt0.bin          -- 1-channel square-wave capture (CH1 only)
  priv_sq_ch1_off_ch2.pkt0.bin  -- 2-channel capture, packet 0 (uploaded=0)
  priv_sq_ch1_off_ch2.pkt1.bin  -- 2-channel capture, packet 1 (uploaded=4000)

Fixture facts (hardware-verified 2026-06-27):
  1-ch: total=4000, 1 packet sufficient, enable='1000', srate=1.25e6
  2-ch: total=8000, 2 packets, enable='1100'; de-interleaved:
        CH1 (pp=53, square wave), CH2 (pp=2, flat ~+50 count)

Run: .venv/Scripts/python.exe -m pytest tests/waveform/test_reader.py -q
"""

from __future__ import annotations

import pathlib

import numpy as np
import pytest

from hantek_dso2d15.transport.fake_transport import FakeTransport
from hantek_dso2d15.waveform.reader import RawFrame, WaveformReader

FIXTURES = pathlib.Path(__file__).parent.parent / "fixtures" / "waveform"

# SCPI command as implemented in reader._QUERY (PRIVate prefix is mandatory).
SCPI_CMD = "PRIVate:WAVeform:DATA:ALL?"


def _fixture(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


# ---------------------------------------------------------------------------
# Import sanity
# ---------------------------------------------------------------------------

class TestImports:
    def test_waveformreader_importable(self):
        assert WaveformReader is not None

    def test_rawframe_importable(self):
        assert RawFrame is not None

    def test_rawframe_has_header_and_payloads(self):
        """RawFrame dataclass has header and data_payloads fields."""
        from hantek_dso2d15.waveform.header import WaveHeader
        hdr = WaveHeader(running=False, triggered=False,
                         enabled_channels=[1], srate=1.25e6)
        frame = RawFrame(header=hdr, data_payloads=[b"\x01\x02"])
        assert frame.header is hdr
        assert frame.data_payloads == [b"\x01\x02"]

    def test_rawframe_default_empty_payloads(self):
        from hantek_dso2d15.waveform.header import WaveHeader
        hdr = WaveHeader(running=False, triggered=False,
                         enabled_channels=[1], srate=1.25e6)
        frame = RawFrame(header=hdr)
        assert frame.data_payloads == []


# ---------------------------------------------------------------------------
# 1-channel frame (priv_sq_ch1.pkt0.bin)
# ---------------------------------------------------------------------------

class TestReadFrame1Channel:
    """Single-channel square-wave capture: 1 packet totals all 4000 sample bytes."""

    def setup_method(self):
        pkt0 = _fixture("priv_sq_ch1.pkt0.bin")
        self.transport = FakeTransport()
        # One packet is sufficient: total=4000, packet carries 4000 sample bytes.
        self.transport.set_raw(pkt0)
        self.transport.open()
        self.reader = WaveformReader(self.transport)

    def test_returns_rawframe(self):
        frame = self.reader.read_frame()
        assert isinstance(frame, RawFrame)

    def test_enabled_channels(self):
        """enable='1000' -> enabled_channels == [1]."""
        frame = self.reader.read_frame()
        assert frame.header.enabled_channels == [1]

    def test_payload_count(self):
        """Exactly one payload (one enabled channel)."""
        frame = self.reader.read_frame()
        assert len(frame.data_payloads) == 1

    def test_payload_length(self):
        """Payload length == 4000 (ACQuire:POINts 4000)."""
        frame = self.reader.read_frame()
        assert len(frame.data_payloads[0]) == 4000

    def test_srate(self):
        """srate field parsed from ASCII '1.250e+06' -> 1 250 000.0 Sa/s."""
        frame = self.reader.read_frame()
        assert frame.header.srate == 1_250_000.0

    def test_running_false(self):
        """running bit '0' -> running is False."""
        frame = self.reader.read_frame()
        assert frame.header.running is False

    def test_triggered_false(self):
        """trig bit '0' -> triggered is False."""
        frame = self.reader.read_frame()
        assert frame.header.triggered is False

    def test_scpi_command_in_writes(self):
        """Reader writes PRIVate:WAVeform:DATA:ALL? (with PRIVate prefix)."""
        self.reader.read_frame()
        assert SCPI_CMD in self.transport.writes

    def test_square_wave_stats(self):
        """CH1 is a 2Vpp square wave: peak-to-peak count > 40 (pp=53 in fixture)."""
        frame = self.reader.read_frame()
        arr = np.frombuffer(frame.data_payloads[0], dtype=np.int8)
        assert int(arr.max()) - int(arr.min()) > 40


# ---------------------------------------------------------------------------
# 2-channel frame (priv_sq_ch1_off_ch2.pkt0.bin + .pkt1.bin)
# ---------------------------------------------------------------------------

class TestReadFrame2Channel:
    """Two-channel capture: 2 packets needed (total=8000 = 2*4000)."""

    def setup_method(self):
        pkt0 = _fixture("priv_sq_ch1_off_ch2.pkt0.bin")
        pkt1 = _fixture("priv_sq_ch1_off_ch2.pkt1.bin")
        self.transport = FakeTransport()
        self.transport.set_raw(pkt0, pkt1)
        self.transport.open()
        self.reader = WaveformReader(self.transport)

    def test_enabled_channels(self):
        """enable='1100' -> enabled_channels == [1, 2]."""
        frame = self.reader.read_frame()
        assert frame.header.enabled_channels == [1, 2]

    def test_payload_count(self):
        """Two payloads, one per enabled channel."""
        frame = self.reader.read_frame()
        assert len(frame.data_payloads) == 2

    def test_payload_length_ch1(self):
        """CH1 payload == 4000 bytes after de-interleave."""
        frame = self.reader.read_frame()
        assert len(frame.data_payloads[0]) == 4000

    def test_payload_length_ch2(self):
        """CH2 payload == 4000 bytes after de-interleave."""
        frame = self.reader.read_frame()
        assert len(frame.data_payloads[1]) == 4000

    def test_payloads_differ(self):
        """De-interleave must produce distinct bytes for CH1 (square) vs CH2 (flat)."""
        frame = self.reader.read_frame()
        assert frame.data_payloads[0] != frame.data_payloads[1]

    def test_ch1_is_square_wave(self):
        """CH1 de-interleaved: DDS 2Vpp square -> peak-to-peak count > 40 (pp=53)."""
        frame = self.reader.read_frame()
        arr = np.frombuffer(frame.data_payloads[0], dtype=np.int8)
        assert int(arr.max()) - int(arr.min()) > 40

    def test_ch2_is_flat(self):
        """CH2 de-interleaved: offset +10V@5V/div -> flat ~+50 count, pp < 10 (pp=2)."""
        frame = self.reader.read_frame()
        arr = np.frombuffer(frame.data_payloads[1], dtype=np.int8)
        assert int(arr.max()) - int(arr.min()) < 10

    def test_scpi_command_in_writes(self):
        """PRIVate:WAVeform:DATA:ALL? must appear in writes for 2-ch capture."""
        frame = self.reader.read_frame()
        assert SCPI_CMD in self.transport.writes

    def test_two_writes_for_two_packets(self):
        """2 packets collected -> 2 writes of the SCPI command."""
        self.reader.read_frame()
        count = self.transport.writes.count(SCPI_CMD)
        assert count == 2

    def test_srate(self):
        """srate == 1.25 MSa/s in 2-channel mode."""
        frame = self.reader.read_frame()
        assert frame.header.srate == 1_250_000.0


# ---------------------------------------------------------------------------
# SCPI command correctness (PRIVate prefix must be present)
# ---------------------------------------------------------------------------

class TestScpiCommand:
    """Verify the exact SCPI string sent to transport."""

    def test_priv_prefix_present(self):
        """Reader must use 'PRIVate:WAVeform:DATA:ALL?' not ':WAVeform:DATA:ALL?'."""
        pkt0 = _fixture("priv_sq_ch1.pkt0.bin")
        t = FakeTransport()
        t.set_raw(pkt0)
        t.open()
        WaveformReader(t).read_frame()
        assert any(w.startswith("PRIVate:") for w in t.writes), (
            f"Expected write starting with 'PRIVate:', got {t.writes!r}"
        )

    def test_exact_scpi_string(self):
        """Exact command string is 'PRIVate:WAVeform:DATA:ALL?'."""
        pkt0 = _fixture("priv_sq_ch1.pkt0.bin")
        t = FakeTransport()
        t.set_raw(pkt0)
        t.open()
        WaveformReader(t).read_frame()
        assert SCPI_CMD in t.writes, (
            f"Expected '{SCPI_CMD}' in writes, got {t.writes!r}"
        )


# ---------------------------------------------------------------------------
# max_packets guard (synthetic: malformed packet causes early termination)
# ---------------------------------------------------------------------------

class TestMaxPacketsGuard:
    """Reader raises RuntimeError when max_packets exceeded without full frame."""

    def _bad_packet(self) -> bytes:
        """Return a syntactically valid packet whose pkt_len is 0 (skipped by reader)."""
        hdr = bytearray(128)
        hdr[0:2] = b"#9"
        hdr[2:11] = b"000000000"   # pkt_len = 0 -> reader skips
        hdr[11:20] = b"000004000"
        hdr[20:29] = b"000000000"
        return bytes(hdr)

    def test_raises_runtime_error(self):
        """RuntimeError raised when all packets have pkt_len=0 and frame never completes."""
        bad = self._bad_packet()
        t = FakeTransport()
        t.set_raw(*([bad] * 20))
        t.open()
        with pytest.raises(RuntimeError):
            WaveformReader(t).read_frame(max_packets=5)
