"""Ядро пресетов настроек прибора Hantek DSO2D15.

Функции:
  capture_preset(scope, paths) → dict   — снять текущие настройки в плоский dict
  apply_preset(scope, preset) → list    — применить dict к прибору, вернуть список ошибок
  save_preset(preset, path) → None      — сохранить в JSON (utf-8, indent=2)
  load_preset(path) → dict              — загрузить из JSON

Класс:
  SnapshotScope(preset_dict)            — прокси «как scope» поверх dict пресета;
                                          позволяет ресинкать панели без I/O.

Навигация по объектному графу (аналогично worker.apply_setting):
  "channel.1.scale" → scope.channel[1].scale
  числовой токен  → obj[int(token)]
  текстовый токен → getattr(obj, token)
"""

from __future__ import annotations

import json
from typing import Any


# ---------------------------------------------------------------------------
# Список точечных путей настроек (frozen — не менять без явного разрешения)
# ---------------------------------------------------------------------------

PRESET_PATHS: tuple[str, ...] = (
    # Аналоговые каналы 1 и 2
    "channel.1.display",
    "channel.1.scale",
    "channel.1.offset",
    "channel.1.coupling",
    "channel.1.probe",
    "channel.1.bwlimit",
    "channel.1.invert",
    "channel.2.display",
    "channel.2.scale",
    "channel.2.offset",
    "channel.2.coupling",
    "channel.2.probe",
    "channel.2.bwlimit",
    "channel.2.invert",
    # Временная развёртка
    "timebase.scale",
    "timebase.position",
    "timebase.mode",
    "timebase.window.enable",
    "timebase.window.scale",
    "timebase.window.position",
    # Триггер
    "trigger.mode",
    "trigger.sweep",
    "trigger.holdoff",
    "trigger.edge.source",
    "trigger.edge.slope",
    "trigger.edge.level",
    # Сбор данных
    "acquire.type",
    "acquire.count",
    "acquire.points",
    # Генератор DDS
    "dds.output",
    "dds.type",
    "dds.freq",
    "dds.amplitude",
    "dds.offset",
    "dds.duty",
    "dds.mod_enable",
    "dds.mod_type",
    "dds.mod_wave",
    "dds.mod_freq",
    "dds.mod_depth",
    "dds.burst_enable",
    "dds.burst_type",
    "dds.burst_count",
)


# ---------------------------------------------------------------------------
# Навигация по объектному графу
# ---------------------------------------------------------------------------

def _navigate(obj: Any, parts: list[str]) -> tuple[Any, str]:
    """Пройти parts по объектному графу obj.

    Числовой токен (token.isdigit()) → obj[int(token)],
    остальные → getattr(obj, token).

    Args:
        obj:   корневой объект (scope или под-объект).
        parts: токены точечного пути, например ["channel", "1", "scale"].

    Returns:
        Пара (owner_obj, last_attr_name): объект-владелец последнего атрибута
        и имя этого атрибута — для getattr/setattr.
    """
    for token in parts[:-1]:
        if token.isdigit():
            obj = obj[int(token)]
        else:
            obj = getattr(obj, token)
    return obj, parts[-1]


# ---------------------------------------------------------------------------
# Приведение к JSON-сериализуемому типу
# ---------------------------------------------------------------------------

