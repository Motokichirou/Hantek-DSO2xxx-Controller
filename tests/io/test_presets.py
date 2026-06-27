"""Тесты для hantek_dso2d15.io.presets — ядро пресетов настроек.

TDD: тесты написаны первыми (RED), до реализации.
Запуск: python -m pytest tests/io/ -q
"""
from __future__ import annotations

import json
import pathlib

import pytest


# ---------------------------------------------------------------------------
# Фейк-объекты прибора (без I/O, без Qt)
# ---------------------------------------------------------------------------

class _FakeChannel:
    """Имитирует Channel с нужными атрибутами."""

    def __init__(self, n: int) -> None:
        self.display = (n == 1)   # CH1 — включён, CH2 — выключен
        self.scale = float(n)     # 1.0 / 2.0
        self.offset = 0.0
        self.coupling = "DC"
        self.probe = 10
        self.bwlimit = False
        self.invert = False


class _FakeChannelCollection:
    def __init__(self) -> None:
        self._ch = {1: _FakeChannel(1), 2: _FakeChannel(2)}

    def __getitem__(self, n: int) -> _FakeChannel:
        return self._ch[n]


class _FakeTimebaseWindow:
    enable = False
    scale = 5e-4
    position = 0.0


class _FakeTimebase:
    scale = 1e-3
    position = 0.0
    mode = "MAIN"

    def __init__(self) -> None:
        self.window = _FakeTimebaseWindow()


class _FakeTriggerEdge:
    source = "CHANnel1"
    slope = "RISIng"
    level = 0.5


class _FakeTrigger:
    mode = "EDGE"
    sweep = "AUTO"
    holdoff = 1e-7

    def __init__(self) -> None:
        self.edge = _FakeTriggerEdge()


class _FakeAcquire:
    type = "NORMal"
    count = 4
    points = 4000


class _FakeDDS:
    output = False
    type = "SINE"
    freq = 1000.0
    amplitude = 1.0
    offset = 0.0
    duty = 50.0
    mod_enable = False
    mod_type = "AM"
    mod_wave = "SINE"
    mod_freq = 100.0
    mod_depth = 50.0
    burst_enable = False
    burst_type = "N_CYCLE"
    burst_count = 1


class FakeScope:
    """Полный фейк-scope со всеми подсистемами."""

    def __init__(self) -> None:
        self.channel = _FakeChannelCollection()
        self.timebase = _FakeTimebase()
        self.trigger = _FakeTrigger()
        self.acquire = _FakeAcquire()
        self.dds = _FakeDDS()


# ---------------------------------------------------------------------------
# Ленивый импорт (тест падает на ImportError, а не на уровне модуля)
# ---------------------------------------------------------------------------

def _import():
    from hantek_dso2d15.io.presets import (
        PRESET_PATHS,
        _navigate,
        capture_preset,
        apply_preset,
        save_preset,
        load_preset,
        SnapshotScope,
    )
    return PRESET_PATHS, _navigate, capture_preset, apply_preset, save_preset, load_preset, SnapshotScope


# ---------------------------------------------------------------------------
# PRESET_PATHS
# ---------------------------------------------------------------------------

