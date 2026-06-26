# Handoff: Hantek DSO2D15 Desktop Control Application UI

## Overview
This is the UI for a **Windows desktop application** that controls a **Hantek DSO2D15**
digital storage oscilloscope over USB (VISA / USBTMC). It is a full-featured replacement
for the vendor software: a 2-channel scope (CH1, CH2), a built-in arbitrary/function
generator (AWG), ~35 automatic measurements, math/FFT, and protocol-decode triggers.

The interface follows the visual language of professional bench test-and-measurement
software: a single dense main window, dark instrument theme, channel color coding, and
monospaced numeric readouts. The real-time dual-channel waveform display is the centerpiece.
Target window: **1920×1080, resizable**.

## About the Design Files
The files in this bundle are **design references created in HTML/Canvas/JS** — a working
prototype that shows the intended look, layout, and interaction model. **They are not
production code to copy directly.** The task is to **recreate this design in the target
application's environment** using its established patterns and libraries.

This is a desktop app, so the realistic target stacks are: **Qt (C++/QML or PyQt/PySide)**,
**WPF / WinUI (C#)**, **Electron + React**, or **Tauri + React/Svelte**. If no environment
exists yet, choose the stack best suited to a real-time instrument GUI — Qt/QML and
WPF are the conventional choices for benchtop instrument software because of their
hardware-accelerated 2D drawing and dense native controls. The waveform display must be
drawn on a **GPU-accelerated canvas/surface** (QML Canvas/Scene Graph, Direct2D, WebGL/
Canvas2D in Electron), not as DOM/SVG nodes, because it redraws every frame.

The prototype's instrument communication is **mocked** (static readouts, a fake sine/square,
a sample SCPI log). The real app must wire every control to actual SCPI commands over
VISA/USBTMC — example commands are shown in the SCPI Terminal section and called out per
control below.

## Fidelity
**High-fidelity (hifi).** Final colors, typography, spacing, density, and channel color
coding are intentional and should be reproduced faithfully. Exact hex values, font sizes,
and the dark-theme palette are specified in Design Tokens below. Recreate the UI
pixel-faithfully using the target codebase's native controls styled to match.

## Layout Regions (top to bottom)
The window is a vertical flex column at 1920×1080:

1. **Top toolbar** — height **48px**, full width.
2. **Main row** — fills remaining height, horizontal split:
   - **Center column** (flex, fills remaining width): waveform display + (optional) SCPI terminal docked at its bottom.
   - **Right control dock** — fixed width **382px**, on the right edge.
3. **Bottom status bar** — height **28px**, full width.

Panel backgrounds layer from darkest to lightest: window `#0E0F12` → waveform graticule
`#08090B` → dock `#13151A` → panel headers / inset surfaces `#16181D` / `#1B1E24`.
All separators are 1px `#2A2D34`.

---

## Screens / Views
This is a single-window app; "views" are the toolbar, the waveform display, and the
swappable right-dock tabs (Scope / Generator / Sweep), plus the toggleable SCPI terminal.

### 1. Top Toolbar (48px, bg `#16181D`, bottom border 1px `#2A2D34`, horizontal padding 12px, gap 10px)
**Left group — connection:**
- VISA resource dropdown: pill `#0E0F12`, 1px `#2A2D34`, radius 5px, height 30px, min-width 300px.
  Contains a 7px status dot (`#37D67A` connected with glow `0 0 6px`, `#5A606C` offline),
  the resource string `USB0::0x049F::0x505::SN21034::INSTR` in **JetBrains Mono 12px/500**, and a `▾`.
- **Disconnect** button (shown when connected): height 30px, padding 0 14px, radius 5px,
  border `#2F4A3C`, bg `rgba(55,214,122,0.12)`, text `#37D67A`, Inter 12px/600. When
  disconnected it reads **Connect** in neutral styling and the dot goes gray.
- Identity block: two lines — `Hantek DSO2D15` (Inter 12px/600, `#E6E9EF`) over
  `FW V1.2.3 · CN21034` (JetBrains Mono 10px/500, `#6E747F`).

