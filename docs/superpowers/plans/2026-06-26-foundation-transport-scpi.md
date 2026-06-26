# Фундамент: transport + ядро scpi — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:test-driven-development для каждой задачи. Шаги отмечены чекбоксами (`- [ ]`). Оркестрация — по `CLAUDE.md` (оркестратор-режим): исполнители пишут file-disjoint юниты, ревьюер проверяет каждый diff, интеграция — за архитектором.

**Goal:** Дать типизированный, протестированный без железа драйвер: транспорт (PyVISA + FakeTransport) и ядро SCPI-подсистем (channel/timebase/acquire/trigger-edge + scope-фасад). Без GUI.

**Architecture:** Слоистая (spec §4). Всё выше транспорта зависит только от абстрактного `Transport`, не от PyVISA. Подсистемы SCPI — тонкие типизированные обёртки 1:1 с frozen reference: сеттер валидирует клиентски и пишет команду, геттер читает readback. У прибора нет `SYSTem:ERRor?` — валидация только клиентская.

**Tech Stack:** Python 3.14 (venv `.venv/`) · PyVISA · NumPy · pytest. (PySide6/pyqtgraph/h5py — в последующих планах.)

## Global Constraints

- **Frozen reference:** строки SCPI — дословно из `docs/scpi-command-reference.md`. Не выдумывать, не «исправлять» опечатки (`RISIng`, `EDGe`, `EXT/10`). Этот план уже содержит выверенную карту литералов (§ «Карта команд») — брать оттуда.
- **Пакет:** `hantek_dso2d15` (импортируемый из корня репо).
- **Нет очереди ошибок прибора** → клиентская валидация по enum/наборам + readback; out-of-range прибор зажимает сам (диапазоны вольт/времени НЕ хардкодим — где мануал границ не даёт, не валидируем, полагаемся на readback).
- **Формат чисел (NR3):** отправка через `fmt_num(v) = f"{float(v):g}"`.
- **Bool:** на прибор шлём `ON`/`OFF`; ответы парсим из `{0,1,ON,OFF}` (регистронезависимо).
- **Тесты — через `FakeTransport`**, без железа. Hardware-smoke (Задача 10) запускает пользователь на приборе.
- Запуск тестов: `.venv/Scripts/python.exe -m pytest -q`.

---

## Карта команд (frozen — копия из reference, единственный источник для исполнителей)

