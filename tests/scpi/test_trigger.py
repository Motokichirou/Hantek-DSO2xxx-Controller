"""Тесты для TriggerEdge и Trigger — Task 8 (TDD).

Все тесты — через FakeTransport, без реального железа.
"""

from __future__ import annotations

import pytest

from hantek_dso2d15.transport.fake_transport import FakeTransport
from hantek_dso2d15.scpi.trigger import TriggerEdge, Trigger


# ---------------------------------------------------------------------------
# Фикстуры
# ---------------------------------------------------------------------------


@pytest.fixture()
def transport() -> FakeTransport:
    t = FakeTransport()
    t.open()
    return t


@pytest.fixture()
def edge(transport: FakeTransport) -> TriggerEdge:
    return TriggerEdge(transport)


@pytest.fixture()
def trg(transport: FakeTransport) -> Trigger:
    return Trigger(transport)


# ---------------------------------------------------------------------------
# TriggerEdge — константы
# ---------------------------------------------------------------------------


class TestTriggerEdgeConstants:
    def test_sources_tuple(self) -> None:
        assert TriggerEdge.SOURCES == (
            "CHANnel1",
            "CHANnel2",
            "CHANnel3",
            "CHANnel4",
            "EXT/10",
        )

    def test_slopes_tuple(self) -> None:
        assert TriggerEdge.SLOPES == ("RISIng", "FALLing", "EITHer")


# ---------------------------------------------------------------------------
# TriggerEdge — source (сеттер)
# ---------------------------------------------------------------------------


class TestTriggerEdgeSourceSetter:
    def test_channel1_lowercase_canonicalized(self, trg: Trigger, transport: FakeTransport) -> None:
        """'channel1' → канонический 'CHANnel1', команда точная."""
        trg.edge.source = "channel1"
        assert transport.writes[-1] == ":TRIGger:EDGe:SOURce CHANnel1"

    def test_channel2(self, trg: Trigger, transport: FakeTransport) -> None:
        trg.edge.source = "channel2"
        assert transport.writes[-1] == ":TRIGger:EDGe:SOURce CHANnel2"

    def test_channel3(self, trg: Trigger, transport: FakeTransport) -> None:
        trg.edge.source = "CHANNEL3"
        assert transport.writes[-1] == ":TRIGger:EDGe:SOURce CHANnel3"

    def test_channel4(self, trg: Trigger, transport: FakeTransport) -> None:
        trg.edge.source = "CHANnel4"
        assert transport.writes[-1] == ":TRIGger:EDGe:SOURce CHANnel4"

    def test_ext10_lowercase_slash(self, trg: Trigger, transport: FakeTransport) -> None:
        """'ext/10' → 'EXT/10' (сохраняет слеш, каноникализирует регистр)."""
        trg.edge.source = "ext/10"
        assert transport.writes[-1] == ":TRIGger:EDGe:SOURce EXT/10"

    def test_ext10_canonical(self, trg: Trigger, transport: FakeTransport) -> None:
        trg.edge.source = "EXT/10"
        assert transport.writes[-1] == ":TRIGger:EDGe:SOURce EXT/10"

    def test_invalid_source_raises(self, trg: Trigger, transport: FakeTransport) -> None:
        before = list(transport.writes)
        with pytest.raises(ValueError):
            trg.edge.source = "MATH"
        assert transport.writes == before  # ничего не записано


# ---------------------------------------------------------------------------
# TriggerEdge — source (геттер)
# ---------------------------------------------------------------------------


class TestTriggerEdgeSourceGetter:
    def test_get_source_returns_stripped_response(self, trg: Trigger, transport: FakeTransport) -> None:
        transport.set_response(":TRIGger:EDGe:SOURce?", "CHANnel1\n")
        assert trg.edge.source == "CHANnel1"

    def test_get_source_ext10(self, trg: Trigger, transport: FakeTransport) -> None:
        transport.set_response(":TRIGger:EDGe:SOURce?", "EXT/10")
        assert trg.edge.source == "EXT/10"


