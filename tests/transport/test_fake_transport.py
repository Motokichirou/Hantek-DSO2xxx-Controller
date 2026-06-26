"""Тесты FakeTransport — acceptance-кейсы Task 4.

TDD: этот файл написан до реализации. Запуск до реализации должен дать FAIL.
"""

from __future__ import annotations

import pytest

from hantek_dso2d15.transport.fake_transport import FakeTransport


# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------


def make_open() -> FakeTransport:
    """Вернуть открытый FakeTransport."""
    t = FakeTransport()
    t.open()
    return t


# ---------------------------------------------------------------------------
# Инициализация и is_open
# ---------------------------------------------------------------------------


class TestLifecycle:
    def test_initial_state_closed(self):
        t = FakeTransport()
        assert t.is_open is False

    def test_open_sets_is_open(self):
        t = FakeTransport()
        t.open()
        assert t.is_open is True

    def test_close_clears_is_open(self):
        t = FakeTransport()
        t.open()
        t.close()
        assert t.is_open is False

    def test_double_open_idempotent(self):
        """Двойной open не должен падать и держит is_open=True."""
        t = FakeTransport()
        t.open()
        t.open()
        assert t.is_open is True

    def test_initial_logs_empty(self):
        t = FakeTransport()
        assert t.writes == []
        assert t.queries == []


# ---------------------------------------------------------------------------
# RuntimeError на закрытом транспорте
# ---------------------------------------------------------------------------


class TestClosedGuard:
    def test_write_on_closed_raises(self):
        t = FakeTransport()
        with pytest.raises(RuntimeError):
            t.write(":X 1")

    def test_query_on_closed_raises(self):
        t = FakeTransport()
        with pytest.raises(RuntimeError):
            t.query(":X?")

    def test_read_raw_on_closed_raises(self):
        """read_raw на закрытом транспорте тоже должен давать RuntimeError."""
        t = FakeTransport()
        with pytest.raises(RuntimeError):
            t.read_raw()


# ---------------------------------------------------------------------------
# write и лог writes
# ---------------------------------------------------------------------------


class TestWrite:
    def test_write_appends_to_log(self):
        t = make_open()
        t.write(":Z 1")
        assert t.writes == [":Z 1"]

    def test_write_multiple(self):
        t = make_open()
        t.write(":A 1")
        t.write(":B 2")
        assert t.writes == [":A 1", ":B 2"]


# ---------------------------------------------------------------------------
# set_response и query (фиксированный ответ)
# ---------------------------------------------------------------------------


class TestSetResponse:
    def test_query_returns_fixed_response(self):
        t = make_open()
        t.set_response(":X?", "5")
        assert t.query(":X?") == "5"

    def test_query_fixed_response_twice(self):
        """Фиксированный ответ возвращается при каждом вызове (не расходуется)."""
        t = make_open()
        t.set_response(":X?", "5")
        assert t.query(":X?") == "5"
        assert t.query(":X?") == "5"

    def test_query_logs_both_calls(self):
        t = make_open()
        t.set_response(":X?", "5")
        t.query(":X?")
        t.query(":X?")
        assert t.queries == [":X?", ":X?"]

    def test_query_missing_key_raises_keyerror(self):
        t = make_open()
        with pytest.raises(KeyError):
            t.query(":MISSING?")


# ---------------------------------------------------------------------------
# queue_response — FIFO с приоритетом над фиксированным ответом
# ---------------------------------------------------------------------------


class TestQueueResponse:
    def test_queue_fifo_order(self):
        t = make_open()
        t.queue_response(":Y?", "a", "b")
        assert t.query(":Y?") == "a"
        assert t.query(":Y?") == "b"

    def test_queue_exhausted_falls_to_fixed(self):
        """После очереди берётся фиксированный ответ."""
        t = make_open()
        t.set_response(":Y?", "fixed")
        t.queue_response(":Y?", "q1")
        assert t.query(":Y?") == "q1"
        assert t.query(":Y?") == "fixed"

    def test_queue_exhausted_no_fixed_raises_keyerror(self):
        """После исчерпания очереди без фиксированного → KeyError."""
        t = make_open()
        t.queue_response(":Y?", "only")
        assert t.query(":Y?") == "only"
        with pytest.raises(KeyError):
            t.query(":Y?")

    def test_queue_priority_over_fixed(self):
        """Очередь приоритетнее фиксированного, пока не пуста."""
        t = make_open()
        t.set_response(":Z?", "fixed")
        t.queue_response(":Z?", "first")
        assert t.query(":Z?") == "first"   # из очереди
        assert t.query(":Z?") == "fixed"   # из фиксированного

    def test_queue_multiple_enqueue_calls(self):
        """Несколько вызовов queue_response накапливают FIFO."""
        t = make_open()
        t.queue_response(":W?", "x")
        t.queue_response(":W?", "y")
        assert t.query(":W?") == "x"
        assert t.query(":W?") == "y"


# ---------------------------------------------------------------------------
# set_raw / read_raw
# ---------------------------------------------------------------------------


class TestRaw:
    def test_read_raw_fifo_order(self):
        t = make_open()
        t.set_raw(b"\x01", b"\x02")
        assert t.read_raw() == b"\x01"
        assert t.read_raw() == b"\x02"

    def test_read_raw_empty_raises_indexerror(self):
        t = make_open()
        with pytest.raises(IndexError):
            t.read_raw()

    def test_read_raw_exhausted_raises_indexerror(self):
        t = make_open()
        t.set_raw(b"\xAA")
        t.read_raw()
        with pytest.raises(IndexError):
            t.read_raw()

    def test_set_raw_appends_to_queue(self):
        """set_raw добавляет чанки в очередь (накопительно, не очищает)."""
        t = make_open()
        t.set_raw(b"\x01")
        t.set_raw(b"\x02")
        # Оба чанка должны быть в очереди
        assert t.read_raw() == b"\x01"
        assert t.read_raw() == b"\x02"


# ---------------------------------------------------------------------------
# reset()
# ---------------------------------------------------------------------------


class TestReset:
    def test_reset_clears_writes(self):
        t = make_open()
        t.write(":A 1")
        t.reset()
        assert t.writes == []

    def test_reset_clears_queries(self):
        t = make_open()
        t.set_response(":X?", "5")
        t.query(":X?")
        t.reset()
        assert t.queries == []

    def test_reset_preserves_fixed_responses(self):
        """reset() не трогает фиксированные ответы."""
        t = make_open()
        t.set_response(":X?", "5")
        t.reset()
        # Транспорт ещё открыт; можно продолжать query
        assert t.query(":X?") == "5"

    def test_reset_preserves_queue_responses(self):
        """reset() не трогает очереди ответов."""
        t = make_open()
        t.queue_response(":Y?", "queued")
        t.reset()
        assert t.query(":Y?") == "queued"

    def test_reset_does_not_close(self):
        """reset() не закрывает транспорт."""
        t = make_open()
        t.reset()
        assert t.is_open is True


# ---------------------------------------------------------------------------
# Является подклассом Transport
# ---------------------------------------------------------------------------


class TestInheritance:
    def test_is_transport_subclass(self):
        from hantek_dso2d15.transport.base import Transport
        assert issubclass(FakeTransport, Transport)

    def test_instance_is_transport(self):
        from hantek_dso2d15.transport.base import Transport
        t = FakeTransport()
        assert isinstance(t, Transport)
