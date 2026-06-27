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
5. **ТЕКУЩЕЕ СОСТОЯНИЕ (2026-06-28, перед сжатием контекста):** рабочее `python -m hantek_dso2d15.app` — live-дисплей обоих каналов + **правый док с 4 панелями** (Вертикаль/Горизонталь/Триггер/Acquire). **495 passed**, всё в `main`, дерево чистое (последний коммит `db29529`).

   **РЕШЕНО СЕГОДНЯ:** (а) поиск `PRIVate:*` исчерпан — есть ТОЛЬКО `PRIVate:WAVeform:DATA:ALL?` (и `PRIV:`); скриншота нет, быстрый readout = только патч прошивки (не делаем); `:SETUp:ALL?` работает (для пресетов). (б) Панели Vertical/Horizontal/Trigger/Acquire собраны (Vertical — вручную как эталон; остальные 3 — делегированы агентам). (в) Решение: **функционал сначала, дизайн-пасс (пиксель-в-пиксель по `design/`) — потом**.

   **АРХИТЕКТУРА GUI (паттерн для новых панелей — копировать `gui/panels/vertical.py`):**
   - Каждая панель = QWidget с сигналом `settingChanged = Signal(str, object)`; путь — точечный по графу драйвера (числовые токены = индексы): `"channel.1.scale"`, `"timebase.scale"`, `"trigger.edge.level"`, `"acquire.points"`. Значение: enum→каноничный SCPI-литерал, число→float/int, bool.
   - Метод `load_from_scope(scope)` — заполнить контролы с **заблокированными сигналами** (не слать команды при загрузке).
   - Числовые поля — `gui/widgets.DecimalSpinBox` (принимает `.` и `,`; применять по `editingFinished`, не на каждый ввод; `setMinimumHeight(24)`).
   - **Потоки:** `main_window._connect` подключает `panel.settingChanged → worker.apply_setting` (QueuedConnection) — весь VISA-I/O в потоке воркера. `EngineWorker.apply_setting(path, value)` навигирует граф `scope` и пишет; для `channel.N.scale|offset|probe` ещё `refresh_scaling` + эмитит `channelReadback(n,scale,offset,probe)` → панель синхронизируется (scale follows probe, кламп offset).
   - **Графикуль** рисует в делениях `y=(volts+offset)/Vдел = count/25` (offset двигает трассу как на приборе; probe только relabel-ит V/дел — HW-verified). `DecodedFrame` несёт `scales`+`offsets`. Ридаут-бейджи (V/дел/срейт/триггер) — `plot_widget._update_readout`.
   - `tests/conftest.py` — единый session-scoped QApplication (иначе сегфолт при смешивании QCoreApplication/QWidget тестов).

   **ОТКРЫТЫЕ ХВОСТЫ:** (1) #2 «горизонталь дёргает старт-стоп» при смене развёртки — пользователь не уточнил; вероятно мигание триг-статуса / медленные кадры на больших s/дел (норма) — подтвердить. (2) zoom-strip на графикуле НЕ нарисован (чекбокс шлёт команду, прибор включает, мы не рисуем) — функциональный TODO. (3) глубина 8M для live медленна (~мин/кадр) — это для capture-в-файл; разделить live(малая)/capture(глубокая) при реализации Save.

   **ПЛАН (функционал сначала):**
   1. Остальные панели Scope-таба: **Measure** (≈35 измерений `:MEASure:CHANnel<n>:ITEM`), **Math/FFT**, **Cursors**, **Display**.
   2. **Generator (DDS)** — ключевая фича (`:DDS:*`).
   3. **Sweep** + **zoom-strip** на графикуле.
   4. **Save/экспорт** (CSV/NPY/HDF5/PNG) + пресеты (`:SETUp:ALL?` raw + наш JSON), **SCPI-терминал**.
   5. **Дизайн-пасс** пиксель-в-пиксель по `design/` (токены, segmented-тогглы, степпер-спинбоксы, аккордеон, маркеры).
   6. **Установщик** MSI/EXE (PyInstaller + Inno Setup) — учесть требование **NI-VISA** на машине (или pyvisa-py?). **Публикация**.

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
- **Git:** инициализирован, ветка `main`. Коммиты: `7ba414b` (baseline: PDF, реестр, spec, UI-промпт), `78c5287` (перевод доки на русский), `f50cb6e` (CLAUDE.md, дизайн-хэндофф `design/`, CONTEXT.md, правки spec §8/§11, `.gitignore` *.zip). Идентичность: motokichirou / motokichirou@gmail.com. Коммитить только по просьбе пользователя. Рабочее дерево чистое (zip игнорируется).
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