**Center group — acquisition transport** (centered, gap 8px):
- **RUN/STOP** toggle, height 34px, min-width 120px, radius 6px. While running it shows
  `■  STOP` (border `#5A2A2C`, bg `rgba(229,72,77,0.16)`, text `#E5484D`). While stopped it
  shows `▶  RUN` (border `#2F4A3C`, bg `rgba(55,214,122,0.16)`, text `#37D67A`). Inter 13px/700.
  → SCPI `:RUN` / `:STOP`.
- **SINGLE** — amber outline: border `#6A521E`, bg `rgba(245,166,35,0.10)`, text `#F5A623`. → `:SINGLe`.
- **FORCE** — neutral: border `#2A2D34`, bg `#1B1E24`, text `#C5C9D1`. → `:TFORce`.
- **AUTO** — neutral (auto-setup). → `:AUToscale`.

**Right group — actions** (gap 6px, neutral icon buttons unless noted):
- **Save** (waveform) — labeled, save-icon (rect+tab SVG). → write waveform to CSV/NPY/HDF5.
- **Screenshot** — camera-icon square button (34px). → screen capture / `:DISPlay:DATA?`.
- **Presets** — labeled, save/load instrument setups.
- **SCPI** — toggles the SCPI terminal; active state = green (border `#2F4A3C`,
  bg `rgba(55,214,122,0.14)`, text `#37D67A`), inactive = neutral. Glyph `>_` in JetBrains Mono.
- **Settings** — gear-icon square button.

### 2. Waveform Display (center, fills space; 10px padding around a graticule card)
Graticule card: bg `#08090B`, 1px `#2A2D34`, radius 4px, `overflow:hidden`, `position:relative`.
A full-size **canvas** fills it (`position:absolute; inset:0`). Everything else is an
absolutely-positioned HTML overlay on top.

**Canvas drawing (redrawn every animation frame):**
- **Graticule**: 14 horizontal × 8 vertical divisions. Minor lines `rgba(255,255,255,0.05)`,
  1px. Center cross (the two middle axes) brighter `rgba(255,255,255,0.16)`. Tick marks
  along the two center axes at 5 subdivisions per division, `rgba(255,255,255,0.28)`, 4px long.
  Outer border `rgba(255,255,255,0.12)`. Grid type is selectable (Full / Dotted / Off) and
  brightness is adjustable (Display panel).
- **CH1 trace** (`#F2C300`): sine, vertically centered, amplitude ≈ 2.0 divisions.
- **CH2 trace** (`#23C8E6`): square wave, vertical offset +2 divisions up, amplitude ≈ 1.35 divisions.
- Both traces drawn with a phosphor glow: `shadowColor = trace color`, `shadowBlur = 7`,
  `lineWidth ≈ 1.7`, round joins/caps. ~720 points per trace.
- **Animation**: while RUN, a phase accumulator advances each frame (CH1 `+0.035`/frame,
  CH2 `+0.028`/frame) so traces drift; while STOP, drawing freezes. In production these are
  real sampled buffers from the instrument, not synthesized math.
- Use device-pixel-ratio scaling (cap at 2) for crisp lines.

**HTML overlays (over the canvas):**
- **Top-left readout stack** (semi-opaque badges `rgba(8,9,11,0.78)`, radius 3px,
  JetBrains Mono): row 1 — `CH1 500mV` (yellow, 10px color chip, badge border
  `rgba(242,195,0,0.45)`) + `DC`; `CH2 1.00V` (cyan, border `rgba(35,200,230,0.45)`) + `DC`.
  Row 2 — `Time 200µs/div`, `1.0 GSa/s`, `4K` (neutral badges, border `#2A2D34`).
- **Trigger-status badge** (top-center): JetBrains Mono 12px/700, border `rgba(color,0.5)`.
  Value + color depend on state: STOP→`Stop` `#E5484D`; Auto sweep→`Auto` `#F5A623`;
  Single→`Ready` `#23C8E6`; Normal/triggered→`Trig'd` `#37D67A`.
- **Top T-marker** (horizontal trigger position): small `#C5C9D1` down-triangle at top edge (~51% across).
- **Left ground-reference markers**: right-pointing colored triangles with the channel
  number in `#08090B` — CH1 (`#F2C300`) at its offset (≈50% / center), CH2 (`#23C8E6`)
  at ≈25% from top. They track each channel's vertical offset.
