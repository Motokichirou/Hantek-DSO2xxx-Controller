"""Тесты подсистемы DDS — встроенный генератор сигналов :DDS:*.

TDD: тесты написаны ДО реализации (RED-first). Покрывают acceptance-кейсы контракта.
Hardware-verified 2026-06-27: все команды работают, прибор молча клампит out-of-range.

Запуск: .venv/Scripts/python.exe -m pytest tests/scpi/test_dds.py -q
"""

from __future__ import annotations

import pytest

from hantek_dso2d15.transport.fake_transport import FakeTransport
from hantek_dso2d15.scpi.dds import DDS


@pytest.fixture
def transport() -> FakeTransport:
    t = FakeTransport()
    t.open()
    return t


@pytest.fixture
def dds(transport: FakeTransport) -> DDS:
    return DDS(transport)


# ---------------------------------------------------------------------------
# Константы класса
# ---------------------------------------------------------------------------

class TestDDSConstants:
    def test_types_tuple(self):
        assert DDS.TYPES == ("SINE", "SQUAre", "RAMP", "EXP", "NOISe", "DC", "ARB1", "ARB2", "ARB3", "ARB4")

    def test_mod_types_tuple(self):
        assert DDS.MOD_TYPES == ("AM", "FM")

    def test_mod_waves_tuple(self):
        assert DDS.MOD_WAVES == ("SINE", "SQUAre", "RAMP")

    def test_burst_types_tuple(self):
        assert DDS.BURST_TYPES == ("N_CYCLE", "INFInit")

    def test_types_count(self):
        assert len(DDS.TYPES) == 10


# ---------------------------------------------------------------------------
# output — :DDS:SWITch
# ---------------------------------------------------------------------------

class TestDDSOutput:
    def test_get_output_true_from_on(self, dds: DDS, transport: FakeTransport):
        transport.set_response(":DDS:SWITch?", "ON")
        assert dds.output is True

    def test_get_output_false_from_off(self, dds: DDS, transport: FakeTransport):
        transport.set_response(":DDS:SWITch?", "OFF")
        assert dds.output is False

    def test_get_output_true_from_1(self, dds: DDS, transport: FakeTransport):
        transport.set_response(":DDS:SWITch?", "1")
        assert dds.output is True

    def test_get_output_false_from_0(self, dds: DDS, transport: FakeTransport):
        transport.set_response(":DDS:SWITch?", "0")
        assert dds.output is False

    def test_get_output_queries_correct_command(self, dds: DDS, transport: FakeTransport):
        transport.set_response(":DDS:SWITch?", "ON")
        _ = dds.output
        assert transport.queries[-1] == ":DDS:SWITch?"

    def test_set_output_true_writes_on(self, dds: DDS, transport: FakeTransport):
        dds.output = True
        assert transport.writes[-1] == ":DDS:SWITch ON"

    def test_set_output_false_writes_off(self, dds: DDS, transport: FakeTransport):
        dds.output = False
        assert transport.writes[-1] == ":DDS:SWITch OFF"

    def test_set_output_string_on_writes_on(self, dds: DDS, transport: FakeTransport):
        dds.output = "ON"
        assert transport.writes[-1] == ":DDS:SWITch ON"

    def test_set_output_string_off_writes_off(self, dds: DDS, transport: FakeTransport):
        dds.output = "OFF"
        assert transport.writes[-1] == ":DDS:SWITch OFF"


# ---------------------------------------------------------------------------
# type — :DDS:TYPE
# ---------------------------------------------------------------------------

