"""Tests for Channel SCPI subsystem — Task 5.

All tests use FakeTransport (no hardware required).
Acceptance cases from plan § Task 5.
"""

import pytest
from hantek_dso2d15.transport.fake_transport import FakeTransport


def make_transport() -> FakeTransport:
    t = FakeTransport()
    t.open()
    return t


# ---------------------------------------------------------------------------
# Channel.__init__ — validation
# ---------------------------------------------------------------------------

class TestChannelInit:
    def test_channel_1_valid(self):
        from hantek_dso2d15.scpi.channel import Channel
        t = make_transport()
        ch = Channel(t, 1)
        assert ch is not None

    def test_channel_4_valid(self):
        from hantek_dso2d15.scpi.channel import Channel
        t = make_transport()
        ch = Channel(t, 4)
        assert ch is not None

    def test_channel_0_raises(self):
        from hantek_dso2d15.scpi.channel import Channel
        t = make_transport()
        with pytest.raises(ValueError):
            Channel(t, 0)

    def test_channel_5_raises(self):
        """Acceptance: Channel(t, 5) → ValueError."""
        from hantek_dso2d15.scpi.channel import Channel
        t = make_transport()
        with pytest.raises(ValueError):
            Channel(t, 5)

    def test_channel_minus1_raises(self):
        from hantek_dso2d15.scpi.channel import Channel
        t = make_transport()
        with pytest.raises(ValueError):
            Channel(t, -1)


# ---------------------------------------------------------------------------
# Channel class-level constants
# ---------------------------------------------------------------------------

class TestChannelConstants:
    def test_couplings(self):
        from hantek_dso2d15.scpi.channel import Channel
        assert Channel.COUPLINGS == ("AC", "DC", "GND")

    def test_probes(self):
        from hantek_dso2d15.scpi.channel import Channel
        assert Channel.PROBES == (1, 10, 100, 1000)


# ---------------------------------------------------------------------------
# scale
# ---------------------------------------------------------------------------

class TestChannelScale:
    def test_set_scale_writes_correct_command(self):
        """Acceptance: ch.scale = 0.5 → writes[-1]==':CHANnel1:SCALe 0.5'."""
        from hantek_dso2d15.scpi.channel import Channel
        t = make_transport()
        ch = Channel(t, 1)
        ch.scale = 0.5
        assert t.writes[-1] == ":CHANnel1:SCALe 0.5"

    def test_set_scale_fmt_num_small(self):
        from hantek_dso2d15.scpi.channel import Channel
        t = make_transport()
        ch = Channel(t, 1)
        ch.scale = 5e-4
        assert t.writes[-1] == ":CHANnel1:SCALe 0.0005"

    def test_set_scale_channel2(self):
        from hantek_dso2d15.scpi.channel import Channel
        t = make_transport()
        ch = Channel(t, 2)
        ch.scale = 1.0
        assert t.writes[-1] == ":CHANnel2:SCALe 1"

    def test_get_scale_parses_float(self):
        """Acceptance: set_response(':CHANnel1:SCALe?','5.000000e-01'); ch.scale == 0.5."""
        from hantek_dso2d15.scpi.channel import Channel
        t = make_transport()
        ch = Channel(t, 1)
        t.set_response(":CHANnel1:SCALe?", "5.000000e-01")
        assert ch.scale == 0.5

    def test_query_command_is_correct(self):
        from hantek_dso2d15.scpi.channel import Channel
        t = make_transport()
        ch = Channel(t, 1)
        t.set_response(":CHANnel1:SCALe?", "1")
        _ = ch.scale
        assert ":CHANnel1:SCALe?" in t.queries


# ---------------------------------------------------------------------------
# offset
# ---------------------------------------------------------------------------

class TestChannelOffset:
    def test_set_offset_negative(self):
        from hantek_dso2d15.scpi.channel import Channel
        t = make_transport()
        ch = Channel(t, 1)
        ch.offset = -1.5
        assert t.writes[-1] == ":CHANnel1:OFFSet -1.5"

    def test_set_offset_zero(self):
        from hantek_dso2d15.scpi.channel import Channel
        t = make_transport()
        ch = Channel(t, 1)
        ch.offset = 0.0
        assert t.writes[-1] == ":CHANnel1:OFFSet 0"

    def test_get_offset_parses_float(self):
        from hantek_dso2d15.scpi.channel import Channel
        t = make_transport()
        ch = Channel(t, 1)
        t.set_response(":CHANnel1:OFFSet?", "-1.5")
        assert ch.offset == -1.5

    def test_offset_channel3(self):
        from hantek_dso2d15.scpi.channel import Channel
        t = make_transport()
        ch = Channel(t, 3)
        ch.offset = 2.0
        assert t.writes[-1] == ":CHANnel3:OFFSet 2"


# ---------------------------------------------------------------------------
# coupling
# ---------------------------------------------------------------------------