**Добавлено в конце сессии 2:**
- Создан **`CLAUDE.md`** (корень репо): сжатая документация проекта (стек, архитектура, источники истины с приоритетом, жёсткие правила, ключевой риск) + интегрированный **оркестратор-режим (Opus)** — надстройка над superpowers-скиллами (author=Sonnet-исполнитель, reviewer=отдельная read-only ревью-сессия, frozen testbench = frozen SCPI-reference + приёмочные pytest/hardware-smoke). LTspice-упоминание из шаблона адаптировано → «полный прогон pytest + hardware-smoke».
- **Коммит `f50cb6e`** — закоммичены CLAUDE.md, CONTEXT.md, `design/`, правки spec, `.gitignore`. Рабочее дерево чистое.

### Сессия 3 — 2026-06-26 (Auto/ultracode)
**Окружение поднято:** Python 3.14.2 (3.11+ в системе не было), venv `.venv/` (в `.gitignore`), установлены pyvisa 1.16.2 / numpy 2.5.0 / pytest 9.1.1. PySide6/h5py — позже (GUI-слои).

**План фундамента записан:** `docs/superpowers/plans/2026-06-26-foundation-transport-scpi.md` — контракт-grade (точные интерфейсы, file-disjoint волны, дословная «Карта команд» SCPI, acceptance-кейсы). 10 задач: scaffold → Transport ABC + validation → FakeTransport + VisaTransport → channel/timebase/acquire/trigger → scope-фасад → hardware-smoke.

**Реализация запущена через Workflow** (оркестратор-режим): волны file-disjoint Sonnet-исполнителей с TDD + adversarial-ревью каждого юнита. Run ID `wf_726805af-75b`. Исполнители НЕ коммитят и НЕ трогают `__init__.py` (реэкспорты + полный прогон + коммиты — за архитектором на интеграции).

**ФУНДАМЕНТ ГОТОВ (workflow + интеграция завершены).**
- Реализованы все 10 задач плана: `transport/` (base ABC, FakeTransport, VisaTransport), `scpi/` (validation, channel, timebase, acquire, trigger+edge, scope-фасад), scaffold (pyproject, editable-пакет), hardware-smoke скрипт.
- **Тесты: 286 passed** (`.venv/Scripts/python.exe -m pytest`). Все SCPI-литералы сверены ревьюерами дословно с frozen reference. 2 minor-замечания ревью исправлены (имя теста FakeTransport, усилена проверка idn в test_scope). Реэкспорты в `transport/__init__.py` и `scpi/__init__.py` дописаны архитектором.
- Файлы драйвера: `hantek_dso2d15/transport/{base,fake_transport,visa_transport}.py`, `hantek_dso2d15/scpi/{validation,channel,timebase,acquire,trigger,scope}.py`. Тесты — зеркально в `tests/`. Smoke — `scripts/hw_smoke_foundation.py`.

**✅ HARDWARE-VERIFY ФУНДАМЕНТА ПРОЙДЕН (сессия 3).**
- Был блокер: smoke нашёл 0 VISA-ресурсов — прибор (`VID_049F/PID_505E`, S/N `CN2352029065656`) сидит на Microsoft `usbtmc.sys`, а единственный установленный **Agilent/Keysight VISA его не видит** (даже по явному адресу → `VI_ERROR_RSRC_NFOUND`). Наш код был корректен — блокер средовой.
- **Решение: установлен NI-VISA** (штатно работает с `usbtmc.sys`). **Смена согласованного бэкенда: Keysight → NI-VISA** (обновлены spec §2 и память).
- После установки NI-VISA прибор виден как `USB0::0x049F::0x505E::CN2352029065656::INSTR`. `hw_smoke_foundation.py`: `*IDN?` → `undefined, DSO2D15, CN2352029065656, 3.0.0(230831.00)`; readback всех подсистем рабочий; **set+readback 3/3 PASS** (coupling/scale/timebase.mode). Sample rate 12.5 MSa/s.
- **Hardware-finding исправлен:** DSO2D15 завершает ответы по USBTMC **EOM**, не по `\n` → `VisaTransport.read_termination` дефолт сменён `"\n"` → **`None`** (иначе байт `0x0A` оборвёт бинарный блок waveform). Тесты и план Task 9 обновлены. Полный прогон: **286 passed**, smoke без варнингов.

