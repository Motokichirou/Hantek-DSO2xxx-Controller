# Waveform-декодер (Layer 3) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:test-driven-development. Оркестрация — по `CLAUDE.md` (оркестратор-режим): file-disjoint юниты, ревью каждого diff, интеграция за архитектором.

**Goal:** Декодер `:WAVeform:DATA:ALL?` — из сырых пакетов прибора в NumPy-массивы вольт + ось времени. Узловой риск §5 (кодировка/масштаб сэмплов) **уже разрешён на железе** — см. фикстуры и «Формат» ниже.

**Architecture:** Чистые функции (байты → counts → вольты), без SCPI внутри. Чанковый ридер поверх абстрактного `Transport` (тестируется через `FakeTransport` реплеем реальных кадров). Фасад собирает кадр + масштабы каналов в декодированный результат.

**Tech Stack:** Python 3.14, NumPy, pytest, `.venv`.

## Global Constraints

- **Формат — HARDWARE-VERIFIED** (петля DDS→CH1, 2026-06-27). Все индексы/формулы ниже — выверены на реальном приборе и на фикстурах `tests/fixtures/waveform/` (см. `FIXTURES.md`). НЕ менять без нового замера на железе.
- Frozen reference §7 даёт байт-раскладку с OCR-неточностями: voltage-поля по 8 символов (не 7) → enable/srate сдвинуты на +4. **В коде — выверенные индексы из этого плана**, frozen reference не трогаем.
- Сэмпл = **signed int8** (`np.frombuffer(payload, dtype=np.int8)`). `COUNTS_PER_DIV = 25`.
- Декодер НЕ шлёт SCPI и не знает про прибор: Vдел/offset/srate приходят аргументами (их добудет engine через scpi-драйвер).
- Тесты: синтетика (точные) + реальные фикстуры (с допуском ±0.1В). Запуск: `.venv/Scripts/python.exe -m pytest tests/waveform -q`.

---

## Формат `:WAVeform:DATA:ALL?` (контракт, выверен на железе)

**Пакетный поток:** каждый запрос `:WAVeform:DATA:ALL?` + `transport.read_raw()` → один пакет:
- Префикс 29 байт ASCII: `#9`(2) + `pkt_len`[2:11] + `total`[11:20] + `uploaded`[20:29].
- HEADER-пакет: `len(raw)==128`, payload `raw[29:128]` = метаданные.
- DATA-пакет: `len(raw)>128`, payload `raw[29:]` = `points` сэмплов signed int8, ОДИН канал.

**Кадр:** HEADER, затем по одному DATA-пакету на каждый включённый канал (по возрастанию CH1→CH2…). Читать DATA пока `uploaded < total`. `total = N_кан × points + 99`.

**Header-поля (абсолютные индексы):** running[29], trig[30], chNoff[31+4k:35+4k] (signed counts, k=0..3), enable[79:83] ('1'/'0' поканально CH1..CH4), srate[83:92] (float). *(Подробнее — `tests/fixtures/waveform/FIXTURES.md`.)*

**Калибровка:** `volts = sample_int8 × (Vдел / 25) − offset_volts`; `t[i] = i / srate`.

---

## Структура файлов

| Файл | Ответственность |
|---|---|
| `hantek_dso2d15/waveform/__init__.py` | реэкспорт (архитектор на интеграции) |
| `hantek_dso2d15/waveform/packet.py` | парсинг IEEE-обёртки пакета (`parse_packet`, `is_header`) |
| `hantek_dso2d15/waveform/header.py` | парсинг метаданных header (`parse_header` → `WaveHeader`) |
| `hantek_dso2d15/waveform/convert.py` | `COUNTS_PER_DIV`, `counts_to_volts`, `time_axis` (NumPy) |
| `hantek_dso2d15/waveform/reader.py` | `WaveformReader(transport).read_frame()` — чанковый сбор кадра |
| `hantek_dso2d15/waveform/decode.py` | `decode_frame(...)` — фасад: кадр+масштабы → вольты/время |
| `tests/waveform/test_*.py` | по модулю |
| `scripts/hw_smoke_waveform.py` | hardware-smoke (петля DDS→CH1) |

**Волны (file-disjoint):** W1 `packet`, W2 `header`, W3 `convert` — параллельно. W4 `reader` (зависит W1,W2). W5 `decode` (зависит W3,W4). Интеграция: реэкспорт `__init__`, полный pytest, hardware-smoke.

Исполнители НЕ трогают `__init__.py` и не коммитят. Импорт из конкретных подмодулей.

---

## Task W1: packet.py — IEEE-обёртка

**Files:** Create `hantek_dso2d15/waveform/packet.py`, `tests/waveform/test_packet.py`.

