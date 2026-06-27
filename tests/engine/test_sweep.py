"""Tests for hantek_dso2d15.engine.sweep — движок параметрического свипа.

TDD: тесты написаны ДО реализации (RED-first). Все зависимости —
фейки-замыкания; Qt, io, scpi, transport не импортируются.
"""
from __future__ import annotations

import pytest

from hantek_dso2d15.engine.sweep import SweepConfig, SweepRunner, sweep_values


# ---------------------------------------------------------------------------
# sweep_values — граничные и типовые случаи
# ---------------------------------------------------------------------------

class TestSweepValues:
    """Тесты генератора линейных значений."""

    def test_step_zero_raises(self):
        """step=0 должен бросать ValueError."""
        with pytest.raises(ValueError):
            sweep_values(0.0, 10.0, 0.0)

    def test_step_negative_raises(self):
        """Отрицательный step должен бросать ValueError."""
        with pytest.raises(ValueError):
            sweep_values(0.0, 10.0, -1.0)

    def test_stop_less_than_start_raises(self):
        """stop < start должен бросать ValueError."""
        with pytest.raises(ValueError):
            sweep_values(10.0, 0.0, 1.0)

    def test_start_equals_stop_returns_single_element(self):
        """start == stop → список из одного элемента [start]."""
        result = sweep_values(5.0, 5.0, 1.0)
        assert result == [5.0]

    def test_example_100_to_100000_step_1000_gives_100_elements(self):
        """Спецификационный пример: start=100, stop=100000, step=1000 → ровно 100 значений.

        Формула: n = int((100000-100)/1000 + 1e-9) + 1 = int(99.9 + 1e-9) + 1 = 100.
        Последнее значение: 100 + 99*1000 = 99100 ≤ stop.
        """
        result = sweep_values(100.0, 100000.0, 1000.0)
        assert len(result) == 100
        assert result[0] == pytest.approx(100.0)
        assert result[-1] == pytest.approx(99100.0)

    def test_integer_steps_0_to_10_inclusive(self):
        """0..10 step 1 → [0, 1, ..., 10] — 11 значений; stop включён."""
        result = sweep_values(0.0, 10.0, 1.0)
        assert len(result) == 11
        assert result[0] == pytest.approx(0.0)
        assert result[-1] == pytest.approx(10.0)

    def test_no_float_accumulation_error(self):
        """Значения вычисляются как start + i*step, без накопления ошибок.

        0.0..1.0 step 0.1 → 11 значений, каждое == pytest.approx(i * 0.1).
        """
        result = sweep_values(0.0, 1.0, 0.1)
        # (1.0-0.0)/0.1 может дать 9.999... → 1e-9 даёт n=11
        assert len(result) == 11
        for i, v in enumerate(result):
            assert v == pytest.approx(i * 0.1), (
                f"Элемент {i}: ожидалось {i * 0.1}, получено {v}"
            )

    def test_single_step_includes_both_endpoints(self):
        """start=0, stop=5, step=5 → [0.0, 5.0] — оба конца."""
        result = sweep_values(0.0, 5.0, 5.0)
        assert len(result) == 2
        assert result == pytest.approx([0.0, 5.0])

    def test_returns_list(self):
        """Возвращаемый тип — list."""
        assert isinstance(sweep_values(0.0, 1.0, 1.0), list)

    def test_three_steps(self):
        """1.0..3.0 step 1.0 → [1.0, 2.0, 3.0]."""
        result = sweep_values(1.0, 3.0, 1.0)
        assert len(result) == 3
        assert result == pytest.approx([1.0, 2.0, 3.0])


# ---------------------------------------------------------------------------
# Вспомогательные фабрики для SweepRunner
# ---------------------------------------------------------------------------

def _make_config(
    start: float = 0.0,
    stop: float = 2.0,
    step: float = 1.0,
    dwell_s: float = 0.0,
) -> SweepConfig:
    """Фейковый SweepConfig для тестов."""
    return SweepConfig(
        parameter="dds.freq",
        start=start,
        stop=stop,
        step=step,
        dwell_s=dwell_s,
        fmt="CSV",
        folder="/tmp/sweep_test",
    )


