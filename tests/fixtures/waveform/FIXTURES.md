# Waveform-фикстуры (реальные захваты с DSO2D15, петля DDS→CH1)

Сняты на железе 2026-06-27. DDS-генератор прибора заведён на вход CH1 (BNC-петля).
Все при `:ACQuire:POINts 4000`, `:TIMebase:SCALe 2e-4`, `srate=1.25e6 Sa/s`, probe=1, coupling DC.

## Формат пакета `:WAVeform:DATA:ALL?` (подтверждён на железе)

Каждый запрос `:WAVeform:DATA:ALL?` → один пакет (через `transport.read_raw()`):
- Префикс (29 байт ASCII): `#9`(2) + `pkt_len`(9 цифр) + `total`(9) + `uploaded`(9).
- **HEADER-пакет**: `len==128`. payload `raw[29:128]` — ASCII-метаданные.
- **DATA-пакет**: `len>128`. payload `raw[29:]` — `points` сэмплов, **signed int8**, ОДИН канал.

Кадр = HEADER, затем по одному DATA-пакету на каждый включённый канал. Читать DATA-пакеты пока `uploaded < total`. `total = N_каналов × points + 99`.

> ⚠️ **КВИРК ПРОШИВКИ 3.0.0 (HARDWARE-VERIFIED 2026-06-27):** все DATA-пакеты кадра **байт-идентичны и содержат только CH1** — прибор НЕ отдаёт CH2 через `:WAVeform:DATA:ALL?` (`:WAVeform:SOURce CHANnel2` не переключает; подтверждено offset-подписью: CH2 с offset+10В при 5В/дел должен дать +50 counts, но данные = CH1/0). Поэтому 2-канальная фикстура `frame_dc_p1v0_ch1ch2.pkt1==pkt2`. Контроллер (`engine`) дедуплицирует и показывает CH1. **CH2 требует реверс-инжиниринга родного софта (захват USBTMC-трафика).**

## Header-поля (абсолютные индексы в raw; HARDWARE-VERIFIED, отличаются от §7 reference)

| Поле | Индексы | Тип | Пример |
|---|---|---|---|
| `#9` | [0:2] | литерал | `#9` |
| pkt_len | [2:11] | 9 цифр | `000000128` |
| total | [11:20] | 9 цифр | `000004099` (1ch) / `000008099` (2ch) |
| uploaded | [20:29] | 9 цифр | `000000000` (header) |
| running | [29] | 1 цифра | `1` |
| trig | [30] | 1 цифра | `0`=NOTRIG |
| ch1off..ch4off | [31:35],[35:39],[39:43],[43:47] | signed int (counts, 25/дел) | `0000`, `0025`, `-025` |
| ch1volt..ch4volt | [47:79] | 4×8 симв, volts/count @204.8/дел | НЕ использовать для этих данных |
| **enable** | **[79:83]** | поканально '1'/'0' (CH1..CH4) | `1000`=CH1, `1100`=CH1+CH2 |
| **srate** | **[83:92]** | float | `1.250e+06` |

> ⚠️ Смещения enable/srate на +4 относительно frozen reference §7 (voltage-поля по 8 символов, не 7). Это hardware-verify правка — frozen reference не трогаем, в коде используем выверенные индексы.

## Калибровка сэмпл→вольты (HARDWARE-VERIFIED, петля DDS, R²=0.995)

- Сэмпл — **signed int8** (np.int8). `COUNTS_PER_DIV = 25`.
- **`volts = sample × (Vдел / 25) − offset_volts`** (Vдел = `:CHANnel<n>:SCALe?`, offset_volts = `:CHANnel<n>:OFFSet?`).
- Время: `t[i] = i / srate`.

## Файлы

| Фикстура | Конфиг | Ожидаемый декод |
|---|---|---|
| `frame_dc_p1v0_ch1.pkt0.bin` (header), `.pkt1.bin` (data) | DDS DC +1.0В, CH1, 1В/дел, off=0 | enable `1000`, ch=[1], srate 1.25e6; CH1 ≈ **+1.0В** (sample mode +25/+26) |
| `frame_dc_p1v0_ch1ch2.pkt0..pkt2.bin` | то же + CH2 включён (висит), 1В/дел | enable `1100`, ch=[1,2], total 8099; 3 пакета (header+2 data); CH1 ≈ +1.0В |
| `sq_2vpp_1k_ch1_1vdiv.hdr.bin` / `.dat.bin` | DDS меандр 2Vpp 1кГц, CH1, 1В/дел | ch=[1]; два уровня ≈ **−1.0В / +1.0В** |
| `dc_p1v0_ch1_1vdiv.hdr.bin` / `.dat.bin` | DDS DC +1.0В, CH1, 1В/дел | дубль одиночного header+data (для convert/header-тестов) |
| `frames_manifest.json` | — | манифест пакетов кадров (len/total/uploaded) |

Допуски в тестах декода: реальные захваты шумят ±1–2 count (±0.04–0.08В) — сверять mean/median с допуском ~±0.1В, не побайтно.
