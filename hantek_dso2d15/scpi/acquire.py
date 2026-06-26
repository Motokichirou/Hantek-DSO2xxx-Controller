"""Подсистема Acquire — Task 7.

Типизированная обёртка SCPI-команд :ACQuire:* для Hantek DSO2D15.
Строки команд — дословно из «Карты команд» плана (frozen reference).
"""

from __future__ import annotations

from hantek_dso2d15.scpi.validation import (
    validate_choice,
    validate_enum,
)


class Acquire:
    """Подсистема управления режимом сбора данных (acquire).

    Attributes:
        POINTS: допустимые значения глубины памяти (точек).
        TYPES:  допустимые режимы сбора.
        COUNTS: допустимые значения числа усреднений.
    """

    POINTS = (4000, 40000, 400000, 4000000, 8000000)
    TYPES = ("NORMal", "AVERage", "PEAK", "HRESolution")
    COUNTS = (4, 8, 16, 32, 64, 128)

    def __init__(self, transport) -> None:
        self._transport = transport

    # ------------------------------------------------------------------
    # points
    # ------------------------------------------------------------------

    @property
    def points(self) -> int:
        """Глубина памяти (количество точек).

        GET: :ACQuire:POINts? → int(float(resp))
        """
        resp = self._transport.query(":ACQuire:POINts?")
        return int(float(resp))

    @points.setter
    def points(self, value: int) -> None:
        """SET: validate_choice(POINTS) → :ACQuire:POINts {v}"""
        validate_choice(value, self.POINTS, "points")
        self._transport.write(f":ACQuire:POINts {value}")

    # ------------------------------------------------------------------
    # type
    # ------------------------------------------------------------------

    @property
    def type(self) -> str:
        """Режим сбора данных.

        GET: :ACQuire:TYPE? → enum-строка
        """
        return self._transport.query(":ACQuire:TYPE?")

    @type.setter
    def type(self, value: str) -> None:
        """SET: validate_enum(TYPES) → :ACQuire:TYPE {canonical}"""
        canonical = validate_enum(value, self.TYPES, "type")
        self._transport.write(f":ACQuire:TYPE {canonical}")

    # ------------------------------------------------------------------
    # count
    # ------------------------------------------------------------------

    @property
    def count(self) -> int:
        """Число усреднений (только для режима AVERage).

        GET: :ACQuire:COUNt? → int(float(resp))
        """
        resp = self._transport.query(":ACQuire:COUNt?")
        return int(float(resp))

    @count.setter
    def count(self, value: int) -> None:
        """SET: validate_choice(COUNTS) → :ACQuire:COUNt {v}"""
        validate_choice(value, self.COUNTS, "count")
        self._transport.write(f":ACQuire:COUNt {value}")

    # ------------------------------------------------------------------
    # srate — только чтение
    # ------------------------------------------------------------------

    @property
    def srate(self) -> float:
        """Частота дискретизации (Sa/s) — только чтение.

        GET: :ACQuire:SRATe? → float
        Присваивание вызывает AttributeError (нет сеттера).
        """
        resp = self._transport.query(":ACQuire:SRATe?")
        return float(resp)