def _make_deps(cancel_before_step: int | None = None):
    """Вернуть (log, sentinel, kwargs) для runner.run().

    log      — общий журнал вызовов: список кортежей вида ("op", ...).
    sentinel — объект, который возвращает capture(); save() должен его получить.
    kwargs   — именованные аргументы для runner.run().

    cancel_before_step: если задан, should_cancel() вернёт True начиная
                        с шага с этим индексом (0-based).
    """
    log: list = []
    sentinel = object()
    call_count = [0]  # счётчик вызовов should_cancel

    def set_param(v):
        log.append(("set_param", v))

    def sleep(s):
        log.append(("sleep", s))

    def capture():
        log.append(("capture",))
        return sentinel

    def save(frame, i):
        log.append(("save", frame, i))

    def on_progress(done, total):
        log.append(("progress", done, total))

    def should_cancel():
        idx = call_count[0]
        call_count[0] += 1
        if cancel_before_step is not None and idx >= cancel_before_step:
            return True
        return False

    kwargs = dict(
        set_param=set_param,
        sleep=sleep,
        capture=capture,
        save=save,
        on_progress=on_progress,
        should_cancel=should_cancel,
    )
    return log, sentinel, kwargs


# ---------------------------------------------------------------------------
# SweepRunner — полный прогон
# ---------------------------------------------------------------------------

class TestSweepRunnerFullRun:
    """Тесты нормального (без отмены) выполнения свипа."""

    def test_full_run_returns_done_equals_total_not_cancelled(self):
        """Полный прогон → {"done": total, "total": total, "cancelled": False}."""
        runner = SweepRunner()
        config = _make_config(start=0.0, stop=2.0, step=1.0)  # 3 шага
        log, sentinel, kwargs = _make_deps()
        result = runner.run(config, **kwargs)
        assert result == {"done": 3, "total": 3, "cancelled": False}

    def test_call_order_for_single_step(self):
        """Один шаг: порядок set_param→sleep→capture→save→progress."""
        runner = SweepRunner()
        config = _make_config(start=0.0, stop=0.0, step=1.0)  # ровно 1 шаг
        log, sentinel, kwargs = _make_deps()
        runner.run(config, **kwargs)
        ops = [entry[0] for entry in log]
        assert ops == ["set_param", "sleep", "capture", "save", "progress"]

    def test_call_order_for_three_steps(self):
        """Три шага: чередование set_param→sleep→capture→save→progress × 3."""
        runner = SweepRunner()
        config = _make_config(start=0.0, stop=2.0, step=1.0)  # 3 шага
        log, sentinel, kwargs = _make_deps()
        runner.run(config, **kwargs)
        ops = [entry[0] for entry in log]
        assert ops == [
            "set_param", "sleep", "capture", "save", "progress",
            "set_param", "sleep", "capture", "save", "progress",
            "set_param", "sleep", "capture", "save", "progress",
        ]

    def test_save_receives_sentinel_from_capture(self):
        """save получает именно объект, возвращённый capture()."""
        runner = SweepRunner()
        config = _make_config(start=0.0, stop=2.0, step=1.0)
        log, sentinel, kwargs = _make_deps()
        runner.run(config, **kwargs)
        save_calls = [e for e in log if e[0] == "save"]
        assert all(e[1] is sentinel for e in save_calls), (
            "save должен получать именно sentinel от capture()"
        )

    def test_save_receives_correct_0based_index(self):
        """save получает корректный 0-based индекс (0, 1, 2, ...)."""
        runner = SweepRunner()
        config = _make_config(start=0.0, stop=2.0, step=1.0)  # 3 шага
        log, sentinel, kwargs = _make_deps()
        runner.run(config, **kwargs)
        save_calls = [e for e in log if e[0] == "save"]
        assert len(save_calls) == 3
        for expected_idx, entry in enumerate(save_calls):
            _, frame, idx = entry
            assert idx == expected_idx, f"Шаг {expected_idx}: ожидался index={expected_idx}, получен {idx}"

    def test_progress_monotone_and_reaches_total(self):
        """on_progress вызывается с монотонно возрастающим done от 1 до total."""
        runner = SweepRunner()
        config = _make_config(start=0.0, stop=4.0, step=1.0)  # 5 шагов
        log, sentinel, kwargs = _make_deps()
        runner.run(config, **kwargs)
        progress_calls = [(e[1], e[2]) for e in log if e[0] == "progress"]
        assert len(progress_calls) == 5
        dones = [p[0] for p in progress_calls]
        totals = [p[1] for p in progress_calls]
        assert dones == [1, 2, 3, 4, 5], f"done должен расти 1..5, получено: {dones}"
        assert all(t == 5 for t in totals), f"total должен быть 5 везде, получено: {totals}"

    def test_sleep_called_with_config_dwell(self):
        """sleep вызывается с config.dwell_s."""
        runner = SweepRunner()
        config = _make_config(start=0.0, stop=1.0, step=1.0, dwell_s=0.5)  # 2 шага
        log, sentinel, kwargs = _make_deps()
        runner.run(config, **kwargs)
        sleep_calls = [e for e in log if e[0] == "sleep"]
        assert len(sleep_calls) == 2
        assert all(e[1] == pytest.approx(0.5) for e in sleep_calls)

    def test_set_param_values_match_sweep_values(self):
        """set_param вызывается с последовательностью из sweep_values(...)."""
        runner = SweepRunner()
        config = _make_config(start=1.0, stop=3.0, step=1.0)
        log, sentinel, kwargs = _make_deps()
        runner.run(config, **kwargs)
        actual = [e[1] for e in log if e[0] == "set_param"]
        expected = sweep_values(1.0, 3.0, 1.0)
        assert actual == pytest.approx(expected)


