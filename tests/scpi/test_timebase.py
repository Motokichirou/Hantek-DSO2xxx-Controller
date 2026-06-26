"""Тесты подсистем Timebase и TimebaseWindow — Task 6.

Все тесты работают через FakeTransport, без реального железа.
Проверяем: точные SCPI-строки (writes) и парсинг ответов (queries).
"""

import pytest

from hantek_dso2d15.transport.fake_transport import FakeTransport
from hantek_dso2d15.scpi.timebase import Timebase, TimebaseWindow


# ---------------------------------------------------------------------------
# Фикстуры
# ---------------------------------------------------------------------------


@pytest.fixture
def transport():
    t = FakeTransport()
    t.open()
    return t


@pytest.fixture
def tb(transport):
    return Timebase(transport)


# ---------------------------------------------------------------------------
# Timebase — scale
# ---------------------------------------------------------------------------


class TestTimebaseScale:
    def test_set_sends_correct_command_5e4(self, transport, tb):
        """Acceptance: tb.scale = 5e-4 → ':TIMebase:SCALe 0.0005'."""
        tb.scale = 5e-4
        assert transport.writes[-1] == ":TIMebase:SCALe 0.0005"

    def test_set_sends_correct_command_plain(self, transport, tb):
        tb.scale = 0.001
        assert transport.writes[-1] == ":TIMebase:SCALe 0.001"

    def test_get_returns_float(self, transport, tb):
        transport.set_response(":TIMebase:SCALe?", "5e-04")
        assert tb.scale == pytest.approx(5e-4)


# ---------------------------------------------------------------------------
# Timebase — position
# ---------------------------------------------------------------------------


class TestTimebasePosition:
    def test_set_sends_correct_command(self, transport, tb):
        tb.position = 1.5
        assert transport.writes[-1] == ":TIMebase:POSition 1.5"

    def test_set_negative(self, transport, tb):
        tb.position = -0.5
        assert transport.writes[-1] == ":TIMebase:POSition -0.5"

    def test_get_returns_float(self, transport, tb):
        transport.set_response(":TIMebase:POSition?", "1.5")
        assert tb.position == pytest.approx(1.5)


# ---------------------------------------------------------------------------
# Timebase — range
# ---------------------------------------------------------------------------


class TestTimebaseRange:
    def test_set_sends_correct_command(self, transport, tb):
        tb.range = 0.01
        assert transport.writes[-1] == ":TIMebase:RANGe 0.01"

    def test_get_returns_float(self, transport, tb):
        transport.set_response(":TIMebase:RANGe?", "0.01")
        assert tb.range == pytest.approx(0.01)


# ---------------------------------------------------------------------------
# Timebase — mode
# ---------------------------------------------------------------------------


class TestTimebaseMode:
    def test_set_main_lowercase_sends_uppercase(self, transport, tb):
        """Acceptance: tb.mode = 'main' → ':TIMebase:MODE MAIN'."""
        tb.mode = "main"
        assert transport.writes[-1] == ":TIMebase:MODE MAIN"

    def test_set_xy(self, transport, tb):
        tb.mode = "XY"
        assert transport.writes[-1] == ":TIMebase:MODE XY"

    def test_set_roll(self, transport, tb):
        tb.mode = "roll"
        assert transport.writes[-1] == ":TIMebase:MODE ROLL"

    def test_get_returns_mode_string(self, transport, tb):
        """Acceptance: set_response(':TIMebase:MODE?','XY'); tb.mode=='XY'."""
        transport.set_response(":TIMebase:MODE?", "XY")
        assert tb.mode == "XY"

    def test_invalid_mode_raises_value_error(self, transport, tb):
        """Acceptance: tb.mode = 'BAD' → ValueError."""
        with pytest.raises(ValueError):
            tb.mode = "BAD"
        # ничего не должно быть записано
        assert len(transport.writes) == 0

    def test_modes_constant(self, tb):
        assert tb.MODES == ("MAIN", "XY", "ROLL")


# ---------------------------------------------------------------------------
# Timebase — window атрибут
# ---------------------------------------------------------------------------


class TestTimebaseWindowAttribute:
    def test_has_window_instance(self, tb):
        assert isinstance(tb.window, TimebaseWindow)


# ---------------------------------------------------------------------------
# TimebaseWindow — enable
# ---------------------------------------------------------------------------


class TestTimebaseWindowEnable:
    @pytest.fixture
    def win(self, transport):
        return TimebaseWindow(transport)

    def test_enable_true_sends_on(self, transport, win):
        """Acceptance: tb.window.enable = True → ':TIMebase:WINDow:ENABle ON'."""
        win.enable = True
        assert transport.writes[-1] == ":TIMebase:WINDow:ENABle ON"

    def test_enable_false_sends_off(self, transport, win):
        win.enable = False
        assert transport.writes[-1] == ":TIMebase:WINDow:ENABle OFF"

    def test_enable_get_parses_zero(self, transport, win):
        transport.set_response(":TIMebase:WINDow:ENABle?", "0")
        assert win.enable is False

    def test_enable_get_parses_one(self, transport, win):
        transport.set_response(":TIMebase:WINDow:ENABle?", "1")
        assert win.enable is True

    def test_enable_get_parses_on(self, transport, win):
        transport.set_response(":TIMebase:WINDow:ENABle?", "ON")
        assert win.enable is True


# ---------------------------------------------------------------------------
# TimebaseWindow — scale
# ---------------------------------------------------------------------------


class TestTimebaseWindowScale:
    @pytest.fixture
    def win(self, transport):
        return TimebaseWindow(transport)

    def test_set_sends_correct_command_1e5(self, transport, win):
        """Acceptance: tb.window.scale = 1e-5 → ':TIMebase:WINDow:SCALe 1e-05'."""
        win.scale = 1e-5
        assert transport.writes[-1] == ":TIMebase:WINDow:SCALe 1e-05"

    def test_set_sends_correct_command_plain(self, transport, win):
        win.scale = 0.001
        assert transport.writes[-1] == ":TIMebase:WINDow:SCALe 0.001"

    def test_get_returns_float(self, transport, win):
        transport.set_response(":TIMebase:WINDow:SCALe?", "1e-05")
        assert win.scale == pytest.approx(1e-5)


# ---------------------------------------------------------------------------
# TimebaseWindow — position
# ---------------------------------------------------------------------------


class TestTimebaseWindowPosition:
    @pytest.fixture
    def win(self, transport):
        return TimebaseWindow(transport)

    def test_set_sends_correct_command(self, transport, win):
        win.position = 0.001
        assert transport.writes[-1] == ":TIMebase:WINDow:POSition 0.001"

    def test_get_returns_float(self, transport, win):
        transport.set_response(":TIMebase:WINDow:POSition?", "0.001")
        assert win.position == pytest.approx(0.001)
