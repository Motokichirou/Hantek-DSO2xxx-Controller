# Hantek DSO2D15 Desktop Client — Design Spec

**Date:** 2026-06-26
**Status:** Draft for review
**Frozen reference:** [`docs/scpi-command-reference.md`](../../scpi-command-reference.md) — full SCPI registry (~189 commands) extracted verbatim from the *DSO2000 Series SCPI Programmers Manual* (61 pp). Commands come from there; we do not invent them.

---

## 1. Goal & scope

A full-featured Windows desktop client for the **Hantek DSO2D15** oscilloscope, written from scratch, talking to the instrument over **USB (USBTMC) via standard VISA**. It replaces the capricious vendor software and exposes every capability documented in the programming manual — no artificial command restrictions.

**In scope (v1 target = entire manual surface):**
- Real-time dual-channel waveform display.
- Full control of every SCPI subsystem: vertical (channel), horizontal (timebase), acquire, trigger (incl. all bus-decode trigger types), math/FFT, measure, cursor, display, mask (pass/fail), system, and the built-in **DDS function generator**.
- Waveform capture to file: CSV, NumPy (`.npy`/`.npz`), HDF5.
- "Screenshot" = render of our own waveform view to PNG (the SCPI set has **no** screen-grab command — see §10).
- Preset save/load (our JSON as primary, `SETUp:ALL?` raw snapshot as bonus).
- Sweep / multi-capture for measurement series.
- SCPI terminal for direct command entry and debugging.

**Out of scope (v1):** reverse-engineering an undocumented instrument-screen protocol; multi-instrument orchestration; remote/network operation.

**Implementation reality:** although the *spec* covers the whole manual, the build proceeds in layered iterations, each verified on real hardware before moving on (per the agreed process).

---

## 2. Target environment

| | |
|---|---|
| OS | Windows 11 |
| Transport | USB / USBTMC |
| VISA backend | Keysight IO Libraries Suite (already installed & working) |
| Device enumeration | Appears as "USB Test and Measurement Device (IVI)"; VISA resource like `USB0::0x????::0x????::<serial>::INSTR` |
| Channels | 2 analog (CH1, CH2). Note: firmware reports `SYSTem:RAM? → 4` and the waveform header carries 4 channel slots generically; we parse generically but present 2. |

---

## 3. Tech stack

| Concern | Choice |
|---|---|
| Language | Python 3.11+ |
| GUI | PySide6 (Qt 6) |
| Plotting | pyqtgraph (fast real-time) |
| Instrument I/O | PyVISA (Keysight VISA backend) |
| Numerics | NumPy |
| File formats | stdlib `csv`, NumPy, `h5py` (HDF5) |
| Tests | pytest |

Rationale: best balance of development speed and real-time plot performance; mature instrument-control ecosystem; minimal, non-bulky dependencies; runs from a venv (no single-exe requirement, though packaging later is possible).

---

## 4. Architecture — layered

Hard separation of layers so that (a) all logic is testable **without hardware**, and (b) blocking VISA I/O never freezes the UI thread.

```
┌───────────────────────────────────────────────────────────┐
│  gui/        PySide6 — main window, plot, control panels,   │
│              generator, sweep, SCPI terminal, status bar    │
├───────────────────────────────────────────────────────────┤
│  engine/     acquisition controller in a background thread; │
│              run/stop/single; emits frames to GUI (signals) │
├──────────────────────────┬────────────────────────────────┤
│  scpi/  typed driver,     │  waveform/  chunked reader +    │
│  1:1 with manual          │  header parser + sample→units   │
│  (frozen reference)       │  conversion → NumPy             │
├──────────────────────────┴────────────────────────────────┤
│  transport/  PyVISA wrapper (open/write/query/read_raw,     │
│              timeouts, reconnect) + FakeTransport for tests │
└───────────────────────────────────────────────────────────┘
        io/  CSV · NPY/NPZ · HDF5 · PNG · presets (JSON)
```

### 4.1 `transport/`
- Thin wrapper over a PyVISA resource: `open(resource)`, `close()`, `write(cmd)`, `query(cmd)`, `read_raw()`, configurable timeout, termination handling.
- Connection lifecycle: discover resources (`ResourceManager.list_resources()`), connect, `*IDN?` self-test, auto-reconnect on dropout.
- `FakeTransport`: scriptable in-memory double returning canned responses and raw byte fixtures — the backbone of hardware-free unit tests.
- **Interface boundary:** everything above depends only on the abstract transport, never on PyVISA directly.

