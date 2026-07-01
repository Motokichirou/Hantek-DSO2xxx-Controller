"""Тесты для hantek_dso2d15.waveform.decode_i2c — клиентский I2C-декодер.

TDD: запусти этот файл ДО создания decode_i2c.py, чтобы убедиться в FAIL,
затем после реализации — в PASS.

Сигнал синтетический: генерируем пару линий SDA/SCL из абстрактного описания
транзакции (start / byte / stop) хелпером make_i2c_wave и проверяем, что
декодер восстанавливает события шины, значения байтов и флаги ACK/NACK.
"""
import numpy as np
import pytest

from hantek_dso2d15.waveform.decode_i2c import I2cSymbol, decode_i2c


THRESHOLD = 1.65  # середина между 0.0 и 3.3 В
PHASE = 10        # сэмплов на одну фазу состояния (такт SCL = 3 фазы = 30 сэмплов)
DT = 1e-7         # шаг времени (с)
VLO, VHI = 0.0, 3.3


# ---------------------------------------------------------------------------
# Хелпер генерации синтетической I2C-волны
# ---------------------------------------------------------------------------

def _expand(states, *, phase_samples=PHASE, dt=DT, vlo=VLO, vhi=VHI):
    """Развернуть список логических состояний (scl, sda) в (times, scl, sda)."""
    n = len(states) * phase_samples
    times = np.arange(n) * dt
    scl = np.empty(n, dtype=float)
    sda = np.empty(n, dtype=float)
    for idx, (s, d) in enumerate(states):
        lo = idx * phase_samples
        hi = lo + phase_samples
        scl[lo:hi] = vhi if s else vlo
        sda[lo:hi] = vhi if d else vlo
    return times, scl, sda


def make_i2c_wave(tokens, *, idle_lead=5, idle_tail=5, **kw):
    """Построить (times, scl, sda) из списка токенов транзакции.

    Токены:
      ("start",)              — (повторный) START
      ("byte", value, ack)    — 8 бит MSB-first + ACK-такт (ack True=ACK/SDA низкий)
      ("stop",)               — STOP

    Тайминг стандартного I2C:
      бит: (SCL низкий, выставить SDA) → (SCL высокий, защёлка) → (SCL низкий)
      START: SDA 1→0 при высоком SCL; STOP: SDA 0→1 при высоком SCL.
    Все START (и первый, и повторный) генерируются одинаковой универсальной
    последовательностью, корректной как из покоя, так и внутри транзакции.
    """
    states = []

    def add(scl, sda, n=1):
        states.extend([(scl, sda)] * n)

    add(1, 1, idle_lead)  # ведущий покой: обе линии высокие
    for tok in tokens:
        kind = tok[0]
        if kind == "start":
            add(0, 1)   # SDA высокий при низком SCL
            add(1, 1)   # SCL высокий, SDA высокий
            add(1, 0)   # SDA падает при высоком SCL → START
            add(0, 0)   # SCL низкий
        elif kind == "byte":
            value, ack = tok[1], tok[2]
            for k in range(7, -1, -1):  # MSB-first
                b = (value >> k) & 1
                add(0, b)   # выставить бит при низком SCL
                add(1, b)   # SCL высокий → защёлка бита
                add(0, b)   # SCL низкий
            ackbit = 0 if ack else 1   # 0 = ACK, 1 = NACK
            add(0, ackbit)
            add(1, ackbit)
            add(0, ackbit)
        elif kind == "stop":
            add(0, 0)   # SDA низкий при низком SCL
            add(1, 0)   # SCL высокий, SDA низкий
            add(1, 1)   # SDA растёт при высоком SCL → STOP
            add(1, 1)   # покой
        else:
            raise ValueError(f"неизвестный токен: {kind}")
    add(1, 1, idle_tail)  # хвостовой покой
    return _expand(states, **kw)


# ---------------------------------------------------------------------------
# Запись в устройство: START, адрес W, байт данных, STOP
# ---------------------------------------------------------------------------

def test_write_transaction():
    tokens = [("start",), ("byte", 0xA0, True), ("byte", 0x3C, True), ("stop",)]
    times, scl, sda = make_i2c_wave(tokens)
    out = decode_i2c(times, sda, scl, threshold=THRESHOLD)

    assert all(isinstance(s, I2cSymbol) for s in out)
    assert [s.kind for s in out] == ["start", "address", "data", "stop"]

    start, addr, data, stop = out
    # адрес 0x50 W: (0x50 << 1) | 0 == 0xA0
    assert addr.value == 0xA0
    assert addr.ack is True
    assert data.value == 0x3C
    assert data.ack is True
    # start/stop не несут значения/ack
    for ev in (start, stop):
        assert ev.value is None
        assert ev.ack is None

    # символы упорядочены по времени
    starts = [s.start for s in out]
    assert starts == sorted(starts)
    # разумные границы события
    assert start.end >= start.start
    assert addr.end > addr.start


def test_byte_span_matches_clocks():
    """Границы байта — от первого до девятого фронта SCL (8 тактовых периодов)."""
    tokens = [("start",), ("byte", 0xA0, True), ("stop",)]
    times, scl, sda = make_i2c_wave(tokens)
    out = decode_i2c(times, sda, scl, threshold=THRESHOLD)
    addr = next(s for s in out if s.kind == "address")
    clock_period = 3 * PHASE * DT     # такт = 3 фазы
    assert addr.end - addr.start == pytest.approx(8 * clock_period, rel=0.1)


