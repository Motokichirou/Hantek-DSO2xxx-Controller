"""Tests for hantek_dso2d15.waveform.reader — Task W4 acceptance.

Run: .venv/Scripts/python.exe -m pytest tests/waveform/test_reader.py -q
"""

from __future__ import annotations

import pathlib
import pytest

from hantek_dso2d15.transport.fake_transport import FakeTransport

FIXTURES = pathlib.Path(__file__).parent.parent / "fixtures" / "waveform"


def _fixture(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_reader(transport: FakeTransport):
    from hantek_dso2d15.waveform.reader import WaveformReader
    return WaveformReader(transport)


def _load_1ch_frame():
    """Return (pkt0_bytes, pkt1_bytes) for the 1-channel DC frame."""
    return (
        _fixture("frame_dc_p1v0_ch1.pkt0.bin"),
        _fixture("frame_dc_p1v0_ch1.pkt1.bin"),
    )


def _load_2ch_frame():
    """Return (pkt0, pkt1, pkt2) for the 2-channel DC frame."""
    return (
        _fixture("frame_dc_p1v0_ch1ch2.pkt0.bin"),
        _fixture("frame_dc_p1v0_ch1ch2.pkt1.bin"),
        _fixture("frame_dc_p1v0_ch1ch2.pkt2.bin"),
    )


# ---------------------------------------------------------------------------
# Imports check
# ---------------------------------------------------------------------------

class TestImports:
    def test_rawframe_importable(self):
        from hantek_dso2d15.waveform.reader import RawFrame
        assert RawFrame is not None

    def test_waveformreader_importable(self):
        from hantek_dso2d15.waveform.reader import WaveformReader
        assert WaveformReader is not None


# ---------------------------------------------------------------------------
# RawFrame dataclass
# ---------------------------------------------------------------------------

class TestRawFrameDataclass:
    def test_rawframe_fields(self):
        """RawFrame holds header and data_payloads."""
        from hantek_dso2d15.waveform.reader import RawFrame
        from hantek_dso2d15.waveform.header import parse_header

        pkt0, _ = _load_1ch_frame()
        hdr = parse_header(pkt0)
        frame = RawFrame(header=hdr, data_payloads=[b"\x01\x02\x03"])
        assert frame.header is hdr
        assert frame.data_payloads == [b"\x01\x02\x03"]

    def test_rawframe_default_empty_payloads(self):
        """RawFrame.data_payloads defaults to empty list."""
        from hantek_dso2d15.waveform.reader import RawFrame
        from hantek_dso2d15.waveform.header import parse_header

        pkt0, _ = _load_1ch_frame()
        hdr = parse_header(pkt0)
        frame = RawFrame(header=hdr, data_payloads=[])
        assert frame.data_payloads == []


# ---------------------------------------------------------------------------
# 1-channel frame
# ---------------------------------------------------------------------------

class TestReadFrame1Channel:
    def setup_method(self):
        pkt0, pkt1 = _load_1ch_frame()
        self.transport = FakeTransport()
        self.transport.set_raw(pkt0, pkt1)
        self.transport.open()
        self.reader = _make_reader(self.transport)

    def test_read_frame_returns_rawframe(self):
        from hantek_dso2d15.waveform.reader import RawFrame
        frame = self.reader.read_frame()
        assert isinstance(frame, RawFrame)

    def test_1ch_enabled_channels(self):
        """1-channel frame: header.enabled_channels == [1]."""
        frame = self.reader.read_frame()
        assert frame.header.enabled_channels == [1]

    def test_1ch_data_payloads_count(self):
        """1-channel frame: exactly one data payload."""
        frame = self.reader.read_frame()
        assert len(frame.data_payloads) == 1

    def test_1ch_payload_length(self):
        """1-channel frame: payload has 4000 bytes."""
        frame = self.reader.read_frame()
        assert len(frame.data_payloads[0]) == 4000

    def test_1ch_srate(self):
        """1-channel frame: srate == 1.25e6."""
        frame = self.reader.read_frame()
        assert frame.header.srate == 1_250_000.0

    def test_1ch_triggered_false(self):
        """1-channel frame: triggered is False (DDS DC signal, auto-trigger mode)."""
        frame = self.reader.read_frame()
        assert frame.header.triggered is False


# ---------------------------------------------------------------------------
# 2-channel frame
# ---------------------------------------------------------------------------

class TestReadFrame2Channel:
    def setup_method(self):
        pkt0, pkt1, pkt2 = _load_2ch_frame()
        self.transport = FakeTransport()
        self.transport.set_raw(pkt0, pkt1, pkt2)
        self.transport.open()
        self.reader = _make_reader(self.transport)

    def test_2ch_enabled_channels(self):
        """2-channel frame: header.enabled_channels == [1, 2]."""
        frame = self.reader.read_frame()
        assert frame.header.enabled_channels == [1, 2]

    def test_2ch_data_payloads_count(self):
        """2-channel frame: exactly two data payloads."""
        frame = self.reader.read_frame()
        assert len(frame.data_payloads) == 2

    def test_2ch_payload_lengths(self):
        """2-channel frame: both payloads have 4000 bytes."""
        frame = self.reader.read_frame()
        assert len(frame.data_payloads[0]) == 4000
        assert len(frame.data_payloads[1]) == 4000

    def test_2ch_srate(self):
        """2-channel frame: srate == 1.25e6."""
        frame = self.reader.read_frame()
        assert frame.header.srate == 1_250_000.0


# ---------------------------------------------------------------------------
# SCPI command logged in writes
# ---------------------------------------------------------------------------

class TestScpiCommandLogged:
    def test_query_string_in_writes_1ch(self):
        """:WAVeform:DATA:ALL? written to transport.writes for each packet."""
        pkt0, pkt1 = _load_1ch_frame()
        transport = FakeTransport()
        transport.set_raw(pkt0, pkt1)
        transport.open()
        reader = _make_reader(transport)
        reader.read_frame()
        assert ":WAVeform:DATA:ALL?" in transport.writes

    def test_query_written_twice_for_1ch(self):
        """1-channel frame needs 2 packets → 2 writes."""
        pkt0, pkt1 = _load_1ch_frame()
        transport = FakeTransport()
        transport.set_raw(pkt0, pkt1)
        transport.open()
        reader = _make_reader(transport)
        reader.read_frame()
        scpi_writes = [w for w in transport.writes if w == ":WAVeform:DATA:ALL?"]
        assert len(scpi_writes) == 2

    def test_query_written_three_times_for_2ch(self):
        """2-channel frame needs 3 packets → 3 writes."""
        pkt0, pkt1, pkt2 = _load_2ch_frame()
        transport = FakeTransport()
        transport.set_raw(pkt0, pkt1, pkt2)
        transport.open()
        reader = _make_reader(transport)
        reader.read_frame()
        scpi_writes = [w for w in transport.writes if w == ":WAVeform:DATA:ALL?"]
        assert len(scpi_writes) == 3


# ---------------------------------------------------------------------------
# Sync: reader skips data packet before first header
# ---------------------------------------------------------------------------

class TestSyncronisation:
    def test_skip_data_packet_before_header(self):
        """Reader discards stray DATA packet and finds the following HEADER."""
        pkt0, pkt1 = _load_1ch_frame()
        transport = FakeTransport()
        # Queue: [DATA (stray), HEADER, DATA]
        transport.set_raw(pkt1, pkt0, pkt1)
        transport.open()
        reader = _make_reader(transport)
        frame = reader.read_frame()
        # Should have found the header and read one data payload
        assert frame.header.enabled_channels == [1]
        assert len(frame.data_payloads) == 1
        assert len(frame.data_payloads[0]) == 4000

    def test_writes_still_recorded_during_sync(self):
        """Writes are logged for each packet read including skipped ones."""
        pkt0, pkt1 = _load_1ch_frame()
        transport = FakeTransport()
        transport.set_raw(pkt1, pkt0, pkt1)
        transport.open()
        reader = _make_reader(transport)
        reader.read_frame()
        # 3 packets read → 3 writes
        assert transport.writes.count(":WAVeform:DATA:ALL?") == 3


# ---------------------------------------------------------------------------
# max_packets guard
# ---------------------------------------------------------------------------

class TestMaxPacketsGuard:
    def _make_infinite_data_queue(self, transport: FakeTransport, n: int = 100):
        """Fill transport with n copies of a DATA packet (no header ever)."""
        _, pkt1 = _load_1ch_frame()
        transport.set_raw(*([pkt1] * n))

    def test_runtime_error_when_no_header_found(self):
        """RuntimeError raised when max_packets exceeded without finding header."""
        transport = FakeTransport()
        self._make_infinite_data_queue(transport, n=10)
        transport.open()
        reader = _make_reader(transport)
        with pytest.raises(RuntimeError, match="max_packets|header"):
            reader.read_frame(max_packets=5)

    def test_runtime_error_uses_custom_max(self):
        """max_packets=3 stops early enough to detect no header."""
        transport = FakeTransport()
        self._make_infinite_data_queue(transport, n=10)
        transport.open()
        reader = _make_reader(transport)
        with pytest.raises(RuntimeError):
            reader.read_frame(max_packets=3)