**Produces:**
- `HEADER_LEN = 128`.
- `@dataclass class Packet: pkt_len:int; total:int; uploaded:int; payload:bytes`.
- `parse_packet(raw: bytes) -> Packet` — проверить `raw[:2]==b"#9"` (иначе `ValueError`); `pkt_len=int(raw[2:11])`, `total=int(raw[11:20])`, `uploaded=int(raw[20:29])`, `payload=raw[29:]`.
- `is_header(raw: bytes) -> bool` — `len(raw)==HEADER_LEN`.

**Acceptance:**
- Синтетика: `raw = b"#9" + b"000000040" + b"000000099" + b"000000040" + b"\x01\x02..."` → `parse_packet` даёт pkt_len=40,total=99,uploaded=40,payload=байты после 29.
- На реальной фикстуре `frame_dc_p1v0_ch1.pkt1.bin`: pkt_len=4029, total=4099, uploaded=99, `len(payload)==4000`.
- `is_header(open('frame_dc_p1v0_ch1.pkt0.bin').read()) is True`; для `.pkt1.bin` — False.
- `parse_packet(b"XX...")` (нет `#9`) → `ValueError`.

- [ ] TDD: тест→FAIL→реализация→PASS. Commit: `feat(waveform): packet framing parser`.

---

## Task W2: header.py — метаданные

**Files:** Create `hantek_dso2d15/waveform/header.py`, `tests/waveform/test_header.py`.

**Produces:**
- `@dataclass class WaveHeader: running:bool; triggered:bool; offsets_counts:list[int]; enabled_channels:list[int]; srate:float`.
- `parse_header(raw: bytes) -> WaveHeader`:
  - `running = raw[29:30]==b"1"`; `triggered = raw[30:31]==b"1"`.
  - `offsets_counts = [int(raw[31+4*k:35+4*k]) for k in range(4)]` (signed; `int(b"-025")==-25`).
  - `enable = raw[79:83].decode("latin1")`; `enabled_channels = [k+1 for k,c in enumerate(enable) if c=="1"]`.
  - `srate = float(raw[83:92])`.

**Acceptance (реальные фикстуры):**
- `frame_dc_p1v0_ch1.pkt0.bin` → enabled_channels==[1], srate==1250000.0, offsets_counts[0]==0, triggered==False.
- `frame_dc_p1v0_ch1ch2.pkt0.bin` → enabled_channels==[1,2], srate==1250000.0.
- Синтетика: header с enable="1100" → [1,2]; "1000" → [1]; offsets с "-025" → -25.

- [ ] TDD. Commit: `feat(waveform): header metadata parser`.

---

## Task W3: convert.py — counts→вольты, время

**Files:** Create `hantek_dso2d15/waveform/convert.py`, `tests/waveform/test_convert.py`.

**Produces:**
- `COUNTS_PER_DIV = 25.0`.
- `counts_to_volts(samples, vdiv: float, offset_volts: float = 0.0) -> np.ndarray`:
  - `samples` может быть `bytes`/`bytearray` (тогда `np.frombuffer(samples, dtype=np.int8)`) или `np.ndarray`.
  - вернуть `arr.astype(np.float64) * (vdiv / COUNTS_PER_DIV) - offset_volts`.
- `time_axis(n: int, srate: float) -> np.ndarray` → `np.arange(n) / srate`.

**Acceptance:**
- `counts_to_volts(np.array([25,-25,0], dtype=np.int8), 1.0, 0.0)` → `[1.0,-1.0,0.0]` (точно).
- `counts_to_volts(np.array([25],dtype=np.int8), 2.0, 0.0)` → `[2.0]`.
- offset: `counts_to_volts(np.array([38],dtype=np.int8), 2.0, 2.0)` → `[38*2/25-2]=[1.04]`.
- bytes-вход: `counts_to_volts(bytes([25, 256-25]), 1.0)` → `[1.0,-1.0]` (256-25=231 → int8 -25).
- `time_axis(4, 1.25e6)` → `[0, 8e-7, 1.6e-6, 2.4e-6]`.
- Реальная фикстура `frame_dc_p1v0_ch1.pkt1.bin`: `mean(counts_to_volts(payload[29:]... )` wait — payload уже без префикса; взять `parse_packet(...).payload`, vdiv=1.0 → `abs(mean - 1.0) < 0.1`.

- [ ] TDD. Commit: `feat(waveform): counts-to-volts conversion`.

---

## Task W4: reader.py — чанковый сбор кадра

**Files:** Create `hantek_dso2d15/waveform/reader.py`, `tests/waveform/test_reader.py`.

