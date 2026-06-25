# DSO2000 Series SCPI Command Registry

Frozen reference appendix extracted verbatim from the **Hantek DSO2000 Series SCPI Programmers Manual** (61 pages).
Command keywords use SCPI casing (UPPERCASE = required short form, lowercase = optional long-form completion). `<n>` denotes a channel index (1–4) unless otherwise noted.

> **OCR / typo notes:** The manual contains a number of OCR artifacts and spelling inconsistencies. These are flagged inline with **[sic]** and summarized at the end of this document. Where the literal device string is ambiguous, the most likely intended keyword is noted.

---

## 1. CHANnel\<n\> Subsystem

Vertical-system parameters (bandwidth limit, coupling, vertical scale, offset) of the analog channels. `<n> ::= {1 | 2 | 3 | 4}` for all commands in this subsystem.

| Command | Query | Parameters / Range | Returns | Description |
|---|---|---|---|---|
| `:CHANnel<n>:BWLimit <type>` | `:CHANnel<n>:BWLimit?` | `<type> ::= {{1 | ON} | {0 | OFF}}` | `0` or `1` | Set/query 20 MHz bandwidth limit for the channel. ON attenuates high-frequency components. |
| `:CHANnel<n>:COUPling <coupling>` | `:CHANnel<n>:COUPling?` | `<coupling> ::= {AC | DC | GND}` | `AC,DC,GND` (one of) | Set/query channel coupling. AC blocks DC component; DC passes both; GND blocks both. |
| `:CHANnel<n>:DISPlay <bool>` | `:CHANnel<n>:DISPlay?` | `<bool> ::= {{1 | ON} | {0 | OFF}}` | `0` or `1` | Turn the channel display on/off. |
| `:CHANnel<n>:INVert <bool>` | `:CHANnel<n>:INVert?` | `<bool> ::= {{1 | ON} | {0 | OFF}}` | `0` or `1` | Turn waveform inversion of the channel on/off. |
| `:CHANnel<n>:OFFSet <offset> [<suffix>]` | `:CHANnel<n>:OFFSet?` | `<offset> ::=` vertical offset in NR3; `<suffix> ::= {V | mV}`; default unit V | Vertical displacement, scientific notation | Set/query vertical displacement. Legal range depends on vertical scale and probe ratio; out-of-range values clamp to nearest legal value. |
| `:CHANnel<n>:SCALe <scale> [<suffix>]` | `:CHANnel<n>:SCALe?` | `<scale> ::=` volts/div in NR3; `<suffix> ::= {V | mV}`; default unit V | Vertical scale, scientific notation | Set/query vertical scale (volts per division). Settable range relates to probe ratio. |
| `:CHANnel<n>:PROBe <atten>` | `:CHANnel<n>:PROBe?` | `<atten> ::= {1 | 10 | 100 | 1000}` | Probe ratio, scientific notation | Set/query probe attenuation factor. |
| `:CHANnel<n>:VERNier <bool>` | `:CHANnel<n>:VERNier?` | `<bool> ::= {{1 | ON} | {0 | OFF}}` | `1` or `0` | Turn fine (vernier) vertical-scale adjustment on/off. Off = coarse 1-2-5 steps. |

---

## 2. TIMebase Subsystem

Horizontal system: dual window (zoom), main timebase, mode.

| Command | Query | Parameters / Range | Returns | Description |
|---|---|---|---|---|
| `:TIMebase:WINDow:ENABle <bool>` | `:TIMebase:WINDow:ENABle?` | `<bool> ::= {{1 | ON} | {0 | OFF}}` | `ON` or `OFF` | Turn dual-window (zoom/delayed scan) function on/off. |
| `:TIMebase:WINDow:POSition <pos value>` | `:TIMebase:WINDow:POSition?` | `<pos value> ::=` horizontal position (seconds) | Position, scientific notation | Set/query horizontal position of the zoomed view. Must keep zoom window within main scan range. |
| `:TIMebase:WINDow:SCALe <scale_value>` | `:TIMebase:WINDow:SCALe?` | `<scale_value> ::=` microseconds per grid of subwindow **[sic: "sacle_value"]** | Sub-window timebase, scientific notation | Set/query horizontal scale of sub-window (µs/div). Max = half the main scan scale. |
| `:TIMebase:POSition <pos value>` | `:TIMebase:POSition?` | `<pos value> ::=` offset value (seconds) | Main timebase offset, scientific notation | Set/query main timebase offset. |
| `:TIMebase:SCALe <scale value>` | `:TIMebase:SCALe?` | `<scale value> ::=` seconds per grid (main window) | Main timebase, scientific notation | Set/query horizontal scale of main window (s/div). |
| `:TIMebase:RANGe <range value>` | `:TIMebase:RANGe?` | `<range value> ::=` range value (seconds) | Full-scale time, scientific notation | Set/query full-scale horizontal time of main window. |
| `:TIMebase:MODE <value>` | `:TIMebase:MODE?` | `<value> ::= {MAIN | XY | ROLL}` | `MAIN`, `XY`, or `ROLL` | Set/query horizontal timebase mode (MAIN=YT, XY, ROLL). |

---

## 3. ACQuire Subsystem

Acquisition memory depth, acquisition type, sample rate, averaging count.

| Command | Query | Parameters / Range | Returns | Description |
|---|---|---|---|---|
| `:ACQuire:POINts <value>` | `:ACQuire:POINts?` | `<value> ::= 4000 | 40000 | 400000 | 4000000 | 8000000` (4K/40K/400K/4M/8M) | Actual point count (integer) | Set/query storage (memory) depth. |
| `:ACQuire:TYPE <value>` | `:ACQuire:TYPE?` | `<value> ::= {NORMal | AVERage | PEAK | HRESolution}` | `NORM`, `AVERage`, `PEAK`, or `HRESolution` | Set/query acquisition method (Normal, Average, Peak Detect, High-Resolution). |
| — | `:ACQuire:SRATe?` | (query only) | Sample rate as real number | Query current sampling rate (waveform points sampled per second). |
| `:ACQuire:COUNt <value>` | `:ACQuire:COUNt?` | `<value> ::= 4 | 8 | 16 | 32 | 64 | 128` | Current average count | Set/query number of averages used in Average acquisition mode. |

---

## 4. TRIGger Subsystem

The largest subsystem. Trigger modes: EDGE, PULSe, TV, SLOPe, TIMeout, WINdow, PATTern, INTerval, UNDerthrow (runt), UART, LIN, CAN, SPI, IIC.

### 4.1–4.5 TRIGger top-level

| Command | Query | Parameters / Range | Returns | Description |
|---|---|---|---|---|
| `:TRIGger:FORCe` | — | (no params) | — | Force a trigger; acquires a waveform even if trigger conditions are not met. |
| `:TRIGger:MODE <mode>` | `:TRIGger:MODE?` | `<mode> ::= {EDGE | PULSe | TV | SLOPe | TIMeout | WINdow | PATTern | INTerval | UNDerthrow | UART | LIN | CAN | SPI | IIC}` | `EDGE, PULSe, TV, SLOPe, TIMeout, WINdow, PATTern, INTerval, UNDerthrow, UART, LIN, CAN, SPI, IIC` | Set/query the trigger type. |
| — | `:TRIGger:STATus?` | (query only) | `TRIGed` or `NOTRIG` | Query current trigger status. |
| `:TRIGger:SWEep <value>` | `:TRIGger:SWEep?` | `<value> ::= {AUTO | NORMal | SINGle}` | `AUTO`, `NORMal`, or `SINGle` | Set/query trigger sweep mode. |
| `:TRIGger:HOLDoff <value>` | `:TRIGger:HOLDoff?` | `<value> ::=` holdoff time (seconds) | Holdoff time, scientific notation | Set/query trigger holdoff. Not available for video/timeout/setup-hold/UART/LIN/CAN/IIC/SPI triggers. |

### 4.6 TRIGger:EDGe