class TestPresetPaths:
    def test_is_tuple(self) -> None:
        PRESET_PATHS, *_ = _import()
        assert isinstance(PRESET_PATHS, tuple)

    def test_contains_channel_paths_for_both_channels(self) -> None:
        PRESET_PATHS, *_ = _import()
        for n in (1, 2):
            for attr in ("display", "scale", "offset", "coupling", "probe", "bwlimit", "invert"):
                assert f"channel.{n}.{attr}" in PRESET_PATHS

    def test_contains_timebase_paths(self) -> None:
        PRESET_PATHS, *_ = _import()
        for key in ("scale", "position", "mode"):
            assert f"timebase.{key}" in PRESET_PATHS
        for key in ("enable", "scale", "position"):
            assert f"timebase.window.{key}" in PRESET_PATHS

    def test_contains_trigger_paths(self) -> None:
        PRESET_PATHS, *_ = _import()
        assert "trigger.mode" in PRESET_PATHS
        assert "trigger.sweep" in PRESET_PATHS
        assert "trigger.edge.source" in PRESET_PATHS
        assert "trigger.edge.slope" in PRESET_PATHS
        assert "trigger.edge.level" in PRESET_PATHS

    def test_contains_acquire_paths(self) -> None:
        PRESET_PATHS, *_ = _import()
        for key in ("type", "count", "points"):
            assert f"acquire.{key}" in PRESET_PATHS

    def test_contains_dds_paths(self) -> None:
        PRESET_PATHS, *_ = _import()
        for key in (
            "output", "type", "freq", "amplitude", "offset", "duty",
            "mod_enable", "mod_type", "mod_wave", "mod_freq", "mod_depth",
            "burst_enable", "burst_type", "burst_count",
        ):
            assert f"dds.{key}" in PRESET_PATHS


# ---------------------------------------------------------------------------
# _navigate
# ---------------------------------------------------------------------------

class TestNavigate:
    def test_two_parts_returns_owner_and_attr(self) -> None:
        _, _navigate, *_ = _import()
        scope = FakeScope()
        owner, attr = _navigate(scope, ["timebase", "scale"])
        assert owner is scope.timebase
        assert attr == "scale"

    def test_numeric_token_indexes_collection(self) -> None:
        _, _navigate, *_ = _import()
        scope = FakeScope()
        owner, attr = _navigate(scope, ["channel", "1", "scale"])
        assert owner is scope.channel[1]
        assert attr == "scale"

    def test_three_levels_trigger_edge_level(self) -> None:
        _, _navigate, *_ = _import()
        scope = FakeScope()
        owner, attr = _navigate(scope, ["trigger", "edge", "level"])
        assert owner is scope.trigger.edge
        assert attr == "level"

    def test_timebase_window_subsystem(self) -> None:
        _, _navigate, *_ = _import()
        scope = FakeScope()
        owner, attr = _navigate(scope, ["timebase", "window", "enable"])
        assert owner is scope.timebase.window
        assert attr == "enable"

    def test_dds_two_parts(self) -> None:
        _, _navigate, *_ = _import()
        scope = FakeScope()
        owner, attr = _navigate(scope, ["dds", "freq"])
        assert owner is scope.dds
        assert attr == "freq"

    def test_getattr_after_navigate_returns_correct_value(self) -> None:
        _, _navigate, *_ = _import()
        scope = FakeScope()
        owner, attr = _navigate(scope, ["channel", "2", "scale"])
        assert getattr(owner, attr) == 2.0


# ---------------------------------------------------------------------------
# capture_preset
# ---------------------------------------------------------------------------