# ---------------------------------------------------------------------------
# TriggerEdge — slope (сеттер)
# ---------------------------------------------------------------------------


class TestTriggerEdgeSlopeSetter:
    def test_rising_lowercase_canonicalized(self, trg: Trigger, transport: FakeTransport) -> None:
        """'rising' → канонический 'RISIng' (заглавная I сохраняется)."""
        trg.edge.slope = "rising"
        assert transport.writes[-1] == ":TRIGger:EDGe:SLOPe RISIng"

    def test_falling_mixed_case(self, trg: Trigger, transport: FakeTransport) -> None:
        trg.edge.slope = "FALLING"
        assert transport.writes[-1] == ":TRIGger:EDGe:SLOPe FALLing"

    def test_either_canonical(self, trg: Trigger, transport: FakeTransport) -> None:
        trg.edge.slope = "EITHer"
        assert transport.writes[-1] == ":TRIGger:EDGe:SLOPe EITHer"

    def test_invalid_slope_raises(self, trg: Trigger, transport: FakeTransport) -> None:
        before = list(transport.writes)
        with pytest.raises(ValueError):
            trg.edge.slope = "POSITIVE"
        assert transport.writes == before


# ---------------------------------------------------------------------------
# TriggerEdge — slope (геттер)
# ---------------------------------------------------------------------------


class TestTriggerEdgeSlopeGetter:
    def test_get_slope_returns_response(self, trg: Trigger, transport: FakeTransport) -> None:
        transport.set_response(":TRIGger:EDGe:SLOPe?", "RISIng")
        assert trg.edge.slope == "RISIng"


# ---------------------------------------------------------------------------
# TriggerEdge — level (сеттер / геттер)
# ---------------------------------------------------------------------------


class TestTriggerEdgeLevel:
    def test_level_set_float(self, trg: Trigger, transport: FakeTransport) -> None:
        trg.edge.level = 0.82
        assert transport.writes[-1] == ":TRIGger:EDGe:LEVel 0.82"

    def test_level_set_zero(self, trg: Trigger, transport: FakeTransport) -> None:
        trg.edge.level = 0.0
        assert transport.writes[-1] == ":TRIGger:EDGe:LEVel 0"

    def test_level_set_negative(self, trg: Trigger, transport: FakeTransport) -> None:
        trg.edge.level = -1.5
        assert transport.writes[-1] == ":TRIGger:EDGe:LEVel -1.5"

    def test_level_get(self, trg: Trigger, transport: FakeTransport) -> None:
        transport.set_response(":TRIGger:EDGe:LEVel?", "8.200000e-01")
        assert trg.edge.level == pytest.approx(0.82)


# ---------------------------------------------------------------------------
# Trigger — константы
# ---------------------------------------------------------------------------


class TestTriggerConstants:
    def test_modes_count(self) -> None:
        assert len(Trigger.MODES) == 14

    def test_modes_contents(self) -> None:
        assert Trigger.MODES == (
            "EDGE",
            "PULSe",
            "TV",
            "SLOPe",
            "TIMeout",
            "WINdow",
            "PATTern",
            "INTerval",
            "UNDerthrow",
            "UART",
            "LIN",
            "CAN",
            "SPI",
            "IIC",
        )

    def test_sweeps_tuple(self) -> None:
        assert Trigger.SWEEPS == ("AUTO", "NORMal", "SINGle")


# ---------------------------------------------------------------------------
# Trigger — edge sub-object
# ---------------------------------------------------------------------------


class TestTriggerEdgeSubobject:
    def test_edge_attribute_is_trigger_edge(self, trg: Trigger) -> None:
        assert isinstance(trg.edge, TriggerEdge)

    def test_edge_shares_transport(self, trg: Trigger, transport: FakeTransport) -> None:
        """edge использует тот же transport: команда попадает в writes."""
        trg.edge.source = "CHANnel1"
        assert transport.writes[-1] == ":TRIGger:EDGe:SOURce CHANnel1"


