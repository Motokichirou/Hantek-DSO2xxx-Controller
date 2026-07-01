"""Тесты для hantek_dso2d15.waveform.decode_uart — клиентский UART-декодер.

TDD: запусти этот файл ДО создания decode_uart.py, чтобы убедиться в FAIL,
затем после реализации — в PASS.

Сигнал синтетический: генерируем UART-волну из байтов хелпером make_uart_wave
и проверяем, что декодер восстанавливает исходные значения и корректно
помечает ошибки parity/framing.
"""
import numpy as np
import pytest

from hantek_dso2d15.waveform.decode_uart import UartSymbol, decode_uart


# ---------------------------------------------------------------------------
# Хелпер генерации синтетической UART-волны
# ---------------------------------------------------------------------------

def make_uart_wave(
    bytes_seq,
    baud,
    sr,
    *,
    bits=8,
    parity="NONE",
    stop_bits=1,
    idle_high=True,
    lsb_first=True,
    vlo=0.0,
    vhi=3.3,
    idle_lead=10.0,   # длительность ведущего покоя в бит-периодах
    idle_gap=2.0,     # покой между кадрами в бит-периодах
    idle_tail=10.0,   # хвостовой покой в бит-периодах
):
    """Построить (times, samples) для последовательности байтов.

    Логические уровни кодируются как vhi для логической 1 и vlo для 0.
    При idle_high покой = логическая 1; иначе линия инвертируется так,
    что покой = vlo (логический 0 на линии), но значения данных те же.
    """
    bit_dt = 1.0 / baud
    samples_per_bit = sr / baud

    def parity_bit(value):
        ones = bin(value & ((1 << bits) - 1)).count("1")
        if parity == "EVEN":
            return ones & 1
        if parity == "ODD":
            return (ones & 1) ^ 1
        return None

    # Список логических битов (в терминах «линия в покое = 1»):
    logic_bits = []

    def emit_idle(n_bits):
        # покой = логическая 1
        logic_bits.extend([1] * int(round(n_bits)))

    emit_idle(idle_lead)
    for value in bytes_seq:
        value &= (1 << bits) - 1
        # старт-бит = 0
        logic_bits.append(0)
        # данные
        data_order = range(bits) if lsb_first else range(bits - 1, -1, -1)
        for k in data_order:
            logic_bits.append((value >> k) & 1)
        # parity
        pb = parity_bit(value)
        if pb is not None:
            logic_bits.append(pb)
        # стоп-бит(ы) = 1
        logic_bits.extend([1] * int(round(stop_bits)))
        # межкадровый покой
        emit_idle(idle_gap)
    emit_idle(idle_tail)

    # Развернуть биты в сэмплы
    total_samples = int(round(len(logic_bits) * samples_per_bit))
    times = np.arange(total_samples) / sr
    samples = np.empty(total_samples, dtype=float)
    for i in range(total_samples):
        bit_index = int(i / samples_per_bit)
        if bit_index >= len(logic_bits):
            bit_index = len(logic_bits) - 1
        logic = logic_bits[bit_index]
        if not idle_high:
            logic ^= 1  # инвертировать линию
        samples[i] = vhi if logic else vlo
    return times, samples


THRESHOLD = 1.65  # середина между 0.0 и 3.3 В


# ---------------------------------------------------------------------------
# Базовый декод одного байта 8N1
# ---------------------------------------------------------------------------

def test_single_byte_0x55():
    baud = 9600.0
    sr = baud * 50
    times, samples = make_uart_wave([0x55], baud, sr)
    out = decode_uart(times, samples, threshold=THRESHOLD, baud=baud)
    assert len(out) == 1
    sym = out[0]
    assert isinstance(sym, UartSymbol)
    assert sym.value == 0x55
    assert sym.error is None
    # длительность кадра = 1 старт + 8 данных + 1 стоп = 10 бит
    assert sym.end - sym.start == pytest.approx(10.0 / baud, rel=0.05)
    assert sym.start >= 0.0