**✅ УЗЛОВОЙ РИСК §5 РАЗРЕШЁН (2026-06-27, петля DDS→CH1, R²=0.995).** Калибровка `WAVeform:DATA:ALL?`:
- Поток пакетов: HEADER (128 б ASCII) → по одному DATA-пакету на включённый канал (CH1→CH2), читать пока `uploaded<total` (`total=N_кан×points+99`). Каналы — отдельными пакетами, НЕ интерлив.
- **Сэмпл = signed int8, 25 counts/div**; `volts = sample×(Vдел/25) − offset_volts`; `t=i/srate`.
- Header-индексы (выверены, +4 к §7): chNoff[31+4k:35+4k], enable[79:83], srate[83:92].
- Реальные фикстуры в репо: `tests/fixtures/waveform/` (+ `FIXTURES.md` с ожидаемыми значениями). Разведочные скрипты — в scratchpad (probe2-6, capture_frames).

**✅ Layer 3 `waveform/` ГОТОВ И ПОДТВЕРЖДЁН НА ЖЕЛЕЗЕ.** План `docs/superpowers/plans/2026-06-27-waveform-decoder.md`. Модули `hantek_dso2d15/waveform/`: packet (IEEE-обёртка), header (метаданные), convert (counts→вольты, 25/div), reader (чанковый сбор кадра, многоканальный), decode (фасад). **373 passed** суммарно (286 фундамент + 87 waveform).
- **hardware-smoke `scripts/hw_smoke_waveform.py` — 4/4 PASS:** CH1 петля DDS DC +1В→1.031В; меандр 2Vpp→Vpp 2.000В (точно); оба канала enabled=[1,2]; CH2 внешний 5Vpp через щуп ×100 (PROBe=100)→~4В (внешняя цепь, не декодер; ×100 применён). Декодер точен (валидация по петле DDS).
- Probe ×100 учитывается автоматически: Vдел/offset берутся из probe-aware запросов `:SCALe?`/`:OFFSet?`.

**✅ Layer 4a — engine ГОТОВ И ПОДТВЕРЖДЁН НА ЖЕЛЕЗЕ.** План `docs/superpowers/plans/2026-06-27-engine-controller.md`. `hantek_dso2d15/engine/`: `RunState` (states.py), `AcquisitionController` (controller.py — чистое ядро read→decode, force, set_sweep), `EngineWorker` (worker.py — Qt-обёртка: сигналы frameReady/errorOccurred/stateChanged, слоты start/stop/single/capture_once, QTimer). **400 passed.**
- **Hardware-вывод (spec §11 п.10):** `:RUN`/`:STOP`/`:SINGle` прибор молча игнорирует (running-байт всегда 1). **Управление сбором — host-side** (кадентность нашего опроса). `:TRIGger:SWEep`/`:TRIGger:FORCe`/`:TRIGger:STATus?` — работают.
- **hardware-smoke `scripts/hw_smoke_engine.py` — 4/4 PASS:** worker в реальном QThread, непрерывный сбор (~27 кадров), 0 ошибок, CH1 Vpp 2.000В, srate ок.
- Ревью нашло major-баг (single+ошибка залипал в SINGLE) — исправлен (stop в finally) + добавлен тест.
- ⚠️ **fps ~2.2 — медленно** (per-frame запросы `:SCALe?`/`:OFFSet?` + sync header/data). **Тюнинг-TODO для GUI-слоя:** кэшировать scale/offset в контроллере, обновлять при смене настроек; уменьшить overhead синхронизации кадра. (spec §4.4: пропускную способность тюним на железе.)

**✅ CH2 РЕШЁН (HARDWARE-VERIFIED 2026-06-27) — `PRIVate:WAVeform:DATA:ALL?`.** Наводка с форума 4pda → GitHub `phmarek/hantek-dso2000` (тот же VID/PID 0x049F/0x505E) дала разгадку:
- Команда **`PRIVate:WAVeform:DATA:ALL?`** (с префиксом `PRIVate:`!) отдаёт ВСЕ каналы. Обычный `:WAVeform:DATA:ALL?` отдаёт только CH1 (потому и был баг «одинаковые графики»).
- Формат: каждый пакет = 128 б meta + кусок сэмплов с байта 128; `total = N_кан × points`; кусок по позиции `uploaded`; читать пока собрано `total`. **Каналы ИНТЕРЛИВНЫ блоками по 2000 байт** `|CH1|CH2|CH1|CH2|` — де-интерлив по индексу канала.
- Meta-поля: enable [75:79], srate [79:88] (как во frozen reference §7 — прежняя «+4» правка была ошибкой, исправлено). Смещения каналов в meta бинарны — берём `:CHANnel<n>:OFFSet?`.
- Калибровка та же: `volts = sample/25 × Vдел − offset` (signed int8), совпала с phmarek.
- **Слой waveform переписан** (header/reader под PRIVate+де-интерлив, контроллер откатан с дедуп-костыля). Hardware-verified: `channels=[1,2]`, CH1 Vpp 2.00В, CH2 корректно. **422 passed.** Тесты (6 файлов) переписаны делегированно (Sonnet-исполнители + ревью); фикстуры пересняты (priv_*).