# ---------------------------------------------------------------------------
# NACK на последнем байте
# ---------------------------------------------------------------------------

def test_nack_last_byte():
    tokens = [("start",), ("byte", 0xA0, True), ("byte", 0x3C, False), ("stop",)]
    times, scl, sda = make_i2c_wave(tokens)
    out = decode_i2c(times, sda, scl, threshold=THRESHOLD)
    data = [s for s in out if s.kind == "data"]
    assert len(data) == 1
    assert data[0].value == 0x3C
    assert data[0].ack is False


# ---------------------------------------------------------------------------
# Чтение: младший бит адреса = 1 (R/W)
# ---------------------------------------------------------------------------

def test_read_address_rw_bit():
    addr_byte = (0x50 << 1) | 1   # 0xA1
    tokens = [("start",), ("byte", addr_byte, True), ("byte", 0x7E, True), ("stop",)]
    times, scl, sda = make_i2c_wave(tokens)
    out = decode_i2c(times, sda, scl, threshold=THRESHOLD)
    addr = next(s for s in out if s.kind == "address")
    assert addr.value == 0xA1
    assert addr.value & 1 == 1


# ---------------------------------------------------------------------------
# Несколько байт данных подряд
# ---------------------------------------------------------------------------

def test_multiple_data_bytes():
    payload = [0x11, 0x22, 0x33, 0x00, 0xFF]
    tokens = [("start",), ("byte", 0xA0, True)]
    tokens += [("byte", v, True) for v in payload]
    tokens += [("stop",)]
    times, scl, sda = make_i2c_wave(tokens)
    out = decode_i2c(times, sda, scl, threshold=THRESHOLD)

    assert [s.kind for s in out] == (
        ["start", "address"] + ["data"] * len(payload) + ["stop"]
    )
    data_vals = [s.value for s in out if s.kind == "data"]
    assert data_vals == payload
    assert all(s.ack is True for s in out if s.kind == "data")


# ---------------------------------------------------------------------------
# Повторный START внутри транзакции
# ---------------------------------------------------------------------------

def test_repeated_start():
    tokens = [
        ("start",),
        ("byte", 0xA0, True),   # адрес W
        ("byte", 0x10, True),   # data (напр. регистр)
        ("start",),             # repeated START
        ("byte", 0xA1, True),   # адрес R
        ("byte", 0x55, False),  # data, NACK (конец чтения)
        ("stop",),
    ]
    times, scl, sda = make_i2c_wave(tokens)
    out = decode_i2c(times, sda, scl, threshold=THRESHOLD)

    assert [s.kind for s in out] == [
        "start", "address", "data", "start", "address", "data", "stop",
    ]
    starts = [s for s in out if s.kind == "start"]
    assert len(starts) == 2
    addrs = [s for s in out if s.kind == "address"]
    assert [a.value for a in addrs] == [0xA0, 0xA1]
    last_data = [s for s in out if s.kind == "data"][-1]
    assert last_data.value == 0x55
    assert last_data.ack is False


# ---------------------------------------------------------------------------
# Граничные случаи
# ---------------------------------------------------------------------------

def test_empty_input():
    assert decode_i2c(np.array([]), np.array([]), np.array([]),
                      threshold=THRESHOLD) == []


def test_idle_only_no_start():
    # только покой — обе линии высокие, никаких событий
    times, scl, sda = make_i2c_wave([], idle_lead=30, idle_tail=0)
    assert decode_i2c(times, sda, scl, threshold=THRESHOLD) == []


def test_scl_clock_without_start():
    """SCL тактирует, но SDA статичен (нет START) → []."""
    states = [(1, 1)] * 5
    for _ in range(8):
        states += [(0, 1), (1, 1)]   # SCL качается, SDA всегда высокий
    states += [(1, 1)] * 5
    times, scl, sda = _expand(states)
    assert decode_i2c(times, sda, scl, threshold=THRESHOLD) == []


def test_truncated_byte_not_emitted():
    """Обрыв посреди байта: START распознан, неполный байт не эмитится как data."""
    tokens = [("start",), ("byte", 0xA0, True), ("byte", 0x3C, True), ("stop",)]
    times, scl, sda = make_i2c_wave(tokens, idle_tail=0)
    # обрезать так, чтобы второй байт не успел защёлкнуться целиком
    cut = int(len(times) * 0.55)
    times, scl, sda = times[:cut], scl[:cut], sda[:cut]
    out = decode_i2c(times, sda, scl, threshold=THRESHOLD)
    assert isinstance(out, list)
    assert [s.kind for s in out][:2] == ["start", "address"]
    # ни одного полного второго data-байта и никакого STOP не появилось
    assert not any(s.kind == "stop" for s in out)


def test_returns_list_type():
    tokens = [("start",), ("byte", 0xA0, True), ("stop",)]
    times, scl, sda = make_i2c_wave(tokens)
    out = decode_i2c(times, sda, scl, threshold=THRESHOLD)
    assert isinstance(out, list)