# ---------------------------------------------------------------------------
# Trigger — mode (сеттер / геттер)
# ---------------------------------------------------------------------------


class TestTriggerMode:
    def test_mode_edge_lowercase(self, trg: Trigger, transport: FakeTransport) -> None:
        trg.mode = "edge"
        assert transport.writes[-1] == ":TRIGger:MODE EDGE"

    def test_mode_pulse_mixed_case(self, trg: Trigger, transport: FakeTransport) -> None:
        trg.mode = "pulse"
        assert transport.writes[-1] == ":TRIGger:MODE PULSe"

    def test_mode_slope_canonical(self, trg: Trigger, transport: FakeTransport) -> None:
        trg.mode = "SLOPe"
        assert transport.writes[-1] == ":TRIGger:MODE SLOPe"

    def test_mode_timeout(self, trg: Trigger, transport: FakeTransport) -> None:
        trg.mode = "timeout"
        assert transport.writes[-1] == ":TRIGger:MODE TIMeout"

    def test_mode_uart(self, trg: Trigger, transport: FakeTransport) -> None:
        trg.mode = "uart"
        assert transport.writes[-1] == ":TRIGger:MODE UART"

    def test_mode_invalid_raises(self, trg: Trigger, transport: FakeTransport) -> None:
        before = list(transport.writes)
        with pytest.raises(ValueError):
            trg.mode = "BAD"
        assert transport.writes == before

    def test_mode_get(self, trg: Trigger, transport: FakeTransport) -> None:
        transport.set_response(":TRIGger:MODE?", "EDGE")
        assert trg.mode == "EDGE"


# ---------------------------------------------------------------------------
# Trigger — sweep (сеттер / геттер)
# ---------------------------------------------------------------------------


class TestTriggerSweep:
    def test_sweep_auto(self, trg: Trigger, transport: FakeTransport) -> None:
        trg.sweep = "auto"
        assert transport.writes[-1] == ":TRIGger:SWEep AUTO"

    def test_sweep_normal_mixed_case(self, trg: Trigger, transport: FakeTransport) -> None:
        trg.sweep = "normal"
        assert transport.writes[-1] == ":TRIGger:SWEep NORMal"

    def test_sweep_single(self, trg: Trigger, transport: FakeTransport) -> None:
        trg.sweep = "single"
        assert transport.writes[-1] == ":TRIGger:SWEep SINGle"

    def test_sweep_invalid_raises(self, trg: Trigger, transport: FakeTransport) -> None:
        before = list(transport.writes)
        with pytest.raises(ValueError):
            trg.sweep = "CONTINUOUS"
        assert transport.writes == before

    def test_sweep_get(self, trg: Trigger, transport: FakeTransport) -> None:
        transport.set_response(":TRIGger:SWEep?", "SINGle")
        assert trg.sweep == "SINGle"


# ---------------------------------------------------------------------------
# Trigger — holdoff (сеттер / геттер)
# ---------------------------------------------------------------------------


class TestTriggerHoldoff:
    def test_holdoff_set(self, trg: Trigger, transport: FakeTransport) -> None:
        trg.holdoff = 1e-6
        assert transport.writes[-1] == ":TRIGger:HOLDoff 1e-06"

    def test_holdoff_set_zero(self, trg: Trigger, transport: FakeTransport) -> None:
        trg.holdoff = 0.0
        assert transport.writes[-1] == ":TRIGger:HOLDoff 0"

    def test_holdoff_get(self, trg: Trigger, transport: FakeTransport) -> None:
        transport.set_response(":TRIGger:HOLDoff?", "1.000000e-06")
        assert trg.holdoff == pytest.approx(1e-6)


# ---------------------------------------------------------------------------
# Trigger — status (R/O property)
# ---------------------------------------------------------------------------


