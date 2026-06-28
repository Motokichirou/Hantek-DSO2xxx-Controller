"""Клиентский декодер UART из сэмплов осциллограммы.

Прибор DSO2D15 не отдаёт декодированные данные шин по SCPI — мы декодируем
асинхронный UART самостоятельно из захваченного аналогового сигнала.

Модуль чистый: только numpy и stdlib. Никакого Qt, I/O или транспорта.

Стандартный асинхронный UART:
- линия в покое держит уровень покоя (idle_high=True → логическая 1);
- кадр начинается со старт-бита (переход покой→актив);
- далее ``bits`` бит данных (порядок задаётся ``lsb_first``);
- опциональный бит чётности;
- один или два стоп-бита (уровень покоя).

Семплирование выполняется по серединам бит-интервалов относительно
зафиксированного фронта старт-бита (t0).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class UartSymbol:
    """Один декодированный UART-символ (кадр)."""

    start: float          # время (с) начала старт-бита
    end: float            # время (с) конца стоп-бита
    value: int            # декодированное значение данных (0..2^bits-1)
    error: str | None     # None | "parity" | "framing"


def _sample_level(times: np.ndarray, level: np.ndarray, t: float) -> int | None:
    """Уровень (0/1) в ближайшем по времени сэмпле к моменту ``t``.

    Возвращает None, если ``t`` выходит за пределы захвата (справа) —
    значит, для центра бита не хватает данных.
    """
    if t > times[-1]:
        return None
    if t <= times[0]:
        return int(level[0])
    # times возрастает → ищем точку вставки и берём ближайшего соседа
    idx = int(np.searchsorted(times, t))
    if idx >= len(times):
        idx = len(times) - 1
    if idx > 0 and (t - times[idx - 1]) <= (times[idx] - t):
        idx -= 1
    return int(level[idx])


def decode_uart(
    times,                # np.ndarray[float], временные метки сэмплов (с), возрастающие
    samples,              # np.ndarray[float], напряжение (В)
    *,
    threshold: float,     # порог логического уровня (В): sample >= threshold → 1, иначе 0
    baud: float,          # бод (бит/с), бит-период = 1/baud
    bits: int = 8,        # ширина данных 5..8
    parity: str = "NONE", # "NONE" | "ODD" | "EVEN"
    stop_bits: float = 1, # 1 или 2 (для проверки framing достаточно одного)
    idle_high: bool = True,   # уровень покоя линии: True=высокий (стандартный UART/RS232-логика)
    lsb_first: bool = True,   # порядок бит данных
) -> list[UartSymbol]:
    """Декодировать UART-кадры из захваченного сигнала.

    Параметры — см. контракт модуля. Возвращает список ``UartSymbol`` в
    порядке появления во времени. Пустой/слишком короткий сигнал → ``[]``.
    Обрыв сигнала посреди кадра не вызывает исключения — декод прекращается.
    """
    times = np.asarray(times, dtype=float)
    samples = np.asarray(samples, dtype=float)
    if times.size == 0 or samples.size == 0 or times.size != samples.size:
        return []

    bit_dt = 1.0 / baud

    # Дигитизация. level[i] = 1, если sample >= threshold, иначе 0.
    raw = (samples >= threshold).astype(np.int8)
    # Приводим к логике «покой = 1, актив = 0» внутренне (как стандартный UART),
    # инвертируя при idle_high=False.
    level = raw if idle_high else (1 - raw)

    idle = 1   # внутренний уровень покоя
    active = 0  # внутренний активный уровень (старт-бит)

    parity = parity.upper()
    has_parity = parity != "NONE"
    n_data = int(bits)

    results: list[UartSymbol] = []
    n = times.size
    i = 1  # индекс сэмпла для поиска фронта (нужен предыдущий)

    while i < n:
        # Поиск старт-фронта: переход покой(1) → актив(0).
        if not (level[i - 1] == idle and level[i] == active):
            i += 1
            continue

        # t0 — момент фронта старт-бита (используем время активного сэмпла).
        t0 = float(times[i])

        # Проверка старт-бита: середина старт-бита должна быть активным уровнем.
        start_mid = t0 + 0.5 * bit_dt
        lvl = _sample_level(times, level, start_mid)
        if lvl is None:
            break  # не хватает данных — прекращаем
        if lvl != active:
            # шум/глитч — не настоящий старт-бит, ищем следующий фронт
            i += 1
            continue

        # Сбор бит данных по серединам.
        bit_levels: list[int] = []
        truncated = False
        # данные занимают позиции 1..n_data (позиция 0 = старт-бит)
        for k in range(n_data):
            centre = t0 + (1 + k + 0.5) * bit_dt
            lvl = _sample_level(times, level, centre)
            if lvl is None:
                truncated = True
                break
            bit_levels.append(lvl)
        if truncated:
            break

        # Внутренняя логика «покой=1»: бит данных читается как логический уровень
        # напрямую (1 = высокий в стандартной полярности). Сбор значения.
        if lsb_first:
            value = 0
            for k, b in enumerate(bit_levels):
                value |= (b & 1) << k
        else:
            value = 0
            for b in bit_levels:
                value = (value << 1) | (b & 1)

        error: str | None = None

        # Бит чётности.
        if has_parity:
            centre = t0 + (1 + n_data + 0.5) * bit_dt
            pbit = _sample_level(times, level, centre)
            if pbit is None:
                break
            ones = bin(value).count("1")
            if parity == "EVEN":
                expected = ones & 1
            else:  # ODD
                expected = (ones & 1) ^ 1
            if (pbit & 1) != expected:
                error = "parity"

        # Стоп-бит: середина первого стоп-бита должна быть уровнем покоя.
        stop_pos = 1 + n_data + (1 if has_parity else 0)
        stop_centre = t0 + (stop_pos + 0.5) * bit_dt
        sbit = _sample_level(times, level, stop_centre)
        if sbit is None:
            break
        if sbit != idle and error is None:
            error = "framing"

        # Границы символа.
        total_bits = 1 + n_data + (1 if has_parity else 0) + stop_bits
        end = t0 + total_bits * bit_dt

        results.append(UartSymbol(start=t0, end=end, value=value, error=error))

        # Продолжить поиск после конца стоп-бита.
        next_idx = int(np.searchsorted(times, end))
        if next_idx <= i:
            next_idx = i + 1
        i = max(next_idx, 1)

    return results