- **Right trigger-level arrow**: left-pointing triangle colored by the trigger source
  channel (here `#F2C300` / CH1) with a `T` label, at the trigger voltage (≈58%).
- **Cursors**: two vertical dashed white lines `rgba(255,255,255,0.55)` at ≈34% and ≈62%,
  each with an 11px draggable square handle (`#0E0F12`, 1px white) near the top.
- **Cursor readout box** (bottom-right): `rgba(8,9,11,0.85)`, 1px `#2A2D34`, radius 4px.
  Title `CURSORS X` (Inter 10px/600 uppercase, `#7A808C`), then label/value rows in
  JetBrains Mono — `ΔX 560.0 µs`, `1/ΔX 1.7857 kHz`, `ΔY 2.48 V` (labels `#7A808C`, values `#E6E9EF`).
- **Zoom strip** (appears only when "Zoom window" is on): a 64px strip below the graticule
  showing the full record with a highlighted zoomed window (`rgba(242,195,0,0.10)` fill,
  yellow side borders).

### 3. SCPI Terminal (docked at bottom of center column when toggled)
Height **230px**, top border 1px `#2A2D34`, bg `#0B0C0F`.
- Header (30px, bg `#16181D`): `>_` (green) + `SCPI Terminal` (Inter 11px/600 uppercase,
  `#9AA0AC`) and a `×` close button.
- Scrollback (flex, padding 8px 12px, JetBrains Mono 12px/500), one line per entry,
  color-coded: **sent** `> …` `#37D67A`, **received** `< …` `#C5C9D1` (or `#6E747F` for
  bare `OK`), **error** `! …` `#E5484D`.
- Input row (38px, top border): green `>` prompt, text input (`#0E0F12`, 1px `#2A2D34`,
  radius 4px, JetBrains Mono 12px, `#E6E9EF`), and a **Send** button (bg `#37D67A`, text
  `#08090B`, Inter 11px/700). Supports command history.

Example session (use as real command reference):
```
> *IDN?
< Hantek,DSO2D15,CN21034,V1.2.3
> :CHAN1:SCAL 0.5
< OK
> :MEAS:VPP? CHAN1
< 3.604E+0
> :TRIG:EDGE:LEV 0.82
< OK
! :TRIG:LEV 99 — value out of range
```

### 4. Right Dock (382px wide, bg `#13151A`, left border 1px `#2A2D34`)
**Tab bar** (38px, bg `#16181D`): three equal tabs **Scope / Generator / Sweep**, Inter 12px/600.
Active tab: bg `#13151A`, text `#E6E9EF`, 2px bottom border `#37D67A`. Inactive: text
`#7A808C`, transparent. Body below scrolls vertically.

#### Tab A — Scope (accordion of collapsible panels)
Each panel has a 32px header (bg `#1B1E24`, title Inter 11px/600 uppercase `#AEB4BF`,
letter-spacing .7px, a `▾`/`▸` chevron, and sometimes a summary chip). Clicking the header
toggles the body. Default expanded: **Vertical, Horizontal, Trigger, Measure**. Default
collapsed: Acquire, Math, Cursors, Display.

Shared control widgets used throughout the dock:
- **Spin-box**: row with a fixed-width label (`#7A808C`, Inter 11px/500) + a field
  (`#0E0F12`, 1px `#2A2D34`, radius 4px, height 26px) holding a centered JetBrains Mono
  12px/600 value (`#E6E9EF`) and a stacked ▲/▼ stepper column (22px wide, divider on top
  button, `#7A808C` 8px glyphs) on the right.
- **Dropdown**: same field but left-aligned value + a trailing `▾` (`#5A606C`).
- **Segmented toggle**: a row of buttons inside a 1px `#2A2D34` rounded container, each 24px
  tall, Inter 11px/600. Active segment: bg `rgba(channelColor,0.16)` (or neutral `#2D313A`),
  text = channel color (or `#E6E9EF`), inset box-shadow `inset 0 0 0 1px rgba(channelColor,0.55)`.
  Inactive: transparent, `#7A808C`.
- **Checkbox**: 14px rounded square, 1px `#3A3F49`; checked fills channel/accent color with
  a `✓` in `#08090B`.
