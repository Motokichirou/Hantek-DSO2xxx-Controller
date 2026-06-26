# Hantek DSO2D15 — контекст проекта / хэндофф для новой сессии

> Этот файл — полный снимок состояния проекта. Прочитай его первым при старте новой сессии Claude Code в этой папке. Он самодостаточен: по нему + репозиторию можно продолжить без потери контекста.
>
> **Последнее обновление: 2026-06-26 (вечер, сессия 2).** Что изменилось — см. раздел «Журнал сессий» внизу (§14).

---

## 0. Как продолжить (для Claude в новой сессии)

1. Прочитай этот файл целиком, затем `docs/superpowers/specs/2026-06-26-hantek-dso2d15-design.md` (spec) и `docs/scpi-command-reference.md` (frozen reference команд).
2. Веди диалог и всю документацию **на русском** (постоянное предпочтение пользователя).
3. Мануал — **frozen reference**: команды берём из `docs/scpi-command-reference.md` / PDF, не выдумываем.
4. **Реальное тестирование на железе после каждой итерации** — прибор физически подключён, пользователь подтверждает или сообщает что сломалось.
5. **СЛЕДУЮЩИЙ ШАГ (с этого продолжить):** дописать первый implementation-план — **фундамент: Layer 1 `transport`+`FakeTransport` + Layer 2 ядро `scpi` (channel/timebase/acquire/trigger-edge + scope-фасад)**. Skill `writing-plans` уже запущен, весь реестр SCPI прочитан. План сохранять в `docs/superpowers/plans/2026-06-26-foundation-transport-scpi.md`. Это первый из нескольких планов (по группам build-order §13); даёт тестируемый без железа + проверяемый на приборе драйвер без GUI. Детали задуманного плана — в §14.

---

## 1. Цель проекта

Полнофункциональный десктоп-клиент под **Windows 11** для осциллографа **Hantek DSO2D15**, с нуля, работа с прибором по **USB (USBTMC) через стандартный VISA** (бэкенд — установленный Keysight IO Libraries). Заменяет капризный родной софт; предоставляет **весь** функционал из программного мануала без искусственных ограничений.

Прибор: 2 аналоговых канала (CH1, CH2) + встроенный генератор (AWG/DDS) + ~35 автоизмерений + math/FFT + триггеры с декодированием шин. Виден в Device Manager как «USB Test and Measurement Device (IVI)».

---

## 2. Технологический стек (согласован)

Python 3.11+ · **PySide6** (Qt6) · **pyqtgraph** (real-time графики) · **PyVISA** (бэкенд Keysight VISA) · **NumPy** · **h5py** (HDF5) · **pytest**. Запуск из venv, single-exe не требуется.

---

## 3. Ключевые решения (все согласованы с пользователем)

| Тема | Решение |
|---|---|
| Стек | Python + PySide6 + pyqtgraph + PyVISA |
| Объём v1 | Весь функционал мануала (полный клиент), сборка слоями с тестом на железе |
| Screenshot | Рендер нашего собственного waveform-view в PNG (в SCPI команды захвата экрана НЕТ) |
| Пресеты | Наш JSON — основной; `SETUp:ALL?` raw-снимок — бонус |
| Форматы сохранения | CSV + NumPy .npy/.npz + HDF5 + PNG |
| Детальность spec | Архитектура + полный реестр команд (frozen reference) |
| Язык UI | Двуязычный EN/RU с runtime-переключателем (по умолчанию EN), все строки через translation layer |
| Оркестрация нескольких приборов | НЕ нужна (прибор один) |
| Git | Инициализирован, baseline закоммичен |
| Язык ведения проекта/доки | Русский |
| Путь проекта | ASCII обязателен (см. §9) |

---

## 4. Архитектура (слоистая) — кратко

Жёсткое разделение слоёв: вся логика тестируется **без железа**, VISA-I/O никогда не блокирует UI-поток.