**Layer 4b — минимальный GUI СОБРАН** (`hantek_dso2d15/gui/`: plot_widget.py графикуль 14×8 в делениях; main_window.py тулбар connect/RUN/STOP/SINGLE + engine в QThread; app.py). pyqtgraph-графикуль, цвета CH1 жёлтый / CH2 зелёный, host-side управление сбором. fps ~2 (потолок передачи). Запуск: `.venv/Scripts/python.exe -m hantek_dso2d15.app`. **402 passed.** GUI на визуальной доводке с пользователем.

**ЗАТЕМ (после GUI):** (PySide6+pyqtgraph установлены 6.11.1/0.14.0): главное окно, pyqtgraph-графикуль, connect/disconnect, RUN/STOP/SINGLE (через EngineWorker в QThread), live-дисплей обоих каналов. Пиксель-в-пиксель по `design/design_handoff_dso2d15_ui/` (токены/раскладка — §6/§7). При интеграции применить fps-оптимизацию (кэш scale/offset).

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

---

### 🏁 ИТОГ НА КОНЕЦ ДНЯ 2026-06-27 (авторитетно; перекрывает промежуточные записи журнала выше)

> Часть промежуточных находок в журнале выше **устарела** (напр. «каналы отдельными пакетами, не интерлив», header-смещения «+4 к §7») — они были верны на момент записи, но перекрыты финалом PRIVate (см. §0.5, spec §4.3, память).

**Работает end-to-end на железе:** `python -m hantek_dso2d15.app` → connect → RUN → **live-дисплей обоих каналов** (CH1 жёлтый, CH2 зелёный), ~3 fps. Полный путь «прибор → вольты → экран» замкнут.

**Слои:** transport (NI-VISA, read_termination=None) · scpi (channel/timebase/acquire/trigger-edge + scope) · waveform (**`PRIVate:WAVeform:DATA:ALL?`**, де-интерлив 2000-байт блоков, оба канала, signed int8, 25 count/дел) · engine (AcquisitionController + EngineWorker в QThread, host-side run/stop/single, кэш scale/offset) · gui (минимальный: тулбар + pyqtgraph-графикуль 14×8 в делениях).

**Тесты: 422 passed.** Коммиты в `main` (последний — `c9f0ec5` «Решить CH2: PRIVate…»), дерево чистое. Скрипты hardware-smoke: `scripts/hw_smoke_{foundation,waveform,engine}.py`. Разведочные probe-скрипты — в scratchpad (не в репо).

**Открытые вопросы / TODO (план на завтра — см. §0.5):** (1) поискать ещё `PRIVate:*` команды (вкл. быстрый bulk-readout — phmarek упоминает quick-fetch 20× быстрее SCPI); (2) правый док панелей UI (особенно probe/scale/offset по каналам — для корректного масштаба CH2 с ×100); (3) MSI/EXE-установщик с зависимостями; (4) публикация. Также: hw_smoke_waveform.py писался под старую модель (CH2 ×100) — при желании обновить под новые priv-фикстуры; fps ~3 (потолок USBTMC) — bulk-readout может ускорить.

**Следующие планы (после фундамента):** waveform (risk §5, калибровка) → engine+минимальный gui → остальные панели → DDS → io/пресеты → sweep/терминал.

### Сессия 4 — 2026-06-28 (GUI: правый док)
Собран правый док с панелями **Вертикаль/Горизонталь/Триггер/Acquire** (Vertical вручную как эталон паттерна, остальные 3 делегированы агентам + ревью). Заложена потоковая инфраструктура управления (`settingChanged(path,value) → worker.apply_setting` в потоке воркера; `channelReadback` синхронизирует панель). `DecimalSpinBox` (. и ,), ридаут-бейджи, фикс кнопок спинбокса, авто-лимит ридера под глубину 8M, `conftest.py` (session QApplication, фикс сегфолта). **495 passed.** Полная картина состояния и паттерн новых панелей — в §0.5. Коммиты: `98d7709`(Vertical) `ab955a1`(панели+интеграция) `59595dd`(reader 8M) `db29529`(спинбокс).
