"""Тесты подсистемы Acquire — Task 7.

TDD: тесты написаны ДО реализации. Покрывают acceptance-кейсы Task 7.
Запуск: .venv/Scripts/python.exe -m pytest tests/scpi/test_acquire.py -q
"""

from __future__ import annotations

import pytest

from hantek_dso2d15.transport.fake_transport import FakeTransport
from hantek_dso2d15.scpi.acquire import Acquire


@pytest.fixture
def transport() -> FakeTransport:
    t = FakeTransport()
    t.open()
    return t


@pytest.fixture
def acq(transport: FakeTransport) -> Acquire:
    return Acquire(transport)


# ---------------------------------------------------------------------------
# Константы класса
# ---------------------------------------------------------------------------

class TestAcquireConstants:
    def test_points_tuple(self):
        assert Acquire.POINTS == (4000, 40000, 400000, 4000000, 8000000)

    def test_types_tuple(self):
        assert Acquire.TYPES == ("NORMal", "AVERage", "PEAK", "HRESolution")

    def test_counts_tuple(self):
        assert Acquire.COUNTS == (4, 8, 16, 32, 64, 128)


# ---------------------------------------------------------------------------
# points: сеттер + геттер
# ---------------------------------------------------------------------------

class TestAcquirePoints:
    def test_set_points_writes_exact_command(self, acq: Acquire, transport: FakeTransport):
        """Acceptance: acq.points = 4000 → ':ACQuire:POINts 4000'"""
        acq.points = 4000
        assert transport.writes[-1] == ":ACQuire:POINts 4000"

    def test_set_points_large_value(self, acq: Acquire, transport: FakeTransport):
        acq.points = 8000000
        assert transport.writes[-1] == ":ACQuire:POINts 8000000"

    def test_set_points_middle_value(self, acq: Acquire, transport: FakeTransport):
        acq.points = 400000
        assert transport.writes[-1] == ":ACQuire:POINts 400000"

    def test_get_points_parses_nr3(self, acq: Acquire, transport: FakeTransport):
        """Acceptance: set_response(':ACQuire:POINts?','4.000000e+03'); acq.points==4000"""
        transport.set_response(":ACQuire:POINts?", "4.000000e+03")
        assert acq.points == 4000
        assert isinstance(acq.points, int)

    def test_get_points_queries_correct_command(self, acq: Acquire, transport: FakeTransport):
        transport.set_response(":ACQuire:POINts?", "4.000000e+04")
        _ = acq.points
        assert ":ACQuire:POINts?" in transport.queries

    def test_set_points_invalid_raises_value_error(self, acq: Acquire, transport: FakeTransport):
        """Неверное значение → ValueError, команда НЕ отправлена."""
        writes_before = len(transport.writes)
        with pytest.raises(ValueError):
            acq.points = 5000  # не из POINTS
        assert len(transport.writes) == writes_before

    def test_set_points_invalid_zero(self, acq: Acquire, transport: FakeTransport):
        with pytest.raises(ValueError):
            acq.points = 0

    def test_set_points_invalid_negative(self, acq: Acquire, transport: FakeTransport):
        with pytest.raises(ValueError):
            acq.points = -4000


# ---------------------------------------------------------------------------
# type: сеттер + геттер
# ---------------------------------------------------------------------------

