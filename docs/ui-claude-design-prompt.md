# Claude Design — промпт для UI (клиент Hantek DSO2D15)

Промпт для генерации макета десктоп-UI в Claude design. Реализация (PySide6) следует утверждённому макету. UI двуязычный EN/RU (по умолчанию EN) — макет на английском; русский обрабатывается на этапе реализации через слой перевода.

> **Примечание:** тело промпта ниже намеренно оставлено на английском — это вход для Claude design, и макет по умолчанию англоязычный (согласно решению о двуязычии: EN-макет, RU на этапе реализации). Если нужен русскоязычный макет — скажи, переведу промпт на русский.

---

```
ROLE
You are designing the UI for a Windows desktop application that controls a Hantek
DSO2D15 digital storage oscilloscope. Produce a polished, production-quality desktop
interface mockup (single main window) in the visual language of professional bench
test-and-measurement instrument software. This is a serious engineering tool, not a
consumer app — prioritize information density, legibility, and fast access to controls
over whitespace and decoration. Target a 1920×1080 desktop window, resizable.

PRODUCT CONTEXT
- 2-channel oscilloscope (CH1, CH2) + built-in arbitrary/function generator (AWG) +
  ~35 automatic measurements + math/FFT + protocol decode triggers.
- The app talks to the instrument over USB (VISA/USBTMC). It is a full-featured
  replacement for the vendor software, exposing every instrument capability.
- Real-time dual-channel waveform display is the centerpiece.

VISUAL DESIGN LANGUAGE
- Dark theme. Near-black instrument background (#0E0F12 ish), panels slightly lighter
  (#16181D), subtle 1px borders (#2A2D34). This is the standard for scope software and
  reduces eye strain in lab settings.
- Channel color coding (industry convention): CH1 = yellow (#F2C300), CH2 = cyan
  (#23C8E6), MATH = magenta/purple (#C77DFF), reference/cursor = white/light gray.
  Every control belonging to a channel is tinted/accented with that channel's color.
- Typography: clean sans-serif for labels (Inter / Segoe UI). All numeric readouts and
  measured values in a monospaced font (JetBrains Mono / Consolas) so digits align.
- Accent color for primary actions (RUN) green (#37D67A), STOP red (#E5484D),
  SINGLE amber. Use color sparingly and meaningfully (status, channel identity).
- Compact, dense control rows. Use small spin-boxes with up/down steppers, segmented
  toggles, and dropdowns rather than large airy cards.

OVERALL LAYOUT (regions, like a real benchtop scope)
1. TOP TOOLBAR (full width, ~48px):
   - Left: device connection control — a dropdown of detected VISA resources
     ("USB0::0x...::INSTR"), a connect/disconnect button, and a small status dot
     (green=connected, gray=offline). Show identity string "Hantek DSO2D15" when linked.
   - Center: acquisition transport — large RUN/STOP toggle button, SINGLE button,
     FORCE (trigger) button, AUTO (auto-setup) button.
   - Right: action buttons with icons — Save Waveform, Screenshot (camera icon),
     Presets (save/load), SCPI Terminal toggle, Settings.

2. CENTER — WAVEFORM DISPLAY (the largest region, dominant):
   - An oscilloscope graticule: 14 horizontal × 8 vertical divisions (the device reports
     a 12+ grid; render a standard 14×8 dotted/solid grid selectable), with a brighter
     center cross. Grid lines dim gray; tick marks on center axes.
   - Two live waveforms drawn over it: CH1 yellow trace, CH2 cyan trace (show realistic
     sine on CH1 and a square wave on CH2 for the mockup).
   - Left edge: per-channel ground-reference markers (small colored arrows "1", "2")
     positioned at each channel's vertical offset.
   - Right edge: trigger level indicator (a colored arrow "T" at the trigger voltage,
     colored by trigger source channel).
   - Top edge: a small T-position marker for horizontal trigger position.
   - Top-left overlay: live readouts — for each channel its V/div ("CH1 500mV") and
     coupling; the timebase ("Time 200µs/div"); the sample rate ("1.0 GSa/s"); memory
     depth ("4K"); and trigger status ("Trig'd" / "Auto" / "Ready" / "Stop") color-coded.
   - Support cursor overlays: dashed vertical (X1/X2) and horizontal (Y1/Y2) cursor lines
     with small draggable handles, and a cursor readout box (ΔX, 1/ΔX, ΔY) in a corner.
   - A thin zoom/window strip can appear below the main graticule when "Zoom" is on
     (shows the full record with a highlighted zoomed section).

3. RIGHT-SIDE CONTROL DOCK (vertical, ~380px wide, tabbed or stacked accordion):
   Organize controls into clearly separated, collapsible panels. Show these panels:

   a) VERTICAL (per channel — render CH1 and CH2 as two compact sub-blocks, each
      accented in its channel color):
      - Channel ON/OFF toggle (colored).
      - Vertical scale (V/div): stepper + value, range like 1mV/div … 10V/div.
      - Vertical offset/position: stepper in V/mV.
      - Coupling: segmented toggle [DC | AC | GND].
      - Bandwidth limit 20MHz: on/off toggle.
      - Probe attenuation: dropdown [1X | 10X | 100X | 1000X].
      - Invert: on/off toggle. Fine (vernier): on/off toggle.

   b) HORIZONTAL / TIMEBASE:
      - Time scale (s/div): stepper, range ns/div … s/div.
      - Horizontal position (trigger offset): stepper in seconds.
      - Timebase mode: segmented [Main | XY | Roll].
      - Zoom window: on/off toggle + window scale + window position (shown when on).

   c) TRIGGER:
      - Trigger type: dropdown [Edge | Pulse | Slope | Video | Timeout | Window |
        Interval | Runt | Pattern | UART | CAN | LIN | I2C | SPI].
      - Source: dropdown [CH1 | CH2].
      - Sweep mode: segmented [Auto | Normal | Single].
      - Level: stepper in V (with a "set to 50%" quick button).
      - For Edge: slope segmented [Rising | Falling | Either].
      - Holdoff: time value.
      - When a bus type (UART/CAN/…/SPI) is selected, the panel reveals that protocol's
        fields (e.g. UART: baud, data bits, parity, stop, polarity, condition). Show the
        Edge layout by default and indicate the panel morphs per type.

   d) ACQUIRE:
      - Acquisition mode: dropdown [Normal | Average | Peak Detect | High-Res].
      - Average count (shown when Average): dropdown [4|8|16|32|64|128].
      - Memory depth: dropdown [4K | 40K | 400K | 4M | 8M].
      - Live readout of current sample rate.

   e) MEASURE:
      - Source selector [CH1 | CH2 | MATH].
      - "Add measurement" dropdown listing types grouped as Voltage (Vpp, Vmax, Vmin,
        Vtop, Vbase, Vamp, Vavg, Vrms, Overshoot, Preshoot…) and Time (Period, Freq,
        Rise, Fall, +Width, -Width, +Duty, -Duty, Delay, Phase…).
      - A list/table of active measurements: Label | Source | Value (monospaced),
        e.g. "Vpp  CH1  3.60 V", "Freq CH1  1.000 kHz". Show 4–6 example rows.

   f) MATH:
      - Math display on/off.
      - Operation: dropdown [CH1+CH2 | CH1-CH2 | CH1×CH2 | CH1÷CH2 | FFT].
      - Scale / offset for the math trace.
      - When FFT: window dropdown [Rectangle|Hanning|Hamming|Blackman], units
        [dBVrms|Vrms], horizontal scale (Hz/div) and center frequency.

   g) CURSORS:
      - Mode: segmented [Off | Manual | Track].
      - Type (manual): segmented [X | Y | XY].
      - Source [CH1|CH2|MATH].
      - Readout of A/B positions and deltas.

   h) DISPLAY:
      - Waveform style: segmented [Vectors | Dots].
      - Grid: segmented [Full | Dotted | Off] + grid brightness slider.
      - Waveform brightness slider.

4. GENERATOR (AWG) — give it its own prominent panel or a dedicated tab (it's a key
   feature, the "D" in DSO2D15):
   - Output ON/OFF (big toggle).
   - Waveform: selectable tiles/dropdown [Sine | Square | Ramp | Pulse(Exp) | Noise |
     DC | Arb1..4].
   - Frequency (Hz, large readout + stepper), Amplitude (V), Offset (V), Duty (%).
   - Modulation section: on/off, type [AM | FM], modulating wave [Sine|Square|Ramp],
     mod frequency, depth/deviation.
   - Burst section: on/off, type [N-Cycle | Infinite], cycle count, trigger button.

5. SWEEP / MULTI-CAPTURE — a panel or modal for automated measurement series:
   - Define a parameter to sweep (e.g. generator frequency or timebase), start/stop/step,
     dwell time, number of captures, output folder, file format [CSV | NPY | HDF5].
   - Progress bar + "captures done / total" + start/stop.

6. SCPI TERMINAL — a slide-in/dock panel (toggled from toolbar):
   - A scrollback log (monospaced) showing sent commands (e.g. ":CHAN1:SCAL 1") and
     responses, color-coded (sent vs received vs error).
   - An input line with send button and command history.
   - This is for direct command entry and debugging.

7. BOTTOM STATUS BAR (full width, ~28px):
   - Connection state, instrument model, current sample rate, memory depth, trigger
     status, and a transient message area ("Waveform saved to capture_001.csv").

STATES TO SHOW IN THE MOCKUP
- Connected and running, both channels on, a clean sine (CH1) + square (CH2) on the
  graticule, trigger level arrow visible, a few live measurements populated, and the
  right dock showing the Vertical + Horizontal + Trigger panels expanded.
- Include a second frame/variant (or annotation) showing the SCPI terminal open and the
  Generator panel active, so the layout's flexibility is visible.

DELIVERABLE
- A single cohesive desktop layout (not mobile). Pixel-faithful, dark instrument theme,
  channel color coding throughout, monospaced numeric readouts, dense professional
  control panels. Provide the main full-window view plus close-up detail of the
  right-side control dock and the generator panel.
```
