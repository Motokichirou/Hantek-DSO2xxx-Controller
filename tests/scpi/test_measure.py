"""Тесты подсистемы Measure — автоизмерения :MEASure:*.

TDD: тесты написаны ДО реализации. Покрывают acceptance-кейсы контракта.
Запуск: .venv/Scripts/python.exe -m pytest tests/scpi/test_measure.py -q
"""

from __future__ import annotations

import pytest

from hantek_dso2d15.transport.fake_transport import FakeTransport
from hantek_dso2d15.scpi.measure import Measure


@pytest.fixture
def transport() -> FakeTransport:
    t = FakeTransport()
    t.open()
    return t


@pytest.fixture
def meas(transport: FakeTransport) -> Measure:
    return Measure(transport)


# ---------------------------------------------------------------------------
# Константы класса
# ---------------------------------------------------------------------------

class TestMeasureConstants:
    def test_sources_tuple(self):
        assert Measure.SOURCES == ("CHANnel1", "CHANnel2", "CHANnel3", "CHANnel4", "MATH")

    def test_items_count(self):
        assert len(Measure.ITEMS) == 37

    def test_items_contains_vmax_not_max(self):
        """VMAX — рабочий литерал (hardware-verified 2026-06-27); MAX — опечатка мануала."""
        assert "VMAX" in Measure.ITEMS
        assert "MAX" not in Measure.ITEMS

    def test_items_contains_all_expected(self):
        expected = (
            "VMAX", "VMIN", "VPP", "VTOP", "VBASe", "VAMP", "VAVG", "VRMS",
            "OVERshoot", "PREShoot", "MARea", "MPARea", "PERiod", "FREQuency",
            "RTIMe", "FTIMe", "PWIDth", "NWIDth", "PDUTy", "NDUTy",
            "RDELay", "FDELay", "RPHase", "FPHase", "TVMAX", "TVMIN",
            "PSLEWrate", "NSLEWrate", "VUPper", "VMID", "VLOWer",
            "VARIance", "PVRMS", "PPULses", "NPULses", "PEDGes", "NEDGes",
        )
        for item in expected:
            assert item in Measure.ITEMS, f"{item!r} не найден в ITEMS"

    def test_sentinel_value(self):
        assert Measure.SENTINEL == 1000.0


# ---------------------------------------------------------------------------
# read_item — корректные запросы и разбор ответа
# ---------------------------------------------------------------------------