- **Slider**: 5px track (`#0E0F12`, 1px `#2A2D34`), filled portion `#37D67A`, 12px round
  white thumb.
- **Switch (toggle pill)**: 30px×16px (or 34×18) rounded track; ON = channel/accent color
  with knob to the right, OFF = `#2A2D34` with knob left.

**VERTICAL** — two channel sub-blocks, each a card bordered/tinted in its channel color
(`rgba(242,195,0,0.30)` for CH1, `rgba(35,200,230,0.30)` for CH2). Card header (bg
`rgba(color,0.07)`): channel name (Inter 12px/700 in channel color) + a `DC · 10X` summary
and an ON/OFF switch (filled with channel color). Card body controls:
- **Scale (V/div)** spin-box — CH1 `500 mV/div`, CH2 `1.00 V/div`. Range 1mV/div…10V/div. → `:CHANn:SCALe`.
- **Offset/Position** spin-box — CH1 `0.00 V`, CH2 `+2.00 V`. → `:CHANn:OFFSet`.
- **Coupling** segmented `[DC | AC | GND]` (tinted in channel color). → `:CHANn:COUPling`.
- **Probe** dropdown `[1X | 10X | 100X | 1000X]`, default `10X`. → `:CHANn:PROBe`.
- (CH1 also shows) checkboxes: **BW 20MHz** (checked), **Invert**, **Fine** (vernier).
  → `:CHANn:BWLimit`, `:CHANn:INVert`, `:CHANn:VERNier`.

**HORIZONTAL / TIMEBASE**:
- **Time/div** spin-box `200 µs/div` (range ns/div…s/div). → `:TIMebase:SCALe`.
- **Position** spin-box `0.000 s` (trigger offset). → `:TIMebase:OFFSet`.
- **Mode** segmented `[Main | XY | Roll]` (Main active). → `:TIMebase:MODE`.
- **Zoom window** checkbox — when on, reveals the zoom strip + window scale/position. → `:TIMebase:DELay:ENABle`.

**TRIGGER** (header summary `Edge · CH1`):
- **Type** dropdown — `Edge` default. Full list: `[Edge | Pulse | Slope | Video | Timeout |
  Window | Interval | Runt | Pattern | UART | CAN | LIN | I2C | SPI]`. → `:TRIGger:MODE`.
- **Source** dropdown `[CH1 | CH2]` — tinted in source channel color (yellow `CH1`). → `:TRIGger:EDGE:SOURce`.
- **Sweep** segmented `[Auto | Normal | Single]` (amber accent, Auto active). → `:TRIGger:SWEep`.
- **Slope** segmented `[Rising | Falling | Either]` (Rising active) — shown for Edge. → `:TRIGger:EDGE:SLOPe`.
- **Level** spin-box `+820 mV` + a **50%** quick button (height 26px, neutral, Inter 10px/600). → `:TRIGger:EDGE:LEVel`, set-to-50%.
- **Holdoff** spin-box `100 ns`. → `:TRIGger:HOLDoff`.
- **The panel morphs per trigger type.** When a bus type (UART/CAN/LIN/I²C/SPI) is selected,
  replace the Slope/Level rows with that protocol's fields, e.g. **UART**: baud, data bits,
  parity, stop bits, polarity, trigger condition. The prototype shows the Edge layout plus a
  note describing this behavior.

**ACQUIRE** (collapsed by default, summary `Normal · 4K`):
- **Mode** dropdown `[Normal | Average | Peak Detect | High-Res]`. → `:ACQuire:TYPE`.
- **Average count** dropdown `[4|8|16|32|64|128]` — shown only when Mode = Average. → `:ACQuire:AVERages`.
- **Mem depth** dropdown `[4K | 40K | 400K | 4M | 8M]`. → `:ACQuire:MDEPth`.
- **Sample rate** live readout row `1.0 GSa/s` (value in `#37D67A`). → `:ACQuire:SRATe?`.

**MEASURE** (expanded):
- **Source** dropdown `[CH1 | CH2 | MATH]` (value tinted to source).
- **+ Add measurement** button (bg `rgba(55,214,122,0.10)`, border `#2F4A3C`, text `#37D67A`).
  Opens a grouped list — **Voltage**: Vpp, Vmax, Vmin, Vtop, Vbase, Vamp, Vavg, Vrms,
  Overshoot, Preshoot… / **Time**: Period, Freq, Rise, Fall, +Width, -Width, +Duty, -Duty, Delay, Phase…