| Command | Query | Parameters / Range | Returns | Description |
|---|---|---|---|---|
| `:TRIGger:EDGe:SOURce <source>` | `:TRIGger:EDGe:SOURce?` | `<source> ::= {CHANnel1 | CHANnel2 | CHANnel3 | CHANnel4 | EXT/10}` | `CHANnel1, CHANnel2, CHANnel3, CHANnel4, EXT/10` | Set/query edge trigger source. |
| `:TRIGger:EDGe:SLOPe <slope>` | `:TRIGger:EDGe:SLOPe?` | `<slope> ::= {RISIng | FALLing | EITHer}` **[sic: RISIng]** | `RISIng, FALLing, EITHer` | Set/query edge type (rising / falling / either). |
| `:TRIGger:EDGe:LEVel <level>` | `:TRIGger:EDGe:LEVel?` | `<level> ::=` trigger level (V) | Level, scientific notation | Set/query edge trigger level. |

### 4.7 TRIGger:PULSe

| Command | Query | Parameters / Range | Returns | Description |
|---|---|---|---|---|
| `:TRIGger:PULSe:SOURce <source>` | `:TRIGger:PULSe:SOURce?` | `<source> ::= {CHANnel1 | CHANnel2 | CHANnel3 | CHANnel4}` | `CHANnel1, CHANnel2, CHANnel3, CHANnel4` | Set/query pulse-width trigger source. |
| `:TRIGger:PULSe:POLarity <polarity>` | `:TRIGger:PULSe:POLarity?` | `<polarity> ::= {POSItive | NEGAtive}` | `POSItive, NEGAtive` | Set/query pulse polarity. |
| `:TRIGger:PULSe:WHEN <when>` | `:TRIGger:PULSe:WHEN?` | `<when> ::= {EQUAl | NEQUal | GREAt | LESS}` **[sic: returns shown as "EQUAI, NEQUal, GRAt, LESS"]** | `EQUAl, NEQUal, GREAt, LESS` | Set/query pulse-width trigger condition (=, ≠, >, <; pulse-width error 5%). |
| `:TRIGger:PULSe:WIDth <value>` | `:TRIGger:PULSe:WIDth?` | `<value> ::=` pulse-width trigger time (seconds) | Pulse width, scientific notation | Set/query pulse-width triggering time. |
| `:TRIGger:PULSe:LEVel <level>` | `:TRIGger:PULSe:LEVel?` | `<level> ::=` trigger level (V) | Level, scientific notation | Set/query pulse-width trigger level. |

### 4.8 TRIGger:SLOPe

| Command | Query | Parameters / Range | Returns | Description |
|---|---|---|---|---|
| `:TRIGger:SLOPe:SOURce <source>` | `:TRIGger:SLOPe:SOURce?` | `<source> ::= {CHANnel1 | CHANnel2 | CHANnel3 | CHANnel4}` | `CHANnel1, CHANnel2, CHANnel3, CHANnel4` | Set/query slope trigger source. |
| `:TRIGger:SLOPe:POLarity <polarity>` | `:TRIGger:SLOPe:POLarity?` | `<polarity> ::= {POSItive | NEGAtive}` | `POSItive, NEGAtive` | Set/query slope trigger polarity. |
| `:TRIGger:SLOPe:WHEN <when>` | `:TRIGger:SLOPe:WHEN?` | `<when> ::= {EQUAl | NEQUal | GREAt | LESS}` | `EQUAl, NEQUal, GREAt, LESS` | Set/query slope trigger condition (=, ≠, >, <; error 5%). |
| `:TRIGger:SLOPe:WIDth <value>` | `:TRIGger:SLOPe:WIDth?` | `<value> ::=` trigger condition value (seconds) | Time, scientific notation | Set/query slope trigger condition time. |
| `:TRIGger:SLOPe:ALEVel <level>` | `:TRIGger:SLOPe:ALEVel?` | `<level> ::=` trigger level upper limit (V) | Upper limit, scientific notation | Set/query upper trigger-level limit (A level). |
| `:TRIGger:SLOPe:BLEVel <level>` | `:TRIGger:SLOPe:BLEVel?` | `<level> ::=` trigger level lower limit (V) | Lower limit, scientific notation | Set/query lower trigger-level limit (B level). |

### 4.9 TRIGger:TV

| Command | Query | Parameters / Range | Returns | Description |
|---|---|---|---|---|
| `:TRIGger:TV:SOURce <source>` | `:TRIGger:TV:SOURce?` | `<source> ::= {CHANnel1 | CHANnel2 | CHANnel3 | CHANnel4}` | `CHANnel1, CHANnel2, CHANnel3, CHANnel4` | Set/query video trigger source. |
| `:TRIGger:TV:POLarity <polarity>` | `:TRIGger:TV:POLarity?` | `<polarity> ::= {POSItive | NEGAtive}` | `POSItive, NEGAtive` | Set/query video polarity. |
| `:TRIGger:TV:MODE <mode>` | `:TRIGger:TV:MODE?` | `<mode> ::= {ALINes | LINes | FIEld1 | FIEld2 | AFIelds}` | `ALINes, LINes, FIEld1, FIEld2, AFIelds` | Set/query video synchronization type (all lines / specified line / odd field / even field / all fields). |
| `:TRIGger:TV:LINE <line>` | `:TRIGger:TV:LINE?` | `<line> ::=` line number. NTSC: 1–525; PAL/SECAM: 1–625 | Integer | Set/query the line number when sync type = specified line. |
| `:TRIGger:TV:STANdard <standard>` | `:TRIGger:TV:STANdard?` | `<standard> ::= {NTSC | PAL}` | `NTSC, PAL` | Set/query video standard. |
| `:TRIGger:VIDeo:LEVel <level>` | `:TRIGger:VIDeo:LEVel?` | `<level> ::=` trigger level (V) | Level, scientific notation | Set/query video trigger level. **[Note: listed under TV section but keyword is `VIDeo`]** |

### 4.10 TRIGger:TIMeout

| Command | Query | Parameters / Range | Returns | Description |
|---|---|---|---|---|
| `:TRIGger:TIMeout:SOURce <source>` | `:TRIGger:TIMeout:SOURce?` | `<source> ::= {CHANnel1 | CHANnel2 | CHANnel3 | CHANnel4}` | `CHANnel1, CHANnel2, CHANnel3, CHANnel4` | Set/query timeout trigger source. |
| `:TRIGger:TIMeout:LEVel <level>` | `:TRIGger:TIMeout:LEVel?` | `<level> ::=` trigger level (V) | Level, scientific notation | Set/query timeout trigger level. |
| `:TRIGger:TIMeout:WIDth <value>` | `:TRIGger:TIMeout:WIDth?` | `<value> ::=` timeout value, range 8 ns–10 s | Timeout, scientific notation | Set/query timeout period. |
| `:TRIGger:TIMeout:POLarity <polarity>` | `:TRIGger:TIMeout:POLarity?` | `<polarity> ::= {POSItive | NEGAtive}` | `POSItive, NEGAtive` | Set/query edge polarity for timeout (POS=rising, NEG=falling). |

### 4.11 TRIGger:WINDOw

| Command | Query | Parameters / Range | Returns | Description |
|---|---|---|---|---|
| `:TRIGger:WINDOw:SOURce <source>` | `:TRIGger:WINDOw:SOURce?` | `<source> ::= {CHANnel1 | CHANnel2 | CHANnel3 | CHANnel4}` | `CHANnel1, CHANnel2, CHANnel3, CHANnel4` | Set/query window trigger source. |
| `:TRIGger:WINDOw:ALEVel <level>` | `:TRIGger:WINDOw:ALEVel?` | `<level> ::=` trigger level upper limit (V) | Upper level, scientific notation | Set/query upper trigger-level limit (A level). |
| `:TRIGger:WINDOw:BLEVel <level>` | `:TRIGger:WINDOw:BLEVel?` | `<level> ::=` trigger level lower limit (V) | Lower level, scientific notation | Set/query lower trigger-level limit (B level). |