def test_single_byte_0x00_and_0xff():
    baud = 19200.0
    sr = baud * 40
    for val in (0x00, 0xFF):
        times, samples = make_uart_wave([val], baud, sr)
        out = decode_uart(times, samples, threshold=THRESHOLD, baud=baud)
        assert len(out) == 1
        assert out[0].value == val
        assert out[0].error is None


# ---------------------------------------------------------------------------
# Последовательность байтов
# ---------------------------------------------------------------------------

def test_byte_sequence():
    baud = 9600.0
    sr = baud * 50
    seq = [0x48, 0x69, 0x21, 0x00, 0xAA]
    times, samples = make_uart_wave(seq, baud, sr)
    out = decode_uart(times, samples, threshold=THRESHOLD, baud=baud)
    assert [s.value for s in out] == seq
    assert all(s.error is None for s in out)
    # символы упорядочены по времени
    starts = [s.start for s in out]
    assert starts == sorted(starts)


# ---------------------------------------------------------------------------
# LSB-first vs MSB-first
# ---------------------------------------------------------------------------

def test_lsb_vs_msb_first():
    baud = 9600.0
    sr = baud * 50
    val = 0x53  # 0b01010011 — несимметричный
    t_lsb, s_lsb = make_uart_wave([val], baud, sr, lsb_first=True)
    out_lsb = decode_uart(t_lsb, s_lsb, threshold=THRESHOLD, baud=baud, lsb_first=True)
    assert out_lsb[0].value == val

    t_msb, s_msb = make_uart_wave([val], baud, sr, lsb_first=False)
    out_msb = decode_uart(t_msb, s_msb, threshold=THRESHOLD, baud=baud, lsb_first=False)
    assert out_msb[0].value == val

    # Если декодировать MSB-сигнал как LSB — получим зеркальное значение, не val.
    out_wrong = decode_uart(t_msb, s_msb, threshold=THRESHOLD, baud=baud, lsb_first=True)
    # 0x53 = 0b01010011 -> reversed 0b11001010 = 0xCA
    assert out_wrong[0].value == 0xCA
    assert out_wrong[0].value != val


# ---------------------------------------------------------------------------
# 7-битные данные
# ---------------------------------------------------------------------------

def test_seven_bit_data():
    baud = 9600.0
    sr = baud * 50
    seq = [0x41, 0x7F, 0x00]
    times, samples = make_uart_wave(seq, baud, sr, bits=7)
    out = decode_uart(times, samples, threshold=THRESHOLD, baud=baud, bits=7)
    assert [s.value for s in out] == seq
    assert all(s.error is None for s in out)


# ---------------------------------------------------------------------------
# Чётность
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("parity", ["EVEN", "ODD"])
def test_parity_correct(parity):
    baud = 9600.0
    sr = baud * 50
    seq = [0x55, 0x53, 0xFF, 0x00]
    times, samples = make_uart_wave(seq, baud, sr, parity=parity)
    out = decode_uart(times, samples, threshold=THRESHOLD, baud=baud, parity=parity)
    assert [s.value for s in out] == seq
    assert all(s.error is None for s in out)


@pytest.mark.parametrize("parity", ["EVEN", "ODD"])
def test_parity_error(parity):
    """Намеренно испортить parity-бит → error == 'parity'."""
    baud = 9600.0
    sr = baud * 50
    val = 0x53
    times, samples = make_uart_wave([val], baud, sr, parity=parity)
    samples_per_bit = sr / baud
    # parity-бит идёт после старт(1) + данные(8) = индекс бита 9 (0-based),
    # с учётом ведущего покоя idle_lead=10 бит.
    parity_bit_index = 10 + 1 + 8  # idle_lead + старт + 8 данных
    centre = int((parity_bit_index + 0.5) * samples_per_bit)
    # инвертировать весь parity-бит
    lo = int(parity_bit_index * samples_per_bit)
    hi = int((parity_bit_index + 1) * samples_per_bit)
    samples[lo:hi] = 3.3 - samples[lo:hi]  # инверсия уровня
    out = decode_uart(times, samples, threshold=THRESHOLD, baud=baud, parity=parity)
    assert len(out) == 1
    assert out[0].value == val
    assert out[0].error == "parity"


