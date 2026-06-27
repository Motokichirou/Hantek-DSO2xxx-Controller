"""Регрессия: PRESET_PATHS покрывает всё, что читают load_from_scope панелей.

Пресет применяется к панелям через SnapshotScope (без I/O). Если панель читает
путь, которого нет в PRESET_PATHS, SnapshotScope бросит KeyError — этот тест
поймает такой дрейф (как поймал недостающий trigger.holdoff).
"""
from __future__ import annotations

import pytest

from hantek_dso2d15.io.presets import PRESET_PATHS, SnapshotScope
from hantek_dso2d15.gui.panels.vertical import VerticalPanel
from hantek_dso2d15.gui.panels.horizontal import HorizontalPanel
from hantek_dso2d15.gui.panels.trigger import TriggerPanel
from hantek_dso2d15.gui.panels.acquire import AcquirePanel
from hantek_dso2d15.gui.panels.generator import GeneratorPanel


def _dummy_value(path: str):
    """Типо-правдоподобное значение по суффиксу пути."""
    if path.endswith((".display", ".invert", ".bwlimit", ".output",
                      ".enable", ".mod_enable", ".burst_enable")):
        return True
    if path.endswith(".coupling"):
        return "DC"
    if path.endswith(".probe"):
        return 10
    if path.endswith(".mode"):
        return "MAIN"
    if path.endswith(".sweep"):
        return "AUTO"
    if path.endswith(".source"):
        return "CHANnel1"
    if path.endswith(".slope"):
        return "RISing"
    if path.endswith((".type", ".mod_type", ".mod_wave", ".burst_type")):
        return "SINE"
    if path.endswith((".count", ".points", ".burst_count")):
        return 4
    return 1.0


@pytest.fixture
def snapshot():
    return SnapshotScope({p: _dummy_value(p) for p in PRESET_PATHS})


@pytest.mark.parametrize("factory", [
    lambda: VerticalPanel(channels=(1, 2)),
    HorizontalPanel,
    TriggerPanel,
    AcquirePanel,
    GeneratorPanel,
])
def test_panel_resync_from_preset_snapshot(factory, snapshot):
    """load_from_scope(SnapshotScope(preset)) не должен падать (полнота путей)."""
    panel = factory()
    panel.load_from_scope(snapshot)  # KeyError => недостающий путь в PRESET_PATHS