```
gui/        PySide6 — окно, plot, панели, генератор, sweep, SCPI-терминал, статус-бар
engine/     контроллер сбора в фоновом QThread; run/stop/single; шлёт кадры в GUI (signals)
scpi/       типизированный драйвер 1:1 с мануалом (frozen reference) + waveform/ (декодер)
transport/  обёртка PyVISA (open/write/query/read_raw, таймауты, реконнект) + FakeTransport
io/         CSV · NPY/NPZ · HDF5 · PNG · пресеты (JSON)
```

Пакет:
```
hantek_dso2d15/
  transport/  scpi/  waveform/  engine/  gui/  io/  app.py
tests/   docs/
```

Полное описание слоёв, структуры пакета и алгоритмов — в spec, §4.

---

## 5. Узловой риск — формат `WAVeform:DATA:ALL?`

Это **единственная** команда выгрузки осциллограммы. Чанковая: первый пакет = IEEE-488.2 блок `#9<9 цифр длины>` + заголовок фикс-формата (running/trigger status, offset/voltage/enable по 4 каналам, sample rate, sampling multiple, trigger time, frame start, reserved — data[0..127]), затем сэмплы; далее повторными запросами докачиваются чанки до полной длины. Прибор generically рапортует 4 канала (`SYSTem:RAM? → 4`), хотя их 2 — парсим обобщённо.

⚠️ **Кодировка сэмплов (байт/сэмпл) и точное counts-per-division масштабирование в мануале НЕ заданы.** Это **первая аппаратная задача**: откалибровать конвертацию сэмплы→вольты/время на железе по эталону (встроенный 1 kHz cal-меандр или DDS-генератор в петле). Блокирует точность всего отображения. Детали формата — в `docs/scpi-command-reference.md` §7 и spec §4.3.

---

## 6. Дизайн UI — импортирован из Claude design

Пользователь сделал hi-fi макет в Claude design. Хэндофф распакован в `design/design_handoff_dso2d15_ui/`:
- `Hantek DSO2D15 Control.dc.html` — прототип (Design Component; логику смотреть в `class Component extends DCLogic`, рендер канвы в `draw()`/`drawTrace()`).
- `README.md` — **детальнейшая спецификация**: точные токены (цвета, шрифты Inter + JetBrains Mono, размеры, отступы, радиусы), все компоненты, состояния, поведение, маппинг контролов на SCPI. **Это основной источник для слоя `gui/`.**
- `reference_main_scope.png`, `reference_scope_scpi_open.png`, `reference_generator.png`, `reference_sweep.png` — визуальные референсы (4 экрана).
- `support.js` — рантайм прототипа, в реализацию НЕ входит.

Макет (подтверждён, соответствует spec): тёмная тема (window `#0E0F12`, графикуль `#08090B`, док `#13151A`), цветокод каналов CH1 жёлтый `#F2C300` / CH2 голубой `#23C8E6` / MATH пурпурный `#C77DFF`, моноширинные ридауты. Раскладка: верхний тулбар 48px (connection, RUN/STOP/SINGLE/FORCE/AUTO, Save/Screenshot/Presets/SCPI/Settings) · центр (графикуль + выезжающий SCPI-терминал 230px снизу) · правый док 382px с табами **Scope / Generator / Sweep** · статус-бар 28px. Графикуль 14×8 делений, рисуется на GPU-канве каждый кадр (в продакшене — реальные буферы сэмплов). Промпт, по которому сделан макет, — `docs/ui-claude-design-prompt.md`.

---

## 7. ⚠️ Расхождение SCPI: README дизайна vs frozen reference

README дизайна предлагает SCPI-команды «conventional DSO2000», и **многие НЕ совпадают с нашим мануалом**. **Визуальная часть дизайна авторитетна и реализуется пиксель-в-пиксель; SCPI-привязка идёт строго по `docs/scpi-command-reference.md`, НЕ по подсказкам README.** Конкретно:

