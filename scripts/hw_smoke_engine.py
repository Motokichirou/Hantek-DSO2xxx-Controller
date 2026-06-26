"""Hardware-smoke engine-слоя — ЗАПУСКАЕТ ПОЛЬЗОВАТЕЛЬ (петля DDS→CH1).

EngineWorker в реальном QThread против живого DSO2D15: непрерывный сбор,
VISA-I/O в фоновом потоке, кадры приходят сигналом frameReady в главный поток.
Замеряет fps и проверяет CH1 Vpp ≈ 2В (DDS меандр 2Vpp/1кГц).
"""
from __future__ import annotations

import sys
import time

import numpy as np
from PySide6.QtCore import QCoreApplication, QThread, QTimer, Qt, QMetaObject

from hantek_dso2d15.transport.visa_transport import VisaTransport
from hantek_dso2d15.scpi.scope import Scope
from hantek_dso2d15.waveform.reader import WaveformReader
from hantek_dso2d15.engine.controller import AcquisitionController
from hantek_dso2d15.engine.worker import EngineWorker

N_FRAMES = 30
TIMEOUT_MS = 12000


def main(argv):
    usb = [r for r in VisaTransport.list_resources() if r.upper().startswith("USB")]
    if not usb:
        print("VISA USB-ресурс не найден."); return 2

    t = VisaTransport(usb[0], timeout_ms=8000)
    scope = Scope(t)
    scope.connect()
    print("IDN:", scope.idn())

    # Конфигурация в главном потоке ДО старта worker (потом транспорт трогает только поток worker)
    ch1 = scope.channel[1]
    ch1.display = True; ch1.coupling = "DC"; ch1.probe = 1; ch1.scale = 1.0; ch1.offset = 0.0
    scope.channel[2].display = False
    scope.acquire.points = 4000
    scope.timebase.scale = 2e-4
    scope.trigger.sweep = "AUTO"
    t.write(":DDS:SWITch ON"); t.write(":DDS:TYPE SQUAre"); t.write(":DDS:FREQ 1000")
    t.write(":DDS:AMP 2.0"); t.write(":DDS:OFFSet 0"); t.write(":DDS:DUTY 50")
    time.sleep(0.6)

    app = QCoreApplication.instance() or QCoreApplication([])
    controller = AcquisitionController(scope, WaveformReader(t))
    worker = EngineWorker(controller, interval_ms=5)
    thread = QThread()
    worker.moveToThread(thread)

    frames = []
    errors = []
    t0 = {"t": None}

    def on_frame(frame):
        if t0["t"] is None:
            t0["t"] = time.perf_counter()
        frames.append(frame)
        if len(frames) >= N_FRAMES:
            app.quit()

    def on_error(msg):
        errors.append(msg)
        print("  errorOccurred:", msg)
        if len(errors) > 5:
            app.quit()

    worker.frameReady.connect(on_frame)
    worker.errorOccurred.connect(on_error)
    thread.started.connect(worker.start)
    QTimer.singleShot(TIMEOUT_MS, app.quit)

    thread.start()
    app.exec()
    t1 = time.perf_counter()

    # Останов worker в его потоке, затем завершение потока
    QMetaObject.invokeMethod(worker, "stop", Qt.ConnectionType.QueuedConnection)
    thread.quit(); thread.wait(3000)

    results = []
    n = len(frames)
    elapsed = (t1 - t0["t"]) if t0["t"] else 0.0
    fps = (n - 1) / elapsed if (n > 1 and elapsed > 0) else 0.0
    # Функциональный порог: непрерывный сбор подтверждён, если пришло >=12 кадров.
    # fps — информативно (низкий fps = per-frame :SCALe?/:OFFSet? запросы, тюнится в GUI-слое).
    results.append(_check("непрерывный сбор (>=12 кадров)", n >= 12, f"{n} кадров за окно, ~{fps:.1f} fps (инфо)"))
    results.append(_check("без ошибок потока", not errors, f"errors={len(errors)}"))

    if frames:
        vpps = []
        for fr in frames[-10:]:
            v = fr.channels.get(1)
            if v is not None and len(v):
                vpps.append(float(np.percentile(v, 90) - np.percentile(v, 10)))
        med = float(np.median(vpps)) if vpps else 0.0
        results.append(_check("CH1 Vpp ~2В (меандр)", abs(med - 2.0) < 0.3, f"медиана Vpp={med:.3f}В по {len(vpps)} кадрам"))
        sr = frames[-1].srate
        results.append(_check("srate в кадре", sr > 0, f"{sr:.0f} Sa/s"))

    t.write(":DDS:SWITch OFF")
    scope.disconnect()

    passed = sum(results)
    print(f"\nИтог: {passed}/{len(results)} PASS")
    if passed != len(results):
        return 1
    print("Engine рабочий на железе: непрерывный сбор в фоновом потоке, кадры в UI-поток.")
    return 0


def _check(label, ok, detail):
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}: {detail}")
    return ok


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