class TestDDSType:
    def test_get_type_returns_string(self, dds: DDS, transport: FakeTransport):
        transport.set_response(":DDS:TYPE?", "SINE")
        assert dds.type == "SINE"

    def test_get_type_queries_correct_command(self, dds: DDS, transport: FakeTransport):
        transport.set_response(":DDS:TYPE?", "SINE")
        _ = dds.type
        assert transport.queries[-1] == ":DDS:TYPE?"

    def test_set_type_sine_writes_canonical(self, dds: DDS, transport: FakeTransport):
        dds.type = "SINE"
        assert transport.writes[-1] == ":DDS:TYPE SINE"

    def test_set_type_square_writes_canonical(self, dds: DDS, transport: FakeTransport):
        dds.type = "SQUAre"
        assert transport.writes[-1] == ":DDS:TYPE SQUAre"

    def test_set_type_ramp_writes_canonical(self, dds: DDS, transport: FakeTransport):
        dds.type = "RAMP"
        assert transport.writes[-1] == ":DDS:TYPE RAMP"

    def test_set_type_noise_writes_canonical(self, dds: DDS, transport: FakeTransport):
        dds.type = "NOISe"
        assert transport.writes[-1] == ":DDS:TYPE NOISe"

    def test_set_type_arb1_writes_canonical(self, dds: DDS, transport: FakeTransport):
        dds.type = "ARB1"
        assert transport.writes[-1] == ":DDS:TYPE ARB1"

    def test_set_type_case_insensitive(self, dds: DDS, transport: FakeTransport):
        """'sine' → каноничный 'SINE' в команде."""
        dds.type = "sine"
        assert transport.writes[-1] == ":DDS:TYPE SINE"

    def test_set_type_invalid_raises_value_error(self, dds: DDS, transport: FakeTransport):
        with pytest.raises(ValueError):
            dds.type = "TRIANGLE"

    def test_set_type_invalid_no_write(self, dds: DDS, transport: FakeTransport):
        """При неверном типе команда НЕ отправляется."""
        with pytest.raises(ValueError):
            dds.type = "GARBAGE"
        assert not transport.writes


# ---------------------------------------------------------------------------
# freq — :DDS:FREQ
# ---------------------------------------------------------------------------

class TestDDSFreq:
    def test_get_freq_parses_float(self, dds: DDS, transport: FakeTransport):
        transport.set_response(":DDS:FREQ?", "1.000000e+03")
        result = dds.freq
        assert result == pytest.approx(1000.0)
        assert isinstance(result, float)

    def test_get_freq_queries_correct_command(self, dds: DDS, transport: FakeTransport):
        transport.set_response(":DDS:FREQ?", "1.000000e+03")
        _ = dds.freq
        assert transport.queries[-1] == ":DDS:FREQ?"

    def test_set_freq_1khz_writes_fmt_num(self, dds: DDS, transport: FakeTransport):
        dds.freq = 1000
        assert transport.writes[-1] == ":DDS:FREQ 1000"

    def test_set_freq_float_writes_fmt_num(self, dds: DDS, transport: FakeTransport):
        dds.freq = 1500.5
        assert transport.writes[-1] == ":DDS:FREQ 1500.5"

    def test_set_freq_1mhz_writes_fmt_num(self, dds: DDS, transport: FakeTransport):
        dds.freq = 1_000_000
        assert transport.writes[-1] == ":DDS:FREQ 1e+06"

    def test_set_freq_small_writes_fmt_num(self, dds: DDS, transport: FakeTransport):
        dds.freq = 0.1
        assert transport.writes[-1] == ":DDS:FREQ 0.1"


# ---------------------------------------------------------------------------
# amplitude — :DDS:AMP
# ---------------------------------------------------------------------------

class TestDDSAmplitude:
    def test_get_amplitude_parses_float(self, dds: DDS, transport: FakeTransport):
        transport.set_response(":DDS:AMP?", "2.000000e+00")
        result = dds.amplitude
        assert result == pytest.approx(2.0)
        assert isinstance(result, float)

    def test_get_amplitude_queries_correct_command(self, dds: DDS, transport: FakeTransport):
        transport.set_response(":DDS:AMP?", "2.000000e+00")
        _ = dds.amplitude
        assert transport.queries[-1] == ":DDS:AMP?"

    def test_set_amplitude_writes_fmt_num(self, dds: DDS, transport: FakeTransport):
        dds.amplitude = 2.0
        assert transport.writes[-1] == ":DDS:AMP 2"

    def test_set_amplitude_small_writes_fmt_num(self, dds: DDS, transport: FakeTransport):
        dds.amplitude = 0.5
        assert transport.writes[-1] == ":DDS:AMP 0.5"

    def test_set_amplitude_large_writes_fmt_num(self, dds: DDS, transport: FakeTransport):
        dds.amplitude = 10.0
        assert transport.writes[-1] == ":DDS:AMP 10"


# ---------------------------------------------------------------------------
# offset — :DDS:OFFSet
# ---------------------------------------------------------------------------