### 4.2 `scpi/` — the frozen-reference driver
- One module/class per subsystem: `channel`, `timebase`, `acquire`, `trigger` (with sub-objects: `edge`, `pulse`, `slope`, `tv`, `timeout`, `window`, `interval`, `runt`, `uart`, `can`, `lin`, `iic`, `spi`, `pattern`), `math`, `measure`, `cursor`, `display`, `mask`, `system`, `dds`.
- Each command maps to a typed Python property/method, with parameter enums and ranges taken **verbatim from the registry**. Example:
  ```python
  scope.channel[1].scale = 1.0          # :CHANnel1:SCALe 1.0
  scope.channel[1].coupling = "DC"      # :CHANnel1:COUPling DC
  scope.timebase.scale = 5e-4           # :TIMebase:SCALe 5e-4
  scope.trigger.edge.level = 0.5        # :TRIGger:EDGe:LEVel 0.5
  ```
- **Client-side validation + readback** (see §9): because the device has no error queue, the driver validates against known enums/ranges before sending and can read the value back to confirm.
- Command strings centralized so the OCR-ambiguous literals (§11) live in exactly one place and are trivially swappable after hardware testing.

### 4.3 `waveform/` — acquisition decode (the crux)
Parses `:WAVeform:DATA:ALL?`. This is the only waveform readout and has a bespoke format:

**Read algorithm:**
1. Issue `:WAVeform:DATA:ALL?`, `read_raw()`.
2. Parse the IEEE-488.2 block prefix `#9` + 9-digit current-packet byte length.
3. **First packet** carries the full header (offsets data[0]…data[127], see registry §7):
   running status, trigger status, per-channel **offset** (4 digits ×4), per-channel **voltage / V-div** (7 digits ×4), **channel-enable** mask (4 digits), **sampling rate** (9 digits), **sampling multiple** (6 digits), trigger time, frame start, reserved — then the first chunk of sample bytes.
4. `total_len` (data[11..19]) gives the full byte count; `uploaded_len` (data[20..28]) gives how much has arrived. Keep issuing `:WAVeform:DATA:ALL?` to pull **subsequent chunks** (short header: `#9`, packet len, total len, uploaded len, then data) until `uploaded == total`.
5. Convert raw samples → volts using header V/div + offset + counts-per-division; build the time axis from sampling rate (`dt = 1/SRATe`).

**Outputs:** per enabled channel, a NumPy array of volts + a shared time array, plus a metadata dict (sample rate, depth, trigger status, per-channel scale/offset).

> ⚠️ **Sample encoding (bytes-per-sample) and exact counts-per-division scaling are NOT fully specified by the manual** and must be calibrated on hardware against a known reference (built-in 1 kHz cal square or the DDS generator looped into a channel). This is the first hardware-verification task (§11).

### 4.4 `engine/` — acquisition controller
- Runs the acquire→read→decode loop on a background `QThread`; emits decoded frames to the GUI via Qt signals. VISA calls never touch the UI thread.
- Manages transport states: Run (free-run/auto), Single, Stop, Force.
- Arms acquisition, polls `:TRIGger:STATus?`, triggers waveform readout, decodes, emits.
- **Depth/refresh tradeoff:** live view uses shallow memory depth (`:ACQuire:POINts 4000`) for fast transfer & high refresh; deep capture (to file) allows up to 8M with a progress indicator, non-real-time. We do **not** promise a fixed FPS — we measure achievable throughput on hardware and tune; the UI decouples from I/O regardless.

### 4.5 `gui/`
PySide6 main window (see §8 / the Claude-design prompt for visual detail):
- Central pyqtgraph graticule (dual channel, grid, cursors, trigger-level & ground markers).
- Right-side control dock: Vertical, Horizontal, Trigger, Acquire, Measure, Math, Cursors, Display panels.
- Generator (DDS) panel, Sweep panel, SCPI terminal dock, top transport toolbar, bottom status bar.

### 4.6 `io/`
CSV, NumPy `.npy`/`.npz`, HDF5 (h5py), PNG screenshot (render of the plot scene), and preset serialization (§7-formats).