class TestChannelCoupling:
    def test_set_coupling_lowercase_dc(self):
        """Acceptance: ch.coupling = 'dc' → ':CHANnel1:COUPling DC'."""
        from hantek_dso2d15.scpi.channel import Channel
        t = make_transport()
        ch = Channel(t, 1)
        ch.coupling = "dc"
        assert t.writes[-1] == ":CHANnel1:COUPling DC"

    def test_set_coupling_uppercase_ac(self):
        from hantek_dso2d15.scpi.channel import Channel
        t = make_transport()
        ch = Channel(t, 1)
        ch.coupling = "AC"
        assert t.writes[-1] == ":CHANnel1:COUPling AC"

    def test_set_coupling_gnd(self):
        from hantek_dso2d15.scpi.channel import Channel
        t = make_transport()
        ch = Channel(t, 1)
        ch.coupling = "gnd"
        assert t.writes[-1] == ":CHANnel1:COUPling GND"

    def test_get_coupling_returns_string(self):
        """Acceptance: set_response(...,'AC'); ch.coupling=='AC'."""
        from hantek_dso2d15.scpi.channel import Channel
        t = make_transport()
        ch = Channel(t, 1)
        t.set_response(":CHANnel1:COUPling?", "AC")
        assert ch.coupling == "AC"

    def test_set_coupling_invalid_raises_no_write(self):
        """Acceptance: ch.coupling = 'XX' → ValueError; ничего не записано."""
        from hantek_dso2d15.scpi.channel import Channel
        t = make_transport()
        ch = Channel(t, 1)
        with pytest.raises(ValueError):
            ch.coupling = "XX"
        assert len(t.writes) == 0

    def test_set_coupling_invalid_does_not_write(self):
        from hantek_dso2d15.scpi.channel import Channel
        t = make_transport()
        ch = Channel(t, 1)
        ch.coupling = "AC"  # one valid write
        with pytest.raises(ValueError):
            ch.coupling = "INVALID"
        # only the first write should be there
        assert len(t.writes) == 1
        assert t.writes[0] == ":CHANnel1:COUPling AC"


# ---------------------------------------------------------------------------
# probe
# ---------------------------------------------------------------------------

class TestChannelProbe:
    def test_set_probe_10_writes_command(self):
        """Acceptance: ch.probe = 10 → ':CHANnel1:PROBe 10'."""
        from hantek_dso2d15.scpi.channel import Channel
        t = make_transport()
        ch = Channel(t, 1)
        ch.probe = 10
        assert t.writes[-1] == ":CHANnel1:PROBe 10"

    def test_set_probe_1(self):
        from hantek_dso2d15.scpi.channel import Channel
        t = make_transport()
        ch = Channel(t, 1)
        ch.probe = 1
        assert t.writes[-1] == ":CHANnel1:PROBe 1"

    def test_set_probe_100(self):
        from hantek_dso2d15.scpi.channel import Channel
        t = make_transport()
        ch = Channel(t, 1)
        ch.probe = 100
        assert t.writes[-1] == ":CHANnel1:PROBe 100"

    def test_set_probe_1000(self):
        from hantek_dso2d15.scpi.channel import Channel
        t = make_transport()
        ch = Channel(t, 1)
        ch.probe = 1000
        assert t.writes[-1] == ":CHANnel1:PROBe 1000"

    def test_get_probe_parses_int_from_scientific(self):
        """Acceptance: set_response(...,'1.000000e+01'); ch.probe==10 (int)."""
        from hantek_dso2d15.scpi.channel import Channel
        t = make_transport()
        ch = Channel(t, 1)
        t.set_response(":CHANnel1:PROBe?", "1.000000e+01")
        result = ch.probe
        assert result == 10
        assert isinstance(result, int)

    def test_set_probe_invalid_raises_no_write(self):
        from hantek_dso2d15.scpi.channel import Channel
        t = make_transport()
        ch = Channel(t, 1)
        with pytest.raises(ValueError):
            ch.probe = 7
        assert len(t.writes) == 0

    def test_set_probe_5_raises(self):
        from hantek_dso2d15.scpi.channel import Channel
        t = make_transport()
        ch = Channel(t, 1)
        with pytest.raises(ValueError):
            ch.probe = 5


# ---------------------------------------------------------------------------
# bwlimit
# ---------------------------------------------------------------------------

