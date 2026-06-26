"""Hardware-smoke фундамента Hantek DSO2D15 — ЗАПУСКАЕТ ПОЛЬЗОВАТЕЛЬ НА ПРИБОРЕ.

Первая проверка драйвера (transport + scpi core) на реальном железе
(build-order Layer 1-2, spec §12). НЕ часть pytest — требует подключённого
DSO2D15 и рабочего VISA-бэкенда (Keysight IO Libraries).

Запуск:
    .venv/Scripts/python.exe scripts/hw_smoke_foundation.py
    .venv/Scripts/python.exe scripts/hw_smoke_foundation.py "USB0::0x...::INSTR"

ВАЖНО (hardware-verify, spec §11): прибор зажимает out-of-range к ближайшему
допустимому. Если readback не совпал с заданным — это сигнал для hardware-verify,
НЕ повод «подгонять» драйвер под желаемое. Зафиксируй расхождение и обсуди.
"""

from __future__ import annotations

import sys

from hantek_dso2d15.transport import VisaTransport
from hantek_dso2d15.scpi import Scope


def _pick_resource(argv: list[str]) -> str | None:
    if len(argv) > 1:
        return argv[1]
    resources = VisaTransport.list_resources()
    print(f"Найдено VISA-ресурсов: {len(resources)}")
    for r in resources:
        print(f"  - {r}")
    usb = [r for r in resources if r.upper().startswith("USB")]
    chosen = (usb or list(resources) or [None])[0]
    if chosen:
        print(f"Выбран ресурс: {chosen}")
    return chosen


def _check(label: str, ok: bool, detail: str) -> bool:
    mark = "PASS" if ok else "FAIL"
    print(f"  [{mark}] {label}: {detail}")
    return ok


def main(argv: list[str]) -> int:
    resource = _pick_resource(argv)
    if not resource:
        print("VISA-ресурс не найден. Подключи DSO2D15 и проверь VISA-бэкенд.")
        return 2

    transport = VisaTransport(resource)
    scope = Scope(transport)
    results: list[bool] = []

    try:
        scope.connect()
        print(f"\n*IDN? -> {scope.idn()}\n")

        print("Readback-проба (только чтение):")
        ch1 = scope.channel[1]
        print(f"  channel[1].scale   = {ch1.scale}")
        print(f"  channel[1].coupling= {ch1.coupling}")
        print(f"  timebase.scale     = {scope.timebase.scale}")
        print(f"  acquire.points     = {scope.acquire.points}")
        print(f"  acquire.srate      = {scope.acquire.srate}")
        print(f"  trigger.sweep      = {scope.trigger.sweep}")
        print(f"  trigger.status     = {scope.trigger.status}")

        print("\nSet + readback (сверка):")
        ch1.coupling = "DC"
        results.append(_check("channel[1].coupling=DC", ch1.coupling == "DC", ch1.coupling))

        ch1.scale = 0.5
        rb = ch1.scale
        results.append(_check("channel[1].scale=0.5", abs(rb - 0.5) < 1e-9, f"readback={rb}"))

        scope.timebase.mode = "MAIN"
        results.append(_check("timebase.mode=MAIN", scope.timebase.mode == "MAIN", scope.timebase.mode))

    except Exception as exc:  # noqa: BLE001 — smoke-скрипт: показать любую ошибку I/O
        print(f"\nОШИБКА во время smoke: {type(exc).__name__}: {exc}")
        return 1
    finally:
        try:
            scope.disconnect()
        except Exception:  # noqa: BLE001
            pass

    passed = sum(results)
    print(f"\nИтог set/readback: {passed}/{len(results)} PASS")
    if passed != len(results):
        print("Есть расхождения — зафиксируй для hardware-verify (spec §11), не подгоняй драйвер.")
        return 1
    print("Все readback совпали. Фундамент драйвера базово рабочий на железе.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
