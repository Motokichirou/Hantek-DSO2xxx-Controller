# Hantek DSO2xxx Controller

A full-featured desktop client for the **Hantek DSO2D15** oscilloscope, written
from scratch in Python. It talks to the instrument over **USB (USBTMC) via
standard VISA** and aims to expose the full functionality of the programming
manual without the limitations of the vendor software.

> Русское описание — [ниже](#описание-rus).

![status](https://img.shields.io/badge/tests-1197%20passing-37D67A)
![python](https://img.shields.io/badge/python-3.11%2B-blue)
![license](https://img.shields.io/badge/license-MIT-green)

---

## Features

- **Live dual-channel display** — real-time CH1/CH2 waveforms on a 14×8 division
  graticule (pyqtgraph), with a faithful **timebase zoom** (shows the `14 × s/div`
  window like the instrument) and per-division readouts.
- **Scope panels** — Vertical, Horizontal, Trigger, **Measure** (~37 automatic
  measurements), Acquire, **Math/FFT** (ADD/SUB/MUL/DIV + FFT), **Cursors**
  (draggable, ΔV/Δt/freq), **Display**.
- **Generator (DDS/AWG)** — waveform type, frequency, amplitude, offset, duty,
  **AM/FM modulation**, and **burst**.
- **Sweep / Multi-capture** — sweep a parameter (e.g. generator frequency) from
  start to stop, dwell at each step, and capture every frame to **CSV / NPY / HDF5**.
- **Save & export** — current frame to CSV/NPY/HDF5, **screenshot** (PNG) of the
  plot, and **presets** (save/restore the full instrument setup as JSON).
- **SCPI logger** — log all SCPI traffic to a file (toggle button, 10 MB rotation,
  waveform packets collapsed) for debugging and protocol analysis.
- **Threaded, non-blocking I/O** — all VISA I/O runs off the UI thread;
  host-side acquisition control (Run / Stop / Single).

## Architecture

Strict layering — all logic is unit-tested **without hardware**, VISA I/O never
blocks the UI thread:

```
gui/        PySide6 — window, plot, panels, generator, sweep, SCPI terminal
engine/     acquisition controller in a background QThread; run/stop/single; sweep
scpi/       typed driver, 1:1 with the manual + waveform/ (chunked decoder)
transport/  PyVISA wrapper (open/write/query/read_raw, logging hook) + FakeTransport
io/         CSV · NPY/NPZ · HDF5 export · presets (JSON)
```

## Requirements

- **Windows 11** (primary target).
- **Python 3.11+**.
- **NI-VISA** installed (the VISA backend used to reach the USBTMC device).
- The oscilloscope connected over USB (appears as a USB Test & Measurement device).
- Python packages: PySide6, pyqtgraph, PyVISA, NumPy, h5py (installed below).

## Install & run

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .
python -m hantek_dso2d15.app
```

Then pick the VISA resource in the toolbar and press **Connect**.

## Tests

```bash
pytest -q
```

The full suite runs headless (no hardware needed) thanks to `FakeTransport` and an
offscreen Qt fixture.

## Status & roadmap

Working end-to-end on hardware: live display, all Scope panels, generator, sweep,
save/export, presets, SCPI logger.

Planned: SCPI terminal (interactive console), protocol-decode triggers, arbitrary
waveform upload for the generator, a pixel-faithful design pass, and a packaged
installer (PyInstaller + Inno Setup).

## License

[MIT](LICENSE) © 2026 Motokichirou.

> This is an independent, unofficial project and is not affiliated with or
> endorsed by Hantek.

---

## Описание (RUS)

Полнофункциональный десктоп-клиент для осциллографа **Hantek DSO2D15**, написанный
с нуля на Python. Связь с прибором — по **USB (USBTMC) через стандартный VISA**;
цель — дать **весь** функционал программного мануала без ограничений родного софта.

**Возможности:** живой двухканальный дисплей с честным зумом развёртки (окно
`14 × s/дел`); панели Scope (Вертикаль, Горизонталь, Триггер, Измерения ~37,
Acquire, Math/FFT, Курсоры, Дисплей); генератор DDS (формы, частота/амплитуда/
смещение/duty, модуляция AM/FM, burst); Sweep / multi-capture с сохранением в
CSV/NPY/HDF5; Save/экспорт + скриншот (PNG) + пресеты (JSON); файловый SCPI-логгер;
потоковый ввод-вывод (VISA вне UI-потока), host-side управление сбором.

**Требования:** Windows 11, Python 3.11+, установленный **NI-VISA**, прибор по USB.

**Запуск:** создать venv → `pip install -e .` → `python -m hantek_dso2d15.app` →
выбрать VISA-ресурс → **Connect**. Тесты: `pytest -q` (без железа).

Проект независимый и неофициальный, с Hantek не связан. Лицензия — [MIT](LICENSE).