| Свойство (Python) | SET | QUERY | Параметр / enum | Парсинг ответа |
|---|---|---|---|---|
| `channel[n].scale` | `:CHANnel{n}:SCALe {v}` | `:CHANnel{n}:SCALe?` | float (V/дел) | `float` |
| `channel[n].offset` | `:CHANnel{n}:OFFSet {v}` | `:CHANnel{n}:OFFSet?` | float (V) | `float` |
| `channel[n].coupling` | `:CHANnel{n}:COUPling {v}` | `:CHANnel{n}:COUPling?` | `AC\|DC\|GND` | enum |
| `channel[n].probe` | `:CHANnel{n}:PROBe {v}` | `:CHANnel{n}:PROBe?` | `1\|10\|100\|1000` | `int(float(resp))` |
| `channel[n].bwlimit` | `:CHANnel{n}:BWLimit {ON/OFF}` | `:CHANnel{n}:BWLimit?` | bool | `parse_bool` |
| `channel[n].display` | `:CHANnel{n}:DISPlay {ON/OFF}` | `:CHANnel{n}:DISPlay?` | bool | `parse_bool` |
| `channel[n].invert` | `:CHANnel{n}:INVert {ON/OFF}` | `:CHANnel{n}:INVert?` | bool | `parse_bool` |
| `channel[n].vernier` | `:CHANnel{n}:VERNier {ON/OFF}` | `:CHANnel{n}:VERNier?` | bool | `parse_bool` |
| `timebase.scale` | `:TIMebase:SCALe {v}` | `:TIMebase:SCALe?` | float (с/дел) | `float` |
| `timebase.position` | `:TIMebase:POSition {v}` | `:TIMebase:POSition?` | float (с) | `float` |
| `timebase.range` | `:TIMebase:RANGe {v}` | `:TIMebase:RANGe?` | float (с) | `float` |
| `timebase.mode` | `:TIMebase:MODE {v}` | `:TIMebase:MODE?` | `MAIN\|XY\|ROLL` | enum |
| `timebase.window.enable` | `:TIMebase:WINDow:ENABle {ON/OFF}` | `:TIMebase:WINDow:ENABle?` | bool | `parse_bool` |
| `timebase.window.scale` | `:TIMebase:WINDow:SCALe {v}` | `:TIMebase:WINDow:SCALe?` | float | `float` |
| `timebase.window.position` | `:TIMebase:WINDow:POSition {v}` | `:TIMebase:WINDow:POSition?` | float | `float` |
| `acquire.points` | `:ACQuire:POINts {v}` | `:ACQuire:POINts?` | `4000\|40000\|400000\|4000000\|8000000` | `int(float(resp))` |
| `acquire.type` | `:ACQuire:TYPE {v}` | `:ACQuire:TYPE?` | `NORMal\|AVERage\|PEAK\|HRESolution` | enum |
| `acquire.count` | `:ACQuire:COUNt {v}` | `:ACQuire:COUNt?` | `4\|8\|16\|32\|64\|128` | `int(float(resp))` |
| `acquire.srate` (R/O) | — | `:ACQuire:SRATe?` | float (Sa/s) | `float` |
| `trigger.mode` | `:TRIGger:MODE {v}` | `:TRIGger:MODE?` | см. `Trigger.MODES` | enum |
| `trigger.sweep` | `:TRIGger:SWEep {v}` | `:TRIGger:SWEep?` | `AUTO\|NORMal\|SINGle` | enum |
| `trigger.holdoff` | `:TRIGger:HOLDoff {v}` | `:TRIGger:HOLDoff?` | float (с) | `float` |
| `trigger.status` (R/O) | — | `:TRIGger:STATus?` | `TRIGed\|NOTRIG` | raw `str.strip()` |
| `trigger.force()` | `:TRIGger:FORCe` | — | — | — |
| `trigger.edge.source` | `:TRIGger:EDGe:SOURce {v}` | `:TRIGger:EDGe:SOURce?` | `CHANnel1..4\|EXT/10` | enum |
| `trigger.edge.slope` | `:TRIGger:EDGe:SLOPe {v}` | `:TRIGger:EDGe:SLOPe?` | `RISIng\|FALLing\|EITHer` | enum |
| `trigger.edge.level` | `:TRIGger:EDGe:LEVel {v}` | `:TRIGger:EDGe:LEVel?` | float (V) | `float` |
| `scope.idn()` | — | `*IDN?` | — | raw `str.strip()` |

`Trigger.MODES = ("EDGE","PULSe","TV","SLOPe","TIMeout","WINdow","PATTern","INTerval","UNDerthrow","UART","LIN","CAN","SPI","IIC")` (дословно из reference §4.1).

Замечания по литералам (НЕ нормализовать): `EDGe` (не EDGE) в подкомандах edge; `RISIng` (заглавная I); `EXT/10` со слешем; `SCALe/POSition/SWEep/HOLDoff/FORCe` — как в таблице.

---

## Структура файлов (этот план)

| Файл | Ответственность |
|---|---|
| `pyproject.toml` | Метаданные пакета `hantek_dso2d15`, зависимости, конфиг pytest |
| `hantek_dso2d15/__init__.py` | Версия пакета |
| `hantek_dso2d15/transport/__init__.py` | Реэкспорт `Transport`, `FakeTransport`, `VisaTransport` |
| `hantek_dso2d15/transport/base.py` | ABC `Transport` |
| `hantek_dso2d15/transport/fake_transport.py` | `FakeTransport` (скриптуемый дубль) |
| `hantek_dso2d15/transport/visa_transport.py` | `VisaTransport` (обёртка PyVISA) |
| `hantek_dso2d15/scpi/__init__.py` | Реэкспорт `Scope` и подсистем |
| `hantek_dso2d15/scpi/validation.py` | `validate_enum/validate_choice/parse_bool/bool_arg/fmt_num` |
| `hantek_dso2d15/scpi/channel.py` | `Channel` |
| `hantek_dso2d15/scpi/timebase.py` | `Timebase`, `TimebaseWindow` |
| `hantek_dso2d15/scpi/acquire.py` | `Acquire` |
| `hantek_dso2d15/scpi/trigger.py` | `Trigger`, `TriggerEdge` |
| `hantek_dso2d15/scpi/scope.py` | `Scope`, `ChannelCollection` |
| `tests/...` | По одному тест-модулю на каждый юнит |
| `scripts/hw_smoke_foundation.py` | Hardware-smoke (запускает пользователь на приборе) |