### 4.7 Package layout
```
hantek_dso2d15/
  transport/   __init__.py  visa_transport.py  fake_transport.py
  scpi/        channel.py timebase.py acquire.py trigger/ math.py
               measure.py cursor.py display.py mask.py system.py dds.py
               scope.py        # top-level facade aggregating subsystems
  waveform/    reader.py  header.py  convert.py
  engine/      controller.py  states.py
  gui/         main_window.py  plot_widget.py  panels/  terminal.py
  io/          csv_io.py  npy_io.py  hdf5_io.py  png_io.py  presets.py
  app.py       # entry point
tests/
docs/
  DSO2000-SCPI-Programmers-Manual.pdf
  scpi-command-reference.md
  superpowers/specs/2026-06-26-hantek-dso2d15-design.md
```

---

## 5. Feature → subsystem mapping (UI surface)

| UI area | SCPI subsystem(s) |
|---|---|
| Vertical (per channel) | `CHANnel<n>`: SCALe, OFFSet, COUPling, BWLimit, PROBe, INVert, VERNier, DISPlay |
| Horizontal | `TIMebase`: SCALe, POSition, RANGe, MODE, WINDow(zoom) |
| Acquire | `ACQuire`: POINts, TYPE, COUNt, SRATe? |
| Trigger | `TRIGger`: MODE, SWEep, HOLDoff, FORCe, STATus?, + per-type (EDGe/PULSe/SLOPe/TV/TIMeout/WINDOw/INTERVAl/UNDER_Am/UART/CAN/LIN/IIC/SPI/PATTern) |
| Measure | `MEASure`: ENABle, SOURce, ADISplay, CHANnel\<n\>:ITEM (37 types), GATE |
| Math | `MATH`: DISPlay, OPERator (ADD/SUB/MUL/DIV/FFT), SOURce1/2, SCALe, OFFSet, FFT:* |
| Cursors | `CURSor`: MODE, MANual:*, TRACk:* |
| Display | `DISPlay`: TYPE, GRID, WBRightness, GBRightness |
| Pass/Fail | `MASK`: EANBle[sic], SOURce, X, Y, CREate, OUTPut, SOOutput, MDISplay |
| Generator | `DDS`: SWITch, TYPE, FREQ, AMP, OFFSet, DUTY, WAVE:MODE, MODE:* (AM/FM), BURSt:*, ARB:DAC16:BIN |
| System/util | `SYSTem`: PON, LANGuage, LOCKed, GAM?, RAM?; `CALibrate`; `SETUp:ALL?` |

---

## 6. Real-time pipeline summary

`engine` thread loop → arm → poll `:TRIGger:STATus?` → `:WAVeform:DATA:ALL?` chunked read → `waveform` decode → emit NumPy frame → `gui` `setData`. Shallow depth for live; deep for capture. Bottleneck is USBTMC transfer; throughput measured & tuned on hardware.

---

## 7. Data formats & presets

**Waveform export:**
- **CSV** — human-readable: time column + one column per enabled channel (volts), header with metadata comments.
- **NumPy `.npy`/`.npz`** — arrays + metadata dict.
- **HDF5** — datasets per channel + attributes (scale, offset, sample rate, depth, timestamp); suited to sweep/multi-capture series.
- **PNG** — render of the plot scene (the "screenshot").

**Presets:**
- **Primary: our JSON** — structured snapshot of every setting we expose; portable, human-readable, versioned. Restored by replaying typed driver setters (with readback confirmation).
- **Bonus: `SETUp:ALL?` raw snapshot** — stored as opaque string. Whether it can be written back to the instrument is **not documented**; flagged for hardware verification (§11). If a write-back form works, we expose "restore raw snapshot"; otherwise JSON-replay remains authoritative.

---

## 8. UI / visual design

Visual mockup is produced separately in **Claude design** (detailed prompt already drafted). Key conventions baked in: dark instrument theme; channel color coding (CH1 yellow, CH2 cyan, MATH magenta); monospaced numeric readouts; dense benchtop-scope layout — central graticule, right-side control dock, transport toolbar, status bar, generator panel, SCPI terminal dock. The Qt implementation follows the approved mockup.

**Localization:** the UI is **bilingual (English / Russian) with a runtime language switcher**. All user-facing strings go through a translation layer (Qt `tr()` / `.ts` files or an equivalent dict-based mechanism) from the start — no hard-coded labels. Default language English; switchable to Russian without restart. Instrument-standard unit tokens (V/div, s/div, Hz) stay as-is in both languages.