# ---------------------------------------------------------------------------
# Framing error
# ---------------------------------------------------------------------------

def test_framing_error():
    """Испортить стоп-бит (активный уровень вместо покоя) → 'framing'."""
    baud = 9600.0
    sr = baud * 50
    val = 0x55
    times, samples = make_uart_wave([val], baud, sr)
    samples_per_bit = sr / baud
    # стоп-бит: idle_lead(10) + старт(1) + данные(8) = индекс 19
    stop_bit_index = 10 + 1 + 8
    lo = int(stop_bit_index * samples_per_bit)
    hi = int((stop_bit_index + 1) * samples_per_bit)
    samples[lo:hi] = 0.0  # принудительно активный уровень (0 при idle_high)
    out = decode_uart(times, samples, threshold=THRESHOLD, baud=baud)
    assert len(out) == 1
    assert out[0].error == "framing"


# ---------------------------------------------------------------------------
# Инвертированная линия (idle_high=False)
# ---------------------------------------------------------------------------

def test_inverted_line():
    baud = 9600.0
    sr = baud * 50
    seq = [0x53, 0xA5]
    times, samples = make_uart_wave(seq, baud, sr, idle_high=False)
    out = decode_uart(times, samples, threshold=THRESHOLD, baud=baud, idle_high=False)
    assert [s.value for s in out] == seq
    assert all(s.error is None for s in out)


# ---------------------------------------------------------------------------
# Шум/мусор перед валидным кадром
# ---------------------------------------------------------------------------

def test_noise_before_frame():
    """Короткий мусорный глитч (уже старт-бита) не должен ломать декод."""
    baud = 9600.0
    sr = baud * 50
    val = 0x42
    times, samples = make_uart_wave([val], baud, sr, idle_lead=20.0)
    samples_per_bit = sr / baud
    # Воткнуть очень короткий глитч в зону покоя (1/5 бит-периода)
    glitch_centre_bit = 5
    lo = int(glitch_centre_bit * samples_per_bit)
    hi = lo + max(1, int(samples_per_bit / 5))
    samples[lo:hi] = 0.0  # кратковременный спад
    out = decode_uart(times, samples, threshold=THRESHOLD, baud=baud)
    # Настоящий кадр должен найтись; значение корректно.
    assert any(s.value == val and s.error is None for s in out)


# ---------------------------------------------------------------------------
# Граничные случаи
# ---------------------------------------------------------------------------

def test_empty_input():
    assert decode_uart(np.array([]), np.array([]), threshold=THRESHOLD, baud=9600.0) == []


def test_idle_only():
    baud = 9600.0
    sr = baud * 50
    # только покой, без байтов
    times, samples = make_uart_wave([], baud, sr, idle_lead=30.0, idle_tail=0.0)
    out = decode_uart(times, samples, threshold=THRESHOLD, baud=baud)
    assert out == []


def test_truncated_frame_does_not_crash():
    """Сигнал обрывается посреди кадра — не падать, вернуть что распознано."""
    baud = 9600.0
    sr = baud * 50
    times, samples = make_uart_wave([0x55], baud, sr, idle_tail=0.0)
    # обрезать последние сэмплы так, чтобы стоп-бит ушёл за границу
    cut = int(len(samples) * 0.7)
    times = times[:cut]
    samples = samples[:cut]
    out = decode_uart(times, samples, threshold=THRESHOLD, baud=baud)
    # не должно быть исключения; список (возможно пустой) корректен
    assert isinstance(out, list)


def test_two_stop_bits():
    baud = 9600.0
    sr = baud * 50
    seq = [0x55, 0x3C]
    times, samples = make_uart_wave(seq, baud, sr, stop_bits=2)
    out = decode_uart(times, samples, threshold=THRESHOLD, baud=baud, stop_bits=2)
    assert [s.value for s in out] == seq
    assert all(s.error is None for s in out)
