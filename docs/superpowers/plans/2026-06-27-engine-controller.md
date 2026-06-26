# Engine-контроллер сбора (Layer 4a) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:test-driven-development. Оркестрация по `CLAUDE.md` (file-disjoint, ревью, интеграция за архитектором).

**Goal:** Контроллер сбора: тянет кадры с прибора (`WaveformReader`) → декодирует (`decode_frame`) → отдаёт в UI через Qt-сигналы из фонового потока. UI-поток никогда не блокируется VISA-I/O.

**Architecture:** Чистое ядро (`AcquisitionController`, без Qt) — полностью тестируется через `FakeTransport`. Тонкий Qt-слой (`EngineWorker(QObject)` + сигналы) — переносится в `QThread` слоем GUI. Управление сбором **host-side** (см. ниже).

**Tech Stack:** Python 3.14, PySide6 (QtCore), NumPy, pytest, `.venv`.

## Global Constraints

- **Управление сбором — host-side (HARDWARE-VERIFIED 2026-06-27):** `:RUN`/`:STOP`/`:SINGle` прибором молча игнорируются (running-байт всегда `1`, очереди ошибок нет). Управляем кадентностью опроса сами: Run = цикл тянет кадры; Stop = не тянем; Single = один кадр. `:TRIGger:SWEep {AUTO|NORMal|SINGle}` и `:TRIGger:FORCe` — документированы и работают.
- Декодер/драйвер уже готовы: `from hantek_dso2d15.waveform import WaveformReader, decode_frame, DecodedFrame`; `from hantek_dso2d15.scpi.scope import Scope`.
- Ядро `controller` НЕ импортирует Qt. Qt — только в `worker.py`.
- Тесты ядра — через `FakeTransport` (queued raw-кадры + readback scale/offset). Тест worker — через `QCoreApplication`, прямой вызов слота (без реальных потоков). Запуск: `.venv/Scripts/python.exe -m pytest tests/engine -q`.
- Исполнители НЕ трогают `__init__.py`, не коммитят, импортируют из конкретных подмодулей.

---

## Структура файлов

| Файл | Ответственность |
|---|---|
| `hantek_dso2d15/engine/__init__.py` | реэкспорт (архитектор) |
| `hantek_dso2d15/engine/states.py` | `RunState` enum (STOPPED/RUNNING/SINGLE) |
| `hantek_dso2d15/engine/controller.py` | `AcquisitionController` — чистое ядро (read+decode, force, sweep) |
| `hantek_dso2d15/engine/worker.py` | `EngineWorker(QObject)` — Qt-сигналы, слоты start/stop/single/capture_once |
| `tests/engine/test_*.py` | по модулю |
| `scripts/hw_smoke_engine.py` | hardware-smoke (worker в реальном QThread, fps) |

**Волны:** W1 `states` + W2 `controller` (параллельно). W3 `worker` (зависит states+controller). Интеграция: реэкспорт, полный pytest, hardware-smoke.

---

## Task E1: states.py

**Files:** Create `hantek_dso2d15/engine/states.py`, `tests/engine/test_states.py`.

**Produces:** `class RunState(enum.Enum): STOPPED = "stopped"; RUNNING = "running"; SINGLE = "single"`.

**Acceptance:** значения строковые как указано; `RunState("running") is RunState.RUNNING`; три члена.

- [ ] TDD. Commit: `feat(engine): add RunState enum`.

---

## Task E2: controller.py — чистое ядро сбора

**Files:** Create `hantek_dso2d15/engine/controller.py`, `tests/engine/test_controller.py`.

**Consumes:** `WaveformReader`, `decode_frame`, `DecodedFrame` из `hantek_dso2d15.waveform`; `Scope`/`FakeTransport` для тестов. **Produces:**
- `class AcquisitionController`:
  - `__init__(self, scope, reader, decoder=decode_frame)` — хранит ссылки.
  - `read_decoded_frame(self) -> DecodedFrame`:
    1. `frame = self.reader.read_frame()`.
    2. `chans = frame.header.enabled_channels`.
    3. `scales = {n: self.scope.channel[n].scale for n in chans}`; `offsets = {n: self.scope.channel[n].offset for n in chans}`.
    4. `return self.decoder(frame, scales, offsets)`.
  - `force(self) -> None` → `self.scope.trigger.force()`.
  - `set_sweep(self, mode: str) -> None` → `self.scope.trigger.sweep = mode`.