- **Active measurements table**: header row (`Type | Source | Value`, Inter 9px/600 uppercase
  `#6E747F`, bg `#16181D`), then rows separated by 1px `#1E2128`. Columns: Type (Inter 11px/600
  `#C5C9D1`, 64px), Source (JetBrains Mono 11px/600 in channel color, 52px), Value
  (JetBrains Mono 12px/600 `#E6E9EF`, right-aligned). Sample rows:
  `Vpp CH1 3.60 V` · `Freq CH1 1.000 kHz` · `Vrms CH1 1.273 V` · `Vmax CH2 +2.48 V` ·
  `Period CH2 250.0 µs` · `+Duty CH2 50.2 %`. → `:MEASure:ITEM`.

**MATH / FFT** (collapsed, magenta `#C77DFF` accent chip in header):
- **Operation** dropdown `[CH1+CH2 | CH1-CH2 | CH1×CH2 | CH1÷CH2 | FFT]` (magenta-tinted). → `:MATH:OPERator`.
- **Math scale / offset** for the math trace.
- When **FFT**: **Window** dropdown `[Rectangle | Hanning | Hamming | Blackman]`, **Units**
  `[dBVrms | Vrms]`, **Hz/div** horizontal scale, and **center frequency**. → `:MATH:FFT:*`.

**CURSORS** (collapsed, summary `Manual · X`):
- **Mode** segmented `[Off | Manual | Track]` (Manual active).
- **Type** segmented `[X | Y | XY]` (X active).
- **Source** `[CH1 | CH2 | MATH]`.
- Readout of A/B positions and deltas (mirrors the on-screen cursor box).

**DISPLAY** (collapsed):
- **Waveform** segmented `[Vectors | Dots]` (Vectors active).
- **Grid** segmented `[Full | Dotted | Off]` (Full active) + a brightness slider.
- **Intensity** (waveform brightness) slider, ~72% filled.

#### Tab B — Generator (AWG)
- **Output card** (border `#2A2D34`, radius 7px, bg `#1B1E24`): title `AWG Output`
  (Inter 13px/700 `#E6E9EF`) over `50 Ω · CH OUT`, and a big **ON/OFF** toggle (label `ON`/`OFF`,
  track green when on). → `:WGEN:OUTPut`.
- **Waveform tiles**: 4-column grid, each tile 48px, radius 6px, glyph over a 9px label.
  `[Sine | Square | Ramp | Pulse | Noise | DC | Arb1 | Arb2]`. Selected tile: border `#37D67A`,
  bg `rgba(55,214,122,0.10)`, text `#37D67A`; others border `#2A2D34`, bg `#0E0F12`, text
  `#9AA0AC`. (Tiles use simple unicode glyphs in the prototype — replace with proper waveform
  icons in production.) → `:WGEN:FUNCtion`.
- **Frequency** spin-box — large 30px field, value `1.000 kHz` in green JetBrains Mono 14px/700. → `:WGEN:FREQuency`.
- **Amplitude** `2.000 Vpp`, **Offset** `0.00 V`, **Duty** `50.0 %` spin-boxes. → `:WGEN:VOLTage` / `:OFFSet` / `:FUNCtion:SQUare:DCYCle`.
- **Modulation** sub-card (header with on/off switch; body dimmed when off): **Type** `[AM | FM]`,
  **Wave** `[Sine | Square | Ramp]`, **Freq**, **Depth/Deviation**. → `:WGEN:MOD:*`.
- **Burst** sub-card (header switch): **Type** `[N-Cycle | Infinite]`, **Cycles** (count), and a
  **Trig** button (amber). → `:WGEN:BURSt:*`.

