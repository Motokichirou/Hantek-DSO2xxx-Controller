# Реестр команд SCPI серии DSO2000

Замороженное справочное приложение, извлечённое дословно из **Руководства программиста по SCPI для серии Hantek DSO2000** (61 страница).
Ключевые слова команд используют регистр SCPI (ПРОПИСНЫЕ = обязательная краткая форма, строчные = необязательное дополнение до полной длинной формы). `<n>` обозначает индекс канала (1–4), если не указано иное.

> **Примечания по OCR / опечаткам:** Руководство содержит ряд артефактов распознавания (OCR) и орфографических несоответствий. Они помечены по месту с помощью **[sic]** и сведены в таблицу в конце этого документа. Там, где буквальная строка устройства неоднозначна, указано наиболее вероятное предполагаемое ключевое слово.

---

## 1. Подсистема CHANnel\<n\>

Параметры вертикальной системы (ограничение полосы, связь по входу, вертикальный масштаб, смещение) аналоговых каналов. `<n> ::= {1 | 2 | 3 | 4}` для всех команд этой подсистемы.

| Команда | Запрос | Параметры / Диапазон | Возвращает | Описание |
|---|---|---|---|---|
| `:CHANnel<n>:BWLimit <type>` | `:CHANnel<n>:BWLimit?` | `<type> ::= {{1 | ON} | {0 | OFF}}` | `0` или `1` | Установить/запросить ограничение полосы 20 МГц для канала. ON ослабляет высокочастотные составляющие. |
| `:CHANnel<n>:COUPling <coupling>` | `:CHANnel<n>:COUPling?` | `<coupling> ::= {AC | DC | GND}` | `AC,DC,GND` (одно из) | Установить/запросить связь канала по входу. AC блокирует постоянную составляющую; DC пропускает обе; GND блокирует обе. |
| `:CHANnel<n>:DISPlay <bool>` | `:CHANnel<n>:DISPlay?` | `<bool> ::= {{1 | ON} | {0 | OFF}}` | `0` или `1` | Включить/выключить отображение канала. |
| `:CHANnel<n>:INVert <bool>` | `:CHANnel<n>:INVert?` | `<bool> ::= {{1 | ON} | {0 | OFF}}` | `0` или `1` | Включить/выключить инверсию осциллограммы канала. |
| `:CHANnel<n>:OFFSet <offset> [<suffix>]` | `:CHANnel<n>:OFFSet?` | `<offset> ::=` вертикальное смещение в NR3; `<suffix> ::= {V | mV}`; единица по умолчанию V | Вертикальное смещение, научная нотация | Установить/запросить вертикальное смещение. Допустимый диапазон зависит от вертикального масштаба и коэффициента пробника; значения вне диапазона ограничиваются ближайшим допустимым значением. |
| `:CHANnel<n>:SCALe <scale> [<suffix>]` | `:CHANnel<n>:SCALe?` | `<scale> ::=` вольт/дел в NR3; `<suffix> ::= {V | mV}`; единица по умолчанию V | Вертикальный масштаб, научная нотация | Установить/запросить вертикальный масштаб (вольт на деление). Настраиваемый диапазон связан с коэффициентом пробника. |
| `:CHANnel<n>:PROBe <atten>` | `:CHANnel<n>:PROBe?` | `<atten> ::= {1 | 10 | 100 | 1000}` | Коэффициент пробника, научная нотация | Установить/запросить коэффициент ослабления пробника. |
| `:CHANnel<n>:VERNier <bool>` | `:CHANnel<n>:VERNier?` | `<bool> ::= {{1 | ON} | {0 | OFF}}` | `1` или `0` | Включить/выключить плавную (нониусную) регулировку вертикального масштаба. Выкл = грубые шаги 1-2-5. |

---

## 2. Подсистема TIMebase

Горизонтальная система: двойное окно (масштабирование), основная развёртка, режим.

| Команда | Запрос | Параметры / Диапазон | Возвращает | Описание |
|---|---|---|---|---|
| `:TIMebase:WINDow:ENABle <bool>` | `:TIMebase:WINDow:ENABle?` | `<bool> ::= {{1 | ON} | {0 | OFF}}` | `ON` или `OFF` | Включить/выключить функцию двойного окна (масштабирование/задержанная развёртка). |
| `:TIMebase:WINDow:POSition <pos value>` | `:TIMebase:WINDow:POSition?` | `<pos value> ::=` горизонтальная позиция (секунды) | Позиция, научная нотация | Установить/запросить горизонтальную позицию масштабированного вида. Окно масштабирования должно оставаться в пределах диапазона основной развёртки. |
| `:TIMebase:WINDow:SCALe <scale_value>` | `:TIMebase:WINDow:SCALe?` | `<scale_value> ::=` микросекунд на деление подокна **[sic: "sacle_value"]** | Развёртка подокна, научная нотация | Установить/запросить горизонтальный масштаб подокна (мкс/дел). Макс. = половина масштаба основной развёртки. |
| `:TIMebase:POSition <pos value>` | `:TIMebase:POSition?` | `<pos value> ::=` значение смещения (секунды) | Смещение основной развёртки, научная нотация | Установить/запросить смещение основной развёртки. |
| `:TIMebase:SCALe <scale value>` | `:TIMebase:SCALe?` | `<scale value> ::=` секунд на деление (основное окно) | Основная развёртка, научная нотация | Установить/запросить горизонтальный масштаб основного окна (с/дел). |
| `:TIMebase:RANGe <range value>` | `:TIMebase:RANGe?` | `<range value> ::=` значение диапазона (секунды) | Полное время по шкале, научная нотация | Установить/запросить полное горизонтальное время основного окна. |
| `:TIMebase:MODE <value>` | `:TIMebase:MODE?` | `<value> ::= {MAIN | XY | ROLL}` | `MAIN`, `XY` или `ROLL` | Установить/запросить режим горизонтальной развёртки (MAIN=YT, XY, ROLL). |

---

## 3. Подсистема ACQuire

Глубина памяти сбора данных, тип сбора, частота дискретизации, число усреднений.

| Команда | Запрос | Параметры / Диапазон | Возвращает | Описание |
|---|---|---|---|---|
| `:ACQuire:POINts <value>` | `:ACQuire:POINts?` | `<value> ::= 4000 | 40000 | 400000 | 4000000 | 8000000` (4K/40K/400K/4M/8M) | Фактическое число точек (целое) | Установить/запросить глубину памяти (сохранения). |
| `:ACQuire:TYPE <value>` | `:ACQuire:TYPE?` | `<value> ::= {NORMal | AVERage | PEAK | HRESolution}` | `NORM`, `AVERage`, `PEAK` или `HRESolution` | Установить/запросить метод сбора данных (нормальный, усреднение, пиковый детектор, высокое разрешение). |
| — | `:ACQuire:SRATe?` | (только запрос) | Частота дискретизации как вещественное число | Запросить текущую частоту дискретизации (число точек осциллограммы, дискретизируемых в секунду). |
| `:ACQuire:COUNt <value>` | `:ACQuire:COUNt?` | `<value> ::= 4 | 8 | 16 | 32 | 64 | 128` | Текущее число усреднений | Установить/запросить число усреднений, используемое в режиме сбора с усреднением. |

---

## 4. Подсистема TRIGger

Самая большая подсистема. Режимы триггера: EDGE, PULSe, TV, SLOPe, TIMeout, WINdow, PATTern, INTerval, UNDerthrow (runt), UART, LIN, CAN, SPI, IIC.

### 4.1–4.5 Верхний уровень TRIGger

| Команда | Запрос | Параметры / Диапазон | Возвращает | Описание |
|---|---|---|---|---|
| `:TRIGger:FORCe` | — | (без параметров) | — | Принудительный запуск триггера; захватывает осциллограмму, даже если условия триггера не выполнены. |
| `:TRIGger:MODE <mode>` | `:TRIGger:MODE?` | `<mode> ::= {EDGE | PULSe | TV | SLOPe | TIMeout | WINdow | PATTern | INTerval | UNDerthrow | UART | LIN | CAN | SPI | IIC}` | `EDGE, PULSe, TV, SLOPe, TIMeout, WINdow, PATTern, INTerval, UNDerthrow, UART, LIN, CAN, SPI, IIC` | Установить/запросить тип триггера. |
| — | `:TRIGger:STATus?` | (только запрос) | `TRIGed` или `NOTRIG` | Запросить текущее состояние триггера. |
| `:TRIGger:SWEep <value>` | `:TRIGger:SWEep?` | `<value> ::= {AUTO | NORMal | SINGle}` | `AUTO`, `NORMal` или `SINGle` | Установить/запросить режим развёртки триггера. |
| `:TRIGger:HOLDoff <value>` | `:TRIGger:HOLDoff?` | `<value> ::=` время удержания (секунды) | Время удержания, научная нотация | Установить/запросить удержание триггера (holdoff). Недоступно для триггеров video/timeout/setup-hold/UART/LIN/CAN/IIC/SPI. |

### 4.6 TRIGger:EDGe

