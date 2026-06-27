"""Тесты хука io_logger в VisaTransport — TDD, RED-first.

Создан как отдельный файл; test_visa_transport.py НЕ тронут.
Использует те же шаблоны заглушек (FakeResource / FakeResourceManager),
но определённые локально — не импортируются из соседнего теста.

Приёмочные кейсы:
  - write вызывает логгер ("TX", cmd)
  - query вызывает ("TX", cmd) и ("RX", resp)
  - read_raw вызывает ("RX", bytes)
  - set_io_logger(None) отключает хук
  - исключение в логгере НЕ ломает I/O
  - без логгера по умолчанию — write/query/read_raw работают как прежде
  - io_logger=callable передаётся в конструктор
"""
from __future__ import annotations

import pytest

from hantek_dso2d15.transport.visa_transport import VisaTransport


# ---------------------------------------------------------------------------
# Фейковые заглушки (локальные, не трогают test_visa_transport.py)
# ---------------------------------------------------------------------------

class _FakeResource:
    """Минимальная заглушка pyvisa-ресурса."""

    def __init__(self, return_value: str = "FAKE_RESP"):
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


class _FakeRM:
    """Минимальная заглушка pyvisa.ResourceManager."""

    def __init__(self) -> None:
        self._last_opened: _FakeResource | None = None
        self.resource_string: str | None = None

    def list_resources(self) -> tuple[str, ...]:
        return ()

    def open_resource(self, resource_string: str) -> _FakeResource:
        self.resource_string = resource_string
        self._last_opened = _FakeResource()
        return self._last_opened