class TestCapturePreset:
    def test_returns_dict(self) -> None:
        _, _, capture_preset, *_ = _import()
        result = capture_preset(FakeScope())
        assert isinstance(result, dict)

    def test_channel_scale_captured_correctly(self) -> None:
        _, _, capture_preset, *_ = _import()
        result = capture_preset(FakeScope())
        assert result["channel.1.scale"] == pytest.approx(1.0)
        assert result["channel.2.scale"] == pytest.approx(2.0)

    def test_channel_display_is_bool_and_correct(self) -> None:
        _, _, capture_preset, *_ = _import()
        result = capture_preset(FakeScope())
        assert isinstance(result["channel.1.display"], bool)
        assert result["channel.1.display"] is True
        assert result["channel.2.display"] is False

    def test_timebase_scale_captured(self) -> None:
        _, _, capture_preset, *_ = _import()
        result = capture_preset(FakeScope())
        assert result["timebase.scale"] == pytest.approx(1e-3)

    def test_timebase_mode_is_str(self) -> None:
        _, _, capture_preset, *_ = _import()
        result = capture_preset(FakeScope())
        assert isinstance(result["timebase.mode"], str)
        assert result["timebase.mode"] == "MAIN"

    def test_trigger_edge_level_captured(self) -> None:
        _, _, capture_preset, *_ = _import()
        result = capture_preset(FakeScope())
        assert result["trigger.edge.level"] == pytest.approx(0.5)

    def test_acquire_points_is_int(self) -> None:
        _, _, capture_preset, *_ = _import()
        result = capture_preset(FakeScope())
        assert isinstance(result["acquire.points"], int)
        assert result["acquire.points"] == 4000

    def test_acquire_count_is_int(self) -> None:
        _, _, capture_preset, *_ = _import()
        result = capture_preset(FakeScope())
        assert isinstance(result["acquire.count"], int)
        assert result["acquire.count"] == 4

    def test_dds_freq_captured(self) -> None:
        _, _, capture_preset, *_ = _import()
        result = capture_preset(FakeScope())
        assert result["dds.freq"] == pytest.approx(1000.0)

    def test_dds_output_is_bool(self) -> None:
        _, _, capture_preset, *_ = _import()
        result = capture_preset(FakeScope())
        assert isinstance(result["dds.output"], bool)
        assert result["dds.output"] is False

    def test_bad_path_skipped_silently(self) -> None:
        """Путь, который выбрасывает исключение, — пропускается."""
        _, _, capture_preset, *_ = _import()
        result = capture_preset(FakeScope(), paths=("nonexistent.path",))
        assert "nonexistent.path" not in result

    def test_partial_capture_keeps_good_paths(self) -> None:
        """Один сбойный путь не ломает снятие остальных."""
        _, _, capture_preset, *_ = _import()
        paths = ("channel.1.scale", "nonexistent.bad.path", "timebase.scale")
        result = capture_preset(FakeScope(), paths=paths)
        assert "channel.1.scale" in result
        assert "timebase.scale" in result
        assert "nonexistent.bad.path" not in result

    def test_all_preset_paths_captured_with_full_fake(self) -> None:
        """С полным фейком ни одного пропуска — все PRESET_PATHS в результате."""
        PRESET_PATHS, _, capture_preset, *_ = _import()
        result = capture_preset(FakeScope())
        assert set(result.keys()) == set(PRESET_PATHS)

    def test_values_are_json_serializable(self) -> None:
        """Все значения сериализуются в JSON без исключений."""
        _, _, capture_preset, *_ = _import()
        result = capture_preset(FakeScope())
        json.dumps(result)  # не должно кидать

    def test_bwlimit_bool_not_confused_with_int(self) -> None:
        """bwlimit=False: результат — bool, а не int 0."""
        _, _, capture_preset, *_ = _import()
        result = capture_preset(FakeScope())
        assert isinstance(result["channel.1.bwlimit"], bool)


# ---------------------------------------------------------------------------
# apply_preset
# ---------------------------------------------------------------------------

