"""Channel SCPI subsystem — Task 5.

Типизированная тонкая обёртка над командами :CHANnel{n}:*.
Сеттер: клиентская валидация → transport.write(точная строка).
Геттер: transport.query(...) → парсинг по карте команд.
"""

from __future__ import annotations

from hantek_dso2d15.scpi.validation import (
    bool_arg,
    fmt_num,
    parse_bool,
    validate_choice,
    validate_enum,
)


class Channel:
    """SCPI-подсистема одного аналогового канала осциллографа Hantek DSO2D15.

    Args:
        transport: Transport — FakeTransport или VisaTransport.
        n: номер канала, должен быть из {1, 2, 3, 4}.

    Raises:
        ValueError: если n не входит в (1, 2, 3, 4).
    """

    COUPLINGS: tuple[str, ...] = ("AC", "DC", "GND")
    PROBES: tuple[int, ...] = (1, 10, 100, 1000)

    def __init__(self, transport, n: int) -> None:
        validate_choice(n, (1, 2, 3, 4), "channel")
        self._transport = transport
        self._n = n
        self._prefix = f":CHANnel{n}"

    # ------------------------------------------------------------------
    # scale — :CHANnel{n}:SCALe
    # ------------------------------------------------------------------

    @property
    def scale(self) -> float:
        """Вертикальный масштаб (V/дел). Геттер возвращает float."""
        return float(self._transport.query(f"{self._prefix}:SCALe?"))

    @scale.setter
    def scale(self, value: float) -> None:
        """Установить вертикальный масштаб. Число форматируется через fmt_num."""
        self._transport.write(f"{self._prefix}:SCALe {fmt_num(value)}")

    # ------------------------------------------------------------------
    # offset — :CHANnel{n}:OFFSet
    # ------------------------------------------------------------------

    @property
    def offset(self) -> float:
        """Смещение нуля по оси Y (V). Геттер возвращает float."""
        return float(self._transport.query(f"{self._prefix}:OFFSet?"))

    @offset.setter
    def offset(self, value: float) -> None:
        """Установить смещение. Число форматируется через fmt_num."""
        self._transport.write(f"{self._prefix}:OFFSet {fmt_num(value)}")

    # ------------------------------------------------------------------
    # coupling — :CHANnel{n}:COUPling
    # ------------------------------------------------------------------

    @property
    def coupling(self) -> str:
        """Режим входной связи: 'AC' | 'DC' | 'GND'."""
        return self._transport.query(f"{self._prefix}:COUPling?").strip()

    @coupling.setter
    def coupling(self, value: str) -> None:
        """Установить режим связи. Допустимые значения: COUPLINGS (регистронезависимо).

        Raises:
            ValueError: если значение не входит в COUPLINGS.
        """
        canonical = validate_enum(value, self.COUPLINGS, "coupling")
        self._transport.write(f"{self._prefix}:COUPling {canonical}")

    # ------------------------------------------------------------------
    # probe — :CHANnel{n}:PROBe
    # ------------------------------------------------------------------

    @property
    def probe(self) -> int:
        """Коэффициент делителя пробника: 1 | 10 | 100 | 1000. Геттер — int."""
        return int(float(self._transport.query(f"{self._prefix}:PROBe?")))

    @probe.setter
    def probe(self, value: int) -> None:
        """Установить коэффициент делителя. Допустимые значения: PROBES.

        Raises:
            ValueError: если значение не входит в PROBES.
        """
        validate_choice(value, self.PROBES, "probe")
        self._transport.write(f"{self._prefix}:PROBe {fmt_num(value)}")

    # ------------------------------------------------------------------
    # bwlimit — :CHANnel{n}:BWLimit
    # ------------------------------------------------------------------

    @property
    def bwlimit(self) -> bool:
        """Ограничение полосы пропускания (Bandwidth Limit). Геттер — bool."""
        return parse_bool(self._transport.query(f"{self._prefix}:BWLimit?"))

    @bwlimit.setter
    def bwlimit(self, value) -> None:
        """Включить/выключить ограничение полосы."""
        self._transport.write(f"{self._prefix}:BWLimit {bool_arg(value)}")

    # ------------------------------------------------------------------
    # display — :CHANnel{n}:DISPlay
    # ------------------------------------------------------------------

    @property
    def display(self) -> bool:
        """Отображение канала на экране. Геттер — bool."""
        return parse_bool(self._transport.query(f"{self._prefix}:DISPlay?"))

    @display.setter
    def display(self, value) -> None:
        """Включить/выключить отображение канала."""
        self._transport.write(f"{self._prefix}:DISPlay {bool_arg(value)}")

    # ------------------------------------------------------------------
    # invert — :CHANnel{n}:INVert
    # ------------------------------------------------------------------

    @property
    def invert(self) -> bool:
        """Инверсия сигнала. Геттер — bool."""
        return parse_bool(self._transport.query(f"{self._prefix}:INVert?"))

    @invert.setter
    def invert(self, value) -> None:
        """Включить/выключить инверсию сигнала."""
        self._transport.write(f"{self._prefix}:INVert {bool_arg(value)}")

    # ------------------------------------------------------------------
    # vernier — :CHANnel{n}:VERNier
    # ------------------------------------------------------------------

    @property
    def vernier(self) -> bool:
        """Тонкая подстройка вертикального масштаба. Геттер — bool."""
        return parse_bool(self._transport.query(f"{self._prefix}:VERNier?"))

    @vernier.setter
    def vernier(self, value) -> None:
        """Включить/выключить тонкую подстройку."""
        self._transport.write(f"{self._prefix}:VERNier {bool_arg(value)}")