class _RecordingLogger:
    """Логгер-заглушка: записывает все вызовы в список."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    def __call__(self, direction: str, payload: object) -> None:
        self.calls.append((direction, payload))


RESOURCE_STR = "USB0::0x0483::0x5740::CN21034::INSTR"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def fake_rm() -> _FakeRM:
    return _FakeRM()


@pytest.fixture
def vt_with_logger(fake_rm):
    """VisaTransport + RecordingLogger, уже открытый."""
    logger = _RecordingLogger()
    vt = VisaTransport(RESOURCE_STR, resource_manager=fake_rm, io_logger=logger)
    vt.open()
    return vt, fake_rm, logger


# ---------------------------------------------------------------------------
# 1. write → логгер TX
# ---------------------------------------------------------------------------

class TestWriteLogging:
    def test_write_calls_logger_tx(self, vt_with_logger):
        vt, rm, logger = vt_with_logger
        vt.write(":CHAN1:DISP ON")
        assert ("TX", ":CHAN1:DISP ON") in logger.calls

    def test_write_calls_logger_before_io(self, fake_rm):
        """Логгер вызывается, затем реальная запись в ресурс."""
        order: list[str] = []

        def log_hook(direction, payload):
            order.append(f"log:{direction}")

        vt = VisaTransport(RESOURCE_STR, resource_manager=fake_rm, io_logger=log_hook)
        vt.open()
        # Подменяем write ресурса, чтобы отследить порядок
        original_write = fake_rm._last_opened.write
        def tracked_write(cmd):
            order.append("io:write")
            original_write(cmd)
        fake_rm._last_opened.write = tracked_write

        vt.write(":X 1")
        assert order == ["log:TX", "io:write"]

    def test_write_still_delegates_to_resource(self, vt_with_logger):
        vt, rm, logger = vt_with_logger
        vt.write(":TRIG:MODE EDGE")
        assert ":TRIG:MODE EDGE" in rm._last_opened._written

    def test_write_no_logger_still_works(self, fake_rm):
        """Без логгера write работает как раньше."""
        vt = VisaTransport(RESOURCE_STR, resource_manager=fake_rm)
        vt.open()
        vt.write(":CHAN2:DISP OFF")
        assert ":CHAN2:DISP OFF" in fake_rm._last_opened._written


# ---------------------------------------------------------------------------
# 2. query → логгер TX + RX
# ---------------------------------------------------------------------------

class TestQueryLogging:
    def test_query_calls_logger_tx(self, vt_with_logger):
        vt, rm, logger = vt_with_logger
        vt.query("*IDN?")
        tx_calls = [c for c in logger.calls if c[0] == "TX"]
        assert ("TX", "*IDN?") in tx_calls

    def test_query_calls_logger_rx(self, vt_with_logger):
        vt, rm, logger = vt_with_logger
        rm._last_opened._return_value = "Hantek,DSO2D15"
        result = vt.query("*IDN?")
        rx_calls = [c for c in logger.calls if c[0] == "RX"]
        assert ("RX", "Hantek,DSO2D15") in rx_calls
        assert result == "Hantek,DSO2D15"

    def test_query_tx_before_rx(self, vt_with_logger):
        """TX должен идти раньше RX в списке вызовов."""
        vt, rm, logger = vt_with_logger
        vt.query("*IDN?")
        directions = [c[0] for c in logger.calls]
        tx_idx = directions.index("TX")
        rx_idx = directions.index("RX")
        assert tx_idx < rx_idx

    def test_query_no_logger_still_returns(self, fake_rm):
        """Без логгера query возвращает ответ как обычно."""
        fake_rm._last_opened = None
        vt = VisaTransport(RESOURCE_STR, resource_manager=fake_rm)
        vt.open()
        fake_rm._last_opened._return_value = "42"
        result = vt.query(":MEAS:FREQ?")
        assert result == "42"


# ---------------------------------------------------------------------------
# 3. read_raw → логгер RX
# ---------------------------------------------------------------------------

class TestReadRawLogging:
    def test_read_raw_calls_logger_rx(self, vt_with_logger):
        vt, rm, logger = vt_with_logger
        rm._last_opened._raw_chunks = [b"\xDE\xAD\xBE\xEF"]
        data = vt.read_raw()
        assert ("RX", b"\xDE\xAD\xBE\xEF") in logger.calls
        assert data == b"\xDE\xAD\xBE\xEF"

    def test_read_raw_no_logger_still_returns(self, fake_rm):
        """Без логгера read_raw возвращает байты как обычно."""
        vt = VisaTransport(RESOURCE_STR, resource_manager=fake_rm)
        vt.open()
        fake_rm._last_opened._raw_chunks = [b"\x01\x02"]
        result = vt.read_raw()
        assert result == b"\x01\x02"


# ---------------------------------------------------------------------------
# 4. set_io_logger — установка / снятие хука на лету
# ---------------------------------------------------------------------------

class TestSetIoLogger:
    def test_set_io_logger_replaces_hook(self, fake_rm):
        """set_io_logger заменяет хук на лету."""
        logger1 = _RecordingLogger()
        logger2 = _RecordingLogger()
        vt = VisaTransport(RESOURCE_STR, resource_manager=fake_rm, io_logger=logger1)
        vt.open()
        vt.write("CMD_A")
        vt.set_io_logger(logger2)
        vt.write("CMD_B")
        assert ("TX", "CMD_A") in logger1.calls
        assert ("TX", "CMD_B") not in logger1.calls
        assert ("TX", "CMD_B") in logger2.calls

    def test_set_io_logger_none_disables_logging(self, vt_with_logger):
        """set_io_logger(None) отключает логирование."""
        vt, rm, logger = vt_with_logger
        vt.set_io_logger(None)
        vt.write(":CHAN1:DISP ON")
        assert not logger.calls, "Логгер должен быть отключён после set_io_logger(None)"

    def test_set_io_logger_none_io_still_works(self, vt_with_logger):
        """После отключения логгера I/O продолжает работать."""
        vt, rm, logger = vt_with_logger
        vt.set_io_logger(None)
        vt.write(":CHAN2:DISP ON")
        assert ":CHAN2:DISP ON" in rm._last_opened._written


# ---------------------------------------------------------------------------
# 5. Исключение в логгере НЕ ломает I/O
# ---------------------------------------------------------------------------

class TestLoggerExceptionIsolation:
    def test_write_survives_logger_exception(self, fake_rm):
        """RuntimeError в логгере не прерывает write."""
        def bad_logger(direction, payload):
            raise RuntimeError("логгер упал")

        vt = VisaTransport(RESOURCE_STR, resource_manager=fake_rm, io_logger=bad_logger)
        vt.open()
        # Не должно бросить исключение
        vt.write(":CHAN1:DISP ON")
        # I/O дошёл до ресурса
        assert ":CHAN1:DISP ON" in fake_rm._last_opened._written

    def test_query_survives_logger_exception(self, fake_rm):
        """RuntimeError в логгере не прерывает query и не меняет ответ."""
        def bad_logger(direction, payload):
            raise ValueError("ошибка логгера")

        vt = VisaTransport(RESOURCE_STR, resource_manager=fake_rm, io_logger=bad_logger)
        vt.open()
        fake_rm._last_opened._return_value = "OK"
        result = vt.query("*IDN?")
        assert result == "OK"

    def test_read_raw_survives_logger_exception(self, fake_rm):
        """RuntimeError в логгере не прерывает read_raw."""
        def bad_logger(direction, payload):
            raise TypeError("ошибка логгера")

        vt = VisaTransport(RESOURCE_STR, resource_manager=fake_rm, io_logger=bad_logger)
        vt.open()
        fake_rm._last_opened._raw_chunks = [b"\xAB"]
        result = vt.read_raw()
        assert result == b"\xAB"


# ---------------------------------------------------------------------------
# 6. Конструктор с io_logger и без
# ---------------------------------------------------------------------------

class TestConstructor:
    def test_default_no_logger(self, fake_rm):
        """По умолчанию логгер None — никаких вызовов."""
        vt = VisaTransport(RESOURCE_STR, resource_manager=fake_rm)
        vt.open()
        # Всё работает без ошибок
        vt.write(":X 1")
        fake_rm._last_opened._raw_chunks = [b"\x00"]
        vt.read_raw()

    def test_constructor_accepts_io_logger_kwarg(self, fake_rm):
        """Конструктор принимает io_logger как keyword-аргумент."""
        logger = _RecordingLogger()
        vt = VisaTransport(RESOURCE_STR, resource_manager=fake_rm, io_logger=logger)
        vt.open()
        vt.write(":Y 2")
        assert logger.calls  # хотя бы один вызов