class TestApplyPreset:
    def test_returns_empty_list_on_full_success(self) -> None:
        _, _, capture_preset, apply_preset, *_ = _import()
        preset = capture_preset(FakeScope())
        errors = apply_preset(FakeScope(), preset)
        assert errors == []

    def test_applies_channel_scale(self) -> None:
        _, _, _, apply_preset, *_ = _import()
        scope = FakeScope()
        apply_preset(scope, {"channel.1.scale": 5.0})
        assert scope.channel[1].scale == pytest.approx(5.0)

    def test_applies_timebase_scale(self) -> None:
        _, _, _, apply_preset, *_ = _import()
        scope = FakeScope()
        apply_preset(scope, {"timebase.scale": 2e-3})
        assert scope.timebase.scale == pytest.approx(2e-3)

    def test_applies_bool_value(self) -> None:
        _, _, _, apply_preset, *_ = _import()
        scope = FakeScope()
        apply_preset(scope, {"channel.1.display": False})
        assert scope.channel[1].display is False

    def test_applies_trigger_edge_level(self) -> None:
        _, _, _, apply_preset, *_ = _import()
        scope = FakeScope()
        apply_preset(scope, {"trigger.edge.level": 2.5})
        assert scope.trigger.edge.level == pytest.approx(2.5)

    def test_applies_multiple_values(self) -> None:
        _, _, _, apply_preset, *_ = _import()
        scope = FakeScope()
        apply_preset(scope, {
            "channel.1.scale": 0.1,
            "channel.2.offset": -1.0,
            "dds.freq": 500.0,
        })
        assert scope.channel[1].scale == pytest.approx(0.1)
        assert scope.channel[2].offset == pytest.approx(-1.0)
        assert scope.dds.freq == pytest.approx(500.0)

    def test_bad_path_collected_in_errors(self) -> None:
        _, _, _, apply_preset, *_ = _import()
        scope = FakeScope()
        errors = apply_preset(scope, {"nonexistent.path": 42})
        assert "nonexistent.path" in errors

    def test_bad_path_does_not_stop_remaining(self) -> None:
        """Ошибочный путь не прерывает применение остальных."""
        _, _, _, apply_preset, *_ = _import()
        scope = FakeScope()
        errors = apply_preset(scope, {
            "nonexistent.path": 42,
            "channel.1.scale": 3.0,
        })
        assert "nonexistent.path" in errors
        assert scope.channel[1].scale == pytest.approx(3.0)

    def test_returns_list_type(self) -> None:
        _, _, _, apply_preset, *_ = _import()
        result = apply_preset(FakeScope(), {})
        assert isinstance(result, list)

    def test_dds_output_applied_last(self) -> None:
        """dds.output ставится ПОСЛЕДНИМ (burst-свитч гасит выход на железе)."""
        _, _, _, apply_preset, *_ = _import()
        order: list[str] = []

        class _RecDDS:
            def __setattr__(self, name, value):
                order.append(name)
                object.__setattr__(self, name, value)

        class _RecScope:
            def __init__(self):
                self.dds = _RecDDS()

        # output стоит ПЕРВЫМ в dict — но применён должен быть последним
        apply_preset(_RecScope(), {
            "dds.output": True,
            "dds.burst_enable": False,
            "dds.type": "SINE",
        })
        assert order[-1] == "output"
        assert order.index("burst_enable") < order.index("output")
        assert order.index("type") < order.index("output")


# ---------------------------------------------------------------------------
# save_preset / load_preset
# ---------------------------------------------------------------------------

class TestSaveLoadRoundtrip:
    def test_round_trip_identical(self, tmp_path) -> None:
        _, _, capture_preset, _, save_preset, load_preset, _ = _import()
        preset = capture_preset(FakeScope())
        path = str(tmp_path / "preset.json")
        save_preset(preset, path)
        loaded = load_preset(path)
        assert loaded == preset

    def test_file_is_valid_json(self, tmp_path) -> None:
        _, _, capture_preset, _, save_preset, _, _ = _import()
        preset = capture_preset(FakeScope())
        path = str(tmp_path / "preset.json")
        save_preset(preset, path)
        text = pathlib.Path(path).read_text(encoding="utf-8")
        parsed = json.loads(text)
        assert isinstance(parsed, dict)

    def test_file_has_indentation(self, tmp_path) -> None:
        """JSON записан с отступами (indent=2) — читаем глазами."""
        _, _, _, _, save_preset, _, _ = _import()
        path = str(tmp_path / "small.json")
        save_preset({"channel.1.scale": 1.0}, path)
        text = pathlib.Path(path).read_text(encoding="utf-8")
        assert "\n" in text

    def test_empty_preset_round_trip(self, tmp_path) -> None:
        _, _, _, _, save_preset, load_preset, _ = _import()
        path = str(tmp_path / "empty.json")
        save_preset({}, path)
        assert load_preset(path) == {}

    def test_bool_preserved_in_round_trip(self, tmp_path) -> None:
        """bool не превращается в int через JSON."""
        _, _, _, _, save_preset, load_preset, _ = _import()
        path = str(tmp_path / "bools.json")
        save_preset({"flag_true": True, "flag_false": False}, path)
        loaded = load_preset(path)
        assert loaded["flag_true"] is True
        assert loaded["flag_false"] is False

    def test_utf8_encoding(self, tmp_path) -> None:
        """Файл пишется в UTF-8."""
        _, _, _, _, save_preset, load_preset, _ = _import()
        path = str(tmp_path / "utf8.json")
        save_preset({"info": "тест"}, path)
        text = pathlib.Path(path).read_text(encoding="utf-8")
        assert "тест" in text