| Команда | Запрос | Параметры / Диапазон | Возвращает | Описание |
|---|---|---|---|---|
| `:TRIGger:EDGe:SOURce <source>` | `:TRIGger:EDGe:SOURce?` | `<source> ::= {CHANnel1 | CHANnel2 | CHANnel3 | CHANnel4 | EXT/10}` | `CHANnel1, CHANnel2, CHANnel3, CHANnel4, EXT/10` | Установить/запросить источник триггера по фронту. |
| `:TRIGger:EDGe:SLOPe <slope>` | `:TRIGger:EDGe:SLOPe?` | `<slope> ::= {RISIng | FALLing | EITHer}` **[sic: RISIng]** | `RISIng, FALLing, EITHer` | Установить/запросить тип фронта (нарастающий / спадающий / любой). |
| `:TRIGger:EDGe:LEVel <level>` | `:TRIGger:EDGe:LEVel?` | `<level> ::=` уровень триггера (V) | Уровень, научная нотация | Установить/запросить уровень триггера по фронту. |

### 4.7 TRIGger:PULSe

| Команда | Запрос | Параметры / Диапазон | Возвращает | Описание |
|---|---|---|---|---|
| `:TRIGger:PULSe:SOURce <source>` | `:TRIGger:PULSe:SOURce?` | `<source> ::= {CHANnel1 | CHANnel2 | CHANnel3 | CHANnel4}` | `CHANnel1, CHANnel2, CHANnel3, CHANnel4` | Установить/запросить источник триггера по длительности импульса. |
| `:TRIGger:PULSe:POLarity <polarity>` | `:TRIGger:PULSe:POLarity?` | `<polarity> ::= {POSItive | NEGAtive}` | `POSItive, NEGAtive` | Установить/запросить полярность импульса. |
| `:TRIGger:PULSe:WHEN <when>` | `:TRIGger:PULSe:WHEN?` | `<when> ::= {EQUAl | NEQUal | GREAt | LESS}` **[sic: возвраты показаны как "EQUAI, NEQUal, GRAt, LESS"]** | `EQUAl, NEQUal, GREAt, LESS` | Установить/запросить условие триггера по длительности импульса (=, ≠, >, <; погрешность длительности импульса 5%). |
| `:TRIGger:PULSe:WIDth <value>` | `:TRIGger:PULSe:WIDth?` | `<value> ::=` время триггера по длительности импульса (секунды) | Длительность импульса, научная нотация | Установить/запросить время триггера по длительности импульса. |
| `:TRIGger:PULSe:LEVel <level>` | `:TRIGger:PULSe:LEVel?` | `<level> ::=` уровень триггера (V) | Уровень, научная нотация | Установить/запросить уровень триггера по длительности импульса. |

### 4.8 TRIGger:SLOPe

| Команда | Запрос | Параметры / Диапазон | Возвращает | Описание |
|---|---|---|---|---|
| `:TRIGger:SLOPe:SOURce <source>` | `:TRIGger:SLOPe:SOURce?` | `<source> ::= {CHANnel1 | CHANnel2 | CHANnel3 | CHANnel4}` | `CHANnel1, CHANnel2, CHANnel3, CHANnel4` | Установить/запросить источник триггера по наклону. |
| `:TRIGger:SLOPe:POLarity <polarity>` | `:TRIGger:SLOPe:POLarity?` | `<polarity> ::= {POSItive | NEGAtive}` | `POSItive, NEGAtive` | Установить/запросить полярность триггера по наклону. |
| `:TRIGger:SLOPe:WHEN <when>` | `:TRIGger:SLOPe:WHEN?` | `<when> ::= {EQUAl | NEQUal | GREAt | LESS}` | `EQUAl, NEQUal, GREAt, LESS` | Установить/запросить условие триггера по наклону (=, ≠, >, <; погрешность 5%). |
| `:TRIGger:SLOPe:WIDth <value>` | `:TRIGger:SLOPe:WIDth?` | `<value> ::=` значение условия триггера (секунды) | Время, научная нотация | Установить/запросить время условия триггера по наклону. |
| `:TRIGger:SLOPe:ALEVel <level>` | `:TRIGger:SLOPe:ALEVel?` | `<level> ::=` верхний предел уровня триггера (V) | Верхний предел, научная нотация | Установить/запросить верхний предел уровня триггера (уровень A). |
| `:TRIGger:SLOPe:BLEVel <level>` | `:TRIGger:SLOPe:BLEVel?` | `<level> ::=` нижний предел уровня триггера (V) | Нижний предел, научная нотация | Установить/запросить нижний предел уровня триггера (уровень B). |

### 4.9 TRIGger:TV

| Команда | Запрос | Параметры / Диапазон | Возвращает | Описание |
|---|---|---|---|---|
| `:TRIGger:TV:SOURce <source>` | `:TRIGger:TV:SOURce?` | `<source> ::= {CHANnel1 | CHANnel2 | CHANnel3 | CHANnel4}` | `CHANnel1, CHANnel2, CHANnel3, CHANnel4` | Установить/запросить источник видеотриггера. |
| `:TRIGger:TV:POLarity <polarity>` | `:TRIGger:TV:POLarity?` | `<polarity> ::= {POSItive | NEGAtive}` | `POSItive, NEGAtive` | Установить/запросить полярность видео. |
| `:TRIGger:TV:MODE <mode>` | `:TRIGger:TV:MODE?` | `<mode> ::= {ALINes | LINes | FIEld1 | FIEld2 | AFIelds}` | `ALINes, LINes, FIEld1, FIEld2, AFIelds` | Установить/запросить тип синхронизации видео (все строки / заданная строка / нечётное поле / чётное поле / все поля). |
| `:TRIGger:TV:LINE <line>` | `:TRIGger:TV:LINE?` | `<line> ::=` номер строки. NTSC: 1–525; PAL/SECAM: 1–625 | Целое число | Установить/запросить номер строки, когда тип синхронизации = заданная строка. |
| `:TRIGger:TV:STANdard <standard>` | `:TRIGger:TV:STANdard?` | `<standard> ::= {NTSC | PAL}` | `NTSC, PAL` | Установить/запросить стандарт видео. |
| `:TRIGger:VIDeo:LEVel <level>` | `:TRIGger:VIDeo:LEVel?` | `<level> ::=` уровень триггера (V) | Уровень, научная нотация | Установить/запросить уровень видеотриггера. **[Примечание: указано в разделе TV, но ключевое слово — `VIDeo`]** |

### 4.10 TRIGger:TIMeout

| Команда | Запрос | Параметры / Диапазон | Возвращает | Описание |
|---|---|---|---|---|
| `:TRIGger:TIMeout:SOURce <source>` | `:TRIGger:TIMeout:SOURce?` | `<source> ::= {CHANnel1 | CHANnel2 | CHANnel3 | CHANnel4}` | `CHANnel1, CHANnel2, CHANnel3, CHANnel4` | Установить/запросить источник триггера по тайм-ауту. |
| `:TRIGger:TIMeout:LEVel <level>` | `:TRIGger:TIMeout:LEVel?` | `<level> ::=` уровень триггера (V) | Уровень, научная нотация | Установить/запросить уровень триггера по тайм-ауту. |
| `:TRIGger:TIMeout:WIDth <value>` | `:TRIGger:TIMeout:WIDth?` | `<value> ::=` значение тайм-аута, диапазон 8 ns–10 s | Тайм-аут, научная нотация | Установить/запросить период тайм-аута. |
| `:TRIGger:TIMeout:POLarity <polarity>` | `:TRIGger:TIMeout:POLarity?` | `<polarity> ::= {POSItive | NEGAtive}` | `POSItive, NEGAtive` | Установить/запросить полярность фронта для тайм-аута (POS=нарастающий, NEG=спадающий). |

### 4.11 TRIGger:WINDOw

| Команда | Запрос | Параметры / Диапазон | Возвращает | Описание |
|---|---|---|---|---|
| `:TRIGger:WINDOw:SOURce <source>` | `:TRIGger:WINDOw:SOURce?` | `<source> ::= {CHANnel1 | CHANnel2 | CHANnel3 | CHANnel4}` | `CHANnel1, CHANnel2, CHANnel3, CHANnel4` | Установить/запросить источник оконного триггера. |
| `:TRIGger:WINDOw:ALEVel <level>` | `:TRIGger:WINDOw:ALEVel?` | `<level> ::=` верхний предел уровня триггера (V) | Верхний уровень, научная нотация | Установить/запросить верхний предел уровня триггера (уровень A). |
| `:TRIGger:WINDOw:BLEVel <level>` | `:TRIGger:WINDOw:BLEVel?` | `<level> ::=` нижний предел уровня триггера (V) | Нижний уровень, научная нотация | Установить/запросить нижний предел уровня триггера (уровень B). |

### 4.12 TRIGger:INTERVAl **[sic: ключевое слово напечатано как "INTERVAl"; вероятно INTerval]**

