"""SCPI-валидация и вспомогательные функции форматирования — Task 3.

Все функции — чистые, без побочных эффектов.
"""

from __future__ import annotations


def validate_enum(value: object, allowed: tuple[str, ...], name: str) -> str:
    """Регистронезависимое сопоставление value с элементом allowed.

    Возвращает **каноничный** литерал из allowed (регистр сохранён как в кортеже).
    Если совпадения нет — ValueError с именем параметра и списком допустимых.
    """
    needle = str(value).upper()
    for candidate in allowed:
        if candidate.upper() == needle:
            return candidate
    raise ValueError(
        f"Недопустимое значение {name!r}: {value!r}. "
        f"Допустимые: {allowed}"
    )


def validate_choice(value: object, allowed: tuple, name: str) -> object:
    """Точное членство value в allowed (для числовых наборов: probe/points/count).

    Возвращает value без изменений. Нет совпадения → ValueError.
    """
    if value in allowed:
        return value
    raise ValueError(
        f"Недопустимое значение {name!r}: {value!r}. "
        f"Допустимые: {allowed}"
    )


def parse_bool(resp: str) -> bool:
    """Разбирает ответ прибора в bool.

    {"1", "ON"} → True; {"0", "OFF"} → False (регистронезависимо, с trim).
    Любое другое значение → ValueError.
    """
    token = resp.strip().upper()
    if token in ("1", "ON"):
        return True
    if token in ("0", "OFF"):
        return False
    raise ValueError(
        f"Не удаётся разобрать bool-ответ: {resp!r}. "
        "Ожидается одно из: '1', 'ON', '0', 'OFF'."
    )


def bool_arg(value: object) -> str:
    """Преобразует аргумент в строку "ON" / "OFF" для отправки прибору.

    - bool/int: True/1 → "ON", False/0 → "OFF".
    - str: {"ON","1"} → "ON", {"OFF","0"} → "OFF" (регистронезависимо).
    - Прочие строки → ValueError.
    """
    if isinstance(value, bool):
        return "ON" if value else "OFF"
    if isinstance(value, int):
        return "ON" if value else "OFF"
    if isinstance(value, str):
        token = value.strip().upper()
        if token in ("ON", "1"):
            return "ON"
        if token in ("OFF", "0"):
            return "OFF"
        raise ValueError(
            f"Недопустимый bool-аргумент: {value!r}. "
            "Ожидается: True/False, 1/0, 'ON'/'OFF', '1'/'0'."
        )
    raise ValueError(
        f"Недопустимый тип для bool_arg: {type(value).__name__!r} ({value!r})."
    )


def fmt_num(value: object) -> str:
    """Форматирует число в строку NR3 для SCPI-команды: f"{float(value):g}"."""
    return f"{float(value):g}"