| Контрол | README дизайна (НЕВЕРНО) | Frozen reference (мануал) |
|---|---|---|
| Генератор | `:WGEN:*` | `:DDS:*` (SWITch/TYPE/FREQ/AMP/OFFSet/DUTY/MODE/BURSt/ARB:DAC16:BIN) |
| Глубина памяти | `:ACQuire:MDEPth` | `:ACQuire:POINts` |
| Усреднения | `:ACQuire:AVERages` | `:ACQuire:COUNt` |
| Смещение по времени | `:TIMebase:OFFSet` | `:TIMebase:POSition` |
| Измерение | `:MEASure:ITEM` | `:MEASure:CHANnel<n>:ITEM` |
| Zoom включить | `:TIMebase:DELay:ENABle` | `:TIMebase:WINDow:ENABle` |
| Screenshot | `:DISPlay:DATA?` | **нет команды** → рендер в PNG |
| Edge source | `:TRIGger:EDGE:SOURce` | `:TRIGger:EDGe:SOURce` (регистр) |

**Run/Stop/Single/Auto-setup:** README предлагает `:RUN`/`:STOP`/`:SINGle`/`:AUToscale`/`:TFORce`. В мануале их **НЕТ** (есть только `:TRIGger:FORCe`, `:TRIGger:SWEep`, `:TRIGger:STATus?`). Многие Hantek/Rigol принимают `:RUN`/`:STOP`/`:SINGle` недокументированно → **добавить в hardware-verify** (как управлять run/stop/single на самом деле).

---

## 8. Hardware-verification TODO (не доверять литералам вслепую)

Мануал — frozen reference, но с OCR-артефактами и пробелами. Проверить на устройстве (полный список — spec §11):
1. **Кодировка/масштаб сэмплов** `WAVeform:DATA:ALL?` (блокер точности). 
2. Команды управления сбором **run/stop/single/autoscale** — есть ли вообще (см. §7).
3. **Write-back `SETUp:ALL?`** — можно ли записать снимок обратно.
4. `:MASK:EANBle` — нужен ли литерал-опечатка или работает `ENABle`.
5. Расхождение ключей триггера: enum `TRIGger:MODE` (`INTerval/UNDerthrow/WINdow/EDGE`) vs ключи подкоманд (`INTERVAl/UNDER_Am/WINDOw/EDGe`).
6. `TRIGger:PATTern` vs `TRIGger:LOGIc` (одна фича, два написания в мануале).
7. «Фантомные» команды только в `SETUp:ALL?`: `UART:STOP`, `CAN:DATA` (без индекса), `LOGIc:CLEVel/DLEVel`.
8. Enum'ы CAN `FRAM_STARE`/`FRAM_REE` (вероятно OCR от FRAME_START/FRAME_ERROR).
9. Источник `EXT/10` — принимает ли 2-канальный DSO2D15.

Драйвер держит эти литералы в одном месте для лёгкой коррекции после тестов.

---

## 9. Заметки по инструментам/окружению

- **Кириллица в пути ломает инструменты** (Bash искажает путь, Read не открывает PDF). Поэтому проект перенесён в ASCII-путь `C:\Claud Projects\Hantek-DSO2D15`. Старая папка `C:\Claud Projects\GUI для Hantek` была cwd прошлой сессии (пустая, можно удалить). **Держать путь проекта ASCII.**
- **PowerShell-классификатор временами недоступен** («temporarily unavailable») — тогда write-операции PowerShell падают; read-only (Glob/Grep/Read) и инструменты Write/Edit работают. Из-за этого не завершилось перемещение `design/` в `docs/design/` (см. §11).
- **Git:** инициализирован, ветка `main`. Коммиты: `7ba414b` (baseline: PDF, реестр, spec, UI-промпт), `78c5287` (перевод доки на русский). Идентичность: motokichirou / motokichirou@gmail.com. Коммитить только по просьбе пользователя.
- **Claude design MCP** = инструмент `DesignSync` (+ skill `/design-sync`), но он для синка локальной либы В проект claude.ai. Импорт дизайна сделан проще — через локальный zip. Авторизация дизайна — `/design-login` (делает пользователь).
- **PDF читается** через Read только по ASCII-пути (`docs/DSO2000-SCPI-Programmers-Manual.pdf`).