#### Tab C — Sweep / Multi-capture
Title `SWEEP / MULTI-CAPTURE`. Controls:
- **Parameter** dropdown — e.g. `Gen Frequency` (or timebase, etc.).
- **Start / Stop / Step** trio (`100 Hz` / `100 kHz` / `1 kHz`), each labeled field.
- **Dwell** (`200 ms`) and **Format** dropdown `[CSV | NPY | HDF5]` (`CSV`).
- **Output folder** field with path `C:\Captures\run_07\` and a folder picker.
- **Progress**: label row `Прогресс  42 / 100` (JetBrains Mono, count in `#37D67A`) + an 8px
  progress bar (track `#0E0F12`, fill `#37D67A`, 42%).
- **Stop** (red outline) / **Start** (green outline) buttons, 32px tall, side by side.

### 5. Status Bar (28px, bg `#16181D`, top border 1px `#2A2D34`, JetBrains Mono 11px/500)
Left-to-right, segments separated by 1px `#2A2D34` dividers:
`● Connected` (green dot + text `#37D67A`) · `Hantek DSO2D15` · `1.0 GSa/s` · `Mem 4K` ·
`Trig: <status>` (colored by trigger status) · (flex spacer) · transient message
`Waveform saved → capture_001.csv` (`#6E747F`).

---

## Interactions & Behavior
- **RUN/STOP**: toggles acquisition. Running animates the traces and sets trigger status to
  `Trig'd`/`Auto`; STOP freezes the canvas and shows `Stop` (red) everywhere it appears.
- **SINGLE / FORCE / AUTO**: single-shot arm, force a trigger, and auto-setup respectively.
- **Tabs** (Scope/Generator/Sweep): swap the right-dock body; active tab gets the green underline.
- **Accordion headers**: click toggles each panel's body; chevron flips `▸`↔`▾`.
- **Segmented toggles** (Coupling, Sweep, Slope, Mode, etc.): click selects; selected segment
  is tinted in the relevant channel/accent color.
- **SCPI button**: toggles the bottom terminal dock; button turns green while open.
- **Zoom window checkbox**: reveals/hides the zoom strip under the graticule.
- **Generator**: Output toggle flips the track color; waveform tiles are single-select.
- **Trigger Type change**: the Trigger panel morphs to expose the selected type's fields
  (most important dynamic behavior to implement — bus types reveal protocol decode fields).
- **Cursors**: handles are draggable along the graticule; the readout box updates ΔX, 1/ΔX, ΔY live.
- **Animation/transition feel**: the prototype keeps transitions minimal (instrument software
  favors instant, low-latency control feedback over decorative motion). The only continuous
  animation is the waveform redraw loop (`requestAnimationFrame`).

## State Management
Top-level UI state (mirrors the prototype):
- `running` (bool) — acquisition on/off, drives trace animation + trigger status.
- `activeTab` — `'scope' | 'generator' | 'sweep'`.
- `scpiOpen` (bool), `zoomOn` (bool).
- `coup1`, `coup2` — `'DC' | 'AC' | 'GND'` per channel.
- `sweep` — `'Auto' | 'Normal' | 'Single'` (drives trigger status text/color).
- `genOn` (bool), `genWave` — selected AWG waveform.
- `exp` — per-panel expanded/collapsed booleans for the 8 Scope panels.
- Derived: trigger status `{label,color}` computed from `running` + `sweep`.

Instrument/data state to add in production:
- Connection state + selected VISA resource + IDN string.
- Per-channel scale/offset/coupling/probe/bwlimit/invert/vernier, timebase scale/offset/mode,
  trigger config (type-dependent), acquire mode/depth, math/FFT config, cursor positions.
- Live sample buffers for CH1/CH2 (+ math), measurement results, sample rate.
- SCPI command history + scrollback log.
- A polling/streaming layer over VISA/USBTMC that pushes waveform frames and measurement
  values into the UI on a timer. Keep the SCPI I/O off the UI thread.

## Design Tokens