class TestDDSOffset:
    def test_get_offset_parses_float(self, dds: DDS, transport: FakeTransport):
        transport.set_response(":DDS:OFFSet?", "0.000000e+00")
        result = dds.offset
        assert result == pytest.approx(0.0)
        assert isinstance(result, float)

    def test_get_offset_queries_correct_command(self, dds: DDS, transport: FakeTransport):
        transport.set_response(":DDS:OFFSet?", "0.000000e+00")
        _ = dds.offset
        assert transport.queries[-1] == ":DDS:OFFSet?"

    def test_set_offset_zero_writes_fmt_num(self, dds: DDS, transport: FakeTransport):
        dds.offset = 0.0
        assert transport.writes[-1] == ":DDS:OFFSet 0"

    def test_set_offset_positive_writes_fmt_num(self, dds: DDS, transport: FakeTransport):
        dds.offset = 1.5
        assert transport.writes[-1] == ":DDS:OFFSet 1.5"

    def test_set_offset_negative_writes_fmt_num(self, dds: DDS, transport: FakeTransport):
        dds.offset = -1.0
        assert transport.writes[-1] == ":DDS:OFFSet -1"


# ---------------------------------------------------------------------------
# duty — :DDS:DUTY
# ---------------------------------------------------------------------------

class TestDDSDuty:
    def test_get_duty_parses_float(self, dds: DDS, transport: FakeTransport):
        transport.set_response(":DDS:DUTY?", "50")
        result = dds.duty
        assert result == pytest.approx(50.0)
        assert isinstance(result, float)

    def test_get_duty_small_parses_float(self, dds: DDS, transport: FakeTransport):
        """Hardware-verified: DUTY? может вернуть '0.002' для очень малого duty."""
        transport.set_response(":DDS:DUTY?", "0.002")
        result = dds.duty
        assert result == pytest.approx(0.002)

    def test_get_duty_queries_correct_command(self, dds: DDS, transport: FakeTransport):
        transport.set_response(":DDS:DUTY?", "50")
        _ = dds.duty
        assert transport.queries[-1] == ":DDS:DUTY?"

    def test_set_duty_50_writes_fmt_num(self, dds: DDS, transport: FakeTransport):
        dds.duty = 50
        assert transport.writes[-1] == ":DDS:DUTY 50"

    def test_set_duty_25_5_writes_fmt_num(self, dds: DDS, transport: FakeTransport):
        dds.duty = 25.5
        assert transport.writes[-1] == ":DDS:DUTY 25.5"


# ---------------------------------------------------------------------------
# mod_enable — :DDS:WAVE:MODE
# ---------------------------------------------------------------------------

class TestDDSModEnable:
    def test_get_mod_enable_true_from_on(self, dds: DDS, transport: FakeTransport):
        transport.set_response(":DDS:WAVE:MODE?", "ON")
        assert dds.mod_enable is True

    def test_get_mod_enable_false_from_off(self, dds: DDS, transport: FakeTransport):
        transport.set_response(":DDS:WAVE:MODE?", "OFF")
        assert dds.mod_enable is False

    def test_get_mod_enable_queries_correct_command(self, dds: DDS, transport: FakeTransport):
        transport.set_response(":DDS:WAVE:MODE?", "OFF")
        _ = dds.mod_enable
        assert transport.queries[-1] == ":DDS:WAVE:MODE?"

    def test_set_mod_enable_true_writes_on(self, dds: DDS, transport: FakeTransport):
        dds.mod_enable = True
        assert transport.writes[-1] == ":DDS:WAVE:MODE ON"

    def test_set_mod_enable_false_writes_off(self, dds: DDS, transport: FakeTransport):
        dds.mod_enable = False
        assert transport.writes[-1] == ":DDS:WAVE:MODE OFF"


# ---------------------------------------------------------------------------
# mod_type — :DDS:MODE:TYPE
# ---------------------------------------------------------------------------