### 4.12 TRIGger:INTERVAl **[sic: keyword printed "INTERVAl"; likely INTerval]**

| Command | Query | Parameters / Range | Returns | Description |
|---|---|---|---|---|
| `:TRIGger:INTERVAl:SOURce <source>` | `:TRIGger:INTERVAl:SOURce?` | `<source> ::= {CHANnel1 | CHANnel2 | CHANnel3 | CHANnel4}` | `CHANnel1, CHANnel2, CHANnel3, CHANnel4` | Set/query interval trigger source. |
| `:TRIGger:INTERVAl:SLOp <slope>` | `:TRIGger:INTERVAl:SLOp?` | `<slope> ::= {RISIng | FALLing}` **[sic: keyword "SLOp"; State adds DOUBle; returns "RISIng, FALLing, DOUBle"]** | `RISIng, FALLing, DOUBle` | Set/query interval edge type. |
| `:TRIGger:INTERVAl:WHEN <when>` | `:TRIGger:INTERVAl:WHEN?` | `<when> ::= {EQUAl | NEQUal | GREAt | LESS}` | `EQUAl, NEQUal, GREAt, LESS` | Set/query interval trigger condition (<, >, =, ≠). |
| `:TRIGger:INTERVAl:TIME <value>` | `:TRIGger:INTERVAl:TIME?` | `<value> ::=` trigger time (seconds), 8 ns–10 s | Time, scientific notation | Set/query interval time value. |
| `:TRIGger:INTERVAl:ALEVel <level>` | `:TRIGger:INTERVAl:ALEVel?` | `<level> ::=` trigger level (V) | Level, scientific notation | Set/query interval trigger level. |

### 4.13 TRIGger:UNDER_Am (Runt trigger) **[sic: keyword "UNDER_Am"; SETUp:ALL? calls it "Runt"]**

| Command | Query | Parameters / Range | Returns | Description |
|---|---|---|---|---|
| `:TRIGger:UNDER_Am:SOURce <source>` | `:TRIGger:UNDER_Am:SOURce?` | `<source> ::= {CHANnel1 | CHANnel2 | CHANnel3 | CHANnel4}` | `CHANnel1, CHANnel2, CHANnel3, CHANnel4` | Set/query runt trigger source. |
| `:TRIGger:UNDER_Am:POLarity <polarity>` | `:TRIGger:UNDER_Am:POLarity?` | `<polarity> ::= {POSItive | NEGAtive}` | `POSItive, NEGAtive` | Set/query runt pulse polarity. |
| `:TRIGger:UNDER_Am:WHEN <when>` | `:TRIGger:UNDER_Am:WHEN?` | `<when> ::= {EQUAl | NEQUal | GREAt | LESS}` | `EQUAl, NEQUal, GREAt, LESS` | Set/query runt qualifier. |
| `:TRIGger:UNDER_Am:TIME <value>` | `:TRIGger:UNDER_Am:TIME?` | `<value> ::=` trigger time (seconds), 8 ns–10 s | Time, scientific notation | Set/query runt trigger time. |
| `:TRIGger:UNDER_Am:ALEVel <level>` | `:TRIGger:UNDER_Am:ALEVel?` | `<level> ::=` trigger level upper limit (V) | Upper level, scientific notation | Set/query upper trigger-level limit (A level). |
| `:TRIGger:UNDER_Am:BLEVel <level>` | `:TRIGger:UNDER_Am:BLEVel?` | `<level> ::=` trigger level lower limit (V) | Lower level, scientific notation | Set/query lower trigger-level limit (B level). |

### 4.14 TRIGger:UART

| Command | Query | Parameters / Range | Returns | Description |
|---|---|---|---|---|
| `:TRIGger:UART:SOURce <source>` | `:TRIGger:UART:SOURce?` | `<source> ::= {CHANnel1 | CHANnel2 | CHANnel3 | CHANnel4}` | `CHANnel1, CHANnel2, CHANnel3, CHANnel4` | Set/query UART trigger source. |
| `:TRIGger:UART:CONdition <condition>` | `:TRIGger:UART:CONdition?` | `<condition> ::= {START | STOP | READ_DATA | PARITY_ERR | COM_ERR}` | `START, STOP, READ_DATA, PARITY_ERR, COM_ERR` | Set/query UART trigger condition. |
| `:TRIGger:UART:BAUd <baud>` | `:TRIGger:UART:BAUd?` | `<baud> ::= 110 | 300 | 600 | 1200 | 2400 | 4800 | 9600 | 14400 | 19200 | 38400 | 57600 | 115200 | 230400 | 380400 | 460400 | 921600 | USER` | Integer or `USER` | Set/query UART baud rate (bps). |
| `:TRIGger:UART:ALEVel <level>` | `:TRIGger:UART:ALEVel?` | `<level> ::=` trigger level (V) | Level, scientific notation | Set/query UART trigger level. |
| `:TRIGger:UART:DATA <data>` | `:TRIGger:UART:DATA?` | `<data> ::= (0 ~ (2^(n-1) - 1))` where n = current data width (5,6,7,8) | Integer | Set/query data value when UART condition = data. |
| `:TRIGger:UART:WIDTh <value>` | `:TRIGger:UART:WIDTh?` | `<value> ::= {5 | 6 | 7 | 8}` | `5, 6, 7, or 8` | Set/query data bit width when condition = data. |
| `:TRIGger:UART:PARIty <parity>` | `:TRIGger:UART:PARIty?` | `<parity> ::= {NONE | ODD | EVEN}` | `EVEN, ODD, or NONE` | Set/query parity/verification mode. |

### 4.15 TRIGger:CAN

| Command | Query | Parameters / Range | Returns | Description |
|---|---|---|---|---|
| `:TRIGger:CAN:SOURce <source>` | `:TRIGger:CAN:SOURce?` | `<source> ::= {CHANnel1 | CHANnel2 | CHANnel3 | CHANnel4}` | `CHANnel1, CHANnel2, CHANnel3, CHANnel4` | Set/query CAN trigger source. |
| `:TRIGger:CAN:IDLe <idle>` | `:TRIGger:CAN:IDLe?` | `<idle> ::= {LOW | HIGH}` | `LOW, HIGH` | Set/query CAN idle level. |
| `:TRIGger:CAN:BAUd <baud>` | `:TRIGger:CAN:BAUd?` | `<baud> ::= 10000 | 20000 | 33300 | 50000 | 62500 | 83300 | 100000 | 125000 | 250000 | 500000 | 800000 | 1000000 | USER` | Integer | Set/query CAN baud rate (bps). |
| `:TRIGger:CAN:CONdition <condition>` | `:TRIGger:CAN:CONdition?` | `<condition> ::= {FRAM_STARE | FRAM_REMO_ID | FRAM_DATA_ID | REMO/DATA_ID | DATA_ID/DATA | FRAM_REE | FRAM_OVERLOAD | ERR_ALL | ACK_ERR}` **[sic: "FRAM_STARE", "FRAM_REE" likely "FRAME_START", "FRAME_ERROR"]** | `FRAM_STARE, FRAM_REMO_ID, FRAM_DATA_ID, REMO/DATA_ID, DATA_ID/DATA, FRAM_REMO_ID_EXT, FRAM_DATA_ID_EXT, REMO/DATA_ID_EXT, DATA_ID/DATA_EXT, FRAM_REE, FRAM_OVERLOAD, ERR_ALL, ACK_ERR` | Set/query CAN trigger condition. |
| `:TRIGger:CAN:ID <id>` | `:TRIGger:CAN:ID?` | `<id> ::= 0 ~ 28` | Integer | Set/query CAN IDENTIFIER. |
| `:TRIGger:CAN:DLC <dlc>` | `:TRIGger:CAN:DLC?` | `<dlc> ::= 4 digits` | Integer | Set/query CAN data length code. |
| `:TRIGger:CAN:DATA <index>,<data>` | `:TRIGger:CAN:DATA? <index>` | `<data> ::= 8 digits`; `<index> ::=` data index 0–3 | Integer | Set/query CAN trigger data value at index. |
| `:TRIGger:CAN:ALEVel <level>` | `:TRIGger:CAN:ALEVel?` | `<level> ::=` trigger level (V) | Level, scientific notation | Set/query CAN trigger level. **[sic: query example printed oddly as `:TRIGger:CAN:ALEVel? TRIGger:CAN:ALEVel?`]** |

