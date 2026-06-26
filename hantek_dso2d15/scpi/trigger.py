"""Trigger и TriggerEdge — подсистема триггера DSO2D15 (Task 8).

SCPI-литералы строго из «Карты команд» плана (frozen reference):
  EDGe, RISIng, FALLing, EITHer, EXT/10, SWEep, HOLDoff, FORCe, STATus.
"""

from __future__ import annotations

from hantek_dso2d15.transport.base import Transport
from hantek_dso2d15.scpi.validation import validate_enum, fmt_num


class TriggerEdge:
    """Подсистема EDGE-триггера (:TRIGger:EDGe:*).

    Параметры:
        SOURCES: допустимые источники триггера.
        SLOPES:  допустимые фронты.
    """

    SOURCES: tuple[str, ...] = (
        "CHANnel1",
        "CHANnel2",
        "CHANnel3",
        "CHANnel4",
        "EXT/10",
    )
    SLOPES: tuple[str, ...] = ("RISIng", "FALLing", "EITHer")

    def __init__(self, transport: Transport) -> None:
        self._transport = transport

    # ------------------------------------------------------------------
    # source
    # ------------------------------------------------------------------

    @property
    def source(self) -> str:
        """:TRIGger:EDGe:SOURce? — вернуть ответ stripped."""
        return self._transport.query(":TRIGger:EDGe:SOURce?").strip()

    @source.setter
    def source(self, value: str) -> None:
        """:TRIGger:EDGe:SOURce {canonical} — с клиентской валидацией."""
        canonical = validate_enum(value, self.SOURCES, "source")
        self._transport.write(f":TRIGger:EDGe:SOURce {canonical}")

    # ------------------------------------------------------------------
    # slope
    # ------------------------------------------------------------------

    @property
    def slope(self) -> str:
        """:TRIGger:EDGe:SLOPe? — вернуть ответ stripped."""
        return self._transport.query(":TRIGger:EDGe:SLOPe?").strip()

    @slope.setter
    def slope(self, value: str) -> None:
        """:TRIGger:EDGe:SLOPe {canonical} — с клиентской валидацией."""
        canonical = validate_enum(value, self.SLOPES, "slope")
        self._transport.write(f":TRIGger:EDGe:SLOPe {canonical}")

    # ------------------------------------------------------------------
    # level
    # ------------------------------------------------------------------

    @property
    def level(self) -> float:
        """:TRIGger:EDGe:LEVel? — вернуть float."""
        return float(self._transport.query(":TRIGger:EDGe:LEVel?"))

    @level.setter
    def level(self, value: float) -> None:
        """:TRIGger:EDGe:LEVel {v} — отправить в NR3-формате."""
        self._transport.write(f":TRIGger:EDGe:LEVel {fmt_num(value)}")


class Trigger:
    """Подсистема триггера (:TRIGger:*).

    Параметры:
        MODES:  допустимые режимы триггера (14 шт., дословно из reference §4.1).
        SWEEPS: режимы развёртки.

    Атрибуты:
        edge: экземпляр TriggerEdge (разделяет тот же transport).
    """

    MODES: tuple[str, ...] = (
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
    SWEEPS: tuple[str, ...] = ("AUTO", "NORMal", "SINGle")

    def __init__(self, transport: Transport) -> None:
        self._transport = transport
        self.edge = TriggerEdge(transport)

    # ------------------------------------------------------------------
    # mode
    # ------------------------------------------------------------------

    @property
    def mode(self) -> str:
        """:TRIGger:MODE? — вернуть ответ stripped."""
        return self._transport.query(":TRIGger:MODE?").strip()

    @mode.setter
    def mode(self, value: str) -> None:
        """:TRIGger:MODE {canonical} — с клиентской валидацией."""
        canonical = validate_enum(value, self.MODES, "mode")
        self._transport.write(f":TRIGger:MODE {canonical}")

    # ------------------------------------------------------------------
    # sweep
    # ------------------------------------------------------------------

    @property
    def sweep(self) -> str:
        """:TRIGger:SWEep? — вернуть ответ stripped."""
        return self._transport.query(":TRIGger:SWEep?").strip()

    @sweep.setter
    def sweep(self, value: str) -> None:
        """:TRIGger:SWEep {canonical} — с клиентской валидацией."""
        canonical = validate_enum(value, self.SWEEPS, "sweep")
        self._transport.write(f":TRIGger:SWEep {canonical}")

    # ------------------------------------------------------------------
    # holdoff
    # ------------------------------------------------------------------

    @property
    def holdoff(self) -> float:
        """:TRIGger:HOLDoff? — вернуть float."""
        return float(self._transport.query(":TRIGger:HOLDoff?"))

    @holdoff.setter
    def holdoff(self, value: float) -> None:
        """:TRIGger:HOLDoff {v} — отправить в NR3-формате."""
        self._transport.write(f":TRIGger:HOLDoff {fmt_num(value)}")

    # ------------------------------------------------------------------
    # status (R/O)
    # ------------------------------------------------------------------

    @property
    def status(self) -> str:
        """:TRIGger:STATus? — raw строка ('TRIGed' / 'NOTRIG'), stripped."""
        return self._transport.query(":TRIGger:STATus?").strip()

    # ------------------------------------------------------------------
    # force
    # ------------------------------------------------------------------

    def force(self) -> None:
        """Отправить :TRIGger:FORCe — принудительный триггер."""
        self._transport.write(":TRIGger:FORCe")
