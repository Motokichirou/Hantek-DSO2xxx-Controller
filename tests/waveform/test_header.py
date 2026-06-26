"""
Tests for hantek_dso2d15.waveform.header — TDD (W2).

Run: .venv/Scripts/python.exe -m pytest tests/waveform/test_header.py -q
"""

import pathlib
import pytest

FIXTURES = pathlib.Path(__file__).parent.parent / "fixtures" / "waveform"


def _make_raw(
    running: str = "1",
    triggered: str = "0",
    offsets: tuple = ("0000", "0000", "0000", "0000"),
    volt_fields: str = " " * 32,   # 4 × 8 bytes, not used
    enable: str = "1000",
    srate: str = "1.250e+06",
) -> bytes:
    """Build a minimal synthetic 128-byte header packet."""
    prefix = b"#9000000128000004099000000000"  # 29 bytes
    running_b = running.encode("latin1")
    triggered_b = triggered.encode("latin1")
    offsets_b = b"".join(o.encode("latin1") for o in offsets)  # 4 × 4 = 16 bytes
    volt_b = volt_fields.encode("latin1")                      # 32 bytes
    enable_b = enable.encode("latin1")                         # 4 bytes
    srate_b = srate.encode("latin1")                           # 9 bytes
    payload = running_b + triggered_b + offsets_b + volt_b + enable_b + srate_b
    # payload starts at index 29; total payload needed = 128 - 29 = 99 bytes
    padding = bytes(99 - len(payload))
    return prefix + payload + padding


# ---------------------------------------------------------------------------
# Synthetic tests
# ---------------------------------------------------------------------------

def test_enabled_channels_ch1ch2():
    """enable='1100' → enabled_channels=[1,2]."""
    from hantek_dso2d15.waveform.header import WaveHeader, parse_header

    raw = _make_raw(enable="1100")
    hdr = parse_header(raw)
    assert isinstance(hdr, WaveHeader)
    assert hdr.enabled_channels == [1, 2]


def test_enabled_channels_ch1_only():
    """enable='1000' → enabled_channels=[1]."""
    from hantek_dso2d15.waveform.header import parse_header

    raw = _make_raw(enable="1000")
    hdr = parse_header(raw)
    assert hdr.enabled_channels == [1]


def test_enabled_channels_all_four():
    """enable='1111' → enabled_channels=[1,2,3,4]."""
    from hantek_dso2d15.waveform.header import parse_header

    raw = _make_raw(enable="1111")
    assert parse_header(raw).enabled_channels == [1, 2, 3, 4]


def test_enabled_channels_none():
    """enable='0000' → enabled_channels=[]."""
    from hantek_dso2d15.waveform.header import parse_header

    raw = _make_raw(enable="0000")
    assert parse_header(raw).enabled_channels == []


def test_offset_negative():
    """offsets_counts with '-025' → -25."""
    from hantek_dso2d15.waveform.header import parse_header

    raw = _make_raw(offsets=("-025", "0025", "0000", "0000"))
    hdr = parse_header(raw)
    assert hdr.offsets_counts[0] == -25
    assert hdr.offsets_counts[1] == 25
    assert hdr.offsets_counts[2] == 0
    assert hdr.offsets_counts[3] == 0


def test_running_triggered_flags():
    """running/triggered parsed from raw[29:30]/raw[30:31]."""
    from hantek_dso2d15.waveform.header import parse_header

    raw_running = _make_raw(running="1", triggered="1")
    hdr = parse_header(raw_running)
    assert hdr.running is True
    assert hdr.triggered is True

    raw_stopped = _make_raw(running="0", triggered="0")
    hdr2 = parse_header(raw_stopped)
    assert hdr2.running is False
    assert hdr2.triggered is False


def test_srate_parsed():
    """srate from raw[83:92]."""
    from hantek_dso2d15.waveform.header import parse_header

    raw = _make_raw(srate="5.000e+08")
    assert parse_header(raw).srate == 5.0e8


# ---------------------------------------------------------------------------
# Real fixture tests
# ---------------------------------------------------------------------------

def test_fixture_ch1_only():
    """frame_dc_p1v0_ch1.pkt0.bin → channels==[1], srate==1.25e6, offset[0]==0, triggered False."""
    from hantek_dso2d15.waveform.header import parse_header

    raw = (FIXTURES / "frame_dc_p1v0_ch1.pkt0.bin").read_bytes()
    hdr = parse_header(raw)
    assert hdr.enabled_channels == [1]
    assert hdr.srate == 1_250_000.0
    assert hdr.offsets_counts[0] == 0
    assert hdr.triggered is False


def test_fixture_ch1ch2():
    """frame_dc_p1v0_ch1ch2.pkt0.bin → channels==[1,2], srate==1.25e6."""
    from hantek_dso2d15.waveform.header import parse_header

    raw = (FIXTURES / "frame_dc_p1v0_ch1ch2.pkt0.bin").read_bytes()
    hdr = parse_header(raw)
    assert hdr.enabled_channels == [1, 2]
    assert hdr.srate == 1_250_000.0