class TestReadItem:
    def test_read_item_vpp_ch1_returns_float(self, meas: Measure, transport: FakeTransport):
        """Acceptance: read_item(1,'VPP') → float 2.08."""
        transport.set_response(":MEASure:CHANnel1:ITEM? VPP", "2.080e+00")
        result = meas.read_item(1, "VPP")
        assert result == pytest.approx(2.080)
        assert isinstance(result, float)

    def test_read_item_sends_exact_query_string(self, meas: Measure, transport: FakeTransport):
        """Точная строка запроса: ':MEASure:CHANnel1:ITEM? VPP'."""
        transport.set_response(":MEASure:CHANnel1:ITEM? VPP", "2.080e+00")
        meas.read_item(1, "VPP")
        assert transport.queries[-1] == ":MEASure:CHANnel1:ITEM? VPP"

    def test_read_item_vrms_ch2(self, meas: Measure, transport: FakeTransport):
        transport.set_response(":MEASure:CHANnel2:ITEM? VRMS", "1.414e+00")
        result = meas.read_item(2, "VRMS")
        assert result == pytest.approx(1.414)
        assert transport.queries[-1] == ":MEASure:CHANnel2:ITEM? VRMS"

    def test_read_item_frequency_ch1(self, meas: Measure, transport: FakeTransport):
        transport.set_response(":MEASure:CHANnel1:ITEM? FREQuency", "1.000e+03")
        result = meas.read_item(1, "FREQuency")
        assert result == pytest.approx(1000.0)
        assert transport.queries[-1] == ":MEASure:CHANnel1:ITEM? FREQuency"

    def test_read_item_vmax_ch3(self, meas: Measure, transport: FakeTransport):
        transport.set_response(":MEASure:CHANnel3:ITEM? VMAX", "5.0e+00")
        result = meas.read_item(3, "VMAX")
        assert result == pytest.approx(5.0)

    def test_read_item_channel4_valid(self, meas: Measure, transport: FakeTransport):
        """Канал 4 допустим."""
        transport.set_response(":MEASure:CHANnel4:ITEM? VMAX", "3.3e+00")
        result = meas.read_item(4, "VMAX")
        assert result == pytest.approx(3.3)

    def test_read_item_case_insensitive_item(self, meas: Measure, transport: FakeTransport):
        """Строчный 'vpp' приводится к каноничному 'VPP' в запросе."""
        transport.set_response(":MEASure:CHANnel1:ITEM? VPP", "3.0e+00")
        result = meas.read_item(1, "vpp")
        assert result == pytest.approx(3.0)
        assert transport.queries[-1] == ":MEASure:CHANnel1:ITEM? VPP"

    def test_read_item_sentinel_returned_unfiltered(self, meas: Measure, transport: FakeTransport):
        """SENTINEL 1000.0 (прошивка: «нет данных») возвращается без фильтрации."""
        transport.set_response(":MEASure:CHANnel1:ITEM? VMAX", "1.000e+03")
        result = meas.read_item(1, "VMAX")
        assert result == 1000.0

    # --- валидация канала ---

    def test_read_item_channel_0_raises_value_error(self, meas: Measure, transport: FakeTransport):
        with pytest.raises(ValueError):
            meas.read_item(0, "VPP")

    def test_read_item_channel_5_raises_value_error(self, meas: Measure, transport: FakeTransport):
        with pytest.raises(ValueError):
            meas.read_item(5, "VPP")

    def test_read_item_channel_invalid_no_query_sent(self, meas: Measure, transport: FakeTransport):
        """При неверном канале запрос к прибору НЕ отправляется."""
        with pytest.raises(ValueError):
            meas.read_item(0, "VPP")
        assert not transport.queries

    # --- валидация item ---

    def test_read_item_invalid_item_raises_value_error(self, meas: Measure, transport: FakeTransport):
        with pytest.raises(ValueError):
            meas.read_item(1, "GARBAGE")

    def test_read_item_item_max_raises_value_error(self, meas: Measure, transport: FakeTransport):
        """'MAX' — опечатка мануала; правильный литерал 'VMAX', MAX должен давать ошибку."""
        with pytest.raises(ValueError):
            meas.read_item(1, "MAX")


# ---------------------------------------------------------------------------
# enable
# ---------------------------------------------------------------------------

class TestMeasureEnable:
    def test_get_enable_true_from_1(self, meas: Measure, transport: FakeTransport):
        transport.set_response(":MEASure:ENABle?", "1")
        assert meas.enable is True

    def test_get_enable_false_from_0(self, meas: Measure, transport: FakeTransport):
        transport.set_response(":MEASure:ENABle?", "0")
        assert meas.enable is False

    def test_get_enable_true_from_on(self, meas: Measure, transport: FakeTransport):
        transport.set_response(":MEASure:ENABle?", "ON")
        assert meas.enable is True

    def test_get_enable_queries_correct_command(self, meas: Measure, transport: FakeTransport):
        transport.set_response(":MEASure:ENABle?", "1")
        _ = meas.enable
        assert transport.queries[-1] == ":MEASure:ENABle?"

    def test_set_enable_true_writes_on(self, meas: Measure, transport: FakeTransport):
        meas.enable = True
        assert transport.writes[-1] == ":MEASure:ENABle ON"

    def test_set_enable_false_writes_off(self, meas: Measure, transport: FakeTransport):
        meas.enable = False
        assert transport.writes[-1] == ":MEASure:ENABle OFF"


# ---------------------------------------------------------------------------
# source
# ---------------------------------------------------------------------------