### Colors
| Token | Hex | Use |
|---|---|---|
| Window bg | `#0E0F12` | App background, input fields |
| Graticule bg | `#08090B` | Waveform area, marker label text |
| Dock bg | `#13151A` | Right control dock |
| Panel header bg | `#1B1E24` | Accordion headers, cards |
| Inset/header bg | `#16181D` | Toolbar, status bar, table headers |
| Border | `#2A2D34` | Default 1px borders/dividers |
| Border light | `#3A3F49` | Checkbox/thumb outlines |
| Divider subtle | `#22252C` / `#1E2128` | Panel + table row separators |
| Text primary | `#E6E9EF` | Values, emphasis |
| Text secondary | `#C5C9D1` | Body text |
| Text muted | `#9AA0AC` / `#7A808C` | Labels |
| Text faint | `#6E747F` / `#5A606C` | Captions, chevrons |
| CH1 (yellow) | `#F2C300` | Channel 1 identity |
| CH2 (cyan) | `#23C8E6` | Channel 2 identity |
| MATH (magenta) | `#C77DFF` | Math/FFT trace |
| Cursor/ref | `#FFFFFF` / `#C5C9D1` | Cursors, reference markers |
| RUN/OK (green) | `#37D67A` | Run, connected, primary action, sample rate |
| STOP/error (red) | `#E5484D` | Stop, errors |
| SINGLE/trigger (amber) | `#F5A623` | Single, auto sweep, warnings |

Tinted fills follow the pattern `rgba(<channel>, 0.07)` (card header), `0.10–0.16`
(active segment / button bg), `0.30–0.45` (tinted borders), `0.55` (active segment inset ring).

### Typography
- **UI / labels**: Inter (fallback Segoe UI, sans-serif). Weights 500/600/700.
  Sizes: panel titles 11px/600 uppercase (letter-spacing .6–.7px); row labels 11px/500;
  buttons 11–13px/600–700; identity 12px/600.
- **Numeric readouts / values / SCPI**: JetBrains Mono (fallback Consolas, monospace).
  Weights 500/600/700. Sizes: values 12px/600; large freq 14px/700; badges 10–12px;
  status bar 11px/500. **All digits use the mono font so columns align.**

### Spacing
- Toolbar 48px · status bar 28px · dock 382px · SCPI terminal 230px · zoom strip 64px.
- Panel header 32px · control field 26px (large fields 30px) · stepper column 22px.
- Body padding 10px 12px; control row gap 7–9px; section gap 12px.
- Graticule outer padding 10px.

### Radius & misc
- Radius: 3px (badges/chips), 4px (fields/segments), 5px (toolbar buttons), 6–7px (cards/tiles).
- Switch pills 30×16 / 34×18. Status dot 6–7px. Checkbox 14px. Slider track 5px / thumb 12px.
- Trace glow: `shadowBlur 7`, `lineWidth 1.7`. Connection dot glow `0 0 6px #37D67A`.

## Assets
- **No external image assets.** Icons in the toolbar are tiny inline SVGs (save = rect+tab,
  screenshot = rounded rect + circle, settings = dashed-ring gear) and should be replaced
  with the codebase's existing icon set (or an icon font). Waveform-tile glyphs are unicode
  placeholders — replace with real waveform icons.
- **Fonts**: Inter and JetBrains Mono (Google Fonts in the prototype; bundle them or use the
  platform equivalents — Segoe UI + Consolas on Windows are acceptable fallbacks).
- The waveform itself is **drawn at runtime on a canvas**, not an image.

## Files
- `Hantek DSO2D15 Control.dc.html` — the full prototype. It is a "Design Component": the
  markup lives inside the `<x-dc>…</x-dc>` element and the behavior lives in the
  `class Component extends DCLogic { … }` script (look for `renderVals()` for the data/handlers
  and `draw()` / `drawTrace()` for the canvas graticule + trace rendering). Open it directly
  in a browser to interact (switch tabs, toggle RUN/STOP and SCPI, change segments).
- `support.js` — the small runtime that renders the Design Component. Needed only to view the
  prototype in a browser; **not** part of what you implement.
- `reference_main_scope.png` — main scope view, SCPI closed.
- `reference_scope_scpi_open.png` — scope view with SCPI terminal open + RUN active (STOP shown).
- `reference_generator.png` — Generator (AWG) tab.
- `reference_sweep.png` — Sweep / multi-capture tab.

> Note on the prototype file: ignore the Design-Component plumbing (`<x-dc>`, `support.js`,
> `renderVals`, `{{ }}` template holes) — it is just how this HTML prototype is wired. What
> matters for implementation is the **visual spec above** and the **canvas drawing approach**
> for the waveform. SCPI command names above are conventional DSO2000-series syntax; verify
> against the DSO2D15 programming manual when wiring real I/O.