**Граф зависимостей / волны сборки (file-disjoint внутри волны):**
- Волна 0 — Задача 1: scaffold (pyproject, `__init__`, пакетные каталоги).
- Волна 1 — Задачи 2 (`base.py`), 3 (`validation.py`) — независимы, параллельно.
- Волна 2 — Задачи 4 (`fake_transport.py`), 9 (`visa_transport.py`) — зависят от `base.py`, параллельно.
- Волна 3 — Задачи 5 (`channel`), 6 (`timebase`), 7 (`acquire`), 8 (`trigger`) — зависят от `validation` + `FakeTransport` (для тестов), параллельно, file-disjoint.
- Волна 4 — Задача 8.5 (`scope.py`) — зависит от всех подсистем.
- Волна 5 — Задача 10 (hardware-smoke скрипт) + интеграция (полный pytest).

---

## Task 1: Scaffold пакета

**Files:** Create `pyproject.toml`, `hantek_dso2d15/__init__.py`, `hantek_dso2d15/transport/__init__.py`, `hantek_dso2d15/scpi/__init__.py`, `tests/__init__.py`, `tests/test_smoke.py`.

**Interfaces — Produces:** импортируемый пакет `hantek_dso2d15` с `__version__: str`. `__init__.py` подсистем поначалу пустые (реэкспорты добавят соответствующие задачи).

- [ ] **Шаг 1.** `pyproject.toml`: `[project] name="hantek-dso2d15"`, `version="0.0.1"`, `requires-python=">=3.11"`, `dependencies=["pyvisa","numpy"]`, `[project.optional-dependencies] test=["pytest"]`. `[tool.pytest.ini_options] testpaths=["tests"]`, `addopts="-q"`. Сборка через setuptools (`[build-system]`), `packages=["hantek_dso2d15", ...]` или `find`.
- [ ] **Шаг 2.** `hantek_dso2d15/__init__.py` → `__version__ = "0.0.1"`. Пустые `transport/__init__.py`, `scpi/__init__.py`, `tests/__init__.py`.
- [ ] **Шаг 3.** `tests/test_smoke.py`: `def test_package_imports(): import hantek_dso2d15; assert hantek_dso2d15.__version__`.
- [ ] **Шаг 4.** Прогнать `.venv/Scripts/python.exe -m pytest -q`. Ожидание: 1 passed.
- [ ] **Шаг 5.** Commit: `feat: scaffold hantek_dso2d15 package`.

---

## Task 2: Transport ABC (`transport/base.py`)

**Files:** Create `hantek_dso2d15/transport/base.py`, `tests/transport/test_base.py`.

**Interfaces — Produces:** абстрактный класс `Transport` (наследовать `abc.ABC`):
- `open(self) -> None`
- `close(self) -> None`
- `is_open` — `@property -> bool`
- `write(self, cmd: str) -> None`
- `query(self, cmd: str) -> str`
- `read_raw(self) -> bytes`

Все абстрактные. Назначение — единственная граница к I/O; всё выше зависит только от него.

- [ ] **Шаг 1.** Тест: попытка инстанцировать `Transport()` напрямую → `TypeError` (абстрактный). Под-класс-заглушка, реализующий все методы, инстанцируется успешно.
- [ ] **Шаг 2.** Прогнать тест — FAIL (нет модуля).
- [ ] **Шаг 3.** Реализовать ABC с `@abstractmethod`.
- [ ] **Шаг 4.** Тест — PASS.
- [ ] **Шаг 5.** Commit: `feat(transport): add Transport ABC`.

---

## Task 3: Validation helpers (`scpi/validation.py`)

**Files:** Create `hantek_dso2d15/scpi/validation.py`, `tests/scpi/test_validation.py`.

**Interfaces — Produces:**
- `validate_enum(value, allowed: tuple[str, ...], name: str) -> str` — регистронезависимое совпадение `str(value)` с элементом `allowed`; возвращает **каноничный литерал из `allowed`** (как в кортеже). Нет совпадения → `ValueError` с именем и списком.
- `validate_choice(value, allowed: tuple, name: str) -> value` — точное членство (для числовых наборов: probe/points/count). Нет → `ValueError`.
- `parse_bool(resp: str) -> bool` — `strip().upper()`; `{"1","ON"}→True`, `{"0","OFF"}→False`; иначе `ValueError`.
- `bool_arg(value) -> str` — `bool`/`int` → `"ON"`/`"OFF"`; строки `{"ON","1"}→"ON"`, `{"OFF","0"}→"OFF"` (регистронезависимо); прочие строки → `ValueError`.
- `fmt_num(value) -> str` — `f"{float(value):g}"`.

