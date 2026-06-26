"""FakeTransport — скриптуемый дубль Transport для тестирования без железа.

Реализует Transport ABC. Поддерживает:
- Публичные логи writes / queries.
- Фиксированные ответы через set_response (многократные).
- FIFO-очереди ответов через queue_response (с приоритетом над фиксированными).
- Очередь сырых чанков через set_raw / read_raw.
- reset() — очищает логи, ответы сохраняет.
"""

from __future__ import annotations

from collections import deque
from typing import Deque

from hantek_dso2d15.transport.base import Transport


class FakeTransport(Transport):
    """Тестовый транспорт без реального I/O.

    Использование::

        t = FakeTransport()
        t.open()
        t.set_response(":CHANnel1:SCALe?", "0.5")
        t.write(":CHANnel1:SCALe 0.5")
        assert t.writes[-1] == ":CHANnel1:SCALe 0.5"
        assert t.query(":CHANnel1:SCALe?") == "0.5"
    """

    def __init__(self) -> None:
        self._is_open: bool = False

        # Публичные логи
        self.writes: list[str] = []
        self.queries: list[str] = []

        # Фиксированные ответы: cmd -> value
        self._fixed: dict[str, str] = {}

        # FIFO-очереди ответов: cmd -> deque[value]
        self._queues: dict[str, Deque[str]] = {}

        # Очередь raw-чанков
        self._raw_queue: Deque[bytes] = deque()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def open(self) -> None:
        """Открыть транспорт (установить is_open=True)."""
        self._is_open = True

    def close(self) -> None:
        """Закрыть транспорт (установить is_open=False)."""
        self._is_open = False

    @property
    def is_open(self) -> bool:
        """True если транспорт открыт."""
        return self._is_open

    # ------------------------------------------------------------------
    # Guard
    # ------------------------------------------------------------------

    def _require_open(self) -> None:
        if not self._is_open:
            raise RuntimeError("FakeTransport не открыт. Вызовите open() перед использованием.")

    # ------------------------------------------------------------------
    # write / query
    # ------------------------------------------------------------------

    def write(self, cmd: str) -> None:
        """Записать SCPI-команду в лог writes.

        Raises:
            RuntimeError: если транспорт не открыт.
        """
        self._require_open()
        self.writes.append(cmd)

    def query(self, cmd: str) -> str:
        """Выполнить запрос SCPI и вернуть ответ.

        Приоритет ответов:
        1. FIFO-очередь (queue_response).
        2. Фиксированный ответ (set_response).
        3. KeyError(cmd) если нет ни того, ни другого.

        Raises:
            RuntimeError: если транспорт не открыт.
            KeyError: если нет зарегистрированного ответа для cmd.
        """
        self._require_open()
        self.queries.append(cmd)

        # Приоритет: FIFO-очередь
        q = self._queues.get(cmd)
        if q:
            return q.popleft()

        # Затем фиксированный ответ
        if cmd in self._fixed:
            return self._fixed[cmd]

        raise KeyError(cmd)

    # ------------------------------------------------------------------
    # Настройка ответов
    # ------------------------------------------------------------------

    def set_response(self, cmd: str, value: str) -> None:
        """Зафиксировать ответ на команду query(cmd).

        Ответ возвращается при каждом вызове query(cmd), когда очередь пуста.
        """
        self._fixed[cmd] = value

    def queue_response(self, cmd: str, *values: str) -> None:
        """Добавить значения в FIFO-очередь ответов для query(cmd).

        Каждый вызов query(cmd) потребляет один элемент из очереди.
        После исчерпания очереди используется фиксированный ответ (set_response),
        или KeyError если его тоже нет.
        """
        if cmd not in self._queues:
            self._queues[cmd] = deque()
        self._queues[cmd].extend(values)

    # ------------------------------------------------------------------
    # Raw I/O
    # ------------------------------------------------------------------

    def set_raw(self, *chunks: bytes) -> None:
        """Добавить сырые байт-чанки в очередь для read_raw()."""
        self._raw_queue.extend(chunks)

    def read_raw(self) -> bytes:
        """Прочитать и вернуть следующий чанк из raw-очереди.

        Raises:
            RuntimeError: если транспорт не открыт.
            IndexError: если очередь пуста.
        """
        self._require_open()
        if not self._raw_queue:
            raise IndexError("raw-очередь FakeTransport пуста.")
        return self._raw_queue.popleft()

    # ------------------------------------------------------------------
    # reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Очистить логи writes и queries. Ответы (fixed/queued) остаются."""
        self.writes.clear()
        self.queries.clear()