| Команда | Запрос | Параметры / Диапазон | Возвращает | Описание |
|---|---|---|---|---|
| `:TRIGger:INTERVAl:SOURce <source>` | `:TRIGger:INTERVAl:SOURce?` | `<source> ::= {CHANnel1 | CHANnel2 | CHANnel3 | CHANnel4}` | `CHANnel1, CHANnel2, CHANnel3, CHANnel4` | Установить/запросить источник интервального триггера. |
| `:TRIGger:INTERVAl:SLOp <slope>` | `:TRIGger:INTERVAl:SLOp?` | `<slope> ::= {RISIng | FALLing}` **[sic: ключевое слово "SLOp"; State добавляет DOUBle; возвраты "RISIng, FALLing, DOUBle"]** | `RISIng, FALLing, DOUBle` | Установить/запросить тип фронта интервала. |
| `:TRIGger:INTERVAl:WHEN <when>` | `:TRIGger:INTERVAl:WHEN?` | `<when> ::= {EQUAl | NEQUal | GREAt | LESS}` | `EQUAl, NEQUal, GREAt, LESS` | Установить/запросить условие интервального триггера (<, >, =, ≠). |
| `:TRIGger:INTERVAl:TIME <value>` | `:TRIGger:INTERVAl:TIME?` | `<value> ::=` время триггера (секунды), 8 ns–10 s | Время, научная нотация | Установить/запросить значение времени интервала. |
| `:TRIGger:INTERVAl:ALEVel <level>` | `:TRIGger:INTERVAl:ALEVel?` | `<level> ::=` уровень триггера (V) | Уровень, научная нотация | Установить/запросить уровень интервального триггера. |

### 4.13 TRIGger:UNDER_Am (триггер по короткому импульсу, runt) **[sic: ключевое слово "UNDER_Am"; в SETUp:ALL? называется "Runt"]**

| Команда | Запрос | Параметры / Диапазон | Возвращает | Описание |
|---|---|---|---|---|
| `:TRIGger:UNDER_Am:SOURce <source>` | `:TRIGger:UNDER_Am:SOURce?` | `<source> ::= {CHANnel1 | CHANnel2 | CHANnel3 | CHANnel4}` | `CHANnel1, CHANnel2, CHANnel3, CHANnel4` | Установить/запросить источник runt-триггера. |
| `:TRIGger:UNDER_Am:POLarity <polarity>` | `:TRIGger:UNDER_Am:POLarity?` | `<polarity> ::= {POSItive | NEGAtive}` | `POSItive, NEGAtive` | Установить/запросить полярность runt-импульса. |
| `:TRIGger:UNDER_Am:WHEN <when>` | `:TRIGger:UNDER_Am:WHEN?` | `<when> ::= {EQUAl | NEQUal | GREAt | LESS}` | `EQUAl, NEQUal, GREAt, LESS` | Установить/запросить квалификатор runt. |
| `:TRIGger:UNDER_Am:TIME <value>` | `:TRIGger:UNDER_Am:TIME?` | `<value> ::=` время триггера (секунды), 8 ns–10 s | Время, научная нотация | Установить/запросить время runt-триггера. |
| `:TRIGger:UNDER_Am:ALEVel <level>` | `:TRIGger:UNDER_Am:ALEVel?` | `<level> ::=` верхний предел уровня триггера (V) | Верхний уровень, научная нотация | Установить/запросить верхний предел уровня триггера (уровень A). |
| `:TRIGger:UNDER_Am:BLEVel <level>` | `:TRIGger:UNDER_Am:BLEVel?` | `<level> ::=` нижний предел уровня триггера (V) | Нижний уровень, научная нотация | Установить/запросить нижний предел уровня триггера (уровень B). |

### 4.14 TRIGger:UART

| Команда | Запрос | Параметры / Диапазон | Возвращает | Описание |
|---|---|---|---|---|
| `:TRIGger:UART:SOURce <source>` | `:TRIGger:UART:SOURce?` | `<source> ::= {CHANnel1 | CHANnel2 | CHANnel3 | CHANnel4}` | `CHANnel1, CHANnel2, CHANnel3, CHANnel4` | Установить/запросить источник триггера UART. |
| `:TRIGger:UART:CONdition <condition>` | `:TRIGger:UART:CONdition?` | `<condition> ::= {START | STOP | READ_DATA | PARITY_ERR | COM_ERR}` | `START, STOP, READ_DATA, PARITY_ERR, COM_ERR` | Установить/запросить условие триггера UART. |
| `:TRIGger:UART:BAUd <baud>` | `:TRIGger:UART:BAUd?` | `<baud> ::= 110 | 300 | 600 | 1200 | 2400 | 4800 | 9600 | 14400 | 19200 | 38400 | 57600 | 115200 | 230400 | 380400 | 460400 | 921600 | USER` | Целое число или `USER` | Установить/запросить скорость передачи UART (bps). |
| `:TRIGger:UART:ALEVel <level>` | `:TRIGger:UART:ALEVel?` | `<level> ::=` уровень триггера (V) | Уровень, научная нотация | Установить/запросить уровень триггера UART. |
| `:TRIGger:UART:DATA <data>` | `:TRIGger:UART:DATA?` | `<data> ::= (0 ~ (2^(n-1) - 1))`, где n = текущая ширина данных (5,6,7,8) | Целое число | Установить/запросить значение данных, когда условие UART = data. |
| `:TRIGger:UART:WIDTh <value>` | `:TRIGger:UART:WIDTh?` | `<value> ::= {5 | 6 | 7 | 8}` | `5, 6, 7 или 8` | Установить/запросить ширину бит данных, когда условие = data. |
| `:TRIGger:UART:PARIty <parity>` | `:TRIGger:UART:PARIty?` | `<parity> ::= {NONE | ODD | EVEN}` | `EVEN, ODD или NONE` | Установить/запросить режим контроля чётности/проверки. |

### 4.15 TRIGger:CAN

| Команда | Запрос | Параметры / Диапазон | Возвращает | Описание |
|---|---|---|---|---|
| `:TRIGger:CAN:SOURce <source>` | `:TRIGger:CAN:SOURce?` | `<source> ::= {CHANnel1 | CHANnel2 | CHANnel3 | CHANnel4}` | `CHANnel1, CHANnel2, CHANnel3, CHANnel4` | Установить/запросить источник триггера CAN. |
| `:TRIGger:CAN:IDLe <idle>` | `:TRIGger:CAN:IDLe?` | `<idle> ::= {LOW | HIGH}` | `LOW, HIGH` | Установить/запросить уровень покоя CAN. |
| `:TRIGger:CAN:BAUd <baud>` | `:TRIGger:CAN:BAUd?` | `<baud> ::= 10000 | 20000 | 33300 | 50000 | 62500 | 83300 | 100000 | 125000 | 250000 | 500000 | 800000 | 1000000 | USER` | Целое число | Установить/запросить скорость передачи CAN (bps). |
| `:TRIGger:CAN:CONdition <condition>` | `:TRIGger:CAN:CONdition?` | `<condition> ::= {FRAM_STARE | FRAM_REMO_ID | FRAM_DATA_ID | REMO/DATA_ID | DATA_ID/DATA | FRAM_REE | FRAM_OVERLOAD | ERR_ALL | ACK_ERR}` **[sic: "FRAM_STARE", "FRAM_REE" вероятно "FRAME_START", "FRAME_ERROR"]** | `FRAM_STARE, FRAM_REMO_ID, FRAM_DATA_ID, REMO/DATA_ID, DATA_ID/DATA, FRAM_REMO_ID_EXT, FRAM_DATA_ID_EXT, REMO/DATA_ID_EXT, DATA_ID/DATA_EXT, FRAM_REE, FRAM_OVERLOAD, ERR_ALL, ACK_ERR` | Установить/запросить условие триггера CAN. |
| `:TRIGger:CAN:ID <id>` | `:TRIGger:CAN:ID?` | `<id> ::= 0 ~ 28` | Целое число | Установить/запросить IDENTIFIER CAN. |
| `:TRIGger:CAN:DLC <dlc>` | `:TRIGger:CAN:DLC?` | `<dlc> ::= 4 цифры` | Целое число | Установить/запросить код длины данных CAN. |
| `:TRIGger:CAN:DATA <index>,<data>` | `:TRIGger:CAN:DATA? <index>` | `<data> ::= 8 цифр`; `<index> ::=` индекс данных 0–3 | Целое число | Установить/запросить значение данных триггера CAN по индексу. |
| `:TRIGger:CAN:ALEVel <level>` | `:TRIGger:CAN:ALEVel?` | `<level> ::=` уровень триггера (V) | Уровень, научная нотация | Установить/запросить уровень триггера CAN. **[sic: пример запроса напечатан странно как `:TRIGger:CAN:ALEVel? TRIGger:CAN:ALEVel?`]** |

### 4.16 TRIGger:LIN