### 4.16 TRIGger:LIN

| Command | Query | Parameters / Range | Returns | Description |
|---|---|---|---|---|
| `:TRIGger:LIN:SOURce <source>` | `:TRIGger:LIN:SOURce?` | `<source> ::= {CHANnel1 | CHANnel2 | CHANnel3 | CHANnel4}` | `CHANnel1, CHANnel2, CHANnel3, CHANnel4` | Set/query LIN trigger source. |
| `:TRIGger:LIN:IDLe <idle>` | `:TRIGger:LIN:IDLe?` | `<idle> ::= {LOW | HIGH}` | `LOW, HIGH` | Set/query LIN idle level. |
| `:TRIGger:LIN:BAUd <baud>` | `:TRIGger:LIN:BAUd?` | `<baud> ::= 110 | 300 | 600 | 1200 | 2400 | 4800 | 9600 | 14400 | 19200 | 38400 | 57600 | 115200 | 230400 | 380400 | 460400 | 921600 | USER` | Integer | Set/query LIN baud rate (bps). |
| `:TRIGger:LIN:CONdition <condition>` | `:TRIGger:LIN:CONdition?` | `<condition> ::= {INTERVAL_FIELD | SYNC_FIELD | ID_FIELD | DATA | IDENTIFIER | ID_DATA}` | `INTERVAL_FIELD, SYNC_FIELD, ID_FIELD, DATA, IDENTIFIER, ID_DATA` | Set/query LIN trigger condition. |
| `:TRIGger:LIN:ID <id>` | `:TRIGger:LIN:ID?` | `<id> ::= 6 digits` | Integer | Set/query LIN identifier. |
| `:TRIGger:LIN:DATA <index>,<data>` | `:TRIGger:LIN:DATA? <index>` | `<data> ::= 8 digits`; `<index> ::=` data index 0–3 | Integer | Set/query LIN trigger data value at index. |
| `:TRIGger:LIN:ALEVel <level>` | `:TRIGger:LIN:ALEVel?` | `<level> ::=` trigger level (V) | Level, scientific notation | Set/query LIN trigger level. |

### 4.17 TRIGger:IIC

| Command | Query | Parameters / Range | Returns | Description |
|---|---|---|---|---|
| `:TRIGger:IIC:SDA:SOURce <source>` | `:TRIGger:IIC:SDA:SOURce?` | `<source> ::= {CHANnel1 | CHANnel2 | CHANnel3 | CHANnel4}` | `CHANnel1, CHANnel2, CHANnel3, CHANnel4` | Set/query I²C data-line (SDA) source. |
| `:TRIGger:IIC:SCL:SOURce <source>` | `:TRIGger:IIC:SCL:SOURce?` | `<source> ::= {CHANnel1 | CHANnel2 | CHANnel3 | CHANnel4}` | `CHANnel1, CHANnel2, CHANnel3, CHANnel4` | Set/query I²C clock-line (SCL) source. |
| `:TRIGger:IIC:CONdition <condition>` | `:TRIGger:IIC:CONdition?` | `<condition> ::= {START | STOP | ACK_LOST | ADDR_NO_ACK | RESTART | READ_DATA}` | `START, STOP, ACK_LOST, ADDR_NO_ACK, RESTART, READ_DATA` | Set/query I²C trigger condition. |
| `:TRIGger:IIC:ADDer <addr>` | `:TRIGger:IIC:ADDer?` | `<addr> ::= 8 digits` | Integer | Set/query address value when condition = address/address-data. |
| `:TRIGger:IIC:DATA <index>,<data>` | `:TRIGger:IIC:DATA? <index>` | `<data> ::= 8 digits`; `<index> ::=` data index 0–8 | Integer | Set/query data value when condition = data/address-data. |
| `:TRIGger:IIC:ALEVel <level>` | `:TRIGger:IIC:ALEVel?` | `<level> ::=` trigger level (V) | Level, scientific notation | Set/query clock-line (SCL) trigger level. |
| `:TRIGger:IIC:BLEVel <level>` | `:TRIGger:IIC:BLEVel?` | `<level> ::=` trigger level (V) | Level, scientific notation | Set/query data-line (SDA) trigger level. |

### 4.18 TRIGger:SPI

| Command | Query | Parameters / Range | Returns | Description |
|---|---|---|---|---|
| `:TRIGger:SPI:SDA:SOURce <source>` | `:TRIGger:SPI:SDA:SOURce?` | `<source> ::= {CHANnel1 | CHANnel2 | CHANnel3 | CHANnel4}` | `CHANnel1, CHANnel2, CHANnel3, CHANnel4` | Set/query SPI data-line source. |
| `:TRIGger:SPI:SCL:SOURce <source>` | `:TRIGger:SPI:SCL:SOURce?` | `<source> ::= {CHANnel1 | CHANnel2 | CHANnel3 | CHANnel4}` | `CHANnel1, CHANnel2, CHANnel3, CHANnel4` | Set/query SPI clock-line source. |
| `:TRIGger:SPI:SCK <slope>` | `:TRIGger:SPI:SCK?` | `<slope> ::= {Rising | Falling}` | `Rising, Falling` | Set/query SPI clock edge type. |
| `:TRIGger:SPI:WIDth <width>` | `:TRIGger:SPI:WIDth?` | `<width> ::= 4 ~ 32` | Integer | Set/query SPI data bit width. |
| `:TRIGger:SPI:DATA <data>` | `:TRIGger:SPI:DATA?` | `<data> ::= 0 ~ (2^32 - 1)` | Integer | Set/query SPI data value. |
| `:TRIGger:SPI:MASK <mask>` | `:TRIGger:SPI:MASK?` | `<mask> ::= 0 ~ (2^32 - 1)` | Integer | Set/query SPI mask value. |
| `:TRIGger:SPI:ALEVel <level>` | `:TRIGger:SPI:ALEVel?` | `<level> ::=` trigger level (V) | Level, scientific notation | Set/query SPI clock-channel trigger level. |
| `:TRIGger:SPI:BLEVel <level>` | `:TRIGger:SPI:BLEVel?` | `<level> ::=` trigger level (V) | Level, scientific notation | Set/query SPI data-channel trigger level. |

### 4.19 TRIGger:PATTern

> **Note:** The manual's command list and section header use `TRIGger:PATTern`, but the SETUp:ALL? remark (§12.6) refers to the same feature via `TRIGger:LOGIc:POLarity/WHEN/TIME/ALEVel/BLEVel/CLEVel/DLEVel`. Implementers should verify which keyword the device accepts. Section 4.19.2 header is printed as `TRIGger:PATTern:LEVel`.

| Command | Query | Parameters / Range | Returns | Description |
|---|---|---|---|---|
| `:TRIGger:PATTern:PATTern <pa_ch1>[,<pa_ch2>[,<pa_ch3>[,<pa_ch4>[,<pa_d0>…[,<pa_d15>]]]]]` | `:TRIGger:PATTern:PATTern?` | See field breakdown below; each `::= {H | L | X}` | Pattern for 4 analog + all channels, comma-separated | Set/query the per-channel pattern when pattern-triggered. |
| `:TRIGger:PATTern:LEVel <chan>,<level>` | `:TRIGger:PATTern:LEVel? <chan>` | `<chan> ::= CHANnel<n>`; `<level> ::=` Integer, range `(-5 × VerticalScale − OFFSet)` to `(5 × VerticalScale − OFFSet)`, default 0 | Level, scientific notation | Set/query trigger level of the specified channel. Valid only when selected source is an analog channel. |

