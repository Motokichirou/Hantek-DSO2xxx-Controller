"""Тесты клиентского декодера SPI (синтетические сигналы).

Сигналы генерируются программно: SCLK + MOSI (+опц. CS) при заданных
clock_edge / bits / msb_first. Никакого железа и I/O.
"""
from __future__ import annotations

import numpy as np
import pytest

from hantek_dso2d15.waveform.decode_spi import SpiWord, decode_spi

HI = 3.3
LO = 0.0
THR = 1.65
SPB = 20  # сэмплов на один такт (бит); фронт — на середине бита


def _word_bits(value: int, bits: int, msb_first: bool) -> list[int]:
    """Физический порядок бит слова на проводе."""
    if msb_first:
        return [(value >> (bits - 1 - i)) & 1 for i in range(bits)]
    return [(value >> i) & 1 for i in range(bits)]


def _gen(
    bit_stream: list[int],
    *,
    clock_edge: str = "Rising",
    spb: int = SPB,
    cs_stream: list[bool] | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray | None]:
    """Сгенерировать SCLK/MOSI(/CS) для потока физических бит.

    Для каждого бита: первая половина такта — SCLK на уровне покоя и данные
    уже выставлены; вторая половина — SCLK на активном уровне (активный фронт
    приходится на середину бита, где данные стабильны).

    ``cs_stream`` (если задан) — по одному булеву флагу «CS активен» на бит;
    активный уровень CS считается низким (active-low) в генераторе.
    """
    rising = clock_edge == "Rising"
    idle_clk = LO if rising else HI
    active_clk = HI if rising else LO

    sclk: list[float] = []
    data: list[float] = []
    cs: list[float] | None = [] if cs_stream is not None else None

    half = spb // 2
    for k, b in enumerate(bit_stream):
        dval = HI if b else LO
        cval = None
        if cs is not None:
            active = cs_stream[k]
            cval = LO if active else HI  # active-low
        for j in range(spb):
            sclk.append(idle_clk if j < half else active_clk)
            data.append(dval)
            if cs is not None:
                cs.append(cval)

    times = np.arange(len(sclk), dtype=float)
    cs_arr = np.asarray(cs, dtype=float) if cs is not None else None
    return times, np.asarray(sclk, dtype=float), np.asarray(data, dtype=float), cs_arr