class TestDDSModType:
    def test_get_mod_type_returns_string(self, dds: DDS, transport: FakeTransport):
        transport.set_response(":DDS:MODE:TYPE?", "AM")
        assert dds.mod_type == "AM"

    def test_get_mod_type_queries_correct_command(self, dds: DDS, transport: FakeTransport):
        transport.set_response(":DDS:MODE:TYPE?", "AM")
        _ = dds.mod_type
        assert transport.queries[-1] == ":DDS:MODE:TYPE?"

    def test_set_mod_type_am_writes_canonical(self, dds: DDS, transport: FakeTransport):
        dds.mod_type = "AM"
        assert transport.writes[-1] == ":DDS:MODE:TYPE AM"

    def test_set_mod_type_fm_writes_canonical(self, dds: DDS, transport: FakeTransport):
        dds.mod_type = "FM"
        assert transport.writes[-1] == ":DDS:MODE:TYPE FM"

    def test_set_mod_type_case_insensitive(self, dds: DDS, transport: FakeTransport):
        dds.mod_type = "am"
        assert transport.writes[-1] == ":DDS:MODE:TYPE AM"

    def test_set_mod_type_invalid_raises_value_error(self, dds: DDS, transport: FakeTransport):
        with pytest.raises(ValueError):
            dds.mod_type = "PM"

    def test_set_mod_type_invalid_no_write(self, dds: DDS, transport: FakeTransport):
        with pytest.raises(ValueError):
            dds.mod_type = "GARBAGE"
        assert not transport.writes


# ---------------------------------------------------------------------------
# mod_wave — :DDS:MODE:WAVE:TYPE
# ---------------------------------------------------------------------------

class TestDDSModWave:
    def test_get_mod_wave_returns_string(self, dds: DDS, transport: FakeTransport):
        transport.set_response(":DDS:MODE:WAVE:TYPE?", "SINE")
        assert dds.mod_wave == "SINE"

    def test_get_mod_wave_queries_correct_command(self, dds: DDS, transport: FakeTransport):
        transport.set_response(":DDS:MODE:WAVE:TYPE?", "SINE")
        _ = dds.mod_wave
        assert transport.queries[-1] == ":DDS:MODE:WAVE:TYPE?"

    def test_set_mod_wave_sine_writes_canonical(self, dds: DDS, transport: FakeTransport):
        dds.mod_wave = "SINE"
        assert transport.writes[-1] == ":DDS:MODE:WAVE:TYPE SINE"

    def test_set_mod_wave_square_writes_canonical(self, dds: DDS, transport: FakeTransport):
        dds.mod_wave = "SQUAre"
        assert transport.writes[-1] == ":DDS:MODE:WAVE:TYPE SQUAre"

    def test_set_mod_wave_ramp_writes_canonical(self, dds: DDS, transport: FakeTransport):
        dds.mod_wave = "RAMP"
        assert transport.writes[-1] == ":DDS:MODE:WAVE:TYPE RAMP"

    def test_set_mod_wave_case_insensitive(self, dds: DDS, transport: FakeTransport):
        dds.mod_wave = "ramp"
        assert transport.writes[-1] == ":DDS:MODE:WAVE:TYPE RAMP"

    def test_set_mod_wave_invalid_raises_value_error(self, dds: DDS, transport: FakeTransport):
        with pytest.raises(ValueError):
            dds.mod_wave = "TRIANGLE"

    def test_set_mod_wave_invalid_no_write(self, dds: DDS, transport: FakeTransport):
        with pytest.raises(ValueError):
            dds.mod_wave = "GARBAGE"
        assert not transport.writes


# ---------------------------------------------------------------------------
# mod_freq — :DDS:MODE:FREQ
# ---------------------------------------------------------------------------

class TestDDSModFreq:
    def test_get_mod_freq_parses_float(self, dds: DDS, transport: FakeTransport):
        transport.set_response(":DDS:MODE:FREQ?", "1.000000e+03")
        result = dds.mod_freq
        assert result == pytest.approx(1000.0)
        assert isinstance(result, float)

    def test_get_mod_freq_queries_correct_command(self, dds: DDS, transport: FakeTransport):
        transport.set_response(":DDS:MODE:FREQ?", "1.000000e+03")
        _ = dds.mod_freq
        assert transport.queries[-1] == ":DDS:MODE:FREQ?"

    def test_set_mod_freq_writes_fmt_num(self, dds: DDS, transport: FakeTransport):
        dds.mod_freq = 100
        assert transport.writes[-1] == ":DDS:MODE:FREQ 100"

    def test_set_mod_freq_float_writes_fmt_num(self, dds: DDS, transport: FakeTransport):
        dds.mod_freq = 50.5
        assert transport.writes[-1] == ":DDS:MODE:FREQ 50.5"


