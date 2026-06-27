"""
Tests for hantek_dso2d15.waveform.header — TDD (W2).

Run: .venv/Scripts/python.exe -m pytest tests/waveform/test_header.py -q

Индексы (HARDWARE-VERIFIED, см. FIXTURES.md / header.py):
  [0:2]   '#9'
  [2:11]  pkt_len (9 цифр)
  [11:20] total   (9 цифр)
  [20:29] uploaded(9 цифр)
  [29]    running  '1'/'0'
  [30]    trig     '1'/'0'
  [31:75] бинарные поля (смещения/напряжения — не используются в header.py)
  [75:79] enable   '1'/'0' на CH1..CH4
  [79:88] srate    float ASCII 9 символов
"""

import pathlib
import pytest

FIXTURES = pathlib.Path(__file__).parent.parent / "fixtures" / "waveform"


def _make_raw(
    running: str = "0",
    triggered: str = "0",
    enable: str = "1000",
    srate: str = "1.250e+06",
) -> bytes:
    """Собрать минимальный синтетический 128-байтовый заголовок пакета.

    Значения размещаются точно по абсолютным индексам из header.py / FIXTURES.md.
    """
    raw = bytearray(128)
    raw[0:2] = b"#9"
    raw[2:11] = b"000000128"   # pkt_len (произвольно для синтетики)
    raw[11:20] = b"000004000"  # total
    raw[20:29] = b"000000000"  # uploaded
    raw[29:30] = running.encode("latin1")
    raw[30:31] = triggered.encode("latin1")
    # [31:75] — оставляем нулями (бинарные поля, не читаются header.py)
    raw[75:79] = enable.encode("latin1")
    raw[79:88] = srate.encode("latin1")
    return bytes(raw)


# ---------------------------------------------------------------------------
# Synthetic tests — enable/channel mapping
# ---------------------------------------------------------------------------

def test_enabled_channels_ch1ch2():
    """enable=b'1100' → enabled_channels=[1,2]."""
    from hantek_dso2d15.waveform.header import WaveHeader, parse_header

    raw = _make_raw(enable="1100")
    hdr = parse_header(raw)
    assert isinstance(hdr, WaveHeader)
    assert hdr.enabled_channels == [1, 2]


def test_enabled_channels_ch1_only():
    """enable=b'1000' → enabled_channels=[1]."""
    from hantek_dso2d15.waveform.header import parse_header

    raw = _make_raw(enable="1000")
    assert parse_header(raw).enabled_channels == [1]


def test_enabled_channels_all_four():
    """enable=b'1111' → enabled_channels=[1,2,3,4]."""
    from hantek_dso2d15.waveform.header import parse_header

    raw = _make_raw(enable="1111")
    assert parse_header(raw).enabled_channels == [1, 2, 3, 4]


def test_enabled_channels_none():
    """enable=b'0000' → enabled_channels=[]."""
    from hantek_dso2d15.waveform.header import parse_header

    raw = _make_raw(enable="0000")
    assert parse_header(raw).enabled_channels == []


# ---------------------------------------------------------------------------
# Synthetic tests — running / triggered flags
# ---------------------------------------------------------------------------

def test_running_flag_true():
    """raw[29]=b'1' → running is True."""
    from hantek_dso2d15.waveform.header import parse_header

    raw = _make_raw(running="1", triggered="0")
    hdr = parse_header(raw)
    assert hdr.running is True
    assert hdr.triggered is False


def test_running_flag_false():
    """raw[29]=b'0' → running is False."""
    from hantek_dso2d15.waveform.header import parse_header

    raw = _make_raw(running="0", triggered="0")
    hdr = parse_header(raw)
    assert hdr.running is False


def test_triggered_flag_true():
    """raw[30]=b'1' → triggered is True."""
    from hantek_dso2d15.waveform.header import parse_header

    raw = _make_raw(running="0", triggered="1")
    hdr = parse_header(raw)
    assert hdr.triggered is True


# ---------------------------------------------------------------------------
# Synthetic tests — srate
# ---------------------------------------------------------------------------

def test_srate_parsed_high():
    """srate=b'5.000e+08' → 500_000_000.0."""
    from hantek_dso2d15.waveform.header import parse_header

    raw = _make_raw(srate="5.000e+08")
    assert parse_header(raw).srate == 5.0e8


def test_srate_parsed_default():
    """srate=b'1.250e+06' → 1_250_000.0."""
    from hantek_dso2d15.waveform.header import parse_header

    raw = _make_raw(srate="1.250e+06")
    assert parse_header(raw).srate == 1_250_000.0


# ---------------------------------------------------------------------------
# ValueError cases
# ---------------------------------------------------------------------------

def test_value_error_too_short():
    """raw < 128 байт → ValueError."""
    from hantek_dso2d15.waveform.header import parse_header

    with pytest.raises(ValueError):
        parse_header(b"#9" + b"\x00" * 100)  # только 102 байта


def test_value_error_no_prefix():
    """raw без '#9' в начале → ValueError."""
    from hantek_dso2d15.waveform.header import parse_header

    bad = bytearray(128)
    bad[0:2] = b"AB"  # не '#9'
    with pytest.raises(ValueError):
        parse_header(bytes(bad))


# ---------------------------------------------------------------------------
# Real fixture tests
# ---------------------------------------------------------------------------

def test_fixture_priv_sq_ch1():
    """priv_sq_ch1.pkt0.bin → channels==[1], srate==1.25e6, running False, triggered False."""
    from hantek_dso2d15.waveform.header import parse_header

    raw = (FIXTURES / "priv_sq_ch1.pkt0.bin").read_bytes()
    hdr = parse_header(raw)
    assert hdr.enabled_channels == [1]
    assert hdr.srate == 1_250_000.0
    assert hdr.running is False
    assert hdr.triggered is False


def test_fixture_priv_sq_ch1_off_ch2():
    """priv_sq_ch1_off_ch2.pkt0.bin → channels==[1,2], srate==1.25e6."""
    from hantek_dso2d15.waveform.header import parse_header

    raw = (FIXTURES / "priv_sq_ch1_off_ch2.pkt0.bin").read_bytes()
    hdr = parse_header(raw)
    assert hdr.enabled_channels == [1, 2]
    assert hdr.srate == 1_250_000.0