**`:TRIGger:PATTern:PATTern` field breakdown:**
- `<pa_ch1>` – Discrete `{H | L | X}`, default `X` — analog channel CH1 pattern
- `<pa_ch2>` – Discrete `{H | L | X}`, default `X` — analog channel CH2 pattern
- `<pa_ch3>` – Discrete `{H | L | X}`, default `X` — analog channel CH3 pattern
- `<pa_ch4>` – Discrete `{H | L | X}`, default `X` — analog channel CH4 pattern
- `<pa_D10>` … `<pa_D43>` – Discrete `{H | L | X}`, default `C` — digital channel patterns
- **Semantics:** H = high level (above channel threshold); L = low level (below threshold); X = ignore this channel. If all channels are X, the scope will not trigger.
- Up to 20 parameters may be sent for all channels; omitted parameters keep their previous state, but at least one parameter (CH1) must be sent. When fewer than 20 sent, the instrument defaults to setting CH1–CH4 and D10–D43 in turn.

---

## 5. CALibrate Subsystem

| Command | Query | Parameters / Range | Returns | Description |
|---|---|---|---|---|
| `:CALibrate:STARt` | — | (no params) | — | Start self-calibration. Disconnect all signals first; most key functions are disabled during calibration. |
| — | `:CALibrate:STATus?` | (query only) | Calibration status | Query current calibration status. |
| `:CALibrate:QUIT` | — | (no params) | — | Exit self-calibration at any time. |

---

## 6. MATH Subsystem

Algebraic operations (ADD/SUBtract/MULTiply/DIVision) and FFT.

| Command | Query | Parameters / Range | Returns | Description |
|---|---|---|---|---|
| `:MATH:DISPlay <bool>` | `:MATH:DISPlay?` | `<bool> ::= {{1 | ON} | {0 | OFF}}` | `ON, OFF` | Turn math operation function on/off. |
| `:MATH:OPERator <type>` | `:MATH:OPERator?` | `<type> ::= {ADD | SUBtract | MULTiply | DIVision | FFT}` | `ADD, SUBtract, MULTiply, DIVision, FFT` | Set/query math operator. |
| `:MATH:SOURce1 <source>` | `:MATH:SOURce1?` | `<source> ::= {CHANnel1 | CHANnel2 | CHANnel3 | CHANnel4}` | `CHANnel1, CHANnel2, CHANnel3, CHANnel4` | Set/query source A of algebraic operation. |
| `:MATH:SOURce2 <source>` | `:MATH:SOURce2?` | `<source> ::= {CHANnel1 | CHANnel2 | CHANnel3 | CHANnel4}` | `CHANnel1, CHANnel2, CHANnel3, CHANnel4` | Set/query source B of algebraic operation. |
| `:MATH:SCALe <value>` | `:MATH:SCALe?` | `<value> ::=` vertical scale in 1-2-5 sequence, unit V | Vertical scale, scientific notation | Set/query vertical scale of operation result. Unit depends on selected operator/source. |
| `:MATH:OFFSet <value>` | `:MATH:OFFSet?` | `<value> ::=` offset value, unit V | Vertical offset, scientific notation | Set/query vertical offset of operation result. |
| `:MATH:FFT:SOURce <source>` | `:MATH:FFT:SOURce?` | `<source> ::= {CHANnel1 | CHANnel2 | CHANnel3 | CHANnel4}` | `CHANnel1, CHANnel2, CHANnel3, CHANnel4` | Set/query FFT operation source. |
| `:MATH:FFT:WINDow <window>` | `:MATH:FFT:WINDow?` | `<window> ::= {RECTangle | HANNing | HAMMing | BLACkman | TRIangle | FLATtop}` | `RECTangle, HANNing, HAMMing, BLACkman, TRIangle, FLATtop` | Set/query FFT window function. |
| `:MATH:FFT:UNIT <unit>` | `:MATH:FFT:UNIT?` | `<unit> ::= {VRMS | DB}` | `VRMS, DB` | Set/query FFT vertical unit. |
| `:MATH:FFT:HSCale <hscale>` | `:MATH:FFT:HSCale?` | `<hscale> ::= {125000 | 250000 | 625000 | 1250000}` | Horizontal scale, scientific notation | Set/query FFT horizontal scale (Hz, default unit Hz). |
| `:MATH:FFT:HCENter <center>` | `:MATH:FFT:HCENter?` | `<center> ::=` center frequency (Hz) | Center frequency, scientific notation | Set/query FFT center frequency (corresponding to horizontal center of screen). |

---

## 7. WAVeform Subsystem

| Command | Query | Parameters / Range | Returns | Description |
|---|---|---|---|---|
| — | `:WAVeform:DATA:ALL?` | (query only) | Waveform data packet (string) with data header | Read waveform data. Returns a packet containing a data header followed by waveform data. |

**`:WAVeform:DATA:ALL?` — first-time header layout (analysis of `data[x]`):**
- `data[0]–data[1]` (2 digits): `#9`
- `data[2]–data[10]` (9 digits): byte length of the current packet
- `data[11]–data[19]` (9 digits): total length of bytes representing the amount of data
- `data[20]–data[28]` (9 digits): byte length of the uploaded data
- `data[29]` (1 digit): current running status
- `data[30]` (1 digit): trigger status
- `data[31]–data[34]` (4 digits): offset of channel 1
- `data[35]–data[38]` (4 digits): offset of channel 2
- `data[39]–data[42]` (4 digits): offset of channel 3
- `data[43]–data[46]` (4 digits): offset of channel 4
- `data[47]–data[53]` (7 digits): voltage of channel 1
- `data[54]–data[60]` (7 digits): voltage of channel 2
- `data[61]–data[67]` (7 digits): voltage of channel 3
- `data[68]–data[74]` (7 digits): voltage of channel 4
- `data[75]–data[78]` (4 digits): channel enable of channel (1–4)
- `data[79]–data[87]` (9 digits): sampling rate
- `data[88]–data[93]` (6 digits): sampling multiple
- `data[94]–data[102]` (9 digits): display trigger time of current frame
- `data[103]–data[111]` (9 digits): current frame display start point of data acquisition start time point
- `data[112]–data[127]` (16 digits): reserved bit

**`:WAVeform:DATA:ALL?` — subsequent reads (data header re-issued before data is read):**
- `data[0]–data[1]` (2 digits): `#9`
- `data[2]–data[10]` (9 digits): byte length of the current data packet
- `data[11]–data[19]` (9 digits): total length of bytes representing the amount of data
- `data[20]–data[28]` (9 digits): byte length of the uploaded data
- `data[29]–data[x]`: waveform data corresponding to the current data header

---

## 8. DISPlay Subsystem

| Command | Query | Parameters / Range | Returns | Description |
|---|---|---|---|---|
| `:DISPlay:TYPE <type>` | `:DISPlay:TYPE?` | `<type> ::= {VECTors | DOTS}` | `VECT, DOTS` **[sic: returns "VECT" not "VECTors"]** | Set/query waveform display type (vectors connect points; dots show sample points). |
| `:DISPlay:WBRightness <value>` | `:DISPlay:WBRightness?` | `<value> ::=` 0 to 100 | Integer | Set/query waveform display brightness. |
| `:DISPlay:GRID <type>` | `:DISPlay:GRID?` | `<type> ::= {DOTTed | REAL}` | `DOTTed, REAL` | Set/query grid type (dot grid / line grid). |
| `:DISPlay:GBRightness <value>` | `:DISPlay:GBRightness?` | `<value> ::=` 0 to 100 | Integer | Set/query screen grid brightness. **[sic: example shown using `:DISPlay:WBRightness`]** |

---

## 9. CURSor Subsystem

Measures X-axis (e.g., time) and Y-axis (e.g., voltage) values of the screen waveform.

