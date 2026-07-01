"""Клиентский декодер SPI из сэмплов осциллограммы.

Прибор DSO2D15 не отдаёт декодированные данные шин по SCPI — мы декодируем
синхронную шину SPI самостоятельно из захваченного аналогового сигнала.

Модуль чистый: только numpy и stdlib. Никакого Qt, I/O или транспорта.

Синхронный SPI:
- SCLK — тактовая линия; бит защёлкивается на выбранном активном фронте
  (``clock_edge``: "Rising" = 0→1, "Falling" = 1→0);
- data (MOSI/MISO) — линия данных; уровень читается в момент активного фронта;
- ``bits`` бит подряд собираются в слово (порядок задаётся ``msb_first``);
- опциональная линия CS: биты учитываются только пока CS активен; снятие CS
  сбрасывает недособранное слово.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class SpiWord:
    """Одно декодированное слово SPI."""

    start: float          # время (с) фронта первого бита слова
    end: float            # время (с) фронта последнего бита слова
    value: int            # собранное значение слова (0..2^bits-1)


def decode_spi(
    times,                # np.ndarray[float], возрастающие метки времени (с)
    sclk,                 # np.ndarray[float], напряжение тактовой линии (SCL)
    data,                 # np.ndarray[float], напряжение линии данных (SDA/MOSI)
    *,
    threshold: float,     # порог логического уровня (В): >= порог → 1
    clock_edge: str = "Rising",   # "Rising" | "Falling" — активный фронт SCL
    bits: int = 8,        # ширина слова 4..32
    msb_first: bool = True,
    cs=None,              # np.ndarray[float] | None — линия выбора кристалла
    cs_active_low: bool = True,   # активный уровень CS
) -> list[SpiWord]:
    """Декодировать слова SPI из захваченных сигналов.

    Параметры — см. контракт модуля. Возвращает список ``SpiWord`` в порядке
    появления во времени. Пустой/несогласованный вход или отсутствие активных
    фронтов → ``[]``. Неполное слово в конце захвата не эмитится.
    """
    times = np.asarray(times, dtype=float)
    sclk = np.asarray(sclk, dtype=float)
    data = np.asarray(data, dtype=float)

    n = times.size
    if n == 0 or sclk.size != n or data.size != n:
        return []

    n_bits = int(bits)

    # Дигитизация линий по порогу.
    sclk_d = (sclk >= threshold).astype(np.int8)
    data_d = (data >= threshold).astype(np.int8)

    cs_active = None
    if cs is not None:
        cs_arr = np.asarray(cs, dtype=float)
        if cs_arr.size != n:
            return []
        cs_raw = (cs_arr >= threshold).astype(np.int8)
        # cs_active[i] = 1, если CS в активном состоянии в сэмпле i.
        cs_active = (cs_raw == 0) if cs_active_low else (cs_raw == 1)

    rising = clock_edge == "Rising"

    results: list[SpiWord] = []
    acc: list[tuple[float, int]] = []  # (время фронта, бит)

    for i in range(1, n):
        # Снятие CS (активен → неактивен) обрывает недособранное слово.
        if cs_active is not None and cs_active[i - 1] and not cs_active[i]:
            acc = []

        # Активный фронт SCL?
        if rising:
            edge = (sclk_d[i - 1] == 0) and (sclk_d[i] == 1)
        else:
            edge = (sclk_d[i - 1] == 1) and (sclk_d[i] == 0)
        if not edge:
            continue

        # Вне активного окна CS — бит не учитываем.
        if cs_active is not None and not cs_active[i]:
            continue

        t_edge = float(times[i])
        bit = int(data_d[i])
        acc.append((t_edge, bit))

        if len(acc) == n_bits:
            if msb_first:
                value = 0
                for _, b in acc:
                    value = (value << 1) | b
            else:
                value = 0
                for k, (_, b) in enumerate(acc):
                    value |= b << k
            results.append(
                SpiWord(start=acc[0][0], end=acc[-1][0], value=value)
            )
            acc = []

    return results