**Acceptance (FakeTransport):**
- Загрузить реальные пакеты `tests/fixtures/waveform/frame_dc_p1v0_ch1.pkt0/pkt1` через `set_raw`; `set_response(":CHANnel1:SCALe?", "1.000000e+00")`, `set_response(":CHANnel1:OFFSet?", "0.000000e+00")`; `transport.open()`. `Scope(transport)` + `WaveformReader(transport)` + controller. `read_decoded_frame()` → `DecodedFrame`, `set(channels)=={1}`, `abs(mean(channels[1]) - 1.0) < 0.1`.
- 2 канала `frame_dc_p1v0_ch1ch2` + readback scale/offset для CH1,CH2 → `set(channels)=={1,2}`.
- `force()` → в `transport.writes` есть `":TRIGger:FORCe"`.
- `set_sweep("NORMal")` → в writes `":TRIGger:SWEep NORMal"`.

- [ ] TDD. Commit: `feat(engine): add AcquisitionController core`.

---

## Task E3: worker.py — Qt-обёртка

**Files:** Create `hantek_dso2d15/engine/worker.py`, `tests/engine/test_worker.py`.

**Consumes:** `AcquisitionController` (E2), `RunState` (E1), PySide6.QtCore. **Produces:**
- `class EngineWorker(QObject)`:
  - Сигналы: `frameReady = Signal(object)` (DecodedFrame); `errorOccurred = Signal(str)`; `stateChanged = Signal(object)` (RunState).
  - `__init__(self, controller, interval_ms: int = 50, parent=None)`: создать `QTimer(self)` с `interval_ms`, `timeout` → `self.capture_once`. `_state = RunState.STOPPED`.
  - `state` — `@property -> RunState`.
  - `@Slot() start(self)`: `_state=RUNNING`; `timer.start()`; `stateChanged.emit(_state)`.
  - `@Slot() stop(self)`: `_state=STOPPED`; `timer.stop()`; `stateChanged.emit(_state)`.
  - `@Slot() single(self)`: `_state=SINGLE`; `stateChanged.emit(_state)`; `capture_once()`.
  - `@Slot() capture_once(self)`: `try: frame=controller.read_decoded_frame(); frameReady.emit(frame)` `except Exception as e: errorOccurred.emit(str(e))`. Если после захвата `_state is RunState.SINGLE` → вызвать `stop()`.

**Acceptance (QCoreApplication; прямой вызов, без реальных потоков):**
- В тесте: `app = QCoreApplication.instance() or QCoreApplication([])`. Фейковый/настоящий controller со `stub`-кадром (можно настоящий controller на FakeTransport, как в E2). Подключить `frameReady` к `lambda f: captured.append(f)`. `worker.capture_once()` → `len(captured)==1`, элемент — `DecodedFrame`.
- `single()` → ровно один `frameReady`, итоговое `worker.state is RunState.STOPPED`, и `stateChanged` испускался.
- Ошибка: controller, бросающий исключение (stub) → `errorOccurred` испущен, `frameReady` НЕ испущен.
- `start()` → `state is RUNNING`; `stop()` → `state is STOPPED` (таймер не обязателен в тесте — проверяем состояние/сигналы).

> Для теста можно сделать лёгкий stub-controller с методом `read_decoded_frame()` (возвращает заранее заданный `DecodedFrame` или бросает) — НЕ обязательно гонять реальный поток/таймер.

- [ ] TDD. Commit: `feat(engine): add EngineWorker (Qt)`.

---

## Task E4: hardware-smoke + интеграция

**Files:** Create `scripts/hw_smoke_engine.py`.

Скрипт: connect; настроить CH1 (петля DDS), DDS меандр 2Vpp 1кГц; создать `AcquisitionController` + `EngineWorker`, перенести worker в реальный `QThread`; `start()`; собрать ~30 кадров через слот на `frameReady` (с `QCoreApplication` event-loop и таймаутом ~5с); посчитать fps и проверить, что CH1 Vpp ≈ 2В на нескольких кадрах; `stop()`; аккуратно завершить поток; disconnect. Печать fps + PASS/FAIL.

- [ ] Реэкспорт `engine/__init__.py` (архитектор): `RunState`, `AcquisitionController`, `EngineWorker`. Полный `pytest` зелёный. Прогон `hw_smoke_engine.py` на железе (петля DDS). Commit.

---

## Self-Review (advisor)
- Ядро `controller` тестируется без Qt (FakeTransport) ✓; Qt-слой тонкий, тест через прямой вызов слота ✓.
- Управление сбором host-side (учтён hardware-вывод про :RUN/:STOP) ✓.
- File-disjoint; `__init__` не трогают исполнители.
- Вне объёма: GUI (Layer 4b — следующий план), глубокие захваты 8M (chunk-loop ридера уже поддерживает uploaded<total; нагрузочную проверку — в gui/engine позже), измерения/math/курсоры/dds-панель/io.