**Consumes:** `packet` (W1), `header` (W2), `Transport` (для типа). **Produces:**
- `@dataclass class RawFrame: header: WaveHeader; data_payloads: list[bytes]` (по payload на канал, в порядке enabled_channels).
- `class WaveformReader`:
  - `__init__(self, transport)`.
  - `read_frame(self, max_packets: int = 64) -> RawFrame`:
    1. Синхронизация: слать `:WAVeform:DATA:ALL?` + `read_raw()`, пока не придёт header-пакет (`is_header`). Парсить `parse_header`.
    2. Затем слать/читать DATA-пакеты; для каждого `parse_packet`, накапливать `payload`, пока `uploaded < total` (`total` из первого header-пакета: его `parse_packet(...).total`).
    3. Вернуть `RawFrame(header, data_payloads)`.
  - Защита от зацикливания: не более `max_packets` итераций (иначе `RuntimeError`).

**Acceptance (FakeTransport реплей реальных кадров):**
- Загрузить `frame_dc_p1v0_ch1.pkt0.bin`,`.pkt1.bin`; `FakeTransport.set_raw(pkt0, pkt1, pkt0, pkt1, ...)` (queue), `transport.open()`. `read_frame()` → header.enabled_channels==[1], len(data_payloads)==1, len(data_payloads[0])==4000.
- `frame_dc_p1v0_ch1ch2.pkt0..2` → enabled_channels==[1,2], len(data_payloads)==2, обе по 4000.
- Синхронизация: если очередь начинается с data-пакета до header — ридер пропускает его и находит header.
- `:WAVeform:DATA:ALL?` действительно записан в `transport.writes`.

- [ ] TDD. Commit: `feat(waveform): chunked frame reader`.

---

## Task W5: decode.py — фасад

**Files:** Create `hantek_dso2d15/waveform/decode.py`, `tests/waveform/test_decode.py`.

**Consumes:** `convert` (W3), `reader`/`RawFrame` (W4), `header`. **Produces:**
- `@dataclass class DecodedFrame: time: np.ndarray; channels: dict[int, np.ndarray]; srate: float; triggered: bool`.
- `decode_frame(frame: RawFrame, scales: dict[int, float], offsets: dict[int, float] | None = None) -> DecodedFrame`:
  - `offsets` default — нули.
  - для i, ch in enumerate(frame.header.enabled_channels): `channels[ch] = counts_to_volts(frame.data_payloads[i], scales[ch], (offsets or {}).get(ch, 0.0))`.
  - `time = time_axis(len(первого канала), frame.header.srate)`.
  - `srate`, `triggered` — из header.

**Acceptance:**
- Построить `RawFrame` из `frame_dc_p1v0_ch1` (через `WaveformReader`+FakeTransport или вручную) → `decode_frame(frame, {1:1.0})`: `abs(mean(channels[1]) - 1.0) < 0.1`, `len(time)==4000`, `time[1]==1/1.25e6`, `triggered is False`.
- 2 канала `frame_dc_p1v0_ch1ch2`, `scales={1:1.0,2:1.0}` → `set(channels)=={1,2}`, `abs(mean(channels[1])-1.0)<0.1`.
- offset: задать `offsets={1:0.5}` → среднее сместится на −0.5 относительно базового.

- [ ] TDD. Commit: `feat(waveform): decode facade`.

---

## Task W6: hardware-smoke + интеграция

**Files:** Create `scripts/hw_smoke_waveform.py`. (Запускает пользователь; петля DDS→CH1.)

Скрипт: connect; CH1 1В/дел off=0 DC probe=1; DDS DC +1.0В → `WaveformReader.read_frame` + `decode_frame({1: scale})` → проверить `mean(CH1) ≈ +1.0В` (±0.1); DDS меандр 2Vpp 1кГц → проверить два уровня ≈ ±1.0В; печать PASS/FAIL; DDS off; disconnect. Vдел/offset/srate берём из scpi-драйвера (`:SCALe?`, `:OFFSet?`, `:ACQuire:SRATe?`/header).

- [ ] Реэкспорт `waveform/__init__.py` (архитектор). Полный `pytest` зелёный. Прогон `hw_smoke_waveform.py` на железе. Commit.

---

## Self-Review (advisor)
- Покрытие: framing ✓, header(выверенные индексы) ✓, конверсия(int8,25cnt/div) ✓, чанковый ридер(многоканальный) ✓, фасад ✓, hardware-smoke ✓.
- File-disjoint по волнам; `__init__` не трогают исполнители.
- Калибровка — на реальных фикстурах + допуски на шум.
- Вне объёма: engine-цикл, gui, дробление 8M-захвата на множество чанков (здесь points=4000, один чанк/канал; большие глубины — отдельная проверка в engine-слое).