class TestChannelBwlimit:
    def test_set_bwlimit_true_writes_on(self):
        """Acceptance: ch.bwlimit = True → ':CHANnel1:BWLimit ON'."""
        from hantek_dso2d15.scpi.channel import Channel
        t = make_transport()
        ch = Channel(t, 1)
        ch.bwlimit = True
        assert t.writes[-1] == ":CHANnel1:BWLimit ON"

    def test_set_bwlimit_false_writes_off(self):
        from hantek_dso2d15.scpi.channel import Channel
        t = make_transport()
        ch = Channel(t, 1)
        ch.bwlimit = False
        assert t.writes[-1] == ":CHANnel1:BWLimit OFF"

    def test_get_bwlimit_parses_1_as_true(self):
        """Acceptance: set_response(...,'1'); ch.bwlimit is True."""
        from hantek_dso2d15.scpi.channel import Channel
        t = make_transport()
        ch = Channel(t, 1)
        t.set_response(":CHANnel1:BWLimit?", "1")
        assert ch.bwlimit is True

    def test_get_bwlimit_parses_0_as_false(self):
        from hantek_dso2d15.scpi.channel import Channel
        t = make_transport()
        ch = Channel(t, 1)
        t.set_response(":CHANnel1:BWLimit?", "0")
        assert ch.bwlimit is False

    def test_get_bwlimit_parses_on_as_true(self):
        from hantek_dso2d15.scpi.channel import Channel
        t = make_transport()
        ch = Channel(t, 1)
        t.set_response(":CHANnel1:BWLimit?", "ON")
        assert ch.bwlimit is True


# ---------------------------------------------------------------------------
# display
# ---------------------------------------------------------------------------

class TestChannelDisplay:
    def test_set_display_true_writes_on(self):
        from hantek_dso2d15.scpi.channel import Channel
        t = make_transport()
        ch = Channel(t, 1)
        ch.display = True
        assert t.writes[-1] == ":CHANnel1:DISPlay ON"

    def test_set_display_false_writes_off(self):
        from hantek_dso2d15.scpi.channel import Channel
        t = make_transport()
        ch = Channel(t, 1)
        ch.display = False
        assert t.writes[-1] == ":CHANnel1:DISPlay OFF"

    def test_get_display_parses_on(self):
        from hantek_dso2d15.scpi.channel import Channel
        t = make_transport()
        ch = Channel(t, 1)
        t.set_response(":CHANnel1:DISPlay?", "ON")
        assert ch.display is True

    def test_get_display_parses_off(self):
        from hantek_dso2d15.scpi.channel import Channel
        t = make_transport()
        ch = Channel(t, 1)
        t.set_response(":CHANnel1:DISPlay?", "OFF")
        assert ch.display is False


# ---------------------------------------------------------------------------
# invert
# ---------------------------------------------------------------------------

class TestChannelInvert:
    def test_set_invert_true(self):
        from hantek_dso2d15.scpi.channel import Channel
        t = make_transport()
        ch = Channel(t, 1)
        ch.invert = True
        assert t.writes[-1] == ":CHANnel1:INVert ON"

    def test_set_invert_false(self):
        from hantek_dso2d15.scpi.channel import Channel
        t = make_transport()
        ch = Channel(t, 1)
        ch.invert = False
        assert t.writes[-1] == ":CHANnel1:INVert OFF"

    def test_get_invert_parses_off(self):
        from hantek_dso2d15.scpi.channel import Channel
        t = make_transport()
        ch = Channel(t, 1)
        t.set_response(":CHANnel1:INVert?", "OFF")
        assert ch.invert is False

    def test_get_invert_parses_on(self):
        from hantek_dso2d15.scpi.channel import Channel
        t = make_transport()
        ch = Channel(t, 1)
        t.set_response(":CHANnel1:INVert?", "1")
        assert ch.invert is True


# ---------------------------------------------------------------------------
# vernier
# ---------------------------------------------------------------------------

class TestChannelVernier:
    def test_set_vernier_true(self):
        from hantek_dso2d15.scpi.channel import Channel
        t = make_transport()
        ch = Channel(t, 1)
        ch.vernier = True
        assert t.writes[-1] == ":CHANnel1:VERNier ON"

    def test_set_vernier_false(self):
        from hantek_dso2d15.scpi.channel import Channel
        t = make_transport()
        ch = Channel(t, 1)
        ch.vernier = False
        assert t.writes[-1] == ":CHANnel1:VERNier OFF"

    def test_get_vernier_parses_1(self):
        from hantek_dso2d15.scpi.channel import Channel
        t = make_transport()
        ch = Channel(t, 1)
        t.set_response(":CHANnel1:VERNier?", "1")
        assert ch.vernier is True

    def test_get_vernier_parses_0(self):
        from hantek_dso2d15.scpi.channel import Channel
        t = make_transport()
        ch = Channel(t, 1)
        t.set_response(":CHANnel1:VERNier?", "0")
        assert ch.vernier is False


# ---------------------------------------------------------------------------
# Channel number in SCPI strings (n=4 check)
# ---------------------------------------------------------------------------

class TestChannelNumber:
    def test_channel4_scale_command(self):
        from hantek_dso2d15.scpi.channel import Channel
        t = make_transport()
        ch = Channel(t, 4)
        ch.scale = 2.0
        assert t.writes[-1] == ":CHANnel4:SCALe 2"

    def test_channel4_coupling_command(self):
        from hantek_dso2d15.scpi.channel import Channel
        t = make_transport()
        ch = Channel(t, 4)
        ch.coupling = "DC"
        assert t.writes[-1] == ":CHANnel4:COUPling DC"