| Command | Query | Parameters / Range | Returns | Description |
|---|---|---|---|---|
| `:CURSor:MODE <type>` | `:CURSor:MODE?` | `<type> ::= {OFF | MANual | TRACk}` | `OFF, MANual, TRACK` | Set/query cursor measurement mode. |
| `:CURSor:MANual:TYPE <type>` | `:CURSor:MANual:TYPE?` | `<type> ::= {X | Y | XY}` | `X, Y, XY` | Set/query manual cursor type. |
| `:CURSor:MANual:SOURce <source>` | `:CURSor:MANual:SOURce?` | `<source> ::= {CHANnel1 | CHANnel2 | MATH}` | `CHANnel1, CHANnel2, MATH` | Set/query channel source for manual cursor. |
| `:CURSor:MANual:AX <value>` | `:CURSor:MANual:AX?` | `<value> ::=` 0 to 770 | Integer | Set/query horizontal position of cursor A (pixel). |
| — | `:CURSor:MANual:AXValue?` | (query only) | X value at cursor A, scientific notation | Query X value at cursor A; unit per selected horizontal unit. |
| `:CURSor:MANual:AY <value>` | `:CURSor:MANual:AY?` | `<value> ::=` 0 to 400 | Integer (0–400) | Set/query vertical position of cursor A (pixel). |
| — | `:CURSor:MANual:AYValue?` | (query only) | Y value at cursor A, scientific notation | Query Y value at cursor A; unit per selected vertical unit. |
| `:CURSor:MANual:BX <value>` | `:CURSor:MANual:BX?` | `<value> ::=` 0 to 770 | Integer (0–770) | Set/query horizontal position of cursor B (pixel). |
| — | `:CURSor:MANual:BXValue?` | (query only) | X value at cursor B, scientific notation | Query X value at cursor B; unit per selected horizontal unit. |
| `:CURSor:MANual:BY <value>` | `:CURSor:MANual:BY?` | `<value> ::=` 0 to 400 | Integer (0–400) | Set/query vertical position of cursor B (pixel). |
| — | `:CURSor:MANual:BYValue?` | (query only) | Y value at cursor B, scientific notation | Query Y value at cursor B; unit per selected vertical unit. |
| `:CURSor:TRACk:SOURcea <source>` | `:CURSor:TRACk:SOURcea?` | `<source> ::= {CHANnel1 | CHANnel2 | CHANnel3 | CHANnel4 | MATH}` | `CHANnel1, CHANnel2, CHANnel3, CHANnel4 or MATH` | Set/query channel source of cursor A in track mode. |
| `:CURSor:TRACk:SOURceb <source>` | `:CURSor:TRACk:SOURceb?` | `<source> ::= {CHANnel1 | CHANnel2 | CHANnel3 | CHANnel4 | MATH}` | `CHANnel1, CHANnel2, CHANnel3, CHANnel4 or MATH` | Set/query channel source of cursor B in track mode. |
| `:CURSor:TRACk:AX <value>` | `:CURSor:TRACk:AX?` | `<value> ::=` 0 to 770 | Integer (0–770) | Set/query horizontal position of cursor A in track mode. |
| — | `:CURSor:TRACk:AXValue?` | (query only) | X value at cursor A, scientific notation (default unit second) | Query X value at cursor A in track mode. |
| — | `:CURSor:TRACk:AY?` | (query only) | Integer | Query vertical position of cursor A in track mode. |
| — | `:CURSor:TRACk:AYValue?` | (query only) | Y value at cursor A, scientific notation | Query Y value at cursor A; unit per selected channel unit. |
| `:CURSor:TRACk:BX <value>` | `:CURSor:TRACk:BX?` | `<value> ::=` 0 to 770 | Integer (0–770) | Set/query horizontal position of cursor B in track mode. |
| — | `:CURSor:TRACk:BXValue?` | (query only) | X value at cursor B, scientific notation (default unit second) | Query X value at cursor B in track mode. |
| — | `:CURSor:TRACk:BY?` | (query only) | Integer | Query vertical position of cursor B in track mode. |
| — | `:CURSor:TRACk:BYValue?` | (query only) | Y value at cursor B, scientific notation | Query Y value at cursor B; unit per selected channel unit. |

---

## 10. MEASure Subsystem

| Command | Query | Parameters / Range | Returns | Description |
|---|---|---|---|---|
| `:MEASure:ENABle <bool>` | `:MEASure:ENABle?` | `<bool> ::= {{1 | ON} | {0 | OFF}}` | `ON, OFF` | Set/query measurement function status. |
| `:MEASure:SOURce <source>` | `:MEASure:SOURce?` | `<source> ::= {CHANnel1 | CHANnel2 | CHANnel3 | CHANnel4 | MATH}` | `CHANnel1, CHANnel2, CHANnel3, CHANnel4, MATH` | Set/query source of current measurement parameters. |
| `:MEASure:ADISplay <bool>` | `:MEASure:ADISplay?` | `<bool> ::= {{1 | ON} | {0 | OFF}}` | `ON, OFF` | Turn all measurements on/off (All-Display). |
| `:MEASure:CHANnel<n>:ITEM <type>` | `:MEASure:CHANnel<n>:ITEM?` | `<n> ::= {1 | 2 | 3 | 4}`; `<type>` see list below | Measurement result (e.g. `VPP 3.600e-01`) | Query measurement result of the specified parameter. **[sic: header printed with space "MEASure: CHANnel<n>:ITEM"]** |
| `:MEASure:GATE:ENABle <bool>` | `:MEASure:GATE:ENABle?` | `<bool> ::= {{1 | ON} | {0 | OFF}}` | `ON, OFF` | Set/query gate control status. |
| `:MEASure:GATE:AY <value>` | `:MEASure:GATE:AY?` | `<value> ::=` 0 to 400 | Integer | Set/query value of gate cursor A. |
| `:MEASure:GATE:BY <value>` | `:MEASure:GATE:BY?` | `<value> ::=` 0 to 400 | Integer | Set/query value of gate cursor B. |

**`:MEASure:CHANnel<n>:ITEM` measurement `<type>` enum (verbatim):**
`MAX, VMIN, VPP, VTOP, VBASe, VAMP, VAVG, VRMS, OVERshoot, PREShoot, MARea, MPARea, PERiod, FREQuency, RTIMe, FTIMe, PWIDth, NWIDth, PDUTy, NDUTy, RDELay, FDELay, RPHase, FPHase, TVMAX, TVMIN, PSLEWrate, NSLEWrate, VUPper, VMID, VLOWer, VARIance, PVRMS, PPULses, NPULses, PEDGes, NEDGes`

---

## 11. MASK Subsystem (Pass/Fail Test)

| Command | Query | Parameters / Range | Returns | Description |
|---|---|---|---|---|
| `:MASK:EANBle <bool>` | `:MASK:EANBle?` | `<bool> ::= {{1 | ON} | {0 | OFF}}` | `ON, OFF` | Turn pass/fail test function on/off. **[sic: keyword "EANBle"; almost certainly ENABle — implementers should test literal "EANBle"]** |
| `:MASK:SOURce <source>` | `:MASK:SOURce?` | `<source> ::= {CHANnel1 | CHANnel2 | MATH}` | `CHANnel1, CHANnel2, MATH` | Set/query measurement source of pass/fail test. |
| `:MASK:MDISplay <bool>` | `:MASK:MDISplay?` | `<bool> ::= {{1 | ON} | {0 | OFF}}` | `ON, OFF` | Turn pass/fail statistics display on/off. |
| `:MASK:OUTPut <bool>` | `:MASK:OUTPut?` | `<bool> ::= {{1 | ON} | {0 | OFF}}` | `ON, OFF` | Turn output (stop-on-fail) on/off. ON: stop test & enter STOP on fail, output one pulse on [Trigger Out]; OFF: continue test, pulse per failed waveform. |
| `:MASK:SOOutput <bool>` | `:MASK:SOOutput?` | `<bool> ::= {{1 | ON} | {0 | OFF}}` | `ON, OFF` | Turn sound prompt on test fail on/off (Sound-Output). |
| `:MASK:X <value>` | `:MASK:X?` | `<value> ::= 0.02 ~ 4`, default unit div | Level adjustment, scientific notation | Set/query horizontal (level) adjustment parameter in pass/fail rule. |
| `:MASK:Y <value>` | `:MASK:Y?` | `<value> ::= 0.04 ~ 5.12`, default unit div | Vertical adjustment, scientific notation | Set/query vertical adjustment parameter in pass/fail rule. |
| `:MASK:CREate` | — | (no params) | — | Create pass/fail rule with current horizontal/vertical adjustment params. Valid only when MASK:ENABle is on and not running (MASK:OPERate). |

