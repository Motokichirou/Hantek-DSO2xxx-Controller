"""Hardware-smoke декодера waveform (Layer 3) — ЗАПУСКАЕТ ПОЛЬЗОВАТЕЛЬ.

Требует подключения:
  - CH1: петля DDS прибора (GEN OUT -> CH1), probe=1.
  - CH2 (опционально): внешний генератор 5Vpp/1kHz через щуп ×100, probe=100, 2В/дел.

Проверяет сквозной путь: WaveformReader + decode_frame на живом приборе.
Калибровка: signed int8, 25 counts/div, volts=sample*(Vdiv/25)-offset (см. FIXTURES.md).
"""
from __future__ import annotations
import sys, time
import numpy as np

from hantek_dso2d15.transport.visa_transport import VisaTransport
from hantek_dso2d15.scpi.scope import Scope
from hantek_dso2d15.waveform.reader import WaveformReader
from hantek_dso2d15.waveform.decode import decode_frame


def _check(label, ok, detail):
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}: {detail}")
    return ok


def acquire_decoded(scope, reader):
    """Снять кадр и декодировать с масштабами/смещениями из драйвера."""
    frame = reader.read_frame()
    chans = frame.header.enabled_channels
    scales = {n: scope.channel[n].scale for n in chans}
    offsets = {n: scope.channel[n].offset for n in chans}
    return decode_frame(frame, scales, offsets), frame


def main(argv):
    res = VisaTransport.list_resources()
    usb = [r for r in res if r.upper().startswith("USB")]
    if not usb:
        print("VISA USB-ресурс не найден.")
        return 2
    t = VisaTransport(usb[0], timeout_ms=8000)
    scope = Scope(t)
    reader = WaveformReader(t)
    results = []
    try:
        scope.connect()
        print("IDN:", scope.idn())
        ch1 = scope.channel[1]
        ch1.display = True; ch1.coupling = "DC"; ch1.probe = 1; ch1.scale = 1.0; ch1.offset = 0.0
        scope.acquire.points = 4000
        scope.timebase.scale = 2e-4
        scope.trigger.sweep = "AUTO"

        # --- CH1: DDS DC +1.0V ---
        t.write(":DDS:SWITch ON"); t.write(":DDS:TYPE DC"); t.write(":DDS:AMP 0"); t.write(":DDS:OFFSet 1.0")
        time.sleep(0.8)
        dec, frame = acquire_decoded(scope, reader)
        m = float(np.mean(dec.channels[1]))
        results.append(_check("CH1 DDS DC +1.0V", abs(m - 1.0) < 0.15, f"mean={m:.3f}V (ожид ~+1.0)"))
        print(f"        enabled={frame.header.enabled_channels} srate={dec.srate:.0f} n={len(dec.time)}")

        # --- CH1: DDS square 2Vpp 1kHz ---
        t.write(":DDS:TYPE SQUAre"); t.write(":DDS:FREQ 1000"); t.write(":DDS:AMP 2.0"); t.write(":DDS:OFFSet 0"); t.write(":DDS:DUTY 50")
        scope.trigger.mode = "EDGE"; scope.trigger.edge.source = "CHANnel1"; scope.trigger.edge.level = 0.0
        time.sleep(0.8)
        dec, _ = acquire_decoded(scope, reader)
        v = dec.channels[1]
        hi = float(np.percentile(v, 90)); lo = float(np.percentile(v, 10)); vpp = hi - lo
        results.append(_check("CH1 DDS square 2Vpp", abs(vpp - 2.0) < 0.3, f"Vpp={vpp:.3f}V (hi={hi:.2f} lo={lo:.2f})"))

        # --- CH2: внешний 5Vpp/1kHz через щуп x100 (если подключён) ---
        ch2 = scope.channel[2]
        ch2.display = True; ch2.coupling = "DC"; ch2.probe = 100; ch2.scale = 2.0; ch2.offset = 0.0
        scope.trigger.edge.source = "CHANnel2"; scope.trigger.edge.level = 0.0
        time.sleep(0.9)
        dec, frame = acquire_decoded(scope, reader)
        results.append(_check("оба канала в кадре", frame.header.enabled_channels == [1, 2],
                              f"enabled={frame.header.enabled_channels} (ожид [1,2])"))
        if 2 in dec.channels:
            v2 = dec.channels[2]
            vpp2 = float(np.percentile(v2, 95) - np.percentile(v2, 5))
            results.append(_check("CH2 внешний 5Vpp (x100)", abs(vpp2 - 5.0) < 1.5,
                                  f"Vpp={vpp2:.2f}V (ожид ~5.0; допуск шире — внешний ген+щуп)"))

        t.write(":DDS:OFFSet 0"); t.write(":DDS:SWITch OFF")
    except Exception as exc:  # noqa: BLE001
        print(f"\nОШИБКА smoke: {type(exc).__name__}: {exc}")
        import traceback; traceback.print_exc()
        return 1
    finally:
        try: scope.disconnect()
        except Exception: pass

    passed = sum(results)
    print(f"\nИтог: {passed}/{len(results)} PASS")
    if passed != len(results):
        print("Есть расхождения — зафиксируй для hardware-verify, не подгоняй декодер.")
        return 1
    print("Декодер waveform рабочий на железе (оба канала, петля DDS + щуп x100).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
