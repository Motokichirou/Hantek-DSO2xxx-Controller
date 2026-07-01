"""Клиентский декодер I2C из сэмплов осциллограммы.

Прибор DSO2D15 не отдаёт декодированные данные шин по SCPI — мы декодируем
I2C самостоятельно из двух захваченных аналоговых линий (SDA и SCL).

Модуль чистый: только numpy и stdlib. Никакого Qt, I/O или транспорта.

Стандартный I2C:
- в покое обе линии высокие;
- START: SDA переходит 1→0, пока SCL высокий;
- STOP:  SDA переходит 0→1, пока SCL высокий;
- между START и STOP биты защёлкиваются по нарастающему фронту SCL (0→1);
  значение бита = уровень SDA в этот момент;
- первый байт после START — адрес: 8 бит MSB-first + 9-й такт ACK/NACK
  (SDA низкий = ACK); значение = полный байт (7-бит адрес<<1 | R/W);
- далее байты данных: 8 бит + такт ACK; повтор до STOP или повторного START.

START/STOP (переход SDA при высоком SCL) отслеживаются в любой момент и
прерывают текущий недосчитанный байт — незавершённый байт не эмитится.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class I2cSymbol:
    """Одно декодированное событие шины I2C."""

    start: float          # время (с) начала события
    end: float            # время (с) конца события
    kind: str             # "start" | "address" | "data" | "stop"
    value: int | None     # байт для address/data (0..255); None для start/stop
    ack: bool | None      # True=ACK, False=NACK для address/data; None для start/stop


def decode_i2c(
    times,                # np.ndarray[float] возрастающие метки времени (с)
    sda,                  # np.ndarray[float] напряжение линии SDA
    scl,                  # np.ndarray[float] напряжение линии SCL
    *,
    threshold: float,     # порог логического уровня (В): sample >= threshold → 1
) -> list[I2cSymbol]:
    """Декодировать события I2C из захваченных линий SDA и SCL.

    Возвращает список ``I2cSymbol`` в порядке появления во времени:
    start → address → data* → (repeated start → address → data* )* → stop.
    Пустой/несогласованный вход или отсутствие START → ``[]``.
    Обрыв сигнала посреди байта не вызывает исключения — недосчитанный
    байт просто не эмитится.
    """
    times = np.asarray(times, dtype=float)
    sda = np.asarray(sda, dtype=float)
    scl = np.asarray(scl, dtype=float)
    n = times.size
    if n == 0 or sda.size != n or scl.size != n:
        return []

    # Дигитизация линий.
    sda_d = (sda >= threshold).astype(np.int8)
    scl_d = (scl >= threshold).astype(np.int8)

    results: list[I2cSymbol] = []

    in_transaction = False        # находимся ли между START и STOP
    byte_is_address = True        # следующий полный байт — адрес?
    bits: list[int] = []          # накопленные биты текущего байта (8 данных + ACK)
    bit_times: list[float] = []   # времена фронтов SCL для этих бит

    def reset_byte() -> None:
        bits.clear()
        bit_times.clear()

    for i in range(1, n):
        scl_prev, scl_cur = int(scl_d[i - 1]), int(scl_d[i])
        sda_prev, sda_cur = int(sda_d[i - 1]), int(sda_d[i])
        t = float(times[i])

        # 1) START/STOP: переход SDA при высоком SCL — приоритетнее защёлки бита.
        if scl_prev == 1 and scl_cur == 1 and sda_prev != sda_cur:
            if sda_prev == 1 and sda_cur == 0:
                # START (первый или повторный) — прерывает недосчитанный байт.
                results.append(I2cSymbol(t, t, "start", None, None))
                in_transaction = True
                byte_is_address = True
                reset_byte()
            else:
                # STOP — валиден только внутри транзакции.
                if in_transaction:
                    results.append(I2cSymbol(t, t, "stop", None, None))
                in_transaction = False
                reset_byte()
            continue

        # 2) Защёлка бита по нарастающему фронту SCL (только в транзакции).
        if in_transaction and scl_prev == 0 and scl_cur == 1:
            bits.append(sda_cur)
            bit_times.append(t)
            if len(bits) == 9:
                # 8 бит данных (MSB-first) + 9-й такт ACK.
                value = 0
                for b in bits[:8]:
                    value = (value << 1) | (b & 1)
                ack = (bits[8] == 0)   # SDA низкий на 9-м такте = ACK
                kind = "address" if byte_is_address else "data"
                results.append(
                    I2cSymbol(
                        start=bit_times[0],
                        end=bit_times[8],
                        kind=kind,
                        value=value,
                        ack=ack,
                    )
                )
                byte_is_address = False
                reset_byte()

    return results