**Acceptance (тест-кейсы, минимум):**
- `validate_enum("dc", ("AC","DC","GND"), "coupling") == "DC"` (каноникализация регистра).
- `validate_enum("RISIng", ("RISIng","FALLing","EITHer"), "slope") == "RISIng"`.
- `validate_enum("ext/10", ("CHANnel1","EXT/10"), "src") == "EXT/10"`.
- `validate_enum("XX", (...), "c")` → `ValueError`.
- `validate_choice(10, (1,10,100,1000), "probe") == 10`; `validate_choice(7, (...), "probe")` → `ValueError`.
- `parse_bool("1") is True`, `parse_bool("OFF") is False`, `parse_bool("ON ") is True`, `parse_bool("x")` → `ValueError`.
- `bool_arg(True)=="ON"`, `bool_arg(0)=="OFF"`, `bool_arg("off")=="OFF"`, `bool_arg("maybe")` → `ValueError`.
- `fmt_num(5e-4)=="0.0005"`, `fmt_num(1.0)=="1"`, `fmt_num(0.5)=="0.5"`.

- [ ] **Шаг 1.** Написать тесты по списку выше. **Шаг 2.** FAIL. **Шаг 3.** Реализовать. **Шаг 4.** PASS. **Шаг 5.** Commit: `feat(scpi): add validation helpers`.

---

## Task 4: FakeTransport (`transport/fake_transport.py`)

**Files:** Create `hantek_dso2d15/transport/fake_transport.py`, `tests/transport/test_fake_transport.py`.

**Interfaces — Consumes:** `Transport` (Задача 2). **Produces:** `FakeTransport(Transport)`:
- `writes: list[str]`, `queries: list[str]` — публичные логи.
- `open()/close()`; `is_open -> bool` (изначально False).
- `write(cmd)` — если не открыт → `RuntimeError`; иначе `writes.append(cmd)`.
- `query(cmd)` — если не открыт → `RuntimeError`; `queries.append(cmd)`; вернуть ответ: сперва FIFO-очередь из `queue_response`, при пустой — фиксированный из `set_response`; если ни того ни другого → `KeyError(cmd)`.
- `set_response(cmd: str, value: str) -> None` — фиксированный ответ (возвращается всегда, когда очередь пуста).
- `queue_response(cmd: str, *values: str) -> None` — добавить значения в FIFO-очередь для `cmd`.
- `set_raw(*chunks: bytes) -> None` — заполнить очередь raw-чанков.
- `read_raw() -> bytes` — popleft из очереди raw; пусто → `IndexError`.
- `reset() -> None` — очистить `writes`, `queries` (ответы оставить).

**Acceptance (минимум):**
- write/query на закрытом → `RuntimeError`.
- После `open()`, `set_response(":X?","5")`, `query(":X?")=="5"` дважды; `queries==[":X?",":X?"]`.
- `queue_response(":Y?","a","b")`: query→"a", query→"b", затем падает на `set_response`/`KeyError`.
- `write(":Z 1")` → `writes==[":Z 1"]`.
- `set_raw(b"\x01", b"\x02")`: `read_raw()==b"\x01"`, затем `b"\x02"`, затем `IndexError`.

- [ ] **Шаг 1.** Тесты. **Шаг 2.** FAIL. **Шаг 3.** Реализовать (`collections.deque` для очередей). **Шаг 4.** PASS. **Шаг 5.** Commit: `feat(transport): add FakeTransport`.

---

## Task 5: Channel (`scpi/channel.py`)

**Files:** Create `hantek_dso2d15/scpi/channel.py`, `tests/scpi/test_channel.py`.