---

## 10. Что сделано — статус

- ✅ Brainstorming пройден, **spec согласован** пользователем (оркестрация исключена — прибор один).
- ✅ Полный реестр SCPI (~189 команд) извлечён из мануала: `docs/scpi-command-reference.md`.
- ✅ Spec написан и переведён на русский: `docs/superpowers/specs/2026-06-26-hantek-dso2d15-design.md`.
- ✅ UI-промпт: `docs/ui-claude-design-prompt.md`. Дизайн-макет сделан и импортирован (`design/`).
- ✅ Git baseline + перевод закоммичены.
- ✅ Память обновлена (см. §12).
- ⏳ Код ещё НЕ писался. Следующий шаг — implementation-план.

---

## 11. Незавершённое — статус по пунктам прошлой сессии

1. ✅ **Дизайн оставлен** в `design/design_handoff_dso2d15_ui/` (в корне, НЕ перемещён в docs/design — перемещение признано лишним; пути в spec §8 приведены к фактическому расположению).
2. ✅ **spec §8 обновлён** — импортированный дизайн прописан как авторитетный визуальный источник для `gui/` + врезка про расхождение SCPI (см. §7).
3. ✅ **spec §11 обновлён** — добавлен пункт 10 про run/stop/single/autoscale (hardware-verify).
4. ⏳ **Коммит не делался** (правило: коммитить только по явной просьбе пользователя). К коммиту готовы: `CONTEXT.md`, `design/`, правки `spec` и `.gitignore`. `*.zip` теперь в `.gitignore` — zip не коммитим, коммитим распакованную `design/`.
5. ⏳ **`writing-plans` запущен**, но первый план ещё НЕ записан на диск — продолжить отсюда (см. §0 шаг 5 и §14).

---

## 12. Память (вне репозитория)