# ---------------------------------------------------------------------------
# mod_depth — :DDS:MODE:DEPThordeviation
# ---------------------------------------------------------------------------

class TestDDSModDepth:
    """mod_depth: двойное назначение — AM-глубина (%) / FM-девиация (Hz).

    Литерал ':DDS:MODE:DEPThordeviation' — дословно из мануала (hardware-verified).
    """

    def test_get_mod_depth_parses_float(self, dds: DDS, transport: FakeTransport):
        transport.set_response(":DDS:MODE:DEPThordeviation?", "50")
        result = dds.mod_depth
        assert result == pytest.approx(50.0)
        assert isinstance(result, float)

    def test_get_mod_depth_queries_correct_command(self, dds: DDS, transport: FakeTransport):
        """Литерал ':DDS:MODE:DEPThordeviation?' — точно такой, без исправлений."""
        transport.set_response(":DDS:MODE:DEPThordeviation?", "50")
        _ = dds.mod_depth
        assert transport.queries[-1] == ":DDS:MODE:DEPThordeviation?"

    def test_set_mod_depth_writes_exact_literal(self, dds: DDS, transport: FakeTransport):
        """Литерал ':DDS:MODE:DEPThordeviation' — точно такой в записи."""
        dds.mod_depth = 50
        assert transport.writes[-1] == ":DDS:MODE:DEPThordeviation 50"

    def test_set_mod_depth_float_writes_fmt_num(self, dds: DDS, transport: FakeTransport):
        dds.mod_depth = 75.5
        assert transport.writes[-1] == ":DDS:MODE:DEPThordeviation 75.5"

    def test_set_mod_depth_fm_deviation_hz(self, dds: DDS, transport: FakeTransport):
        """FM-девиация в Hz использует ту же команду."""
        dds.mod_depth = 1000
        assert transport.writes[-1] == ":DDS:MODE:DEPThordeviation 1000"


# ---------------------------------------------------------------------------
# burst_enable — :DDS:BURSt:SWITch
# ---------------------------------------------------------------------------

class TestDDSBurstEnable:
    def test_get_burst_enable_true_from_on(self, dds: DDS, transport: FakeTransport):
        transport.set_response(":DDS:BURSt:SWITch?", "ON")
        assert dds.burst_enable is True

    def test_get_burst_enable_false_from_off(self, dds: DDS, transport: FakeTransport):
        transport.set_response(":DDS:BURSt:SWITch?", "OFF")
        assert dds.burst_enable is False

    def test_get_burst_enable_queries_correct_command(self, dds: DDS, transport: FakeTransport):
        transport.set_response(":DDS:BURSt:SWITch?", "OFF")
        _ = dds.burst_enable
        assert transport.queries[-1] == ":DDS:BURSt:SWITch?"

    def test_set_burst_enable_true_writes_on(self, dds: DDS, transport: FakeTransport):
        dds.burst_enable = True
        assert transport.writes[-1] == ":DDS:BURSt:SWITch ON"

    def test_set_burst_enable_false_writes_off(self, dds: DDS, transport: FakeTransport):
        dds.burst_enable = False
        assert transport.writes[-1] == ":DDS:BURSt:SWITch OFF"


# ---------------------------------------------------------------------------
# burst_type — :DDS:BURSt:TYPE
# ---------------------------------------------------------------------------

class TestDDSBurstType:
    def test_get_burst_type_returns_string(self, dds: DDS, transport: FakeTransport):
        transport.set_response(":DDS:BURSt:TYPE?", "N_CYCLE")
        assert dds.burst_type == "N_CYCLE"

    def test_get_burst_type_queries_correct_command(self, dds: DDS, transport: FakeTransport):
        transport.set_response(":DDS:BURSt:TYPE?", "N_CYCLE")
        _ = dds.burst_type
        assert transport.queries[-1] == ":DDS:BURSt:TYPE?"

    def test_set_burst_type_n_cycle_writes_canonical(self, dds: DDS, transport: FakeTransport):
        dds.burst_type = "N_CYCLE"
        assert transport.writes[-1] == ":DDS:BURSt:TYPE N_CYCLE"

    def test_set_burst_type_infinit_writes_canonical(self, dds: DDS, transport: FakeTransport):
        dds.burst_type = "INFInit"
        assert transport.writes[-1] == ":DDS:BURSt:TYPE INFInit"

    def test_set_burst_type_case_insensitive(self, dds: DDS, transport: FakeTransport):
        dds.burst_type = "n_cycle"
        assert transport.writes[-1] == ":DDS:BURSt:TYPE N_CYCLE"

    def test_set_burst_type_invalid_raises_value_error(self, dds: DDS, transport: FakeTransport):
        with pytest.raises(ValueError):
            dds.burst_type = "SINGLE"

    def test_set_burst_type_invalid_no_write(self, dds: DDS, transport: FakeTransport):
        with pytest.raises(ValueError):
            dds.burst_type = "GARBAGE"
        assert not transport.writes