**Interfaces — Consumes:** `validation` (Задача 3), `FakeTransport` (для тестов). **Produces:** `Channel`:
- `Channel.COUPLINGS = ("AC","DC","GND")`, `Channel.PROBES = (1,10,100,1000)`.
- `__init__(self, transport, n: int)` — `validate_choice(n,(1,2,3,4),"channel")`, сохранить.
- Свойства по «Карте команд» (строки `channel[n].*`). Сеттер: валидация → `transport.write(...)`; геттер: `transport.query(...)` → парсинг.
- `scale/offset`: set `fmt_num`, get `float`. `coupling`: `validate_enum(COUPLINGS)`. `probe`: `validate_choice(PROBES)`, get `int(float(resp))`. `bwlimit/display/invert/vernier`: `bool_arg`/`parse_bool`.

**Acceptance (через FakeTransport, n=1; проверять и точную строку в `writes`, и парсинг ответа):**
- `ch.scale = 0.5` → `writes[-1]==":CHANnel1:SCALe 0.5"`.
- `set_response(":CHANnel1:SCALe?","5.000000e-01"); ch.scale == 0.5`.
- `ch.coupling = "dc"` → `":CHANnel1:COUPling DC"`; `set_response(...,"AC"); ch.coupling=="AC"`.
- `ch.probe = 10` → `":CHANnel1:PROBe 10"`; `set_response(...,"1.000000e+01"); ch.probe==10`.
- `ch.bwlimit = True` → `":CHANnel1:BWLimit ON"`; `set_response(...,"1"); ch.bwlimit is True`.
- `ch.coupling = "XX"` → `ValueError` (ничего не записано).
- `Channel(t, 5)` → `ValueError`.

- [ ] Шаги TDD 1–4 (тесты→FAIL→реализация→PASS). **Шаг 5.** Commit: `feat(scpi): add Channel subsystem`.

---

## Task 6: Timebase (`scpi/timebase.py`)

**Files:** Create `hantek_dso2d15/scpi/timebase.py`, `tests/scpi/test_timebase.py`.

**Interfaces — Consumes:** `validation`, `FakeTransport`. **Produces:**
- `TimebaseWindow(transport)`: `enable` (bool), `scale` (float), `position` (float) — строки `:TIMebase:WINDow:*` из карты.
- `Timebase(transport)`: в `__init__` создаёт `self.window = TimebaseWindow(transport)`; `MODES=("MAIN","XY","ROLL")`; свойства `scale/position/range` (float), `mode` (`validate_enum(MODES)`).

**Acceptance (минимум):**
- `tb.scale = 5e-4` → `":TIMebase:SCALe 0.0005"`.
- `tb.mode = "main"` → `":TIMebase:MODE MAIN"`; `set_response(":TIMebase:MODE?","XY"); tb.mode=="XY"`.
- `tb.window.enable = True` → `":TIMebase:WINDow:ENABle ON"`.
- `tb.window.scale = 1e-5` → `":TIMebase:WINDow:SCALe 1e-05"`.
- `tb.mode = "BAD"` → `ValueError`.

- [ ] Шаги TDD 1–4. **Шаг 5.** Commit: `feat(scpi): add Timebase subsystem`.

---

## Task 7: Acquire (`scpi/acquire.py`)

**Files:** Create `hantek_dso2d15/scpi/acquire.py`, `tests/scpi/test_acquire.py`.

**Interfaces — Consumes:** `validation`, `FakeTransport`. **Produces:** `Acquire(transport)`:
- `POINTS=(4000,40000,400000,4000000,8000000)`, `TYPES=("NORMal","AVERage","PEAK","HRESolution")`, `COUNTS=(4,8,16,32,64,128)`.
- `points` (`validate_choice(POINTS)`, get `int(float)`), `type` (`validate_enum(TYPES)`), `count` (`validate_choice(COUNTS)`, get `int(float)`), `srate` — `@property` только-чтение (`float`).

**Acceptance (минимум):**
- `acq.points = 4000` → `":ACQuire:POINts 4000"`; `set_response(":ACQuire:POINts?","4.000000e+03"); acq.points==4000`.
- `acq.type = "average"` → `":ACQuire:TYPE AVERage"`.
- `acq.count = 16` → `":ACQuire:COUNt 16"`; `acq.count = 7` → `ValueError`.
- `set_response(":ACQuire:SRATe?","1.0e9"); acq.srate == 1e9`. Присваивание `acq.srate=...` → `AttributeError` (нет сеттера).

- [ ] Шаги TDD 1–4. **Шаг 5.** Commit: `feat(scpi): add Acquire subsystem`.

---

## Task 8: Trigger + TriggerEdge (`scpi/trigger.py`)

**Files:** Create `hantek_dso2d15/scpi/trigger.py`, `tests/scpi/test_trigger.py`.