---

## 12. SYSTem Subsystem

| Command | Query | Parameters / Range | Returns | Description |
|---|---|---|---|---|
| — | `:SYSTem:GAM?` | (query only) | `12` | Query number of horizontal grids on screen. |
| — | `:SYSTem:RAM?` | (query only) | `4` | Query number of analog channels of the instrument. |
| `:SYSTem:PON <value>` | `:SYSTem:PON?` | `<value> ::= {LATest | DEFault}` | `LATest, DEFault` | Set/query power-on configuration type. |
| `:SYSTem:LANGuage <value>` | `:SYSTem:LANGuage?` | `<value> ::= {ENGLish | SCHinese}` | `ENGLish, SCHinese` | Set/query system display language. |
| `:SYSTem:LOCKed <bool>` | `:SYSTem:LOCKed?` | `<bool> ::= {{1 | ON} | {0 | OFF}}` | `ON, OFF` | Turn keyboard lock on/off. |
| — | `:SETUp:ALL?` | (query only) | String of all settings, each status separated by `;` | Get all states needed to boot up at once. See field breakdown below. |

**`:SETUp:ALL?` — returned settings (semicolon-separated, verbatim field list):**
- Channel enable: `CHANnel<n>:DISPlay`
- Channel coupling: `CHANnel<n>:COUPling`
- Channel bandwidth limit: `CHANnel<n>:BWLimit`
- Probe ratio: `CHANnel<n>:PROBe`
- Voltage gear: `<>`
- Channel offset: offset (one value) of waveform relative to center line (zero center; up positive, down negative). Large divisions represent 25 values (e.g. CH1 offset value 75 = center offset by three large divisions).
- Channel inversion: `CHANnel<n>:INVert`
- Running status: `RUNning`
- Acquisition mode: `ACQuire:MODe`
- Collection type: `ACQuire:TYPE`
- Trigger method: `TRIGger:SWEep`
- Time base value: `TIMebase:SCALe`
- (Placeholder)
- Sampling rate: current sampling rate value
- Storage depth: `ACQuire:POINts`
- Trigger type: `TRIGger:MODE`
- (Placeholder)
- Edge trigger source: `TRIGger:EDGe:SOURce`
- Edge trigger level: `TRIGger:EDGe:LEVel`
- Edge trigger polarity: `TRIGger:EDGe:SLOPe`
- Pulse width trigger source: `TRIGger:PULSe:SOURce`
- Pulse width trigger level: `TRIGger:PULSe:LEVel`
- Pulse width trigger polarity: `TRIGger:PULSe:POLarity`
- Pulse width trigger condition: `TRIGger:PULSe:WHEN`
- Pulse width trigger width: `TRIGger:PULSe:WIDth`
- Timeout trigger source: `TRIGger:TIMeout:SOURce`
- Timeout trigger level: `TRIGger:TIMeout:LEVel`
- Timeout trigger polarity: `TRIGger:TIMeout:POLarity`
- Timeout trigger width: `TRIGger:TIMeout:WIDth`
- Slope trigger source: `TRIGger:SLOPe:SOURce`
- Slope trigger level a: `TRIGger:SLOPe:ALEVel`
- Slope trigger level b: `TRIGger:SLOPe:BLEVel`
- Slope trigger polarity: `TRIGger:SLOPe:POLarity`
- Conditions for slope triggering: `TRIGger:SLOPe:WHEN`
- Slope trigger width: `TRIGger:SLOPe:WIDth`
- Video trigger source: `TRIGger:TV:SOURce`
- Video trigger level: `TRIGger:VIDeo:LEVel`
- Video trigger polarity: `TRIGger:TV:POLarity`
- Video trigger standard: `TRIGger:TV:STANdard`
- Video trigger synchronization: `TRIGger:TV:MODE`
- Number of lines triggered by video: `TRIGger:TV:LINE`
- Window trigger source: `TRIGger:WINDOw:SOURce`
- Window trigger level a: `TRIGger:WINDOw:ALEVel`
- Window trigger level b: `TRIGger:WINDOw:BLEVel`
- Interval trigger source: `TRIGger:INTERVAl:SOURce`
- Interval trigger edge: `TRIGger:INTERVAl:SLOp`
- Interval trigger condition: `TRIGger:INTERVAl:WHEN`
- Interval trigger time: `TRIGger:INTERVAl:TIME`
- Interval trigger level: `TRIGger:INTERVAl:ALEVel`
- Runt trigger source: `TRIGger:UNDER_Am:SOURce`
- Runt trigger polarity: `TRIGger:UNDER_Am:POLarity`
- Runt trigger condition: `TRIGger:UNDER_Am:WHEN`
- Runt trigger time: `TRIGger:UNDER_Am:TIME`
- Runt trigger level a: `TRIGger:UNDER_Am:ALEVel`
- Runt trigger level b: `TRIGger:UNDER_Am:BLEVel`
- Serial port trigger source: `TRIGger:UART:SOURce`
- Serial port trigger conditions: `TRIGger:UART:CONdition`
- Serial port trigger baud rate: `TRIGger:UART:BAUd`
- Serial port trigger level: `TRIGger:UART:ALEVel`
- Serial port trigger data: `TRIGger:UART:DATA`
- Serial port trigger data bit width: `TRIGger:UART:WIDTh`
- Serial port trigger stop bit: `TRIGger:UART:STOP`
- Serial port trigger polarity: `TRIGger:UART:PARIty`
- CAN trigger source: `TRIGger:CAN:SOURce`
- CAN trigger idle level: `TRIGger:CAN:IDLe`
- CAN trigger baud rate: `TRIGger:CAN:BAUd`
- CAN trigger condition: `TRIGger:CAN:CONdition`
- CAN trigger data: `TRIGger:CAN:DATA`
- CAN trigger ID: `TRIGger:CAN:ID`
- CAN trigger dlc: `TRIGger:CAN:DLC`
- CAN trigger level: `TRIGger:CAN:ALEVel`
- LIN trigger source: `TRIGger:LIN:SOURce`
- LIN trigger idle level: `TRIGger:LIN:IDLe`
- LIN trigger baud rate: `TRIGger:LIN:BAUd`
- LIN trigger condition: `TRIGger:LIN:CONdition`
- LIN trigger ID: `TRIGger:LIN:ID`
- LIN trigger data: `TRIGger:LIN:DATA`
- LIN trigger level: `TRIGger:LIN:ALEVel`
- IIC trigger data-line channel source: `TRIGger:IIC:SDA:SOURce`
- IIC trigger clock-line channel source: `TRIGger:IIC:SCL:SOURce`
- IIC trigger condition: `TRIGger:IIC:CONdition`
- IIC trigger address: `TRIGger:IIC:ADDer`
- IIC trigger data: `TRIGger:IIC:DATA`
- IIC trigger clock-channel level: `TRIGger:IIC:ALEVel`
- IIC trigger data-channel level: `TRIGger:IIC:BLEVel`
- SPI trigger data-line channel source: `TRIGger:SPI:SDA:SOURce`
- SPI trigger clock-line channel source: `TRIGger:SPI:SCL:SOURce`
- SPI trigger clock edge type: `TRIGger:SPI:SCK`
- SPI trigger data bit width: `TRIGger:SPI:WIDth`
- SPI trigger data: `TRIGger:SPI:DATA`
- SPI trigger mask data: `TRIGger:SPI:MASK`
- SPI trigger clock-channel level: `TRIGger:SPI:ALEVel`
- SPI trigger data-channel level: `TRIGger:SPI:BLEVel`
- Pattern triggered by pattern: `TRIGger:LOGIc:POLarity`
- Conditions for pattern triggering: `TRIGger:LOGIc:WHEN`
- Pattern trigger width: `TRIGger:LOGIc:TIME`
- Pattern trigger CH1 level: `TRIGger:LOGIc:ALEVel`
- Pattern trigger CH2 level: `TRIGger:LOGIc:BLEVel`
- Pattern trigger CH3 level: `TRIGger:LOGIc:CLEVel`
- Pattern trigger CH4 level: `TRIGger:LOGIc:DLEVel`