| Команда | Запрос | Параметры / Диапазон | Возвращает | Описание |
|---|---|---|---|---|
| `:TRIGger:LIN:SOURce <source>` | `:TRIGger:LIN:SOURce?` | `<source> ::= {CHANnel1 | CHANnel2 | CHANnel3 | CHANnel4}` | `CHANnel1, CHANnel2, CHANnel3, CHANnel4` | Установить/запросить источник триггера LIN. |
| `:TRIGger:LIN:IDLe <idle>` | `:TRIGger:LIN:IDLe?` | `<idle> ::= {LOW | HIGH}` | `LOW, HIGH` | Установить/запросить уровень покоя LIN. |
| `:TRIGger:LIN:BAUd <baud>` | `:TRIGger:LIN:BAUd?` | `<baud> ::= 110 | 300 | 600 | 1200 | 2400 | 4800 | 9600 | 14400 | 19200 | 38400 | 57600 | 115200 | 230400 | 380400 | 460400 | 921600 | USER` | Целое число | Установить/запросить скорость передачи LIN (bps). |
| `:TRIGger:LIN:CONdition <condition>` | `:TRIGger:LIN:CONdition?` | `<condition> ::= {INTERVAL_FIELD | SYNC_FIELD | ID_FIELD | DATA | IDENTIFIER | ID_DATA}` | `INTERVAL_FIELD, SYNC_FIELD, ID_FIELD, DATA, IDENTIFIER, ID_DATA` | Установить/запросить условие триггера LIN. |
| `:TRIGger:LIN:ID <id>` | `:TRIGger:LIN:ID?` | `<id> ::= 6 цифр` | Целое число | Установить/запросить идентификатор LIN. |
| `:TRIGger:LIN:DATA <index>,<data>` | `:TRIGger:LIN:DATA? <index>` | `<data> ::= 8 цифр`; `<index> ::=` индекс данных 0–3 | Целое число | Установить/запросить значение данных триггера LIN по индексу. |
| `:TRIGger:LIN:ALEVel <level>` | `:TRIGger:LIN:ALEVel?` | `<level> ::=` уровень триггера (V) | Уровень, научная нотация | Установить/запросить уровень триггера LIN. |

### 4.17 TRIGger:IIC

| Команда | Запрос | Параметры / Диапазон | Возвращает | Описание |
|---|---|---|---|---|
| `:TRIGger:IIC:SDA:SOURce <source>` | `:TRIGger:IIC:SDA:SOURce?` | `<source> ::= {CHANnel1 | CHANnel2 | CHANnel3 | CHANnel4}` | `CHANnel1, CHANnel2, CHANnel3, CHANnel4` | Установить/запросить источник линии данных I²C (SDA). |
| `:TRIGger:IIC:SCL:SOURce <source>` | `:TRIGger:IIC:SCL:SOURce?` | `<source> ::= {CHANnel1 | CHANnel2 | CHANnel3 | CHANnel4}` | `CHANnel1, CHANnel2, CHANnel3, CHANnel4` | Установить/запросить источник линии тактирования I²C (SCL). |
| `:TRIGger:IIC:CONdition <condition>` | `:TRIGger:IIC:CONdition?` | `<condition> ::= {START | STOP | ACK_LOST | ADDR_NO_ACK | RESTART | READ_DATA}` | `START, STOP, ACK_LOST, ADDR_NO_ACK, RESTART, READ_DATA` | Установить/запросить условие триггера I²C. |
| `:TRIGger:IIC:ADDer <addr>` | `:TRIGger:IIC:ADDer?` | `<addr> ::= 8 цифр` | Целое число | Установить/запросить значение адреса, когда условие = address/address-data. |
| `:TRIGger:IIC:DATA <index>,<data>` | `:TRIGger:IIC:DATA? <index>` | `<data> ::= 8 цифр`; `<index> ::=` индекс данных 0–8 | Целое число | Установить/запросить значение данных, когда условие = data/address-data. |
| `:TRIGger:IIC:ALEVel <level>` | `:TRIGger:IIC:ALEVel?` | `<level> ::=` уровень триггера (V) | Уровень, научная нотация | Установить/запросить уровень триггера линии тактирования (SCL). |
| `:TRIGger:IIC:BLEVel <level>` | `:TRIGger:IIC:BLEVel?` | `<level> ::=` уровень триггера (V) | Уровень, научная нотация | Установить/запросить уровень триггера линии данных (SDA). |

### 4.18 TRIGger:SPI

| Команда | Запрос | Параметры / Диапазон | Возвращает | Описание |
|---|---|---|---|---|
| `:TRIGger:SPI:SDA:SOURce <source>` | `:TRIGger:SPI:SDA:SOURce?` | `<source> ::= {CHANnel1 | CHANnel2 | CHANnel3 | CHANnel4}` | `CHANnel1, CHANnel2, CHANnel3, CHANnel4` | Установить/запросить источник линии данных SPI. |
| `:TRIGger:SPI:SCL:SOURce <source>` | `:TRIGger:SPI:SCL:SOURce?` | `<source> ::= {CHANnel1 | CHANnel2 | CHANnel3 | CHANnel4}` | `CHANnel1, CHANnel2, CHANnel3, CHANnel4` | Установить/запросить источник линии тактирования SPI. |
| `:TRIGger:SPI:SCK <slope>` | `:TRIGger:SPI:SCK?` | `<slope> ::= {Rising | Falling}` | `Rising, Falling` | Установить/запросить тип тактового фронта SPI. |
| `:TRIGger:SPI:WIDth <width>` | `:TRIGger:SPI:WIDth?` | `<width> ::= 4 ~ 32` | Целое число | Установить/запросить ширину бит данных SPI. |
| `:TRIGger:SPI:DATA <data>` | `:TRIGger:SPI:DATA?` | `<data> ::= 0 ~ (2^32 - 1)` | Целое число | Установить/запросить значение данных SPI. |
| `:TRIGger:SPI:MASK <mask>` | `:TRIGger:SPI:MASK?` | `<mask> ::= 0 ~ (2^32 - 1)` | Целое число | Установить/запросить значение маски SPI. |
| `:TRIGger:SPI:ALEVel <level>` | `:TRIGger:SPI:ALEVel?` | `<level> ::=` уровень триггера (V) | Уровень, научная нотация | Установить/запросить уровень триггера тактового канала SPI. |
| `:TRIGger:SPI:BLEVel <level>` | `:TRIGger:SPI:BLEVel?` | `<level> ::=` уровень триггера (V) | Уровень, научная нотация | Установить/запросить уровень триггера канала данных SPI. |

### 4.19 TRIGger:PATTern

> **Примечание:** Список команд руководства и заголовок раздела используют `TRIGger:PATTern`, но примечание к SETUp:ALL? (§12.6) ссылается на ту же функцию через `TRIGger:LOGIc:POLarity/WHEN/TIME/ALEVel/BLEVel/CLEVel/DLEVel`. Разработчикам следует проверить, какое ключевое слово принимает устройство. Заголовок раздела 4.19.2 напечатан как `TRIGger:PATTern:LEVel`.

| Команда | Запрос | Параметры / Диапазон | Возвращает | Описание |
|---|---|---|---|---|
| `:TRIGger:PATTern:PATTern <pa_ch1>[,<pa_ch2>[,<pa_ch3>[,<pa_ch4>[,<pa_d0>…[,<pa_d15>]]]]]` | `:TRIGger:PATTern:PATTern?` | См. разбор полей ниже; каждое `::= {H | L | X}` | Шаблон для 4 аналоговых + всех каналов, через запятую | Установить/запросить покаждоканальный шаблон при триггере по шаблону. |
| `:TRIGger:PATTern:LEVel <chan>,<level>` | `:TRIGger:PATTern:LEVel? <chan>` | `<chan> ::= CHANnel<n>`; `<level> ::=` Целое число, диапазон от `(-5 × VerticalScale − OFFSet)` до `(5 × VerticalScale − OFFSet)`, по умолчанию 0 | Уровень, научная нотация | Установить/запросить уровень триггера указанного канала. Действительно только когда выбранный источник — аналоговый канал. |

**Разбор полей `:TRIGger:PATTern:PATTern`:**
- `<pa_ch1>` – Дискретное `{H | L | X}`, по умолчанию `X` — шаблон аналогового канала CH1
- `<pa_ch2>` – Дискретное `{H | L | X}`, по умолчанию `X` — шаблон аналогового канала CH2
- `<pa_ch3>` – Дискретное `{H | L | X}`, по умолчанию `X` — шаблон аналогового канала CH3
- `<pa_ch4>` – Дискретное `{H | L | X}`, по умолчанию `X` — шаблон аналогового канала CH4
- `<pa_D10>` … `<pa_D43>` – Дискретное `{H | L | X}`, по умолчанию `C` — шаблоны цифровых каналов
- **Семантика:** H = высокий уровень (выше порога канала); L = низкий уровень (ниже порога); X = игнорировать этот канал. Если все каналы установлены в X, осциллограф не сработает.
- Можно отправить до 20 параметров для всех каналов; пропущенные параметры сохраняют своё предыдущее состояние, но как минимум один параметр (CH1) должен быть отправлен. Когда отправлено менее 20, прибор по умолчанию устанавливает CH1–CH4 и D10–D43 по порядку.

---

## 5. Подсистема CALibrate

