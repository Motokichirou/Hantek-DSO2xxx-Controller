"""Накопитель статистики автоизмерений (чистая логика, без Qt).

Прибор Hantek DSO2D15 в SCPI отдаёт только **текущее** значение измерения
(`:MEASure:CHANnel<n>:ITEM? <type>`) — статистик (avg/max/min/std/count) у него нет.
Поэтому считаем их у себя: накапливаем поток текущих значений по кадрам и отдаём
снапшот cur/avg/max/min/std/count на ключ ``(channel, item)``.

Сброс — по требованию (старт Run/Single, кнопка Reset); см. ``reset()``.
"""
from __future__ import annotations

import math


class _Acc:
    """Инкрементальный аккумулятор по одному ключу (channel, item)."""

    __slots__ = ("count", "_sum", "_sumsq", "min", "max", "cur")

    def __init__(self) -> None:
        self.count = 0
        self._sum = 0.0
        self._sumsq = 0.0
        self.min = math.inf
        self.max = -math.inf
        self.cur = 0.0

    def add(self, value: float) -> None:
        self.cur = value
        self.count += 1
        self._sum += value
        self._sumsq += value * value
        if value < self.min:
            self.min = value
        if value > self.max:
            self.max = value

    @property
    def avg(self) -> float:
        return self._sum / self.count if self.count else 0.0

    @property
    def std(self) -> float:
        """Популяционное СКО (ddof=0). Для count<=1 → 0."""
        if self.count <= 1:
            return 0.0
        mean = self._sum / self.count
        var = self._sumsq / self.count - mean * mean
        return math.sqrt(var) if var > 0.0 else 0.0

    @property
    def rms(self) -> float:
        """Среднеквадратичное самих значений: √(Σv²/n). Для count=0 → 0."""
        if self.count == 0:
            return 0.0
        return math.sqrt(self._sumsq / self.count)


class MeasurementStats:
    """Накопитель статистики по активным измерениям.

    Ключ — пара ``(channel, item)``. ``update`` принимает payload в формате
    ``measurementsReady`` (``list[dict]`` с полями ``channel``/``item``/``value``);
    значения ``None`` и битые записи пропускаются. ``stats_for`` отдаёт снапшот
    одного ключа, ``reset`` — обнуляет всё.
    """

    def __init__(self) -> None:
        self._acc: dict[tuple[int, str], _Acc] = {}

    def update(self, payload) -> None:
        """Добавить кадр измерений. Битые/``None``-записи пропускаются."""
        for entry in payload or []:
            try:
                channel = int(entry["channel"])
                item = str(entry["item"])
                value = entry.get("value")
            except (KeyError, TypeError, ValueError):
                continue
            if value is None:
                continue
            try:
                fval = float(value)
            except (TypeError, ValueError):
                continue
            key = (channel, item)
            acc = self._acc.get(key)
            if acc is None:
                acc = self._acc[key] = _Acc()
            acc.add(fval)

    def stats_for(self, channel: int, item: str) -> dict | None:
        """Снапшот статистики ключа или ``None``, если ключ не накапливался."""
        acc = self._acc.get((int(channel), str(item)))
        if acc is None or acc.count == 0:
            return None
        return {
            "cur": acc.cur,
            "avg": acc.avg,
            "max": acc.max,
            "min": acc.min,
            "std": acc.std,
            "rms": acc.rms,
            "count": acc.count,
        }

    def reset(self) -> None:
        """Сбросить всю накопленную статистику."""
        self._acc.clear()