# ---------------------------------------------------------------------------
# SweepRunner — отмена (cancellation)
# ---------------------------------------------------------------------------

class TestSweepRunnerCancellation:
    """Тесты прерывания свипа через should_cancel()."""

    def test_cancel_immediately_done_0(self):
        """should_cancel=True с первого вызова → done=0, cancelled=True, ничего не выполнено."""
        runner = SweepRunner()
        config = _make_config(start=0.0, stop=2.0, step=1.0)  # 3 шага
        log, sentinel, kwargs = _make_deps(cancel_before_step=0)
        result = runner.run(config, **kwargs)
        assert result == {"done": 0, "total": 3, "cancelled": True}
        assert log == [], "При немедленной отмене ни один callback не должен быть вызван"

    def test_cancel_before_step_2_returns_done_1(self):
        """should_cancel=True перед шагом 1 (index=1) → done=1."""
        runner = SweepRunner()
        config = _make_config(start=0.0, stop=4.0, step=1.0)  # 5 шагов
        log, sentinel, kwargs = _make_deps(cancel_before_step=1)
        result = runner.run(config, **kwargs)
        assert result == {"done": 1, "total": 5, "cancelled": True}

    def test_cancel_before_step_3_returns_done_2_set_param_called_twice(self):
        """should_cancel=True перед шагом 2 (index=2) → done=2, cancelled=True.

        set_param вызван дважды (для i=0 и i=1), но НЕ для i=2.
        """
        runner = SweepRunner()
        config = _make_config(start=0.0, stop=4.0, step=1.0)  # 5 шагов
        log, sentinel, kwargs = _make_deps(cancel_before_step=2)
        result = runner.run(config, **kwargs)
        assert result == {"done": 2, "total": 5, "cancelled": True}
        set_param_calls = [e for e in log if e[0] == "set_param"]
        assert len(set_param_calls) == 2, (
            f"set_param должен быть вызван ровно 2 раза, получено {len(set_param_calls)}"
        )

    def test_cancel_before_step_3_set_param_not_called_for_step_3(self):
        """Конкретные значения set_param: только шаги 0 и 1, но не шаг 2."""
        runner = SweepRunner()
        config = _make_config(start=10.0, stop=14.0, step=1.0)  # 5 шагов: 10,11,12,13,14
        log, sentinel, kwargs = _make_deps(cancel_before_step=2)
        runner.run(config, **kwargs)
        set_param_values = [e[1] for e in log if e[0] == "set_param"]
        # Только первые 2 шага: 10.0, 11.0
        assert set_param_values == pytest.approx([10.0, 11.0])

    def test_cancel_at_last_step_done_equals_total_minus_1(self):
        """Отмена перед последним шагом → done = total - 1."""
        runner = SweepRunner()
        config = _make_config(start=0.0, stop=2.0, step=1.0)  # 3 шага
        log, sentinel, kwargs = _make_deps(cancel_before_step=2)
        result = runner.run(config, **kwargs)
        assert result == {"done": 2, "total": 3, "cancelled": True}

    def test_partial_run_progress_is_consistent(self):
        """При отмене после 2 шагов прогресс отражает 2 выполненных шага."""
        runner = SweepRunner()
        config = _make_config(start=0.0, stop=4.0, step=1.0)  # 5 шагов
        log, sentinel, kwargs = _make_deps(cancel_before_step=2)
        runner.run(config, **kwargs)
        progress_calls = [(e[1], e[2]) for e in log if e[0] == "progress"]
        # Прогресс только для шагов 0 и 1
        assert progress_calls == [(1, 5), (2, 5)]