| Команда | Запрос | Параметры / Диапазон | Возвращает | Описание |
|---|---|---|---|---|
| `:CALibrate:STARt` | — | (без параметров) | — | Запустить самокалибровку. Сначала отсоедините все сигналы; большинство ключевых функций отключены во время калибровки. |
| — | `:CALibrate:STATus?` | (только запрос) | Состояние калибровки | Запросить текущее состояние калибровки. |
| `:CALibrate:QUIT` | — | (без параметров) | — | Выйти из самокалибровки в любой момент. |

---

## 6. Подсистема MATH

Алгебраические операции (ADD/SUBtract/MULTiply/DIVision) и БПФ (FFT).

| Команда | Запрос | Параметры / Диапазон | Возвращает | Описание |
|---|---|---|---|---|
| `:MATH:DISPlay <bool>` | `:MATH:DISPlay?` | `<bool> ::= {{1 | ON} | {0 | OFF}}` | `ON, OFF` | Включить/выключить функцию математических операций. |
| `:MATH:OPERator <type>` | `:MATH:OPERator?` | `<type> ::= {ADD | SUBtract | MULTiply | DIVision | FFT}` | `ADD, SUBtract, MULTiply, DIVision, FFT` | Установить/запросить математический оператор. |
| `:MATH:SOURce1 <source>` | `:MATH:SOURce1?` | `<source> ::= {CHANnel1 | CHANnel2 | CHANnel3 | CHANnel4}` | `CHANnel1, CHANnel2, CHANnel3, CHANnel4` | Установить/запросить источник A алгебраической операции. |
| `:MATH:SOURce2 <source>` | `:MATH:SOURce2?` | `<source> ::= {CHANnel1 | CHANnel2 | CHANnel3 | CHANnel4}` | `CHANnel1, CHANnel2, CHANnel3, CHANnel4` | Установить/запросить источник B алгебраической операции. |
| `:MATH:SCALe <value>` | `:MATH:SCALe?` | `<value> ::=` вертикальный масштаб в последовательности 1-2-5, единица V | Вертикальный масштаб, научная нотация | Установить/запросить вертикальный масштаб результата операции. Единица зависит от выбранного оператора/источника. |
| `:MATH:OFFSet <value>` | `:MATH:OFFSet?` | `<value> ::=` значение смещения, единица V | Вертикальное смещение, научная нотация | Установить/запросить вертикальное смещение результата операции. |
| `:MATH:FFT:SOURce <source>` | `:MATH:FFT:SOURce?` | `<source> ::= {CHANnel1 | CHANnel2 | CHANnel3 | CHANnel4}` | `CHANnel1, CHANnel2, CHANnel3, CHANnel4` | Установить/запросить источник операции БПФ. |
| `:MATH:FFT:WINDow <window>` | `:MATH:FFT:WINDow?` | `<window> ::= {RECTangle | HANNing | HAMMing | BLACkman | TRIangle | FLATtop}` | `RECTangle, HANNing, HAMMing, BLACkman, TRIangle, FLATtop` | Установить/запросить оконную функцию БПФ. |
| `:MATH:FFT:UNIT <unit>` | `:MATH:FFT:UNIT?` | `<unit> ::= {VRMS | DB}` | `VRMS, DB` | Установить/запросить вертикальную единицу БПФ. |
| `:MATH:FFT:HSCale <hscale>` | `:MATH:FFT:HSCale?` | `<hscale> ::= {125000 | 250000 | 625000 | 1250000}` | Горизонтальный масштаб, научная нотация | Установить/запросить горизонтальный масштаб БПФ (Hz, единица по умолчанию Hz). |
| `:MATH:FFT:HCENter <center>` | `:MATH:FFT:HCENter?` | `<center> ::=` центральная частота (Hz) | Центральная частота, научная нотация | Установить/запросить центральную частоту БПФ (соответствующую горизонтальному центру экрана). |

---

## 7. Подсистема WAVeform

| Команда | Запрос | Параметры / Диапазон | Возвращает | Описание |
|---|---|---|---|---|
| — | `:WAVeform:DATA:ALL?` | (только запрос) | Пакет данных осциллограммы (строка) с заголовком данных | Прочитать данные осциллограммы. Возвращает пакет, содержащий заголовок данных, за которым следуют данные осциллограммы. |

**`:WAVeform:DATA:ALL?` — структура заголовка при первом чтении (анализ `data[x]`):**
- `data[0]–data[1]` (2 цифры): `#9`
- `data[2]–data[10]` (9 цифр): длина текущего пакета в байтах
- `data[11]–data[19]` (9 цифр): общая длина в байтах, представляющая объём данных
- `data[20]–data[28]` (9 цифр): длина выгруженных данных в байтах
- `data[29]` (1 цифра): текущее состояние работы
- `data[30]` (1 цифра): состояние триггера
- `data[31]–data[34]` (4 цифры): смещение канала 1
- `data[35]–data[38]` (4 цифры): смещение канала 2
- `data[39]–data[42]` (4 цифры): смещение канала 3
- `data[43]–data[46]` (4 цифры): смещение канала 4
- `data[47]–data[53]` (7 цифр): напряжение канала 1
- `data[54]–data[60]` (7 цифр): напряжение канала 2
- `data[61]–data[67]` (7 цифр): напряжение канала 3
- `data[68]–data[74]` (7 цифр): напряжение канала 4
- `data[75]–data[78]` (4 цифры): включение канала (1–4)
- `data[79]–data[87]` (9 цифр): частота дискретизации
- `data[88]–data[93]` (6 цифр): множитель дискретизации
- `data[94]–data[102]` (9 цифр): отображаемое время триггера текущего кадра
- `data[103]–data[111]` (9 цифр): точка начала отображения текущего кадра относительно момента начала сбора данных
- `data[112]–data[127]` (16 цифр): зарезервированные биты

**`:WAVeform:DATA:ALL?` — последующие чтения (заголовок данных повторно выдаётся перед чтением данных):**
- `data[0]–data[1]` (2 цифры): `#9`
- `data[2]–data[10]` (9 цифр): длина текущего пакета данных в байтах
- `data[11]–data[19]` (9 цифр): общая длина в байтах, представляющая объём данных
- `data[20]–data[28]` (9 цифр): длина выгруженных данных в байтах
- `data[29]–data[x]`: данные осциллограммы, соответствующие текущему заголовку данных

---

## 8. Подсистема DISPlay

| Команда | Запрос | Параметры / Диапазон | Возвращает | Описание |
|---|---|---|---|---|
| `:DISPlay:TYPE <type>` | `:DISPlay:TYPE?` | `<type> ::= {VECTors | DOTS}` | `VECT, DOTS` **[sic: возврат "VECT", а не "VECTors"]** | Установить/запросить тип отображения осциллограммы (векторы соединяют точки; точки показывают отсчёты). |
| `:DISPlay:WBRightness <value>` | `:DISPlay:WBRightness?` | `<value> ::=` от 0 до 100 | Целое число | Установить/запросить яркость отображения осциллограммы. |
| `:DISPlay:GRID <type>` | `:DISPlay:GRID?` | `<type> ::= {DOTTed | REAL}` | `DOTTed, REAL` | Установить/запросить тип сетки (точечная / линейная). |
| `:DISPlay:GBRightness <value>` | `:DISPlay:GBRightness?` | `<value> ::=` от 0 до 100 | Целое число | Установить/запросить яркость сетки экрана. **[sic: пример показан с использованием `:DISPlay:WBRightness`]** |

---

## 9. Подсистема CURSor

Измеряет значения по оси X (например, время) и по оси Y (например, напряжение) осциллограммы на экране.

