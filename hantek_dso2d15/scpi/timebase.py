"""Timebase и TimebaseWindow SCPI-подсистемы — Task 6.

Карта команд (frozen, из плана):
  :TIMebase:SCALe {v} / :TIMebase:SCALe?
  :TIMebase:POSition {v} / :TIMebase:POSition?
  :TIMebase:RANGe {v} / :TIMebase:RANGe?
  :TIMebase:MODE {v} / :TIMebase:MODE?   (MAIN|XY|ROLL)
  :TIMebase:WINDow:ENABle {ON/OFF} / :TIMebase:WINDow:ENABle?
  :TIMebase:WINDow:SCALe {v} / :TIMebase:WINDow:SCALe?
  :TIMebase:WINDow:POSition {v} / :TIMebase:WINDow:POSition?

Числа форматируются через fmt_num (NR3: f"{float(v):g}").
Bool-аргументы: ON/OFF; парсинг: {0,1,ON,OFF}.
"""

from __future__ import annotations

from hantek_dso2d15.scpi.validation import (
    bool_arg,
    fmt_num,
    parse_bool,
    validate_enum,
)
from hantek_dso2d15.transport.base import Transport


class TimebaseWindow:
    """Подсистема окна (zoom) временной развёртки.

    Команды: :TIMebase:WINDow:{ENABle|SCALe|POSition}
    """

    def __init__(self, transport: Transport) -> None:
        self._transport = transport

    # ------------------------------------------------------------------
    # enable
    # ------------------------------------------------------------------

    @property
    def enable(self) -> bool:
        """Состояние окна: True = включено, False = выключено."""
        resp = self._transport.query(":TIMebase:WINDow:ENABle?")
        return parse_bool(resp)

    @enable.setter
    def enable(self, value: object) -> None:
        self._transport.write(f":TIMebase:WINDow:ENABle {bool_arg(value)}")

    # ------------------------------------------------------------------
    # scale
    # ------------------------------------------------------------------

    @property
    def scale(self) -> float:
        """Масштаб окна (с/дел)."""
        return float(self._transport.query(":TIMebase:WINDow:SCALe?"))

    @scale.setter
    def scale(self, value: float) -> None:
        self._transport.write(f":TIMebase:WINDow:SCALe {fmt_num(value)}")

    # ------------------------------------------------------------------
    # position
    # ------------------------------------------------------------------

    @property
    def position(self) -> float:
        """Позиция окна (с)."""
        return float(self._transport.query(":TIMebase:WINDow:POSition?"))

    @position.setter
    def position(self, value: float) -> None:
        self._transport.write(f":TIMebase:WINDow:POSition {fmt_num(value)}")


class Timebase:
    """Основная подсистема временной развёртки.

    Команды: :TIMebase:{SCALe|POSition|RANGe|MODE}
    Подсистема окна: self.window (TimebaseWindow).
    """

    MODES: tuple[str, ...] = ("MAIN", "XY", "ROLL")

    def __init__(self, transport: Transport) -> None:
        self._transport = transport
        self.window = TimebaseWindow(transport)

    # ------------------------------------------------------------------
    # scale
    # ------------------------------------------------------------------

    @property
    def scale(self) -> float:
        """Масштаб развёртки (с/дел)."""
        return float(self._transport.query(":TIMebase:SCALe?"))

    @scale.setter
    def scale(self, value: float) -> None:
        self._transport.write(f":TIMebase:SCALe {fmt_num(value)}")

    # ------------------------------------------------------------------
    # position
    # ------------------------------------------------------------------

    @property
    def position(self) -> float:
        """Горизонтальная позиция (с)."""
        return float(self._transport.query(":TIMebase:POSition?"))

    @position.setter
    def position(self, value: float) -> None:
        self._transport.write(f":TIMebase:POSition {fmt_num(value)}")

    # ------------------------------------------------------------------
    # range
    # ------------------------------------------------------------------

    @property
    def range(self) -> float:
        """Полный диапазон временной развёртки (с)."""
        return float(self._transport.query(":TIMebase:RANGe?"))

    @range.setter
    def range(self, value: float) -> None:
        self._transport.write(f":TIMebase:RANGe {fmt_num(value)}")

    # ------------------------------------------------------------------
    # mode
    # ------------------------------------------------------------------

    @property
    def mode(self) -> str:
        """Режим развёртки: MAIN | XY | ROLL."""
        return self._transport.query(":TIMebase:MODE?").strip()

    @mode.setter
    def mode(self, value: str) -> None:
        canonical = validate_enum(value, self.MODES, "mode")
        self._transport.write(f":TIMebase:MODE {canonical}")