✅ **Перенесена** в новый путь проекта `C:\Users\motok\.claude\projects\C--Claud-Projects-Hantek-DSO2D15\memory\`:
- `MEMORY.md` — индекс.
- `lead-project-in-russian.md` — вести проект и доки на русском.
- `hantek-project-context.md` — стек, решения, локации, ключевой риск.

(Старая копия в `C--Claud-Projects-GUI-----Hantek\memory\` больше не нужна.)

---

## 13. Build-order (из spec §13) — порядок реализации

1. `transport` + `FakeTransport` + self-test соединения.
2. Ядро `scpi` (channel/timebase/acquire/trigger-edge) с валидацией+readback.
3. `waveform` reader/декодер — **калибровка на железе** (risk §5).
4. `engine` loop + минимальный `gui` (plot + connect + run/stop) → первый live-дисплей обоих каналов.
5. Остальные панели (полный триггер, измерения, math/FFT, курсоры, дисплей, mask).
6. Панель генератора (DDS).
7. IO (CSV/npy/HDF5/PNG) + пресеты.
8. Sweep/multi-capture + SCPI-терминал.

GUI можно вести параллельно от дизайна на mock-данных (`FakeTransport` + синтетический источник), затем подключить к реальному драйверу.

---

## 14. Журнал сессий

### Сессия 2 — 2026-06-26 (вечер)
**Сделано:**
- Перенесена память в новый ASCII-путь проекта (§12).
- Закрыты пункты §11.1–§11.3: дизайн оставлен в корне `design/`; spec §8 и §11 обновлены.
- `.gitignore`: добавлен `*.zip` (zip не коммитим — он распакован в `design/`).
- Запущен skill `writing-plans`; прочитан **весь** `docs/scpi-command-reference.md` (538 строк). Сделан вывод: build-order §13 режем на отдельные планы (каждый = работающее тестируемое ПО), первый — фундамент.

**Остановились на:** написании первого плана (на диск ещё НЕ записан).

**Замысел первого плана** — `docs/superpowers/plans/2026-06-26-foundation-transport-scpi.md` (Layer 1 + Layer 2 build-order):
- TDD на `FakeTransport` (без железа), точки smoke-проверки на приборе в конце.
- **Структура пакета этого плана:**
  - `pyproject.toml` (deps: pyvisa, numpy, pytest; Python 3.11+; пакет `hantek_dso2d15`).
  - `transport/base.py` — ABC `Transport` (`open/close/write/query/read_raw/is_open`).
  - `transport/fake_transport.py` — `FakeTransport`: лог `writes`, лог `queries`, программируемые ответы `set_response(cmd,val)`, очередь raw-чанков (для будущего waveform). Скриптуемый дубль.
  - `transport/visa_transport.py` — `VisaTransport` (обёртка PyVISA: list_resources/open/timeout/termination/реконнект). Тест через monkeypatch pyvisa; реальный self-test (`*IDN?`) — hardware-gated skip.
  - `scpi/validation.py` — хелперы: `validate_enum` (case-insensitive→каноничный литерал), `validate_choice` (int-наборы), `parse_bool` ("0/1/ON/OFF"→bool), `bool_arg` (→"ON"/"OFF"), `fmt_num` (`f"{float(v):g}"`, NR3). **Range НЕ валидируем** где мануал не задаёт границы — прибор сам зажимает (см. §9 spec); полагаемся на readback.
  - `scpi/channel.py` — `Channel(transport,n)`: scale/offset(float), coupling(AC|DC|GND), probe(1|10|100|1000), bwlimit/display/invert/vernier(bool). Индекс n валидируем 1–4 (команды документированы n∈{1..4}), UI использует 1–2.
  - `scpi/timebase.py` — `Timebase`: scale/position/range(float), mode(MAIN|XY|ROLL) + вложенный `window` (enable bool, scale, position) → `:TIMebase:WINDow:*`.
  - `scpi/acquire.py` — `Acquire`: points(4000|40000|400000|4000000|8000000), type(NORMal|AVERage|PEAK|HRESolution), count(4|8|16|32|64|128), srate (read-only `:ACQuire:SRATe?`).
  - `scpi/trigger.py` — `Trigger`: mode(14 типов), sweep(AUTO|NORMal|SINGle), holdoff(float), status (read-only→TRIGed|NOTRIG), `force()` (`:TRIGger:FORCe`); вложенный `edge` → `TriggerEdge`: source(CHANnel1..4|EXT/10), slope(RISIng|FALLing|EITHer), level(float). **Регистр литералов — дословно из реестра** (RISIng, EDGe и т.п.).
  - `scpi/scope.py` — фасад `Scope(transport)`: агрегирует channel-коллекцию (`scope.channel[1]`), timebase, acquire, trigger; `connect()/disconnect()`, `idn()` (`*IDN?` — IEEE-488.2, в таблице мануала его нет, но USBTMC принимает).
- **Задачи плана (bite-sized, TDD):** 1) scaffold+pyproject; 2) Transport ABC + FakeTransport; 3) validation.py; 4) Channel; 5) Timebase; 6) Acquire; 7) Trigger+TriggerEdge; 8) Scope-фасад; 9) VisaTransport + hardware smoke-script.
- **Каждый сеттер пишет команду, геттер читает readback** (валидация клиентская — у прибора нет `SYSTem:ERRor?`). Литералы-опечатки (RISIng, EANBle, UNDER_Am, INTERVAl) держим централизованно — корректируем после hardware-verify (§8/§11 здесь).

**Следующие планы (после фундамента):** waveform (risk §5, калибровка) → engine+минимальный gui → остальные панели → DDS → io/пресеты → sweep/терминал.