def _to_json_value(value: Any) -> bool | int | float | str:
    """Привести значение к JSON-сериализуемому типу.

    Порядок проверки: bool перед int (bool — подкласс int).
    Всё прочее — приводим к str (enum, пользовательские типы).
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return value
    return str(value)


# ---------------------------------------------------------------------------
# capture_preset
# ---------------------------------------------------------------------------

def capture_preset(
    scope: Any,
    paths: tuple[str, ...] = PRESET_PATHS,
) -> dict:
    """Снять текущие настройки прибора в плоский dict.

    Для каждого пути из paths читает значение через getattr.
    При любом исключении на пути — пропускает путь (не падает).

    Значения приводятся к JSON-сериализуемым типам: bool/int/float/str.

    Args:
        scope:  объект-фасад прибора (Scope или фейк).
        paths:  перечень точечных путей; по умолчанию PRESET_PATHS.

    Returns:
        Плоский dict {path: value}.
    """
    result: dict = {}
    for path in paths:
        try:
            parts = path.split(".")
            owner, attr = _navigate(scope, parts)
            raw = getattr(owner, attr)
            result[path] = _to_json_value(raw)
        except Exception:  # noqa: BLE001
            # Пути, недоступные на данном приборе/фейке — молча пропускаем
            pass
    return result


# ---------------------------------------------------------------------------
# apply_preset
# ---------------------------------------------------------------------------

#: Пути, применяемые ПОСЛЕДНИМИ (после всей конфигурации). На DSO2D15 команда
#: :DDS:BURSt:SWITch сбрасывает выход генератора в OFF (hardware-verified
#: 2026-06-27), поэтому :DDS:SWITch (dds.output) надо ставить после burst/конфига,
#: иначе пресет с включённым выходом «гасит» генератор. Устойчиво к порядку ключей
#: (чинит и старые пресеты).
DEFERRED_PATHS: tuple[str, ...] = ("dds.output",)


def apply_preset(scope: Any, preset: dict) -> list[str]:
    """Применить пресет к прибору.

    Для каждого (path, value) из preset: setattr по навигации.
    При исключении — собирает путь в список ошибок (не прерывает цикл).
    Пути из :data:`DEFERRED_PATHS` применяются последними (см. там почему).

    Args:
        scope:  объект-фасад прибора (Scope или фейк).
        preset: плоский dict {path: value}.

    Returns:
        Список путей-ошибок. Пустой список = всё применилось.
    """
    errors: list[str] = []

    def _apply_one(path: str, value: Any) -> None:
        try:
            parts = path.split(".")
            owner, attr = _navigate(scope, parts)
            setattr(owner, attr, value)
        except Exception:  # noqa: BLE001
            errors.append(path)

    # сначала всё, кроме отложенных
    for path, value in preset.items():
        if path not in DEFERRED_PATHS:
            _apply_one(path, value)
    # затем отложенные (в порядке DEFERRED_PATHS)
    for path in DEFERRED_PATHS:
        if path in preset:
            _apply_one(path, preset[path])
    return errors


# ---------------------------------------------------------------------------
# save_preset / load_preset
# ---------------------------------------------------------------------------

def save_preset(preset: dict, path: str) -> None:
    """Сохранить пресет в JSON-файл.

    Кодировка: utf-8, ensure_ascii=False, indent=2 (читаемый формат).

    Args:
        preset: плоский dict {path: value}.
        path:   путь к файлу (создаётся или перезаписывается).
    """
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(preset, fh, ensure_ascii=False, indent=2)


def load_preset(path: str) -> dict:
    """Загрузить пресет из JSON-файла.

    Args:
        path: путь к JSON-файлу.

    Returns:
        Плоский dict {path: value}.
    """
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# SnapshotScope — прокси поверх плоского dict пресета
# ---------------------------------------------------------------------------

class SnapshotScope:
    """Прокси «как scope» поверх плоского dict пресета.

    Позволяет обращаться к настройкам через dot-нотацию и индексирование,
    как к реальному объекту Scope, без реального I/O:

        sc = SnapshotScope({"channel.1.scale": 0.5, "timebase.scale": 1e-3})
        sc.channel[1].scale  # → 0.5
        sc.timebase.scale    # → 1e-3

    Назначение: ресинк панелей без обращения к прибору.
    ``panel.load_from_scope(SnapshotScope(preset))``

    Args:
        preset_dict: плоский dict {path: value}.
        _prefix:     внутренний — накопленный путь (используется рекурсивно).

    Raises:
        KeyError: если обращение к «листу», которого нет в dict, и нет ни одного
                  дочернего ключа — сигнал панели, что атрибут не сохранён.
    """

    def __init__(self, preset_dict: dict, _prefix: str = "") -> None:
        # object.__setattr__ — чтобы не рекурсировать через переопределённый __getattr__
        object.__setattr__(self, "_dict", preset_dict)
        object.__setattr__(self, "_prefix", _prefix)

    def __getattr__(self, name: str) -> Any:
        """Расширить накопленный путь атрибутом name."""
        _dict: dict = self.__dict__["_dict"]
        _prefix: str = self.__dict__["_prefix"]

        new_prefix = f"{_prefix}.{name}" if _prefix else name

        # Накопленный путь является листом в dict → вернуть значение
        if new_prefix in _dict:
            return _dict[new_prefix]

        # Есть дочерние ключи → вернуть под-прокси (промежуточный узел)
        dot_prefix = new_prefix + "."
        if any(k.startswith(dot_prefix) for k in _dict):
            return SnapshotScope(_dict, new_prefix)

        # Ни листа, ни потомков — обращение к отсутствующему пути
        raise KeyError(f"Путь '{new_prefix}' не найден в снимке пресета")

    def __getitem__(self, i: int | str) -> Any:
        """Добавить числовой/строковый индекс к накопленному пути."""
        _dict: dict = self.__dict__["_dict"]
        _prefix: str = self.__dict__["_prefix"]

        new_prefix = f"{_prefix}.{i}" if _prefix else str(i)

        if new_prefix in _dict:
            return _dict[new_prefix]

        dot_prefix = new_prefix + "."
        if any(k.startswith(dot_prefix) for k in _dict):
            return SnapshotScope(_dict, new_prefix)

        raise KeyError(f"Путь '{new_prefix}' не найден в снимке пресета")