class TestAcquireType:
    def test_set_type_average_canonical(self, acq: Acquire, transport: FakeTransport):
        """Acceptance: acq.type = 'average' → ':ACQuire:TYPE AVERage'"""
        acq.type = "average"
        assert transport.writes[-1] == ":ACQuire:TYPE AVERage"

    def test_set_type_normal(self, acq: Acquire, transport: FakeTransport):
        acq.type = "NORMal"
        assert transport.writes[-1] == ":ACQuire:TYPE NORMal"

    def test_set_type_peak(self, acq: Acquire, transport: FakeTransport):
        acq.type = "peak"
        assert transport.writes[-1] == ":ACQuire:TYPE PEAK"

    def test_set_type_hresolution(self, acq: Acquire, transport: FakeTransport):
        acq.type = "hresolution"
        assert transport.writes[-1] == ":ACQuire:TYPE HRESolution"

    def test_get_type_returns_string(self, acq: Acquire, transport: FakeTransport):
        transport.set_response(":ACQuire:TYPE?", "AVERage")
        assert acq.type == "AVERage"

    def test_set_type_invalid_raises_value_error(self, acq: Acquire, transport: FakeTransport):
        writes_before = len(transport.writes)
        with pytest.raises(ValueError):
            acq.type = "INVALID"
        assert len(transport.writes) == writes_before

    def test_set_type_invalid_does_not_write(self, acq: Acquire, transport: FakeTransport):
        with pytest.raises(ValueError):
            acq.type = "FAST"
        assert not transport.writes


# ---------------------------------------------------------------------------
# count: сеттер + геттер
# ---------------------------------------------------------------------------

class TestAcquireCount:
    def test_set_count_writes_exact_command(self, acq: Acquire, transport: FakeTransport):
        """Acceptance: acq.count = 16 → ':ACQuire:COUNt 16'"""
        acq.count = 16
        assert transport.writes[-1] == ":ACQuire:COUNt 16"

    def test_set_count_all_valid_values(self, acq: Acquire, transport: FakeTransport):
        for v in (4, 8, 16, 32, 64, 128):
            transport.writes.clear()
            acq.count = v
            assert transport.writes[-1] == f":ACQuire:COUNt {v}"

    def test_get_count_parses_int(self, acq: Acquire, transport: FakeTransport):
        transport.set_response(":ACQuire:COUNt?", "1.600000e+01")
        assert acq.count == 16
        assert isinstance(acq.count, int)

    def test_set_count_invalid_raises_value_error(self, acq: Acquire, transport: FakeTransport):
        """Acceptance: acq.count = 7 → ValueError"""
        writes_before = len(transport.writes)
        with pytest.raises(ValueError):
            acq.count = 7
        assert len(transport.writes) == writes_before

    def test_set_count_invalid_does_not_write(self, acq: Acquire, transport: FakeTransport):
        with pytest.raises(ValueError):
            acq.count = 7
        assert not transport.writes

    def test_set_count_3_invalid(self, acq: Acquire, transport: FakeTransport):
        with pytest.raises(ValueError):
            acq.count = 3

    def test_set_count_256_invalid(self, acq: Acquire, transport: FakeTransport):
        with pytest.raises(ValueError):
            acq.count = 256


# ---------------------------------------------------------------------------
# srate: только-чтение
# ---------------------------------------------------------------------------

class TestAcquireSrate:
    def test_get_srate_returns_float(self, acq: Acquire, transport: FakeTransport):
        """Acceptance: set_response(':ACQuire:SRATe?','1.0e9'); acq.srate == 1e9"""
        transport.set_response(":ACQuire:SRATe?", "1.0e9")
        result = acq.srate
        assert result == 1e9
        assert isinstance(result, float)

    def test_get_srate_queries_correct_command(self, acq: Acquire, transport: FakeTransport):
        transport.set_response(":ACQuire:SRATe?", "500000000.0")
        _ = acq.srate
        assert ":ACQuire:SRATe?" in transport.queries

    def test_set_srate_raises_attribute_error(self, acq: Acquire):
        """Acceptance: acq.srate = ... → AttributeError (нет сеттера)"""
        with pytest.raises(AttributeError):
            acq.srate = 1e9  # type: ignore[misc]

    def test_srate_is_property(self):
        """srate должен быть property только-чтения на уровне класса."""
        prop = Acquire.__dict__.get("srate")
        assert isinstance(prop, property), "srate должен быть @property"
        assert prop.fset is None, "srate не должен иметь сеттера"
