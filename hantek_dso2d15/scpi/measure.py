"""Подсистема Measure — автоизмерения :MEASure:*.

Типизированная обёртка SCPI-команд :MEASure:* для Hantek DSO2D15.
Строки команд — дословно из «Карты команд» (frozen reference).

Hardware-verified 2026-06-27:
- Чтение измерения: :MEASure:CHANnel{n}:ITEM? <type> — тип передаётся как аргумент запроса.
  Форма «set-then-bare-query» на этом приборе НЕ работает.
- Литерал 'MAX' из мануала — опечатка; реальный рабочий литерал: 'VMAX'
  (MAX возвращает sentinel 1000, VMAX — корректное значение).
- SENTINEL = 1000.0: значение-заглушка прошивки для «нет данных» (N/A).
  НЕ фильтруется — возвращается как есть; интерпретация на стороне вызывающего.
"""

from __future__ import annotations

from hantek_dso2d15.scpi.validation import (
    bool_arg,
    parse_bool,
    validate_enum,
)


class Measure:
    """Подсистема автоизмерений осциллографа Hantek DSO2D15 (:MEASure:*).

    Args:
        transport: экземпляр Transport (FakeTransport или VisaTransport).

    Attributes:
        SOURCES:  допустимые источники сигнала для свойства source.
        ITEMS:    допустимые типы автоизмерений.
                  Примечание: 'MAX' из мануала заменён на рабочий литерал 'VMAX'
                  (hardware-verified 2026-06-27).
        SENTINEL: значение-заглушка прошивки (1000.0) — означает «нет данных».
                  НЕ фильтруется; возвращается как есть через read_item().
    """

    SOURCES: tuple[str, ...] = (
        "CHANnel1", "CHANnel2", "CHANnel3", "CHANnel4", "MATH",
    )
    ITEMS: tuple[str, ...] = (
        "VMAX", "VMIN", "VPP", "VTOP", "VBASe", "VAMP", "VAVG", "VRMS",
        "OVERshoot", "PREShoot", "MARea", "MPARea", "PERiod", "FREQuency",
        "RTIMe", "FTIMe", "PWIDth", "NWIDth", "PDUTy", "NDUTy",
        "RDELay", "FDELay", "RPHase", "FPHase", "TVMAX", "TVMIN",
        "PSLEWrate", "NSLEWrate", "VUPper", "VMID", "VLOWer",
        "VARIance", "PVRMS", "PPULses", "NPULses", "PEDGes", "NEDGes",
    )
    SENTINEL: float = 1000.0

    _VALID_CHANNELS: frozenset[int] = frozenset({1, 2, 3, 4})

    def __init__(self, transport) -> None:
        self._transport = transport

    # ------------------------------------------------------------------
    # enable
    # ------------------------------------------------------------------

    @property
    def enable(self) -> bool:
        """Включение/выключение подсистемы автоизмерений.

        GET: :MEASure:ENABle? → parse_bool
        """
        return parse_bool(self._transport.query(":MEASure:ENABle?"))

    @enable.setter
    def enable(self, value) -> None:
        """SET: validate bool → :MEASure:ENABle {ON|OFF}"""
        self._transport.write(f":MEASure:ENABle {bool_arg(value)}")

    # ------------------------------------------------------------------
    # source
    # ------------------------------------------------------------------

    @property
    def source(self) -> str:
        """Источник сигнала для автоизмерений.

        GET: :MEASure:SOURce? → строка
        """
        return self._transport.query(":MEASure:SOURce?")

    @source.setter
    def source(self, value: str) -> None:
        """SET: validate_enum(SOURCES) → :MEASure:SOURce {canonical}

        Raises:
            ValueError: если значение не входит в SOURCES.
        """
        canonical = validate_enum(value, self.SOURCES, "source")
        self._transport.write(f":MEASure:SOURce {canonical}")

    # ------------------------------------------------------------------
    # adisplay
    # ------------------------------------------------------------------

    @property
    def adisplay(self) -> bool:
        """Отображение всех автоизмерений на экране (All Display).

        GET: :MEASure:ADISplay? → parse_bool
        """
        return parse_bool(self._transport.query(":MEASure:ADISplay?"))

    @adisplay.setter
    def adisplay(self, value) -> None:
        """SET: → :MEASure:ADISplay {ON|OFF}"""
        self._transport.write(f":MEASure:ADISplay {bool_arg(value)}")

    # ------------------------------------------------------------------
    # read_item
    # ------------------------------------------------------------------

    def read_item(self, channel: int, item: str) -> float:
        """Прочитать одно автоизмерение с заданного канала.

        Hardware-verified 2026-06-27: запрос формируется как
        ':MEASure:CHANnel{n}:ITEM? {type}' — тип является аргументом запроса.
        Форма «set-then-bare-query» НЕ работает на приборе DSO2D15.

        Args:
            channel: номер канала, должен быть из {1, 2, 3, 4}.
            item:    тип измерения — регистронезависимо, сопоставляется с ITEMS.
                     Используй 'VMAX', а не 'MAX' (MAX — опечатка мануала).

        Returns:
            Результат измерения в единицах, соответствующих типу (float).
            При «нет данных» прошивка возвращает SENTINEL (1000.0) — он не фильтруется.

        Raises:
            ValueError: если channel не входит в {1, 2, 3, 4}.
            ValueError: если item не входит в ITEMS.
        """
        if channel not in self._VALID_CHANNELS:
            raise ValueError(
                f"Недопустимый номер канала: {channel!r}. "
                f"Допустимые значения: {sorted(self._VALID_CHANNELS)}."
            )
        canonical = validate_enum(item, self.ITEMS, "item")
        resp = self._transport.query(f":MEASure:CHANnel{channel}:ITEM? {canonical}")
        return float(resp)

    # ------------------------------------------------------------------
    # gate_enable
    # ------------------------------------------------------------------

    @property
    def gate_enable(self) -> bool:
        """Включение/выключение gate-ограничения измерений.

        GET: :MEASure:GATE:ENABle? → parse_bool
        """
        return parse_bool(self._transport.query(":MEASure:GATE:ENABle?"))

    @gate_enable.setter
    def gate_enable(self, value) -> None:
        """SET: → :MEASure:GATE:ENABle {ON|OFF}"""
        self._transport.write(f":MEASure:GATE:ENABle {bool_arg(value)}")

    # ------------------------------------------------------------------
    # gate_ay
    # ------------------------------------------------------------------

    @property
    def gate_ay(self) -> int:
        """Левая граница gate-измерений (пиксели, 0..400).

        GET: :MEASure:GATE:AY? → int(float(resp))
        """
        resp = self._transport.query(":MEASure:GATE:AY?")
        return int(float(resp))

    @gate_ay.setter
    def gate_ay(self, value: int) -> None:
        """SET: validate 0..400 → :MEASure:GATE:AY {v}

        Raises:
            ValueError: если value не входит в [0, 400].
        """
        if not (0 <= value <= 400):
            raise ValueError(
                f"Недопустимое значение gate_ay: {value!r}. "
                "Допустимый диапазон: 0..400."
            )
        self._transport.write(f":MEASure:GATE:AY {value}")

    # ------------------------------------------------------------------
    # gate_by
    # ------------------------------------------------------------------

    @property
    def gate_by(self) -> int:
        """Правая граница gate-измерений (пиксели, 0..400).

        GET: :MEASure:GATE:BY? → int(float(resp))
        """
        resp = self._transport.query(":MEASure:GATE:BY?")
        return int(float(resp))

    @gate_by.setter
    def gate_by(self, value: int) -> None:
        """SET: validate 0..400 → :MEASure:GATE:BY {v}

        Raises:
            ValueError: если value не входит в [0, 400].
        """
        if not (0 <= value <= 400):
            raise ValueError(
                f"Недопустимое значение gate_by: {value!r}. "
                "Допустимый диапазон: 0..400."
            )
        self._transport.write(f":MEASure:GATE:BY {value}")