---

## 9. Error handling & validation

- **No `SYSTem:ERRor?` in the manual** → the instrument exposes no queryable error queue. Therefore:
  - The driver **validates parameters client-side** against the registry's enums/ranges before sending.
  - After a set, it can **read the value back** to confirm the instrument applied it (the manual notes out-of-range values clamp to nearest legal).
- VISA timeouts / disconnects → surfaced in the status bar, auto-reconnect attempted, UI never crashes.
- SCPI terminal shows sent/received/error lines so the user can diagnose directly.

---

## 10. Notable manual findings driving design

- `:WAVeform:DATA:ALL?` is the **only** waveform readout; chunked; bespoke header (§4.3).
- **No screenshot command** anywhere in the SCPI set → screenshot = render of our own view.
- `:SETUp:ALL?` gives a full settings snapshot string (write-back undocumented).
- `:MEASure:CHANnel<n>:ITEM?` returns instrument-computed measurements (37 types) — query only.
- `:DDS:ARB:DAC16:BIN` downloads arbitrary waveforms (exactly 4096 points, 2 bytes/point, little-endian).

---

## 11. Hardware-verification TODO (do not trust blindly)

The manual is a frozen reference but contains OCR artifacts and gaps. Before the driver trusts these literals, confirm on the device:

1. **Sample encoding & scaling** — bytes-per-sample and counts-per-division for `WAVeform:DATA:ALL?` conversion; calibrate against a known signal. *(Blocks accurate volts/time.)*
2. **`SETUp:ALL?` write-back** — is there a set form to restore a raw snapshot?
3. **`:MASK:EANBle`** — is the literal misspelling required, or does `ENABle` work?
4. **Trigger keyword divergence** — `TRIGger:MODE` enum spells types `INTerval / UNDerthrow / WINdow / EDGE`, but sub-command keywords are `INTERVAl / UNDER_Am / WINDOw / EDGe`. Confirm each literal the firmware accepts.
5. **`PATTern` vs `LOGIc`** — §4.19 uses `TRIGger:PATTern:*`; `SETUp:ALL?` references `TRIGger:LOGIc:*` for the same feature. Which does the device accept?
6. **Phantom commands** in `SETUp:ALL?` only: `TRIGger:UART:STOP`, `TRIGger:CAN:DATA` (no index), `TRIGger:LOGIc:CLEVel/DLEVel`.
7. **CAN condition enums** `FRAM_STARE` / `FRAM_REE` — likely OCR for `FRAME_START` / `FRAME_ERROR`; confirm literal strings.
8. **`RISIng` / `EQUAI` / `GRAt`** casing in slope/pulse enums.
9. **EXT/10 trigger source** — does DSO2D15 (2-ch) accept `EXT/10`?

Each becomes a smoke-test assertion; the driver keeps these literals in one place for easy correction.

---

## 12. Testing strategy

- **Hardware-free unit tests (pytest):** header parser & sample conversion against captured raw-byte fixtures; command-string formatting; parameter validation; preset (JSON) round-trip; file-format round-trips — all via `FakeTransport`. TDD especially for `waveform/` and `scpi/`.
- **Hardware smoke tests:** scripted routines the user runs after each iteration (connect/`*IDN?`, set+readback per subsystem, one full waveform capture+decode, generator output, the §11 verification checks).
- **Iteration discipline:** each layer verified on the real DSO2D15 before building atop it.

---

## 13. Build order (informs the implementation plan)

1. `transport` + `FakeTransport` + connection self-test.
2. `scpi` core (channel/timebase/acquire/trigger-edge) with validation+readback.
3. `waveform` reader/decoder — **calibrated on hardware** (verification item #1).
4. `engine` loop + minimal `gui` (plot + connect + run/stop) → first live dual-channel display.
5. Remaining control panels (full trigger, measure, math/FFT, cursor, display, mask).
6. Generator (DDS) panel.
7. IO (CSV/npy/HDF5/PNG) + presets.
8. Sweep/multi-capture + SCPI terminal.

(Detailed task plan to be produced via the writing-plans step.)

---

## 14. Open questions

- HDF5 schema details (finalize when wiring sweep).
- Exact live-view default memory depth (pick after measuring throughput).

*(Resolved: UI is bilingual EN/RU with runtime switcher — §8. Git repository initialized as project baseline.)*