| Команда | Запрос | Параметры / Диапазон | Возвращает | Описание |
|---|---|---|---|---|
| `:CURSor:MODE <type>` | `:CURSor:MODE?` | `<type> ::= {OFF | MANual | TRACk}` | `OFF, MANual, TRACK` | Установить/запросить режим курсорных измерений. |
| `:CURSor:MANual:TYPE <type>` | `:CURSor:MANual:TYPE?` | `<type> ::= {X | Y | XY}` | `X, Y, XY` | Установить/запросить тип ручного курсора. |
| `:CURSor:MANual:SOURce <source>` | `:CURSor:MANual:SOURce?` | `<source> ::= {CHANnel1 | CHANnel2 | MATH}` | `CHANnel1, CHANnel2, MATH` | Установить/запросить источник канала для ручного курсора. |
| `:CURSor:MANual:AX <value>` | `:CURSor:MANual:AX?` | `<value> ::=` от 0 до 770 | Целое число | Установить/запросить горизонтальную позицию курсора A (пиксель). |
| — | `:CURSor:MANual:AXValue?` | (только запрос) | Значение X в курсоре A, научная нотация | Запросить значение X в курсоре A; единица согласно выбранной горизонтальной единице. |
| `:CURSor:MANual:AY <value>` | `:CURSor:MANual:AY?` | `<value> ::=` от 0 до 400 | Целое число (0–400) | Установить/запросить вертикальную позицию курсора A (пиксель). |
| — | `:CURSor:MANual:AYValue?` | (только запрос) | Значение Y в курсоре A, научная нотация | Запросить значение Y в курсоре A; единица согласно выбранной вертикальной единице. |
| `:CURSor:MANual:BX <value>` | `:CURSor:MANual:BX?` | `<value> ::=` от 0 до 770 | Целое число (0–770) | Установить/запросить горизонтальную позицию курсора B (пиксель). |
| — | `:CURSor:MANual:BXValue?` | (только запрос) | Значение X в курсоре B, научная нотация | Запросить значение X в курсоре B; единица согласно выбранной горизонтальной единице. |
| `:CURSor:MANual:BY <value>` | `:CURSor:MANual:BY?` | `<value> ::=` от 0 до 400 | Целое число (0–400) | Установить/запросить вертикальную позицию курсора B (пиксель). |
| — | `:CURSor:MANual:BYValue?` | (только запрос) | Значение Y в курсоре B, научная нотация | Запросить значение Y в курсоре B; единица согласно выбранной вертикальной единице. |
| `:CURSor:TRACk:SOURcea <source>` | `:CURSor:TRACk:SOURcea?` | `<source> ::= {CHANnel1 | CHANnel2 | CHANnel3 | CHANnel4 | MATH}` | `CHANnel1, CHANnel2, CHANnel3, CHANnel4 или MATH` | Установить/запросить источник канала курсора A в режиме слежения. |
| `:CURSor:TRACk:SOURceb <source>` | `:CURSor:TRACk:SOURceb?` | `<source> ::= {CHANnel1 | CHANnel2 | CHANnel3 | CHANnel4 | MATH}` | `CHANnel1, CHANnel2, CHANnel3, CHANnel4 или MATH` | Установить/запросить источник канала курсора B в режиме слежения. |
| `:CURSor:TRACk:AX <value>` | `:CURSor:TRACk:AX?` | `<value> ::=` от 0 до 770 | Целое число (0–770) | Установить/запросить горизонтальную позицию курсора A в режиме слежения. |
| — | `:CURSor:TRACk:AXValue?` | (только запрос) | Значение X в курсоре A, научная нотация (единица по умолчанию — секунда) | Запросить значение X в курсоре A в режиме слежения. |
| — | `:CURSor:TRACk:AY?` | (только запрос) | Целое число | Запросить вертикальную позицию курсора A в режиме слежения. |
| — | `:CURSor:TRACk:AYValue?` | (только запрос) | Значение Y в курсоре A, научная нотация | Запросить значение Y в курсоре A; единица согласно выбранной единице канала. |
| `:CURSor:TRACk:BX <value>` | `:CURSor:TRACk:BX?` | `<value> ::=` от 0 до 770 | Целое число (0–770) | Установить/запросить горизонтальную позицию курсора B в режиме слежения. |
| — | `:CURSor:TRACk:BXValue?` | (только запрос) | Значение X в курсоре B, научная нотация (единица по умолчанию — секунда) | Запросить значение X в курсоре B в режиме слежения. |
| — | `:CURSor:TRACk:BY?` | (только запрос) | Целое число | Запросить вертикальную позицию курсора B в режиме слежения. |
| — | `:CURSor:TRACk:BYValue?` | (только запрос) | Значение Y в курсоре B, научная нотация | Запросить значение Y в курсоре B; единица согласно выбранной единице канала. |

---

## 10. Подсистема MEASure

| Команда | Запрос | Параметры / Диапазон | Возвращает | Описание |
|---|---|---|---|---|
| `:MEASure:ENABle <bool>` | `:MEASure:ENABle?` | `<bool> ::= {{1 | ON} | {0 | OFF}}` | `ON, OFF` | Установить/запросить состояние функции измерений. |
| `:MEASure:SOURce <source>` | `:MEASure:SOURce?` | `<source> ::= {CHANnel1 | CHANnel2 | CHANnel3 | CHANnel4 | MATH}` | `CHANnel1, CHANnel2, CHANnel3, CHANnel4, MATH` | Установить/запросить источник текущих параметров измерения. |
| `:MEASure:ADISplay <bool>` | `:MEASure:ADISplay?` | `<bool> ::= {{1 | ON} | {0 | OFF}}` | `ON, OFF` | Включить/выключить все измерения (All-Display). |
| `:MEASure:CHANnel<n>:ITEM <type>` | `:MEASure:CHANnel<n>:ITEM?` | `<n> ::= {1 | 2 | 3 | 4}`; `<type>` см. список ниже | Результат измерения (например, `VPP 3.600e-01`) | Запросить результат измерения указанного параметра. **[sic: заголовок напечатан с пробелом "MEASure: CHANnel<n>:ITEM"]** |
| `:MEASure:GATE:ENABle <bool>` | `:MEASure:GATE:ENABle?` | `<bool> ::= {{1 | ON} | {0 | OFF}}` | `ON, OFF` | Установить/запросить состояние стробирования. |
| `:MEASure:GATE:AY <value>` | `:MEASure:GATE:AY?` | `<value> ::=` от 0 до 400 | Целое число | Установить/запросить значение строб-курсора A. |
| `:MEASure:GATE:BY <value>` | `:MEASure:GATE:BY?` | `<value> ::=` от 0 до 400 | Целое число | Установить/запросить значение строб-курсора B. |

**Перечисление `<type>` измерений `:MEASure:CHANnel<n>:ITEM` (дословно):**
`MAX, VMIN, VPP, VTOP, VBASe, VAMP, VAVG, VRMS, OVERshoot, PREShoot, MARea, MPARea, PERiod, FREQuency, RTIMe, FTIMe, PWIDth, NWIDth, PDUTy, NDUTy, RDELay, FDELay, RPHase, FPHase, TVMAX, TVMIN, PSLEWrate, NSLEWrate, VUPper, VMID, VLOWer, VARIance, PVRMS, PPULses, NPULses, PEDGes, NEDGes`

