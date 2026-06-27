"""Подсистема DDS — встроенный генератор сигналов :DDS:*.

Типизированная обёртка SCPI-команд :DDS:* для Hantek DSO2D15.
Строки команд — дословно из frozen reference (docs/scpi-command-reference.md).

Hardware-verified 2026-06-27:
- Все команды работают; прибор молча клампит out-of-range значения.
- Форматы readback: SWITch?→'ON'/'OFF'; TYPE?→эхо литерала;
  FREQ?/AMP?/OFFSet?/MODE:FREQ?→NR3 ('1.000000e+03');
  DUTY?→число ('50' или '0.002'); MODE:DEPThordeviation?→число;
  BURSt:CNT?→целое-строка (может быть NR3).
- Литерал ':DDS:MODE:DEPThordeviation' — дословно из мануала, не «исправлять».
"""

from __future__ import annotations

from hantek_dso2d15.scpi.validation import (
    bool_arg,
    fmt_num,
    parse_bool,
    validate_enum,
)


class DDS:
    """Подсистема генератора сигналов (DDS/AWG) Hantek DSO2D15 (:DDS:*).

    Args:
        transport: экземпляр Transport (FakeTransport или VisaTransport).

    Attributes:
        TYPES:       допустимые формы сигнала.
        MOD_TYPES:   допустимые типы модуляции (AM/FM).
        MOD_WAVES:   допустимые формы волны модулятора.
        BURST_TYPES: допустимые режимы burst.

    Примечание:
        ARB-загрузка (:DDS:ARB:DAC16:BIN) не реализована — отдельный таск.
    """

    TYPES: tuple[str, ...] = (
        "SINE", "SQUAre", "RAMP", "EXP", "NOISe", "DC", "ARB1", "ARB2", "ARB3", "ARB4"
    )
    MOD_TYPES: tuple[str, ...] = ("AM", "FM")
    MOD_WAVES: tuple[str, ...] = ("SINE", "SQUAre", "RAMP")
    BURST_TYPES: tuple[str, ...] = ("N_CYCLE", "INFInit")

    def __init__(self, transport) -> None:
        self._transport = transport

    # ------------------------------------------------------------------
    # output — :DDS:SWITch
    # ------------------------------------------------------------------

    @property
    def output(self) -> bool:
        """Включение/выключение выхода генератора.

        GET: :DDS:SWITch? → parse_bool
        """
        return parse_bool(self._transport.query(":DDS:SWITch?"))

    @output.setter
    def output(self, value) -> None:
        """SET: bool_arg(value) → :DDS:SWITch {ON|OFF}"""
        self._transport.write(f":DDS:SWITch {bool_arg(value)}")

    # ------------------------------------------------------------------
    # type — :DDS:TYPE
    # ------------------------------------------------------------------

    @property
    def type(self) -> str:
        """Форма выходного сигнала.

        GET: :DDS:TYPE? → эхо литерала
        """
        return self._transport.query(":DDS:TYPE?")

    @type.setter
    def type(self, value: str) -> None:
        """SET: validate_enum(TYPES) → :DDS:TYPE {canonical}

        Raises:
            ValueError: если значение не входит в TYPES.
        """
        canonical = validate_enum(value, self.TYPES, "type")
        self._transport.write(f":DDS:TYPE {canonical}")

    # ------------------------------------------------------------------
    # freq — :DDS:FREQ
    # ------------------------------------------------------------------

    @property
    def freq(self) -> float:
        """Частота несущей (Hz).

        GET: :DDS:FREQ? → float (NR3)
        Нет жёсткой проверки диапазона — прибор клампит.
        """
        return float(self._transport.query(":DDS:FREQ?"))

    @freq.setter
    def freq(self, value) -> None:
        """SET: :DDS:FREQ {fmt_num(value)}"""
        self._transport.write(f":DDS:FREQ {fmt_num(value)}")

    # ------------------------------------------------------------------
    # amplitude — :DDS:AMP
    # ------------------------------------------------------------------

    @property
    def amplitude(self) -> float:
        """Амплитуда (Vpp).

        GET: :DDS:AMP? → float (NR3)
        """
        return float(self._transport.query(":DDS:AMP?"))

    @amplitude.setter
    def amplitude(self, value) -> None:
        """SET: :DDS:AMP {fmt_num(value)}"""
        self._transport.write(f":DDS:AMP {fmt_num(value)}")

    # ------------------------------------------------------------------
    # offset — :DDS:OFFSet
    # ------------------------------------------------------------------

    @property
    def offset(self) -> float:
        """Смещение DC (V).

        GET: :DDS:OFFSet? → float (NR3)
        """
        return float(self._transport.query(":DDS:OFFSet?"))

    @offset.setter
    def offset(self, value) -> None:
        """SET: :DDS:OFFSet {fmt_num(value)}"""
        self._transport.write(f":DDS:OFFSet {fmt_num(value)}")

    # ------------------------------------------------------------------
    # duty — :DDS:DUTY
    # ------------------------------------------------------------------

    @property
    def duty(self) -> float:
        """Скважность (%, для меандра/пилы).

        GET: :DDS:DUTY? → float
        Hardware-verified: возвращает '50' или '0.002'.
        """
        return float(self._transport.query(":DDS:DUTY?"))

    @duty.setter
    def duty(self, value) -> None:
        """SET: :DDS:DUTY {fmt_num(value)}"""
        self._transport.write(f":DDS:DUTY {fmt_num(value)}")

    # ------------------------------------------------------------------
    # mod_enable — :DDS:WAVE:MODE
    # ------------------------------------------------------------------

    @property
    def mod_enable(self) -> bool:
        """Включение/выключение модуляции.

        GET: :DDS:WAVE:MODE? → parse_bool
        """
        return parse_bool(self._transport.query(":DDS:WAVE:MODE?"))

    @mod_enable.setter
    def mod_enable(self, value) -> None:
        """SET: :DDS:WAVE:MODE {ON|OFF}"""
        self._transport.write(f":DDS:WAVE:MODE {bool_arg(value)}")

    # ------------------------------------------------------------------
    # mod_type — :DDS:MODE:TYPE
    # ------------------------------------------------------------------

    @property
    def mod_type(self) -> str:
        """Тип модуляции (AM/FM).

        GET: :DDS:MODE:TYPE? → эхо литерала
        """
        return self._transport.query(":DDS:MODE:TYPE?")

    @mod_type.setter
    def mod_type(self, value: str) -> None:
        """SET: validate_enum(MOD_TYPES) → :DDS:MODE:TYPE {canonical}

        Raises:
            ValueError: если значение не входит в MOD_TYPES.
        """
        canonical = validate_enum(value, self.MOD_TYPES, "mod_type")
        self._transport.write(f":DDS:MODE:TYPE {canonical}")

    # ------------------------------------------------------------------
    # mod_wave — :DDS:MODE:WAVE:TYPE
    # ------------------------------------------------------------------

    @property
    def mod_wave(self) -> str:
        """Форма волны модулятора.

        GET: :DDS:MODE:WAVE:TYPE? → эхо литерала
        """
        return self._transport.query(":DDS:MODE:WAVE:TYPE?")

    @mod_wave.setter
    def mod_wave(self, value: str) -> None:
        """SET: validate_enum(MOD_WAVES) → :DDS:MODE:WAVE:TYPE {canonical}

        Raises:
            ValueError: если значение не входит в MOD_WAVES.
        """
        canonical = validate_enum(value, self.MOD_WAVES, "mod_wave")
        self._transport.write(f":DDS:MODE:WAVE:TYPE {canonical}")

    # ------------------------------------------------------------------
    # mod_freq — :DDS:MODE:FREQ
    # ------------------------------------------------------------------

    @property
    def mod_freq(self) -> float:
        """Частота модулятора (Hz).

        GET: :DDS:MODE:FREQ? → float (NR3)
        """
        return float(self._transport.query(":DDS:MODE:FREQ?"))

    @mod_freq.setter
    def mod_freq(self, value) -> None:
        """SET: :DDS:MODE:FREQ {fmt_num(value)}"""
        self._transport.write(f":DDS:MODE:FREQ {fmt_num(value)}")

    # ------------------------------------------------------------------
    # mod_depth — :DDS:MODE:DEPThordeviation
    # ------------------------------------------------------------------

    @property
    def mod_depth(self) -> float:
        """Глубина AM-модуляции (%) или FM-девиация (Hz).

        GET: :DDS:MODE:DEPThordeviation? → float
        Литерал 'DEPThordeviation' — дословно из мануала (не исправлять).
        """
        return float(self._transport.query(":DDS:MODE:DEPThordeviation?"))

    @mod_depth.setter
    def mod_depth(self, value) -> None:
        """SET: :DDS:MODE:DEPThordeviation {fmt_num(value)}"""
        self._transport.write(f":DDS:MODE:DEPThordeviation {fmt_num(value)}")

    # ------------------------------------------------------------------
    # burst_enable — :DDS:BURSt:SWITch
    # ------------------------------------------------------------------

    @property
    def burst_enable(self) -> bool:
        """Включение/выключение burst-режима.

        GET: :DDS:BURSt:SWITch? → parse_bool
        """
        return parse_bool(self._transport.query(":DDS:BURSt:SWITch?"))

    @burst_enable.setter
    def burst_enable(self, value) -> None:
        """SET: :DDS:BURSt:SWITch {ON|OFF}"""
        self._transport.write(f":DDS:BURSt:SWITch {bool_arg(value)}")

    # ------------------------------------------------------------------
    # burst_type — :DDS:BURSt:TYPE
    # ------------------------------------------------------------------

    @property
    def burst_type(self) -> str:
        """Тип burst (N_CYCLE / INFInit).

        GET: :DDS:BURSt:TYPE? → эхо литерала
        """
        return self._transport.query(":DDS:BURSt:TYPE?")

    @burst_type.setter
    def burst_type(self, value: str) -> None:
        """SET: validate_enum(BURST_TYPES) → :DDS:BURSt:TYPE {canonical}

        Raises:
            ValueError: если значение не входит в BURST_TYPES.
        """
        canonical = validate_enum(value, self.BURST_TYPES, "burst_type")
        self._transport.write(f":DDS:BURSt:TYPE {canonical}")

    # ------------------------------------------------------------------
    # burst_count — :DDS:BURSt:CNT
    # ------------------------------------------------------------------

    @property
    def burst_count(self) -> int:
        """Число периодов в burst.

        GET: :DDS:BURSt:CNT? → int(float(resp))
        Hardware-verified: readback может быть строкой-integer или NR3.
        """
        return int(float(self._transport.query(":DDS:BURSt:CNT?")))

    @burst_count.setter
    def burst_count(self, value) -> None:
        """SET: :DDS:BURSt:CNT {int(value)}"""
        self._transport.write(f":DDS:BURSt:CNT {int(value)}")

    # ------------------------------------------------------------------
    # burst_trigger — действие (без запроса)
    # ------------------------------------------------------------------

    def burst_trigger(self) -> None:
        """Программно запустить burst.

        Отправляет :DDS:BURSt:TRIGger без ожидания ответа.
        """
        self._transport.write(":DDS:BURSt:TRIGger")
