"""Движок параметрического свипа (multi-capture) — hantek_dso2d15.engine.sweep.

Чистый оркестратор: не импортирует Qt, io, scpi, transport. Все
зависимости (set_param, capture, save, sleep, on_progress, should_cancel)
инъектируются снаружи. Интеграция с QThread-воркером — задача оркестратора.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SweepConfig:
    """Конфигурация одного параметрического свипа.

    Attributes
    ----------
    parameter:
        Путь параметра прибора, напр. ``"dds.freq"`` или ``"channel.1.scale"``.
    start:
        Начальное значение свипа.
    stop:
        Конечное значение (включительно при кратности шага с допуском).
    step:
        Шаг свипа. Должен быть > 0.
    dwell_s:
        Выдержка в секундах после установки параметра (перед захватом кадра).
    fmt:
        Формат сохранения кадра: ``"CSV"``, ``"NPY"`` или ``"HDF5"``.
    folder:
        Путь к папке для сохранения кадров.
    """

    parameter: str
    start: float
    stop: float
    step: float
    dwell_s: float
    fmt: str
    folder: str


def sweep_values(start: float, stop: float, step: float) -> list[float]:
    """Вернуть линейный список значений от start до stop включительно.

    Количество шагов: ``n = int((stop - start) / step + 1e-9) + 1``.
    Значения вычисляются как ``start + i * step`` (умножение вместо суммы —
    исключает накопление ошибки float).

    Допуск 1e-9 обеспечивает корректное включение stop, когда float-деление
    даёт значение чуть ниже целого (например, 9.9999999999 вместо 10.0).

    Parameters
    ----------
    start:
        Начальное значение.
    stop:
        Конечное значение (включается при кратности шага с допуском 1e-9).
    step:
        Шаг. Должен быть строго > 0.

    Returns
    -------
    list[float]
        Линейная последовательность значений.

    Raises
    ------
    ValueError
        Если ``step <= 0`` или ``stop < start``.

    Examples
    --------
    >>> sweep_values(0.0, 10.0, 1.0)
    [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]

    >>> sweep_values(100.0, 100000.0, 1000.0)  # 100 значений: 100..99100
    [100.0, 1100.0, ..., 99100.0]
    """
    if step <= 0:
        raise ValueError(f"step должен быть > 0, получено: {step!r}")
    if stop < start:
        raise ValueError(
            f"stop должен быть >= start, получено: start={start!r}, stop={stop!r}"
        )
    # Число шагов: допуск 1e-9 корректирует накопление ошибки float-деления
    n = int((stop - start) / step + 1e-9) + 1
    return [start + i * step for i in range(n)]


class SweepRunner:
    """Оркестратор параметрического свипа (multi-capture).

    Выполняет заданное число шагов по ``sweep_values(config.start, config.stop,
    config.step)``. На каждом шаге: проверяет отмену, устанавливает параметр,
    выдерживает паузу, снимает кадр, сохраняет его, обновляет прогресс.

    Не импортирует Qt, io, scpi или transport. Полностью тестируется через
    фейки-замыкания без железа.
    """

    def run(
        self,
        config: SweepConfig,
        *,
        set_param,
        capture,
        save,
        sleep,
        on_progress,
        should_cancel,
    ) -> dict:
        """Выполнить свип согласно конфигурации.

        Порядок действий для каждого шага i (строго):
        0. ``should_cancel()`` → True: немедленный возврат с ``cancelled=True``.
        1. ``set_param(value)`` — установить параметр прибора.
        2. ``sleep(dwell_s)`` — выдержка.
        3. ``frame = capture()`` — захват кадра.
        4. ``save(frame, i)`` — сохранение (индекс 0-based).
        5. ``on_progress(i + 1, total)`` — обновление прогресса.

        Parameters
        ----------
        config:
            Конфигурация свипа (``SweepConfig``).
        set_param:
            ``(value: float) -> None`` — установить параметр прибора.
        capture:
            ``() -> Any`` — снять один кадр.
        save:
            ``(frame: Any, index: int) -> None`` — сохранить кадр.
        sleep:
            ``(seconds: float) -> None`` — выдержка.
        on_progress:
            ``(done: int, total: int) -> None`` — callback прогресса.
        should_cancel:
            ``() -> bool`` — вернуть ``True``, чтобы прервать свип.

        Returns
        -------
        dict
            ``{"done": int, "total": int, "cancelled": bool}``.
            ``done`` — число успешно завершённых шагов (0..total).
        """
        values = sweep_values(config.start, config.stop, config.step)
        total = len(values)

        for i, v in enumerate(values):
            # Отмена проверяется ПЕРЕД установкой параметра каждого шага
            if should_cancel():
                return {"done": i, "total": total, "cancelled": True}
            set_param(v)
            sleep(config.dwell_s)
            frame = capture()
            save(frame, i)
            on_progress(i + 1, total)

        return {"done": total, "total": total, "cancelled": False}