# --- границы фронтов для проверки времён -----------------------------------
# Для бита с индексом k активный фронт приходится на сэмпл k*SPB + SPB//2.
def _edge_t(k: int, spb: int = SPB) -> float:
    return float(k * spb + spb // 2)


def test_single_word_rising_msb() -> None:
    bits = _word_bits(0xA5, 8, msb_first=True)
    times, sclk, data, _ = _gen(bits, clock_edge="Rising")
    out = decode_spi(times, sclk, data, threshold=THR, clock_edge="Rising", bits=8)
    assert len(out) == 1
    w = out[0]
    assert isinstance(w, SpiWord)
    assert w.value == 0xA5
    assert w.start == pytest.approx(_edge_t(0))
    assert w.end == pytest.approx(_edge_t(7))


def test_multiple_words_sequence() -> None:
    values = [0x3C, 0xF0, 0x01]
    stream: list[int] = []
    for v in values:
        stream += _word_bits(v, 8, msb_first=True)
    times, sclk, data, _ = _gen(stream, clock_edge="Rising")
    out = decode_spi(times, sclk, data, threshold=THR, clock_edge="Rising", bits=8)
    assert [w.value for w in out] == values
    # времена по возрастанию, каждое слово начинается позже предыдущего
    starts = [w.start for w in out]
    assert starts == sorted(starts)
    assert out[0].start == pytest.approx(_edge_t(0))
    assert out[1].start == pytest.approx(_edge_t(8))


def test_falling_edge() -> None:
    bits = _word_bits(0x6E, 8, msb_first=True)
    times, sclk, data, _ = _gen(bits, clock_edge="Falling")
    out = decode_spi(times, sclk, data, threshold=THR, clock_edge="Falling", bits=8)
    assert len(out) == 1
    assert out[0].value == 0x6E


def test_msb_vs_lsb_first() -> None:
    # 0x53 = 0b01010011, зеркало бит = 0b11001010 = 0xCA (не палиндром).
    phys = _word_bits(0x53, 8, msb_first=True)
    times, sclk, data, _ = _gen(phys, clock_edge="Rising")
    msb = decode_spi(times, sclk, data, threshold=THR, bits=8, msb_first=True)
    lsb = decode_spi(times, sclk, data, threshold=THR, bits=8, msb_first=False)
    assert msb[0].value == 0x53
    assert lsb[0].value == 0xCA
    assert msb[0].value != lsb[0].value


def test_word_width_12() -> None:
    value = 0xABC  # 12 бит
    phys = _word_bits(value, 12, msb_first=True)
    times, sclk, data, _ = _gen(phys, clock_edge="Rising")
    out = decode_spi(times, sclk, data, threshold=THR, bits=12, msb_first=True)
    assert len(out) == 1
    assert out[0].value == value


def test_cs_two_windows_and_ignored_bits() -> None:
    # Окно 1: слово 0x2D (CS активен). Затем 8 «мусорных» тактов при неактивном
    # CS (должны игнорироваться). Затем окно 2: слово 0x91 (CS активен).
    w1 = _word_bits(0x2D, 8, msb_first=True)
    garbage = _word_bits(0xFF, 8, msb_first=True)
    w2 = _word_bits(0x91, 8, msb_first=True)
    stream = w1 + garbage + w2
    cs_stream = [True] * 8 + [False] * 8 + [True] * 8
    times, sclk, data, cs = _gen(stream, clock_edge="Rising", cs_stream=cs_stream)
    out = decode_spi(
        times, sclk, data, threshold=THR, bits=8, cs=cs, cs_active_low=True
    )
    assert [w.value for w in out] == [0x2D, 0x91]


def test_cs_partial_word_discarded() -> None:
    # 4 бита при активном CS, затем CS снят (недособранное слово выбрасывается),
    # потом полноценное слово в новом активном окне.
    partial = _word_bits(0xF, 4, msb_first=True)  # только 4 физических бита
    full = _word_bits(0x77, 8, msb_first=True)
    stream = partial + full
    cs_stream = [True] * 4 + [True] * 8  # оба окна активны, но между ними разрыв
    # Вставим разрыв CS: неактивный «холостой» бит между partial и full.
    gap = _word_bits(0x0, 1, msb_first=True)
    stream = partial + gap + full
    cs_stream = [True] * 4 + [False] * 1 + [True] * 8
    times, sclk, data, cs = _gen(stream, clock_edge="Rising", cs_stream=cs_stream)
    out = decode_spi(times, sclk, data, threshold=THR, bits=8, cs=cs)
    assert [w.value for w in out] == [0x77]


def test_no_edges_returns_empty() -> None:
    times = np.arange(100, dtype=float)
    sclk = np.full(100, LO)  # такт всё время низкий — нет фронтов
    data = np.full(100, HI)
    out = decode_spi(times, sclk, data, threshold=THR, clock_edge="Rising", bits=8)
    assert out == []


def test_empty_input_returns_empty() -> None:
    empty = np.array([], dtype=float)
    out = decode_spi(empty, empty, empty, threshold=THR, bits=8)
    assert out == []


def test_incomplete_trailing_word_not_emitted() -> None:
    # Одно полное слово + 3 «висящих» бита в конце.
    full = _word_bits(0x5A, 8, msb_first=True)
    tail = _word_bits(0x5, 3, msb_first=True)
    times, sclk, data, _ = _gen(full + tail, clock_edge="Rising")
    out = decode_spi(times, sclk, data, threshold=THR, bits=8)
    assert len(out) == 1
    assert out[0].value == 0x5A
