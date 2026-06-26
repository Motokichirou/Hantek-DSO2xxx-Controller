"""Тесты для Transport ABC (hantek_dso2d15/transport/base.py).

TDD — Task 2 плана 2026-06-26-foundation-transport-scpi.md.
"""

import pytest
from hantek_dso2d15.transport.base import Transport


class ConcreteTransport(Transport):
    """Минимальная заглушка, реализующая все абстрактные методы."""

    def __init__(self) -> None:
        self._open = False

    def open(self) -> None:
        self._open = True

    def close(self) -> None:
        self._open = False

    @property
    def is_open(self) -> bool:
        return self._open

    def write(self, cmd: str) -> None:
        pass

    def query(self, cmd: str) -> str:
        return ""

    def read_raw(self) -> bytes:
        return b""


class IncompleteTransport(Transport):
    """Заглушка с одним не реализованным методом (is_open)."""

    def open(self) -> None:
        pass

    def close(self) -> None:
        pass

    def write(self, cmd: str) -> None:
        pass

    def query(self, cmd: str) -> str:
        return ""

    def read_raw(self) -> bytes:
        return b""


# --- Тест 1: прямое инстанцирование ABC → TypeError ---

def test_transport_direct_instantiation_raises_type_error() -> None:
    """Transport() напрямую должен вызывать TypeError."""
    with pytest.raises(TypeError):
        Transport()  # type: ignore[abstract]


# --- Тест 2: неполная реализация → TypeError ---

def test_incomplete_subclass_raises_type_error() -> None:
    """Подкласс без реализации всех абстрактных членов инстанцироваться не должен."""
    with pytest.raises(TypeError):
        IncompleteTransport()  # type: ignore[abstract]


# --- Тест 3: полная реализация — инстанцируется успешно ---

def test_concrete_subclass_instantiates_ok() -> None:
    """Подкласс, реализующий все абстрактные методы, создаётся без ошибок."""
    t = ConcreteTransport()
    assert isinstance(t, Transport)


# --- Тест 4: контракт методов работает на заглушке ---

def test_concrete_transport_open_close_cycle() -> None:
    t = ConcreteTransport()
    assert t.is_open is False
    t.open()
    assert t.is_open is True
    t.close()
    assert t.is_open is False


def test_concrete_transport_write_does_not_raise() -> None:
    t = ConcreteTransport()
    t.write(":CHANnel1:SCALe 0.5")  # должен принять строку без исключений


def test_concrete_transport_query_returns_str() -> None:
    t = ConcreteTransport()
    result = t.query(":CHANnel1:SCALe?")
    assert isinstance(result, str)


def test_concrete_transport_read_raw_returns_bytes() -> None:
    t = ConcreteTransport()
    result = t.read_raw()
    assert isinstance(result, bytes)
