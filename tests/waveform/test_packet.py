"""Tests for hantek_dso2d15.waveform.packet — Task W1 acceptance."""

import os
import pytest

from hantek_dso2d15.waveform.packet import HEADER_LEN, Packet, parse_packet, is_header

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "..", "fixtures", "waveform")


def _fixture(name: str) -> bytes:
    path = os.path.join(FIXTURE_DIR, name)
    return open(path, "rb").read()


# ---------------------------------------------------------------------------
# Synthetic tests
# ---------------------------------------------------------------------------

class TestParsePacketSynthetic:
    def test_basic_fields(self):
        """parse_packet returns correct pkt_len, total, uploaded, payload."""
        body = b"\x01\x02\x03\x04\x05"
        raw = b"#9" + b"000000040" + b"000000099" + b"000000040" + body
        pkt = parse_packet(raw)
        assert pkt.pkt_len == 40
        assert pkt.total == 99
        assert pkt.uploaded == 40
        assert pkt.payload == body

    def test_payload_is_everything_after_29_bytes(self):
        """payload equals raw[29:] exactly."""
        body = bytes(range(50))
        raw = b"#9" + b"000000079" + b"000000200" + b"000000050" + body
        pkt = parse_packet(raw)
        assert pkt.payload == body

    def test_zero_fields(self):
        """All-zero numeric fields parse correctly."""
        raw = b"#9" + b"000000000" + b"000000000" + b"000000000"
        pkt = parse_packet(raw)
        assert pkt.pkt_len == 0
        assert pkt.total == 0
        assert pkt.uploaded == 0
        assert pkt.payload == b""

    def test_invalid_prefix_raises_value_error(self):
        """parse_packet raises ValueError when prefix is not #9."""
        raw = b"XX" + b"000000040" + b"000000099" + b"000000040" + b"\x00" * 5
        with pytest.raises(ValueError):
            parse_packet(raw)

    def test_wrong_prefix_char_raises(self):
        """Any deviation from #9 in first two bytes raises ValueError."""
        raw = b"#8" + b"000000040" + b"000000099" + b"000000040"
        with pytest.raises(ValueError):
            parse_packet(raw)

    def test_returns_packet_dataclass(self):
        """parse_packet returns a Packet instance."""
        raw = b"#9" + b"000000005" + b"000000010" + b"000000003" + b"\xAB\xCD\xEF"
        pkt = parse_packet(raw)
        assert isinstance(pkt, Packet)


class TestIsHeaderSynthetic:
    def test_exactly_128_bytes_is_header(self):
        raw = b"#9" + b"000000128" + b"000000099" + b"000000000" + b"\x00" * 99
        assert len(raw) == 128
        assert is_header(raw) is True

    def test_127_bytes_not_header(self):
        raw = b"\x00" * 127
        assert is_header(raw) is False

    def test_129_bytes_not_header(self):
        raw = b"\x00" * 129
        assert is_header(raw) is False

    def test_header_len_constant(self):
        assert HEADER_LEN == 128


# ---------------------------------------------------------------------------
# Real fixture tests — priv_sq_ch1.pkt0.bin (single-channel, 1 packet)
# ---------------------------------------------------------------------------

class TestParsePacketRealFixtures:
    def test_priv_sq_ch1_pkt0_pkt_len(self):
        """priv_sq_ch1.pkt0.bin: pkt_len == 4128."""
        raw = _fixture("priv_sq_ch1.pkt0.bin")
        pkt = parse_packet(raw)
        assert pkt.pkt_len == 4128

    def test_priv_sq_ch1_pkt0_total(self):
        """priv_sq_ch1.pkt0.bin: total == 4000 (1 channel × 4000 points)."""
        raw = _fixture("priv_sq_ch1.pkt0.bin")
        pkt = parse_packet(raw)
        assert pkt.total == 4000

    def test_priv_sq_ch1_pkt0_uploaded(self):
        """priv_sq_ch1.pkt0.bin: uploaded == 0 (first packet)."""
        raw = _fixture("priv_sq_ch1.pkt0.bin")
        pkt = parse_packet(raw)
        assert pkt.uploaded == 0

    def test_priv_sq_ch1_pkt0_payload_length(self):
        """priv_sq_ch1.pkt0.bin: payload length equals len(raw) - 29."""
        raw = _fixture("priv_sq_ch1.pkt0.bin")
        pkt = parse_packet(raw)
        assert len(pkt.payload) == len(raw) - 29

    def test_priv_sq_ch1_pkt0_payload_is_raw_29_slice(self):
        """priv_sq_ch1.pkt0.bin: payload is exactly raw[29:]."""
        raw = _fixture("priv_sq_ch1.pkt0.bin")
        pkt = parse_packet(raw)
        assert pkt.payload == raw[29:]

    # Two-channel fixture — pkt0 (first transfer, uploaded=0)
    def test_priv_sq_ch1_off_ch2_pkt0_fields(self):
        """priv_sq_ch1_off_ch2.pkt0.bin: pkt_len==4128, total==8000, uploaded==0."""
        raw = _fixture("priv_sq_ch1_off_ch2.pkt0.bin")
        pkt = parse_packet(raw)
        assert pkt.pkt_len == 4128
        assert pkt.total == 8000
        assert pkt.uploaded == 0

    # Two-channel fixture — pkt1 (second transfer, uploaded=4000)
    def test_priv_sq_ch1_off_ch2_pkt1_fields(self):
        """priv_sq_ch1_off_ch2.pkt1.bin: pkt_len==4128, total==8000, uploaded==4000."""
        raw = _fixture("priv_sq_ch1_off_ch2.pkt1.bin")
        pkt = parse_packet(raw)
        assert pkt.pkt_len == 4128
        assert pkt.total == 8000
        assert pkt.uploaded == 4000


class TestIsHeaderRealFixtures:
    def test_priv_sq_ch1_pkt0_is_not_header(self):
        """priv_sq_ch1.pkt0.bin (len=4128) → is_header is False."""
        raw = _fixture("priv_sq_ch1.pkt0.bin")
        assert is_header(raw) is False

    def test_priv_sq_ch1_off_ch2_pkt0_is_not_header(self):
        """priv_sq_ch1_off_ch2.pkt0.bin (len=4128) → is_header is False."""
        raw = _fixture("priv_sq_ch1_off_ch2.pkt0.bin")
        assert is_header(raw) is False

    def test_priv_sq_ch1_off_ch2_pkt1_is_not_header(self):
        """priv_sq_ch1_off_ch2.pkt1.bin (len=4128) → is_header is False."""
        raw = _fixture("priv_sq_ch1_off_ch2.pkt1.bin")
        assert is_header(raw) is False

    def test_synthetic_128_byte_header_true(self):
        """Synthetic 128-byte '#9…' packet → is_header is True."""
        raw = b"#9" + b"000000128" + b"000000000" + b"000000000" + b"\x00" * 99
        assert len(raw) == 128
        assert is_header(raw) is True
