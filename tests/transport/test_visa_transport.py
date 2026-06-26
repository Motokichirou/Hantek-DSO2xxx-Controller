"""Тесты VisaTransport через инъекцию фейкового resource_manager.

Реальный PyVISA не открывается — весь I/O через заглушки.
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from hantek_dso2d15.transport.visa_transport import VisaTransport


# ---------------------------------------------------------------------------
# Фейковые классы-заглушки (ручной вариант, без MagicMock)
# ---------------------------------------------------------------------------

class FakeResource:
    """Заглушка pyvisa-ресурса."""

    def __init__(self, return_value: str = "FAKE"):
        self.timeout: int | None = None
        self.read_termination: str | None = None
        self.write_termination: str | None = None
        self._return_value = return_value
        self._written: list[str] = []
        self._raw_chunks: list[bytes] = []
        self._closed = False

    def write(self, cmd: str) -> None:
        self._written.append(cmd)

    def query(self, cmd: str) -> str:
        return self._return_value

    def read_raw(self) -> bytes:
        return self._raw_chunks.pop(0)

    def close(self) -> None:
        self._closed = True


class FakeResourceManager:
    """Заглушка pyvisa.ResourceManager."""

    def __init__(self, resources: tuple[str, ...] = ("USB0::0x0483::INSTR",)):
        self._resources = resources
        self._last_opened: FakeResource | None = None
        self.resource_string: str | None = None

    def list_resources(self) -> tuple[str, ...]:
        return self._resources

    def open_resource(self, resource_string: str) -> FakeResource:
        self.resource_string = resource_string
        self._last_opened = FakeResource()
        return self._last_opened


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

RESOURCE_STR = "USB0::0x0483::0x5740::CN21034::INSTR"


@pytest.fixture
def fake_rm():
    return FakeResourceManager()


@pytest.fixture
def vt(fake_rm):
    """VisaTransport с фейковым RM, ещё не открытый."""
    return VisaTransport(RESOURCE_STR, resource_manager=fake_rm)


@pytest.fixture
def vt_open(fake_rm):
    """VisaTransport с фейковым RM, уже открытый."""
    t = VisaTransport(RESOURCE_STR, resource_manager=fake_rm)
    t.open()
    return t


# ---------------------------------------------------------------------------
# 1. list_resources
# ---------------------------------------------------------------------------

class TestListResources:
    def test_returns_tuple(self):
        rm = FakeResourceManager(("USB0::A", "GPIB0::1"))
        result = VisaTransport.list_resources(resource_manager=rm)
        assert isinstance(result, tuple)

    def test_delegates_to_rm(self):
        rm = FakeResourceManager(("USB0::A", "GPIB0::1"))
        result = VisaTransport.list_resources(resource_manager=rm)
        assert result == ("USB0::A", "GPIB0::1")

    def test_empty_list(self):
        rm = FakeResourceManager(())
        result = VisaTransport.list_resources(resource_manager=rm)
        assert result == ()


# ---------------------------------------------------------------------------
# 2. open() — вызывает open_resource, выставляет атрибуты ресурса
# ---------------------------------------------------------------------------

class TestOpen:
    def test_calls_open_resource_with_correct_string(self, fake_rm, vt):
        vt.open()
        assert fake_rm.resource_string == RESOURCE_STR

    def test_sets_timeout(self, fake_rm, vt):
        vt.open()
        assert fake_rm._last_opened.timeout == 5000

    def test_sets_read_termination(self, fake_rm, vt):
        # USBTMC завершает чтение по EOM, не по символу; default None (подтверждено на железе).
        vt.open()
        assert fake_rm._last_opened.read_termination is None

    def test_sets_write_termination(self, fake_rm, vt):
        vt.open()
        assert fake_rm._last_opened.write_termination == "\n"

    def test_custom_timeout(self, fake_rm):
        vt = VisaTransport(RESOURCE_STR, timeout_ms=2000, resource_manager=fake_rm)
        vt.open()
        assert fake_rm._last_opened.timeout == 2000

    def test_custom_terminations(self, fake_rm):
        vt = VisaTransport(RESOURCE_STR, read_termination="\r\n",
                           write_termination="\r\n", resource_manager=fake_rm)
        vt.open()
        assert fake_rm._last_opened.read_termination == "\r\n"
        assert fake_rm._last_opened.write_termination == "\r\n"

    def test_is_open_after_open(self, vt):
        assert vt.is_open is False
        vt.open()
        assert vt.is_open is True


# ---------------------------------------------------------------------------
# 3. close()
# ---------------------------------------------------------------------------

class TestClose:
    def test_is_open_false_after_close(self, vt_open):
        assert vt_open.is_open is True
        vt_open.close()
        assert vt_open.is_open is False

    def test_close_calls_resource_close(self, fake_rm, vt_open):
        resource = fake_rm._last_opened
        vt_open.close()
        assert resource._closed is True

    def test_close_on_already_closed_is_noop(self, vt):
        """close() на уже закрытом не должен падать."""
        vt.close()  # должно быть безопасно


# ---------------------------------------------------------------------------
# 4. write() / query() / read_raw() — делегируют ресурсу
# ---------------------------------------------------------------------------

class TestWriteQuery:
    def test_write_delegates_to_resource(self, fake_rm, vt_open):
        vt_open.write(":X 1")
        assert fake_rm._last_opened._written == [":X 1"]

    def test_write_raises_on_closed(self, vt):
        with pytest.raises(RuntimeError):
            vt.write(":X 1")

    def test_query_returns_resource_value(self, fake_rm, vt_open):
        fake_rm._last_opened._return_value = "Hantek,DSO2D15"
        result = vt_open.query("*IDN?")
        assert result == "Hantek,DSO2D15"

    def test_query_raises_on_closed(self, vt):
        with pytest.raises(RuntimeError):
            vt.query("*IDN?")

    def test_read_raw_delegates_to_resource(self, fake_rm, vt_open):
        fake_rm._last_opened._raw_chunks = [b"\x01\x02"]
        result = vt_open.read_raw()
        assert result == b"\x01\x02"

    def test_read_raw_raises_on_closed(self, vt):
        with pytest.raises(RuntimeError):
            vt.read_raw()


# ---------------------------------------------------------------------------
# 5. reconnect()
# ---------------------------------------------------------------------------

class TestReconnect:
    def test_reconnect_closes_and_reopens(self, fake_rm, vt_open):
        old_resource = fake_rm._last_opened
        vt_open.reconnect()
        # Старый ресурс закрыт
        assert old_resource._closed is True
        # Снова открыт (новый ресурс)
        assert vt_open.is_open is True

    def test_write_works_after_reconnect(self, fake_rm, vt_open):
        vt_open.reconnect()
        vt_open.write(":Y 2")
        assert fake_rm._last_opened._written == [":Y 2"]


# ---------------------------------------------------------------------------
# 6. Наследование от Transport ABC
# ---------------------------------------------------------------------------

class TestInheritance:
    def test_is_transport_subclass(self):
        from hantek_dso2d15.transport.base import Transport
        assert issubclass(VisaTransport, Transport)

    def test_instance_is_transport(self, vt):
        from hantek_dso2d15.transport.base import Transport
        assert isinstance(vt, Transport)


# ---------------------------------------------------------------------------
# 7. MagicMock вариант (дополнительный acceptance-тест из плана)
# ---------------------------------------------------------------------------

class TestWithMagicMock:
    """Acceptance-кейсы Task 9 с unittest.mock.MagicMock."""

    def test_open_resource_called(self):
        rm = MagicMock()
        fake_res = MagicMock()
        rm.open_resource.return_value = fake_res

        vt = VisaTransport("USB0::X::INSTR", resource_manager=rm)
        vt.open()

        rm.open_resource.assert_called_once_with("USB0::X::INSTR")
        assert fake_res.timeout == 5000
        assert fake_res.read_termination is None
        assert fake_res.write_termination == "\n"

    def test_write_delegates(self):
        rm = MagicMock()
        fake_res = MagicMock()
        rm.open_resource.return_value = fake_res

        vt = VisaTransport("USB0::X::INSTR", resource_manager=rm)
        vt.open()
        vt.write(":X 1")

        fake_res.write.assert_called_once_with(":X 1")

    def test_query_delegates(self):
        rm = MagicMock()
        fake_res = MagicMock()
        fake_res.query.return_value = "Hantek"
        rm.open_resource.return_value = fake_res

        vt = VisaTransport("USB0::X::INSTR", resource_manager=rm)
        vt.open()
        result = vt.query("*IDN?")

        fake_res.query.assert_called_once_with("*IDN?")
        assert result == "Hantek"

    def test_list_resources_delegates_to_mock_rm(self):
        rm = MagicMock()
        rm.list_resources.return_value = ("USB0::A", "GPIB::1")

        result = VisaTransport.list_resources(resource_manager=rm)

        rm.list_resources.assert_called_once()
        assert result == ("USB0::A", "GPIB::1")