# ---------------------------------------------------------------------------
# SnapshotScope
# ---------------------------------------------------------------------------

class TestSnapshotScope:
    def _cls(self):
        _, _, _, _, _, _, SnapshotScope = _import()
        return SnapshotScope

    def test_channel_scale_via_index(self) -> None:
        sc = self._cls()({"channel.1.scale": 0.5, "timebase.scale": 1e-3})
        assert sc.channel[1].scale == pytest.approx(0.5)

    def test_timebase_scale_via_attr(self) -> None:
        sc = self._cls()({"channel.1.scale": 0.5, "timebase.scale": 1e-3})
        assert sc.timebase.scale == pytest.approx(1e-3)

    def test_three_level_trigger_edge_level(self) -> None:
        sc = self._cls()({"trigger.edge.level": 1.5})
        assert sc.trigger.edge.level == pytest.approx(1.5)

    def test_timebase_window_enable(self) -> None:
        sc = self._cls()({"timebase.window.enable": True})
        assert sc.timebase.window.enable is True

    def test_missing_leaf_raises_key_error(self) -> None:
        sc = self._cls()({"channel.1.scale": 0.5})
        with pytest.raises(KeyError):
            _ = sc.channel[1].offset   # отсутствует в dict

    def test_missing_top_attr_raises_key_error(self) -> None:
        """Атрибут без единого дочернего пути → KeyError."""
        sc = self._cls()({"channel.1.scale": 0.5})
        with pytest.raises(KeyError):
            _ = sc.timebase   # нет ни одного ключа, начинающегося с 'timebase.'

    def test_intermediate_node_returns_proxy_not_error(self) -> None:
        """Промежуточный узел (есть дочерние пути) возвращает под-прокси."""
        sc = self._cls()({"channel.1.scale": 0.5, "channel.2.scale": 1.0})
        proxy = sc.channel  # должен вернуть SnapshotScope, а не KeyError
        assert not isinstance(proxy, (int, float, str, bool))

    def test_key_error_message_contains_path(self) -> None:
        """Сообщение KeyError содержит накопленный путь."""
        sc = self._cls()({"channel.1.scale": 0.5})
        with pytest.raises(KeyError) as exc_info:
            _ = sc.channel[1].offset
        assert "channel.1.offset" in str(exc_info.value)

    def test_bool_value_preserved(self) -> None:
        sc = self._cls()({"channel.1.display": True})
        assert sc.channel[1].display is True

    def test_int_value_preserved(self) -> None:
        sc = self._cls()({"acquire.points": 4000})
        assert sc.acquire.points == 4000

    def test_full_preset_access(self) -> None:
        """С пресетом от capture_preset доступны все ключи."""
        PRESET_PATHS, _, capture_preset, _, _, _, SnapshotScope = _import()
        preset = capture_preset(FakeScope())
        sc = SnapshotScope(preset)
        # Выборочная проверка нескольких уровней
        assert sc.channel[1].scale == pytest.approx(preset["channel.1.scale"])
        assert sc.timebase.scale == pytest.approx(preset["timebase.scale"])
        assert sc.trigger.edge.level == pytest.approx(preset["trigger.edge.level"])
        assert sc.dds.freq == pytest.approx(preset["dds.freq"])
        assert sc.timebase.window.enable == preset["timebase.window.enable"]

    def test_channel2_via_index(self) -> None:
        sc = self._cls()({"channel.2.coupling": "AC"})
        assert sc.channel[2].coupling == "AC"

    def test_empty_dict_raises_key_error(self) -> None:
        sc = self._cls()({})
        with pytest.raises(KeyError):
            _ = sc.channel