# ---------------------------------------------------------------------------
# burst_count — :DDS:BURSt:CNT
# ---------------------------------------------------------------------------

class TestDDSBurstCount:
    def test_get_burst_count_parses_int(self, dds: DDS, transport: FakeTransport):
        transport.set_response(":DDS:BURSt:CNT?", "5")
        result = dds.burst_count
        assert result == 5
        assert isinstance(result, int)

    def test_get_burst_count_from_nr3_parses_int(self, dds: DDS, transport: FakeTransport):
        """Hardware-verified: readback может вернуть '5.000000e+00' (NR3-формат)."""
        transport.set_response(":DDS:BURSt:CNT?", "5.000000e+00")
        result = dds.burst_count
        assert result == 5
        assert isinstance(result, int)

    def test_get_burst_count_queries_correct_command(self, dds: DDS, transport: FakeTransport):
        transport.set_response(":DDS:BURSt:CNT?", "1")
        _ = dds.burst_count
        assert transport.queries[-1] == ":DDS:BURSt:CNT?"

    def test_set_burst_count_1_writes_int(self, dds: DDS, transport: FakeTransport):
        dds.burst_count = 1
        assert transport.writes[-1] == ":DDS:BURSt:CNT 1"

    def test_set_burst_count_100_writes_int(self, dds: DDS, transport: FakeTransport):
        dds.burst_count = 100
        assert transport.writes[-1] == ":DDS:BURSt:CNT 100"

    def test_set_burst_count_writes_int_not_float(self, dds: DDS, transport: FakeTransport):
        """Значение должно быть записано как int, не '100.0'."""
        dds.burst_count = 100
        assert "." not in transport.writes[-1]


# ---------------------------------------------------------------------------
# burst_trigger — :DDS:BURSt:TRIGger
# ---------------------------------------------------------------------------

class TestDDSBurstTrigger:
    def test_burst_trigger_writes_exact_command(self, dds: DDS, transport: FakeTransport):
        dds.burst_trigger()
        assert transport.writes[-1] == ":DDS:BURSt:TRIGger"

    def test_burst_trigger_writes_only_once(self, dds: DDS, transport: FakeTransport):
        dds.burst_trigger()
        assert len(transport.writes) == 1

    def test_burst_trigger_returns_none(self, dds: DDS, transport: FakeTransport):
        result = dds.burst_trigger()
        assert result is None

    def test_burst_trigger_no_query_sent(self, dds: DDS, transport: FakeTransport):
        dds.burst_trigger()
        assert not transport.queries


# ---------------------------------------------------------------------------
# Интеграция со Scope: scope.dds должен быть экземпляром DDS
# ---------------------------------------------------------------------------

class TestScopeHasDDS:
    def test_scope_has_dds_attribute(self):
        from hantek_dso2d15.scpi.scope import Scope
        t = FakeTransport()
        t.open()
        scope = Scope(t)
        assert hasattr(scope, "dds")

    def test_scope_dds_is_dds_instance(self):
        from hantek_dso2d15.scpi.scope import Scope
        t = FakeTransport()
        t.open()
        scope = Scope(t)
        assert isinstance(scope.dds, DDS)

    def test_scope_existing_subsystems_intact(self):
        """Подключение DDS не должно сломать другие подсистемы."""
        from hantek_dso2d15.scpi.scope import Scope
        from hantek_dso2d15.scpi.acquire import Acquire
        from hantek_dso2d15.scpi.measure import Measure
        t = FakeTransport()
        t.open()
        scope = Scope(t)
        assert hasattr(scope, "acquire")
        assert hasattr(scope, "measure")
        assert hasattr(scope, "timebase")
        assert hasattr(scope, "trigger")
        assert hasattr(scope, "channel")