class TestTriggerStatus:
    def test_status_triged(self, trg: Trigger, transport: FakeTransport) -> None:
        transport.set_response(":TRIGger:STATus?", "TRIGed")
        assert trg.status == "TRIGed"

    def test_status_notrig(self, trg: Trigger, transport: FakeTransport) -> None:
        transport.set_response(":TRIGger:STATus?", "NOTRIG")
        assert trg.status == "NOTRIG"

    def test_status_strips_whitespace(self, trg: Trigger, transport: FakeTransport) -> None:
        transport.set_response(":TRIGger:STATus?", "  TRIGed\n")
        assert trg.status == "TRIGed"

    def test_status_no_setter(self, trg: Trigger) -> None:
        """status должен быть свойством только для чтения."""
        with pytest.raises(AttributeError):
            trg.status = "TRIGed"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Trigger — force()
# ---------------------------------------------------------------------------


class TestTriggerForce:
    def test_force_sends_command(self, trg: Trigger, transport: FakeTransport) -> None:
        trg.force()
        assert transport.writes[-1] == ":TRIGger:FORCe"

    def test_force_does_not_query(self, trg: Trigger, transport: FakeTransport) -> None:
        trg.force()
        assert transport.queries == []


# ---------------------------------------------------------------------------
# Acceptance-кейсы Task 8 (дословно из плана)
# ---------------------------------------------------------------------------


class TestTask8Acceptance:
    def test_source_channel1_canonical_command(self, trg: Trigger, transport: FakeTransport) -> None:
        """trg.edge.source = 'channel1' → ':TRIGger:EDGe:SOURce CHANnel1'."""
        trg.edge.source = "channel1"
        assert transport.writes[-1] == ":TRIGger:EDGe:SOURce CHANnel1"

    def test_source_ext10_command(self, trg: Trigger, transport: FakeTransport) -> None:
        """trg.edge.source = 'ext/10' → ':TRIGger:EDGe:SOURce EXT/10'."""
        trg.edge.source = "ext/10"
        assert transport.writes[-1] == ":TRIGger:EDGe:SOURce EXT/10"

    def test_slope_rising_canonical(self, trg: Trigger, transport: FakeTransport) -> None:
        """trg.edge.slope = 'rising' → ':TRIGger:EDGe:SLOPe RISIng'."""
        trg.edge.slope = "rising"
        assert transport.writes[-1] == ":TRIGger:EDGe:SLOPe RISIng"

    def test_level_082(self, trg: Trigger, transport: FakeTransport) -> None:
        """trg.edge.level = 0.82 → ':TRIGger:EDGe:LEVel 0.82'."""
        trg.edge.level = 0.82
        assert transport.writes[-1] == ":TRIGger:EDGe:LEVel 0.82"

    def test_mode_edge_command(self, trg: Trigger, transport: FakeTransport) -> None:
        """trg.mode = 'edge' → ':TRIGger:MODE EDGE'."""
        trg.mode = "edge"
        assert transport.writes[-1] == ":TRIGger:MODE EDGE"

    def test_sweep_single_command(self, trg: Trigger, transport: FakeTransport) -> None:
        """trg.sweep = 'single' → ':TRIGger:SWEep SINGle'."""
        trg.sweep = "single"
        assert transport.writes[-1] == ":TRIGger:SWEep SINGle"

    def test_force_command(self, trg: Trigger, transport: FakeTransport) -> None:
        """trg.force() → writes[-1] == ':TRIGger:FORCe'."""
        trg.force()
        assert transport.writes[-1] == ":TRIGger:FORCe"

    def test_status_triged(self, trg: Trigger, transport: FakeTransport) -> None:
        """set_response(':TRIGger:STATus?', 'TRIGed') → trg.status == 'TRIGed'."""
        transport.set_response(":TRIGger:STATus?", "TRIGed")
        assert trg.status == "TRIGed"

    def test_mode_bad_raises_valueerror(self, trg: Trigger, transport: FakeTransport) -> None:
        """trg.mode = 'BAD' → ValueError."""
        with pytest.raises(ValueError):
            trg.mode = "BAD"