class TestMeasureSource:
    def test_get_source_returns_string(self, meas: Measure, transport: FakeTransport):
        transport.set_response(":MEASure:SOURce?", "CHANnel1")
        assert meas.source == "CHANnel1"

    def test_get_source_queries_correct_command(self, meas: Measure, transport: FakeTransport):
        transport.set_response(":MEASure:SOURce?", "CHANnel1")
        _ = meas.source
        assert transport.queries[-1] == ":MEASure:SOURce?"

    def test_set_source_channel1(self, meas: Measure, transport: FakeTransport):
        meas.source = "CHANnel1"
        assert transport.writes[-1] == ":MEASure:SOURce CHANnel1"

    def test_set_source_channel2(self, meas: Measure, transport: FakeTransport):
        meas.source = "CHANnel2"
        assert transport.writes[-1] == ":MEASure:SOURce CHANnel2"

    def test_set_source_math(self, meas: Measure, transport: FakeTransport):
        meas.source = "MATH"
        assert transport.writes[-1] == ":MEASure:SOURce MATH"

    def test_set_source_case_insensitive_canonical(self, meas: Measure, transport: FakeTransport):
        """'channel1' → каноничный 'CHANnel1' в команде."""
        meas.source = "channel1"
        assert transport.writes[-1] == ":MEASure:SOURce CHANnel1"

    def test_set_source_invalid_raises_value_error(self, meas: Measure, transport: FakeTransport):
        with pytest.raises(ValueError):
            meas.source = "INVALID"

    def test_set_source_invalid_no_write(self, meas: Measure, transport: FakeTransport):
        """При неверном источнике команда НЕ отправляется."""
        with pytest.raises(ValueError):
            meas.source = "INVALID"
        assert not transport.writes


# ---------------------------------------------------------------------------
# adisplay
# ---------------------------------------------------------------------------

class TestMeasureAdisplay:
    def test_get_adisplay_true(self, meas: Measure, transport: FakeTransport):
        transport.set_response(":MEASure:ADISplay?", "1")
        assert meas.adisplay is True

    def test_get_adisplay_false(self, meas: Measure, transport: FakeTransport):
        transport.set_response(":MEASure:ADISplay?", "0")
        assert meas.adisplay is False

    def test_get_adisplay_queries_correct_command(self, meas: Measure, transport: FakeTransport):
        transport.set_response(":MEASure:ADISplay?", "0")
        _ = meas.adisplay
        assert transport.queries[-1] == ":MEASure:ADISplay?"

    def test_set_adisplay_true_writes_on(self, meas: Measure, transport: FakeTransport):
        meas.adisplay = True
        assert transport.writes[-1] == ":MEASure:ADISplay ON"

    def test_set_adisplay_false_writes_off(self, meas: Measure, transport: FakeTransport):
        meas.adisplay = False
        assert transport.writes[-1] == ":MEASure:ADISplay OFF"


# ---------------------------------------------------------------------------
# gate_enable
# ---------------------------------------------------------------------------

class TestMeasureGateEnable:
    def test_get_gate_enable_true(self, meas: Measure, transport: FakeTransport):
        transport.set_response(":MEASure:GATE:ENABle?", "1")
        assert meas.gate_enable is True

    def test_get_gate_enable_false(self, meas: Measure, transport: FakeTransport):
        transport.set_response(":MEASure:GATE:ENABle?", "0")
        assert meas.gate_enable is False

    def test_get_gate_enable_queries_correct_command(self, meas: Measure, transport: FakeTransport):
        transport.set_response(":MEASure:GATE:ENABle?", "0")
        _ = meas.gate_enable
        assert transport.queries[-1] == ":MEASure:GATE:ENABle?"

    def test_set_gate_enable_true_writes_on(self, meas: Measure, transport: FakeTransport):
        meas.gate_enable = True
        assert transport.writes[-1] == ":MEASure:GATE:ENABle ON"

    def test_set_gate_enable_false_writes_off(self, meas: Measure, transport: FakeTransport):
        meas.gate_enable = False
        assert transport.writes[-1] == ":MEASure:GATE:ENABle OFF"


# ---------------------------------------------------------------------------
# gate_ay
# ---------------------------------------------------------------------------