> **Hardware-verified (2026-06-27, S/N CN2352029065656, FW 3.0.0):**
> - **Чтение значения:** только форма `:MEASure:CHANnel<n>:ITEM? <type>` (тип — АРГУМЕНТ запроса). Ответ — float NR3, напр. `2.080e+00`. Форма «set `:MEASure:CHANnel<n>:ITEM <type>`, затем bare `:MEASure:CHANnel<n>:ITEM?`» НЕ работает (bare-query отдаёт мусор). README дизайна (`:MEAS:VPP? CHAN1`, `:MEASure:VPP? CHANnel1`) → VisaIOError, неверно.
> - **`MAX` — опечатка `VMAX`:** `MAX` → sentinel `1.000e+03`; `VMAX` → корректное значение. В коде драйвера (`scpi/measure.py`) используется `VMAX`. (Список выше асимметричен: `MAX`/`VMIN` без пары — подтверждает опечатку.)
> - **Sentinel `1.000e+03`** = «измерение недоступно для этого item/источника» (напр. межканальные `RDELay/FDELay/RPHase/FPHase` при source=одного канала; часть item'ов на меандре). Внимание: для `FREQuency` значение `1.000e+03` может быть РЕАЛЬНЫМ (1 кГц) — sentinel неотличим по значению, не фильтруется автоматически.
> - **Полная per-литерал карта валидности** (какие item'ы реально считаются на разных сигналах/2 каналах) — TODO следующего hardware-прохода; драйвер пока принимает весь канонический список.

---

## 11. Подсистема MASK (тест допуск/брак, Pass/Fail)

| Команда | Запрос | Параметры / Диапазон | Возвращает | Описание |
|---|---|---|---|---|
| `:MASK:EANBle <bool>` | `:MASK:EANBle?` | `<bool> ::= {{1 | ON} | {0 | OFF}}` | `ON, OFF` | Включить/выключить функцию теста допуск/брак. **[sic: ключевое слово "EANBle"; почти наверняка ENABle — разработчикам следует протестировать буквальное "EANBle"]** |
| `:MASK:SOURce <source>` | `:MASK:SOURce?` | `<source> ::= {CHANnel1 | CHANnel2 | MATH}` | `CHANnel1, CHANnel2, MATH` | Установить/запросить источник измерения для теста допуск/брак. |
| `:MASK:MDISplay <bool>` | `:MASK:MDISplay?` | `<bool> ::= {{1 | ON} | {0 | OFF}}` | `ON, OFF` | Включить/выключить отображение статистики допуск/брак. |
| `:MASK:OUTPut <bool>` | `:MASK:OUTPut?` | `<bool> ::= {{1 | ON} | {0 | OFF}}` | `ON, OFF` | Включить/выключить выход (остановка при браке). ON: при браке остановить тест и перейти в STOP, выдать один импульс на [Trigger Out]; OFF: продолжить тест, импульс на каждую бракованную осциллограмму. |
| `:MASK:SOOutput <bool>` | `:MASK:SOOutput?` | `<bool> ::= {{1 | ON} | {0 | OFF}}` | `ON, OFF` | Включить/выключить звуковое оповещение при браке теста (Sound-Output). |
| `:MASK:X <value>` | `:MASK:X?` | `<value> ::= 0.02 ~ 4`, единица по умолчанию div | Регулировка уровня, научная нотация | Установить/запросить параметр горизонтальной (уровневой) регулировки в правиле допуск/брак. |
| `:MASK:Y <value>` | `:MASK:Y?` | `<value> ::= 0.04 ~ 5.12`, единица по умолчанию div | Вертикальная регулировка, научная нотация | Установить/запросить параметр вертикальной регулировки в правиле допуск/брак. |
| `:MASK:CREate` | — | (без параметров) | — | Создать правило допуск/брак с текущими параметрами горизонтальной/вертикальной регулировки. Действительно только когда MASK:ENABle включён и тест не запущен (MASK:OPERate). |

---

## 12. Подсистема SYSTem

| Команда | Запрос | Параметры / Диапазон | Возвращает | Описание |
|---|---|---|---|---|
| — | `:SYSTem:GAM?` | (только запрос) | `12` | Запросить число горизонтальных делений сетки на экране. |
| — | `:SYSTem:RAM?` | (только запрос) | `4` | Запросить число аналоговых каналов прибора. |
| `:SYSTem:PON <value>` | `:SYSTem:PON?` | `<value> ::= {LATest | DEFault}` | `LATest, DEFault` | Установить/запросить тип конфигурации при включении питания. |
| `:SYSTem:LANGuage <value>` | `:SYSTem:LANGuage?` | `<value> ::= {ENGLish | SCHinese}` | `ENGLish, SCHinese` | Установить/запросить язык отображения системы. |
| `:SYSTem:LOCKed <bool>` | `:SYSTem:LOCKed?` | `<bool> ::= {{1 | ON} | {0 | OFF}}` | `ON, OFF` | Включить/выключить блокировку клавиатуры. |
| — | `:SETUp:ALL?` | (только запрос) | Строка всех настроек, каждое состояние разделено `;` | Получить все состояния, необходимые для загрузки, за один раз. См. разбор полей ниже. |

**`:SETUp:ALL?` — возвращаемые настройки (разделены точкой с запятой, дословный список полей):**
- Включение канала: `CHANnel<n>:DISPlay`
- Связь канала по входу: `CHANnel<n>:COUPling`
- Ограничение полосы канала: `CHANnel<n>:BWLimit`
- Коэффициент пробника: `CHANnel<n>:PROBe`
- Ступень напряжения: `<>`
- Смещение канала: смещение (одно значение) осциллограммы относительно центральной линии (нулевой центр; вверх положительное, вниз отрицательное). Большие деления представляют 25 значений (например, значение смещения CH1 = 75 соответствует смещению центра на три больших деления).
- Инверсия канала: `CHANnel<n>:INVert`
- Состояние работы: `RUNning`
- Режим сбора данных: `ACQuire:MODe`
- Тип сбора: `ACQuire:TYPE`
- Метод триггера: `TRIGger:SWEep`
- Значение развёртки: `TIMebase:SCALe`
- (Заполнитель)
- Частота дискретизации: текущее значение частоты дискретизации
- Глубина памяти: `ACQuire:POINts`
- Тип триггера: `TRIGger:MODE`
- (Заполнитель)
- Источник триггера по фронту: `TRIGger:EDGe:SOURce`
- Уровень триггера по фронту: `TRIGger:EDGe:LEVel`
- Полярность триггера по фронту: `TRIGger:EDGe:SLOPe`
- Источник триггера по длительности импульса: `TRIGger:PULSe:SOURce`
- Уровень триггера по длительности импульса: `TRIGger:PULSe:LEVel`
- Полярность триггера по длительности импульса: `TRIGger:PULSe:POLarity`
- Условие триггера по длительности импульса: `TRIGger:PULSe:WHEN`
- Ширина триггера по длительности импульса: `TRIGger:PULSe:WIDth`
- Источник триггера по тайм-ауту: `TRIGger:TIMeout:SOURce`
- Уровень триггера по тайм-ауту: `TRIGger:TIMeout:LEVel`
- Полярность триггера по тайм-ауту: `TRIGger:TIMeout:POLarity`
- Ширина триггера по тайм-ауту: `TRIGger:TIMeout:WIDth`
- Источник триггера по наклону: `TRIGger:SLOPe:SOURce`
- Уровень a триггера по наклону: `TRIGger:SLOPe:ALEVel`
- Уровень b триггера по наклону: `TRIGger:SLOPe:BLEVel`
- Полярность триггера по наклону: `TRIGger:SLOPe:POLarity`
- Условия триггера по наклону: `TRIGger:SLOPe:WHEN`
- Ширина триггера по наклону: `TRIGger:SLOPe:WIDth`
- Источник видеотриггера: `TRIGger:TV:SOURce`
- Уровень видеотриггера: `TRIGger:VIDeo:LEVel`
- Полярность видеотриггера: `TRIGger:TV:POLarity`
- Стандарт видеотриггера: `TRIGger:TV:STANdard`
- Синхронизация видеотриггера: `TRIGger:TV:MODE`
- Число строк, запускаемых видеотриггером: `TRIGger:TV:LINE`
- Источник оконного триггера: `TRIGger:WINDOw:SOURce`
- Уровень a оконного триггера: `TRIGger:WINDOw:ALEVel`
- Уровень b оконного триггера: `TRIGger:WINDOw:BLEVel`
- Источник интервального триггера: `TRIGger:INTERVAl:SOURce`
- Фронт интервального триггера: `TRIGger:INTERVAl:SLOp`
- Условие интервального триггера: `TRIGger:INTERVAl:WHEN`
- Время интервального триггера: `TRIGger:INTERVAl:TIME`
- Уровень интервального триггера: `TRIGger:INTERVAl:ALEVel`
- Источник runt-триггера: `TRIGger:UNDER_Am:SOURce`
- Полярность runt-триггера: `TRIGger:UNDER_Am:POLarity`
- Условие runt-триггера: `TRIGger:UNDER_Am:WHEN`
- Время runt-триггера: `TRIGger:UNDER_Am:TIME`
- Уровень a runt-триггера: `TRIGger:UNDER_Am:ALEVel`
- Уровень b runt-триггера: `TRIGger:UNDER_Am:BLEVel`
- Источник триггера последовательного порта: `TRIGger:UART:SOURce`
- Условия триггера последовательного порта: `TRIGger:UART:CONdition`
- Скорость передачи триггера последовательного порта: `TRIGger:UART:BAUd`
- Уровень триггера последовательного порта: `TRIGger:UART:ALEVel`
- Данные триггера последовательного порта: `TRIGger:UART:DATA`
- Ширина бит данных триггера последовательного порта: `TRIGger:UART:WIDTh`
- Стоп-бит триггера последовательного порта: `TRIGger:UART:STOP`
- Полярность триггера последовательного порта: `TRIGger:UART:PARIty`
- Источник триггера CAN: `TRIGger:CAN:SOURce`
- Уровень покоя триггера CAN: `TRIGger:CAN:IDLe`
- Скорость передачи триггера CAN: `TRIGger:CAN:BAUd`
- Условие триггера CAN: `TRIGger:CAN:CONdition`
- Данные триггера CAN: `TRIGger:CAN:DATA`
- ID триггера CAN: `TRIGger:CAN:ID`
- dlc триггера CAN: `TRIGger:CAN:DLC`
- Уровень триггера CAN: `TRIGger:CAN:ALEVel`
- Источник триггера LIN: `TRIGger:LIN:SOURce`
- Уровень покоя триггера LIN: `TRIGger:LIN:IDLe`
- Скорость передачи триггера LIN: `TRIGger:LIN:BAUd`
- Условие триггера LIN: `TRIGger:LIN:CONdition`
- ID триггера LIN: `TRIGger:LIN:ID`
- Данные триггера LIN: `TRIGger:LIN:DATA`
- Уровень триггера LIN: `TRIGger:LIN:ALEVel`
- Источник канала линии данных триггера IIC: `TRIGger:IIC:SDA:SOURce`
- Источник канала линии тактирования триггера IIC: `TRIGger:IIC:SCL:SOURce`
- Условие триггера IIC: `TRIGger:IIC:CONdition`
- Адрес триггера IIC: `TRIGger:IIC:ADDer`
- Данные триггера IIC: `TRIGger:IIC:DATA`
- Уровень тактового канала триггера IIC: `TRIGger:IIC:ALEVel`
- Уровень канала данных триггера IIC: `TRIGger:IIC:BLEVel`
- Источник канала линии данных триггера SPI: `TRIGger:SPI:SDA:SOURce`
- Источник канала линии тактирования триггера SPI: `TRIGger:SPI:SCL:SOURce`
- Тип тактового фронта триггера SPI: `TRIGger:SPI:SCK`
- Ширина бит данных триггера SPI: `TRIGger:SPI:WIDth`
- Данные триггера SPI: `TRIGger:SPI:DATA`
- Данные маски триггера SPI: `TRIGger:SPI:MASK`
- Уровень тактового канала триггера SPI: `TRIGger:SPI:ALEVel`
- Уровень канала данных триггера SPI: `TRIGger:SPI:BLEVel`
- Триггер по шаблону: `TRIGger:LOGIc:POLarity`
- Условия триггера по шаблону: `TRIGger:LOGIc:WHEN`
- Ширина триггера по шаблону: `TRIGger:LOGIc:TIME`
- Уровень CH1 триггера по шаблону: `TRIGger:LOGIc:ALEVel`
- Уровень CH2 триггера по шаблону: `TRIGger:LOGIc:BLEVel`
- Уровень CH3 триггера по шаблону: `TRIGger:LOGIc:CLEVel`
- Уровень CH4 триггера по шаблону: `TRIGger:LOGIc:DLEVel`

> **Примечание:** Примечание к SETUp:ALL? ссылается на ключевые слова триггеров (`TRIGger:UART:STOP`, `TRIGger:LOGIc:*`, `TRIGger:CAN:DATA` без индекса и т. д.), которые не все присутствуют как отдельные документированные команды в §4. Они могут быть внутренними/недокументированными или альтернативными написаниями команд PATTern.

---

## 13. Подсистема DDS (встроенный источник сигнала / AWG)

| Команда | Запрос | Параметры / Диапазон | Возвращает | Описание |
|---|---|---|---|---|
| `:DDS:SWITch <bool>` | `:DDS:SWITch?` | `<bool> ::= {{1 | ON} | {0 | OFF}}` | `ON, OFF` | Установить/запросить состояние источника сигнала (выход вкл/выкл). |
| `:DDS:TYPE <type>` | `:DDS:TYPE?` | `<type> ::= {SINE | SQUAre | RAMP | EXP | NOISe | DC | ARB1 | ARB2 | ARB3 | ARB4}` | `SINE, SQUAre, RAMP, EXP, NOISe, DC, ARB1, ARB2, ARB3, ARB4` | Установить/запросить тип выходной волны источника сигнала. |
| `:DDS:FREQ <freq>` | `:DDS:FREQ?` | `<freq> ::=` единица Hz | Частота, научная нотация | Установить/запросить частоту сигнала источника. |
| `:DDS:AMP <amp>` | `:DDS:AMP?` | `<amp> ::=` единица V | Амплитуда, научная нотация | Установить/запросить амплитуду источника сигнала. |
| `:DDS:OFFSet <offset>` | `:DDS:OFFSet?` | `<offset> ::=` единица V | Смещение, научная нотация | Установить/запросить смещение сигнала источника. |
| `:DDS:DUTY <duty>` | `:DDS:DUTY?` | `<duty> ::= 0 ~ 99` | Значение коэффициента заполнения | Установить/запросить коэффициент заполнения источника сигнала. |
| `:DDS:WAVE:MODE <bool>` | `:DDS:WAVE:MODE?` | `<bool> ::= {{1 | ON} | {0 | OFF}}` | `ON, OFF` | Установить/запросить состояние модуляции источника сигнала. |
| `:DDS:MODE:TYPE <type>` | `:DDS:MODE:TYPE?` | `<type> ::= {AM | FM}` | `AM, FM` | Установить/запросить тип модуляции источника сигнала. |
| `:DDS:MODE:WAVE:TYPE <type>` | `:DDS:MODE:WAVE:TYPE?` | `<type> ::= {SINE | SQUAre | RAMP}` | `SINE, SQUAre, RAMP` | Установить/запросить тип модулирующей волны при модуляции. |
| `:DDS:MODE:FREQ <freq>` | `:DDS:MODE:FREQ?` | `<freq> ::=` единица Hz | Частота, научная нотация | Установить/запросить частоту модулирующей волны. |
| `:DDS:MODE:DEPThordeviation <value>` | `:DDS:MODE:DEPThordeviation?` | AM: `<value> ::=` глубина модуляции; FM: `<value> ::=` девиация **[sic: ключевое слово "DEPThordeviation" = "depth-or-deviation"]** | AM → глубина модуляции; FM → девиация | Установить/запросить девиацию или глубину модуляции. |
| `:DDS:BURSt:SWITch <bool>` | `:DDS:BURSt:SWITch?` | `<bool> ::= {{1 | ON} | {0 | OFF}}` | `ON, OFF` | Установить/запросить состояние пакетного режима (burst) источника сигнала. |
| `:DDS:BURSt:TYPE <type>` | `:DDS:BURSt:TYPE?` | `<type> ::= {N_CYCLE | INFInit}` | `N_CYCLE, INFInit` | Установить/запросить тип пакета (burst) источника сигнала. |
| `:DDS:BURSt:CNT <cnt>` | `:DDS:BURSt:CNT?` | `<value> ::=` целое число | Целое число | Установить/запросить число циклов сигнала. |
| `:DDS:BURSt:TRIGger` | — | (без параметров) | — | Отправить один пакет (burst) источника сигнала. |
| `:DDS:ARB:DAC16:BIN <binary_block_data>` | — | `<binary_block_data>` = двоичный блок, начинающийся с `#`, например `#508192` (5 = число символов поля длины, 8192 = число байт). Каждая точка = 2 байта (младший байт первым); число байт должно быть чётным. Число точек произвольной осциллограммы должно быть **4096**. | — | Загрузить данные произвольной осциллограммы. |

---

## Сводка артефактов OCR и опечаток (буквальные строки устройства)

Это буквальные строки в том виде, как они напечатаны в руководстве. Разработчикам следует тестировать именно эти точные написания, поскольку именно их может фактически ожидать прошивка:

| Расположение | Напечатано (буквально) | Вероятно подразумевалось | Примечания |
|---|---|---|---|
| §11.1 MASK | `:MASK:EANBle` | `:MASK:ENABle` | Буквы переставлены. **Сначала протестируйте `EANBle`** — прошивка может действительно использовать его. |
| §4.12 TRIGger | `:TRIGger:INTERVAl:*` | `:TRIGger:INTerval:*` | Строчная "l" вместо ожидаемой длинной формы. Используется последовательно, включая SETUp:ALL?. |
| §4.12.2 | `:TRIGger:INTERVAl:SLOp` | `…:SLOPe` | Усечённое ключевое слово. |
| §4.13 TRIGger | `:TRIGger:UNDER_Am:*` | Runt-триггер | Подчёркивание + необычный регистр; согласовано во всём документе. |
| §13.11 DDS | `:DDS:MODE:DEPThordeviation` | depth/deviation | Одно объединённое ключевое слово и для глубины AM, и для девиации FM. |
| §4.6.2 / §4.12.2 | `RISIng` | `RISing` | Заглавная "I" появляется в перечислениях наклона. |
| §4.7.3 возвраты | `EQUAI`, `GRAt` | `EQUAl`, `GREAt` | OCR "l"→"I"; "GREAt"/"GRAt" несогласованы в той же подсистеме. |
| §10.4 MEASure | `:MEASure: CHANnel<n>:ITEM` | `:MEASure:CHANnel<n>:ITEM` | Лишний пробел после двоеточия в заголовке (вероятно, только вёрстка). |
| §4.15.4 CAN | `FRAM_STARE`, `FRAM_REE` | `FRAME_START`, `FRAME_ERROR` | Перечисления условий CAN выглядят искажёнными OCR; используйте показанные буквальные строки. |
| §4.9 | `:TRIGger:VIDeo:LEVel` | (в разделе TV) | Уровень видео использует ключевое слово `VIDeo`, хотя сгруппировано под `TV`. |
| §8.1 возвраты | `VECT` | `VECTors` | Возврат DISPlay:TYPE? сокращён. |
| §8.4 пример | использует `:DISPlay:WBRightness` | `:DISPlay:GBRightness` | Ошибка копирования в примере. |
| §4.15.8 CAN | `:TRIGger:CAN:ALEVel? TRIGger:CAN:ALEVel?` | один запрос | Пример напечатан с продублированным/искажённым запросом. |
| §4.19 PATTern | `TRIGger:PATTern` против `TRIGger:LOGIc` | — | Раздел использует `PATTern`; SETUp:ALL? использует `LOGIc` для той же функции. Проверьте, что принимает устройство. |
| §2.3 | `<sacle_value>` | `<scale_value>` | Опечатка в имени параметра. |
| §13.6 пример | `:DDS: DUTY 50` | `:DDS:DUTY 50` | Лишний пробел в примере. |
| §4.7.1 / §4.8.1 | списки источников PULSe/SLOPe содержат только CHANnel1–4 | — | В отличие от EDGe (где добавлен `EXT/10`), источники pulse/slope/и др. — только CH1–CH4. |

**Неоднозначности, отмеченные для разработчиков:**
- `TRIGger:UART:STOP` и `TRIGger:CAN:DATA` (без индекса) появляются в SETUp:ALL?, но не имеют выделенных определений команд в §4.
- `TRIGger:LOGIc:CLEVel` / `:DLEVel` (уровни шаблона CH3/CH4) появляются только в SETUp:ALL?; §4.19 документирует только `PATTern:LEVel <chan>,<level>`.
- Список параметров `MATH:OPERator` показывает `FFT` как значение оператора, что согласуется с отдельным поддеревом `MATH:FFT:*`.