**Interfaces — Consumes:** `validation`, `FakeTransport`. **Produces:**
- `TriggerEdge(transport)`: `SOURCES=("CHANnel1","CHANnel2","CHANnel3","CHANnel4","EXT/10")`, `SLOPES=("RISIng","FALLing","EITHer")`; свойства `source` (enum), `slope` (enum), `level` (float).
- `Trigger(transport)`: `MODES` (см. «Карта команд», 14 шт.), `SWEEPS=("AUTO","NORMal","SINGle")`; в `__init__`: `self.edge = TriggerEdge(transport)`; свойства `mode` (enum), `sweep` (enum), `holdoff` (float); `status` — `@property` R/O, возвращает `transport.query(":TRIGger:STATus?").strip()` (raw `"TRIGed"`/`"NOTRIG"`); метод `force()` → `transport.write(":TRIGger:FORCe")`.

**Acceptance (минимум):**
- `trg.edge.source = "chan­nel1"`? нет — `trg.edge.source = "channel1"` → `":TRIGger:EDGe:SOURce CHANnel1"`.
- `trg.edge.source = "ext/10"` → `":TRIGger:EDGe:SOURce EXT/10"`.
- `trg.edge.slope = "rising"` → `":TRIGger:EDGe:SLOPe RISIng"` (каноничный регистр литерала).
- `trg.edge.level = 0.82` → `":TRIGger:EDGe:LEVel 0.82"`.
- `trg.mode = "edge"` → `":TRIGger:MODE EDGE"`; `trg.sweep = "single"` → `":TRIGger:SWEep SINGle"`.
- `trg.force()` → `writes[-1]==":TRIGger:FORCe"`.
- `set_response(":TRIGger:STATus?","TRIGed"); trg.status=="TRIGed"`.
- `trg.mode = "BAD"` → `ValueError`.

- [ ] Шаги TDD 1–4. **Шаг 5.** Commit: `feat(scpi): add Trigger + edge subsystem`.

---

## Task 8.5: Scope-фасад (`scpi/scope.py`)

**Files:** Create `hantek_dso2d15/scpi/scope.py`, `tests/scpi/test_scope.py`. Modify `hantek_dso2d15/scpi/__init__.py` (реэкспорт `Scope`).

**Interfaces — Consumes:** `Channel`, `Timebase`, `Acquire`, `Trigger`, `Transport`. **Produces:**
- `ChannelCollection(transport)`: `__getitem__(n)` → кэшированный `Channel(transport,n)`, валидирует `n∈{1,2,3,4}` (иначе `KeyError`/`ValueError`).
- `Scope(transport)`: `__init__` создаёт `self.channel=ChannelCollection(t)`, `self.timebase=Timebase(t)`, `self.acquire=Acquire(t)`, `self.trigger=Trigger(t)`. Методы: `connect()`→`t.open()`, `disconnect()`→`t.close()`, `is_connected`→`@property` `t.is_open`, `idn()`→`t.query("*IDN?").strip()`.

**Acceptance (минимум):**
- `scope.channel[1] is scope.channel[1]` (кэш); `scope.channel[1]` ≠ `scope.channel[2]`.
- `scope.connect()` → `transport.is_open is True`; `scope.is_connected is True`; `disconnect()` → False.
- `set_response("*IDN?","Hantek,DSO2D15,CN21034,V1.2.3"); scope.idn()` равно строке (stripped).
- `scope.channel[1].scale = 1.0` пишет `":CHANnel1:SCALe 1"` (сквозная проверка интеграции подсистем).
- `scope.channel[9]` → ошибка.

- [ ] Шаги TDD 1–4. **Шаг 5.** Commit: `feat(scpi): add Scope facade`.

---

## Task 9: VisaTransport (`transport/visa_transport.py`)

**Files:** Create `hantek_dso2d15/transport/visa_transport.py`, `tests/transport/test_visa_transport.py`. Modify `hantek_dso2d15/transport/__init__.py` (реэкспорт всех трёх).