class TestMeasureGateAy:
    def test_get_gate_ay_parses_int(self, meas: Measure, transport: FakeTransport):
        transport.set_response(":MEASure:GATE:AY?", "1.00e+02")
        result = meas.gate_ay
        assert result == 100
        assert isinstance(result, int)

    def test_get_gate_ay_queries_correct_command(self, meas: Measure, transport: FakeTransport):
        transport.set_response(":MEASure:GATE:AY?", "0")
        _ = meas.gate_ay
        assert transport.queries[-1] == ":MEASure:GATE:AY?"

    def test_set_gate_ay_100_writes_exact(self, meas: Measure, transport: FakeTransport):
        meas.gate_ay = 100
        assert transport.writes[-1] == ":MEASure:GATE:AY 100"

    def test_set_gate_ay_zero_boundary(self, meas: Measure, transport: FakeTransport):
        meas.gate_ay = 0
        assert transport.writes[-1] == ":MEASure:GATE:AY 0"

    def test_set_gate_ay_max_boundary(self, meas: Measure, transport: FakeTransport):
        meas.gate_ay = 400
        assert transport.writes[-1] == ":MEASure:GATE:AY 400"

    def test_set_gate_ay_negative_raises_value_error(self, meas: Measure, transport: FakeTransport):
        with pytest.raises(ValueError):
            meas.gate_ay = -1

    def test_set_gate_ay_over_max_raises_value_error(self, meas: Measure, transport: FakeTransport):
        with pytest.raises(ValueError):
            meas.gate_ay = 401

    def test_set_gate_ay_invalid_no_write(self, meas: Measure, transport: FakeTransport):
        """При неверном значении команда НЕ отправляется."""
        with pytest.raises(ValueError):
            meas.gate_ay = -1
        assert not transport.writes


# ---------------------------------------------------------------------------
# gate_by
# ---------------------------------------------------------------------------

class TestMeasureGateBy:
    def test_get_gate_by_parses_int(self, meas: Measure, transport: FakeTransport):
        transport.set_response(":MEASure:GATE:BY?", "2.00e+02")
        result = meas.gate_by
        assert result == 200
        assert isinstance(result, int)

    def test_get_gate_by_queries_correct_command(self, meas: Measure, transport: FakeTransport):
        transport.set_response(":MEASure:GATE:BY?", "0")
        _ = meas.gate_by
        assert transport.queries[-1] == ":MEASure:GATE:BY?"

    def test_set_gate_by_200_writes_exact(self, meas: Measure, transport: FakeTransport):
        meas.gate_by = 200
        assert transport.writes[-1] == ":MEASure:GATE:BY 200"

    def test_set_gate_by_zero_boundary(self, meas: Measure, transport: FakeTransport):
        meas.gate_by = 0
        assert transport.writes[-1] == ":MEASure:GATE:BY 0"

    def test_set_gate_by_max_boundary(self, meas: Measure, transport: FakeTransport):
        meas.gate_by = 400
        assert transport.writes[-1] == ":MEASure:GATE:BY 400"

    def test_set_gate_by_negative_raises_value_error(self, meas: Measure, transport: FakeTransport):
        with pytest.raises(ValueError):
            meas.gate_by = -1

    def test_set_gate_by_over_max_raises_value_error(self, meas: Measure, transport: FakeTransport):
        with pytest.raises(ValueError):
            meas.gate_by = 401

    def test_set_gate_by_invalid_no_write(self, meas: Measure, transport: FakeTransport):
        """При неверном значении команда НЕ отправляется."""
        with pytest.raises(ValueError):
            meas.gate_by = -1
        assert not transport.writes


# ---------------------------------------------------------------------------
# Интеграция со Scope: scope.measure должен быть экземпляром Measure
# ---------------------------------------------------------------------------

class TestScopeHasMeasure:
    def test_scope_has_measure_attribute(self):
        from hantek_dso2d15.scpi.scope import Scope
        t = FakeTransport()
        t.open()
        scope = Scope(t)
        assert hasattr(scope, "measure")

    def test_scope_measure_is_measure_instance(self):
        from hantek_dso2d15.scpi.scope import Scope
        t = FakeTransport()
        t.open()
        scope = Scope(t)
        assert isinstance(scope.measure, Measure)
