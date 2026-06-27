"""Scope-фасад и ChannelCollection — Task 8.5.

Scope агрегирует все SCPI-подсистемы и предоставляет единую точку входа.
ChannelCollection реализует кэшированный доступ к Channel по номеру (1..4).

Зависимости:
  from hantek_dso2d15.scpi.channel import Channel
  from hantek_dso2d15.scpi.timebase import Timebase
  from hantek_dso2d15.scpi.acquire import Acquire
  from hantek_dso2d15.scpi.trigger import Trigger
"""

from __future__ import annotations

from hantek_dso2d15.scpi.channel import Channel
from hantek_dso2d15.scpi.timebase import Timebase
from hantek_dso2d15.scpi.acquire import Acquire
from hantek_dso2d15.scpi.trigger import Trigger
from hantek_dso2d15.scpi.measure import Measure


class ChannelCollection:
    """Кэшированная коллекция аналоговых каналов осциллографа.

    Args:
        transport: экземпляр Transport (FakeTransport или VisaTransport).

    Допустимые индексы: 1, 2, 3, 4.
    При обращении к каналу по допустимому индексу возвращает один и тот же
    объект Channel (кэш, инициализируется лениво).

    Raises:
        ValueError: если индекс не входит в {1, 2, 3, 4} (пробрасывается
            из Channel.__init__ через validate_choice).
    """

    _VALID: frozenset[int] = frozenset({1, 2, 3, 4})

    def __init__(self, transport) -> None:
        self._transport = transport
        self._cache: dict[int, Channel] = {}

    def __getitem__(self, n: int) -> Channel:
        """Вернуть Channel(n), создав и кэшировав при первом обращении.

        Args:
            n: номер канала. Должен быть в {1, 2, 3, 4}.

        Returns:
            Кэшированный объект Channel.

        Raises:
            ValueError: если n не входит в {1, 2, 3, 4}.
        """
        if n not in self._VALID:
            raise ValueError(
                f"Недопустимый номер канала: {n!r}. "
                f"Допустимые значения: {sorted(self._VALID)}."
            )
        if n not in self._cache:
            self._cache[n] = Channel(self._transport, n)
        return self._cache[n]


class Scope:
    """Фасад осциллографа Hantek DSO2D15.

    Агрегирует все SCPI-подсистемы и управляет жизненным циклом транспорта.

    Args:
        transport: экземпляр Transport (FakeTransport или VisaTransport).

    Attributes:
        channel:  ChannelCollection — доступ к каналам 1..4.
        timebase: Timebase — подсистема временной развёртки.
        acquire:  Acquire  — подсистема сбора данных.
        trigger:  Trigger  — подсистема триггера.
        measure:  Measure  — подсистема автоизмерений.
    """

    def __init__(self, transport) -> None:
        self._transport = transport
        self.channel = ChannelCollection(transport)
        self.timebase = Timebase(transport)
        self.acquire = Acquire(transport)
        self.trigger = Trigger(transport)
        self.measure = Measure(transport)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def connect(self) -> None:
        """Открыть транспорт (t.open())."""
        self._transport.open()

    def disconnect(self) -> None:
        """Закрыть транспорт (t.close())."""
        self._transport.close()

    @property
    def is_connected(self) -> bool:
        """True если транспорт открыт (t.is_open)."""
        return self._transport.is_open

    # ------------------------------------------------------------------
    # Identification
    # ------------------------------------------------------------------

    def idn(self) -> str:
        """Запросить идентификацию прибора (*IDN?).

        Returns:
            Stripped строка ответа, например
            'Hantek,DSO2D15,CN21034,V1.2.3'.
        """
        return self._transport.query("*IDN?").strip()