**Interfaces — Consumes:** `Transport` (Задача 2), `pyvisa`. **Produces:** `VisaTransport(Transport)`:
- `__init__(self, resource: str, *, timeout_ms: int = 5000, read_termination: str | None = None, write_termination: str | None = "\n", resource_manager=None)`. *(read_termination=None: USBTMC завершает чтение по EOM; DSO2D15 не шлёт `\n` в ответах — подтверждено на железе; None также защищает бинарный блок waveform от обрыва на `0x0A`.)*
- `list_resources(resource_manager=None) -> tuple[str, ...]` — `@staticmethod`; берёт/создаёт RM (`pyvisa.ResourceManager()`), возвращает `tuple(rm.list_resources())`.
- `open()` — создать RM при необходимости, `self._res = rm.open_resource(resource)`, выставить `timeout`, `read_termination`, `write_termination`.
- `close()` — закрыть ресурс, занулить; `is_open` → `bool(self._res)`.
- `write(cmd)` → `self._res.write(cmd)`; `query(cmd)` → `self._res.query(cmd)`; `read_raw()` → `self._res.read_raw()`. На закрытом → `RuntimeError`.
- `reconnect()` — `close()` затем `open()`.

**Тестирование без железа:** через инъекцию фейкового `resource_manager`. Реальный PyVISA не дёргать. Подойдёт ручной фейк-класс или `unittest.mock.MagicMock`.

**Acceptance (минимум, фейковый RM):**
- `VisaTransport.list_resources(resource_manager=fake_rm)` возвращает `tuple`, делегирует `fake_rm.list_resources()`.
- `open()` вызывает `fake_rm.open_resource("USB0::...::INSTR")`; на ресурсе выставлены `timeout==5000`, `read_termination`, `write_termination`.
- `write(":X 1")` делегирует `resource.write(":X 1")`; `query("*IDN?")` возвращает то, что вернул фейк-ресурс.
- `write` на закрытом (до `open`) → `RuntimeError`.
- `close()` → `is_open is False`.

- [ ] Шаги TDD 1–4. **Шаг 5.** Commit: `feat(transport): add VisaTransport (PyVISA wrapper)`.

---

## Task 10: Hardware-smoke скрипт + интеграция

**Files:** Create `scripts/hw_smoke_foundation.py`. (Запускает **пользователь** на подключённом приборе — НЕ часть pytest.)

**Назначение:** первая проверка драйвера на железе (build-order, spec §12). Скрипт:
1. `VisaTransport.list_resources()` — печать найденных ресурсов; выбрать первый USB или из `sys.argv[1]`.
2. `scope.connect()`, печать `scope.idn()`.
3. Readback-проба: прочитать `channel[1].scale`, `timebase.scale`, `acquire.points`, `acquire.srate`, `trigger.sweep`, `trigger.status`.
4. Set+readback: `channel[1].coupling="DC"`, `channel[1].scale=0.5`, прочитать обратно, сверить.
5. Печать сводки PASS/FAIL по каждому readback; `scope.disconnect()`.

**Важно (комментарий в шапке скрипта):** это smoke на реальном приборе; out-of-range прибор зажимает; если readback не совпал — отметить в hardware-verify (spec §11), НЕ «чинить» под желаемое.

- [ ] **Шаг 1.** Написать скрипт (без pytest-зависимостей; чистый запуск `.venv/Scripts/python.exe scripts/hw_smoke_foundation.py`).
- [ ] **Шаг 2.** Интеграция: прогнать **весь** `pytest -q` — все зелёные.
- [ ] **Шаг 3.** Commit: `feat: add foundation hardware-smoke script`.
- [ ] **Шаг 4.** Передать пользователю инструкцию: подключить DSO2D15, запустить скрипт, прислать вывод (hardware-verify итерации).

---

## Self-Review (архитектор, перед делегированием — advisor-проход)

- **Покрытие build-order Layer 1–2:** transport (base/fake/visa) ✓, scpi core (channel/timebase/acquire/trigger-edge) ✓, scope-фасад ✓, connect/idn self-test ✓, hardware-smoke ✓.
- **File-disjoint в волнах:** да; `__init__.py` подсистем правят только Задачи 8.5 (scpi) и 9 (transport) — разные файлы, в разных волнах.
- **Типы согласованы:** `Transport` API един для Fake/Visa; подсистемы зовут только `write/query`; `Scope` агрегирует ровно объявленные классы.
- **Frozen literals:** все строки — из «Карты команд», сверены с reference. `EDGe/RISIng/EXT/10/SWEep` сохранены как есть.
- **Вне объёма (последующие планы):** waveform-декодер (risk §5), engine, gui, io, dds, остальные подсистемы триггера/measure/math/cursor/display/mask.
