"""Абстрактный базовый класс Transport — единственная граница к I/O.

Все подсистемы SCPI зависят только от этого интерфейса, не от PyVISA напрямую.
"""

from __future__ import annotations

import abc


class Transport(abc.ABC):
    """Абстрактный транспорт для осциллографа Hantek DSO2D15.

    Реализации: FakeTransport (тесты), VisaTransport (реальный прибор).
    """

    @abc.abstractmethod
    def open(self) -> None:
        """Открыть соединение с прибором."""

    @abc.abstractmethod
    def close(self) -> None:
        """Закрыть соединение с прибором."""

    @property
    @abc.abstractmethod
    def is_open(self) -> bool:
        """True если соединение установлено."""

    @abc.abstractmethod
    def write(self, cmd: str) -> None:
        """Отправить команду SCPI прибору без ожидания ответа."""

    @abc.abstractmethod
    def query(self, cmd: str) -> str:
        """Отправить запрос SCPI и вернуть ответ в виде строки."""

    @abc.abstractmethod
    def read_raw(self) -> bytes:
        """Прочитать сырые байты из буфера прибора."""