> **Note:** The SETUp:ALL? remark references trigger keywords (`TRIGger:UART:STOP`, `TRIGger:LOGIc:*`, `TRIGger:CAN:DATA` without index, etc.) that do not all appear as standalone documented commands in §4. These may be internal/undocumented or alternate spellings of the PATTern commands.

---

## 13. DDS Subsystem (Built-in Signal Source / AWG)

| Command | Query | Parameters / Range | Returns | Description |
|---|---|---|---|---|
| `:DDS:SWITch <bool>` | `:DDS:SWITch?` | `<bool> ::= {{1 | ON} | {0 | OFF}}` | `ON, OFF` | Set/query signal source status (output on/off). |
| `:DDS:TYPE <type>` | `:DDS:TYPE?` | `<type> ::= {SINE | SQUAre | RAMP | EXP | NOISe | DC | ARB1 | ARB2 | ARB3 | ARB4}` | `SINE, SQUAre, RAMP, EXP, NOISe, DC, ARB1, ARB2, ARB3, ARB4` | Set/query signal source output wave type. |
| `:DDS:FREQ <freq>` | `:DDS:FREQ?` | `<freq> ::=` unit Hz | Frequency, scientific notation | Set/query frequency of source signal. |
| `:DDS:AMP <amp>` | `:DDS:AMP?` | `<amp> ::=` unit V | Amplitude, scientific notation | Set/query amplitude of signal source. |
| `:DDS:OFFSet <offset>` | `:DDS:OFFSet?` | `<offset> ::=` unit V | Offset, scientific notation | Set/query offset of source signal. |
| `:DDS:DUTY <duty>` | `:DDS:DUTY?` | `<duty> ::= 0 ~ 99` | Duty cycle value | Set/query duty cycle of signal source. |
| `:DDS:WAVE:MODE <bool>` | `:DDS:WAVE:MODE?` | `<bool> ::= {{1 | ON} | {0 | OFF}}` | `ON, OFF` | Set/query modulation status of signal source. |
| `:DDS:MODE:TYPE <type>` | `:DDS:MODE:TYPE?` | `<type> ::= {AM | FM}` | `AM, FM` | Set/query modulation type of signal source. |
| `:DDS:MODE:WAVE:TYPE <type>` | `:DDS:MODE:WAVE:TYPE?` | `<type> ::= {SINE | SQUAre | RAMP}` | `SINE, SQUAre, RAMP` | Set/query modulation wave type when modulated. |
| `:DDS:MODE:FREQ <freq>` | `:DDS:MODE:FREQ?` | `<freq> ::=` unit Hz | Frequency, scientific notation | Set/query frequency of modulating wave. |
| `:DDS:MODE:DEPThordeviation <value>` | `:DDS:MODE:DEPThordeviation?` | AM: `<value> ::=` modulation depth; FM: `<value> ::=` deviation **[sic: keyword "DEPThordeviation" = "depth-or-deviation"]** | AM → modulation depth; FM → deviation | Set/query deviation or depth of modulation. |
| `:DDS:BURSt:SWITch <bool>` | `:DDS:BURSt:SWITch?` | `<bool> ::= {{1 | ON} | {0 | OFF}}` | `ON, OFF` | Set/query signal source burst status. |
| `:DDS:BURSt:TYPE <type>` | `:DDS:BURSt:TYPE?` | `<type> ::= {N_CYCLE | INFInit}` | `N_CYCLE, INFInit` | Set/query signal source burst type. |
| `:DDS:BURSt:CNT <cnt>` | `:DDS:BURSt:CNT?` | `<value> ::=` integer | Integer | Set/query number of signal cycles. |
| `:DDS:BURSt:TRIGger` | — | (no params) | — | Send a signal source burst once. |
| `:DDS:ARB:DAC16:BIN <binary_block_data>` | — | `<binary_block_data>` = binary block starting with `#`, e.g. `#508192` (5 = chars of length field, 8192 = byte count). Each point = 2 bytes (low byte first); byte count must be even. Number of arbitrary waveform points must be **4096**. | — | Download arbitrary waveform data. |

---

## OCR Artifacts & Typos Summary (literal device strings)

These are the literal strings as printed in the manual. Implementers should test against these exact spellings, as they may be what the firmware actually expects:

| Location | Printed (literal) | Likely intended | Notes |
|---|---|---|---|
| §11.1 MASK | `:MASK:EANBle` | `:MASK:ENABle` | Letters transposed. **Test `EANBle` first** — firmware may genuinely use it. |
| §4.12 TRIGger | `:TRIGger:INTERVAl:*` | `:TRIGger:INTerval:*` | Lowercase "l" instead of expected long form. Used consistently incl. SETUp:ALL?. |
| §4.12.2 | `:TRIGger:INTERVAl:SLOp` | `…:SLOPe` | Truncated keyword. |
| §4.13 TRIGger | `:TRIGger:UNDER_Am:*` | Runt trigger | Underscore + odd casing; consistent throughout. |
| §13.11 DDS | `:DDS:MODE:DEPThordeviation` | depth/deviation | One concatenated keyword for both AM depth and FM deviation. |
| §4.6.2 / §4.12.2 | `RISIng` | `RISing` | Capital "I" appears in slope enums. |
| §4.7.3 returns | `EQUAI`, `GRAt` | `EQUAl`, `GREAt` | OCR "l"→"I"; "GREAt"/"GRAt" inconsistent within same subsystem. |
| §10.4 MEASure | `:MEASure: CHANnel<n>:ITEM` | `:MEASure:CHANnel<n>:ITEM` | Stray space after colon in header (likely typesetting only). |
| §4.15.4 CAN | `FRAM_STARE`, `FRAM_REE` | `FRAME_START`, `FRAME_ERROR` | CAN condition enums look OCR-mangled; use literal strings shown. |
| §4.9 | `:TRIGger:VIDeo:LEVel` | (under TV section) | Video level uses `VIDeo` keyword though grouped under `TV`. |
| §8.1 returns | `VECT` | `VECTors` | DISPlay:TYPE? return abbreviated. |
| §8.4 example | uses `:DISPlay:WBRightness` | `:DISPlay:GBRightness` | Example copy/paste error. |
| §4.15.8 CAN | `:TRIGger:CAN:ALEVel? TRIGger:CAN:ALEVel?` | single query | Example printed with duplicated/garbled query. |
| §4.19 PATTern | `TRIGger:PATTern` vs `TRIGger:LOGIc` | — | Section uses `PATTern`; SETUp:ALL? uses `LOGIc` for the same feature. Verify which the device accepts. |
| §2.3 | `<sacle_value>` | `<scale_value>` | Parameter name typo. |
| §13.6 example | `:DDS: DUTY 50` | `:DDS:DUTY 50` | Stray space in example. |
| §4.7.1 / §4.8.1 | PULSe/SLOPe source lists only CHANnel1–4 | — | Unlike EDGe (which adds `EXT/10`), pulse/slope/etc. sources are CH1–CH4 only. |

**Ambiguities flagged for implementers:**
- `TRIGger:UART:STOP` and `TRIGger:CAN:DATA` (no index) appear in SETUp:ALL? but lack dedicated command definitions in §4.
- `TRIGger:LOGIc:CLEVel` / `:DLEVel` (CH3/CH4 pattern levels) appear only in SETUp:ALL?; §4.19 documents only `PATTern:LEVel <chan>,<level>`.
- `MATH:OPERator` parameter list shows `FFT` as an operator value, consistent with the separate `MATH:FFT:*` subtree.
