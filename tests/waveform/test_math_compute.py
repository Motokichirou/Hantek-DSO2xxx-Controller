"""Тесты для hantek_dso2d15.waveform.math_compute.

Чистые numpy-тесты, без Qt, без железа.
Запуск: .venv/Scripts/python.exe -m pytest tests/waveform/test_math_compute.py -q
"""
from __future__ import annotations

import numpy as np
import pytest

from hantek_dso2d15.waveform.decode import DecodedFrame
from hantek_dso2d15.waveform.math_compute import MathResult, compute_math


# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------

def _make_decoded(
    ch1: np.ndarray | None = None,
    ch2: np.ndarray | None = None,
    srate: float = 1000.0,
) -> DecodedFrame:
    """Построить минимальный DecodedFrame для тестов."""
    arrays: dict[int, np.ndarray] = {}
    if ch1 is not None:
        arrays[1] = np.asarray(ch1, dtype=np.float64)
    if ch2 is not None:
        arrays[2] = np.asarray(ch2, dtype=np.float64)
    n = next(iter(arrays.values())).shape[0] if arrays else 4
    t = np.arange(n, dtype=np.float64) / srate
    return DecodedFrame(time=t, channels=arrays, srate=srate)


def _cfg(**overrides) -> dict:
    """Базовый конфиг (все ключи), переопределённый через overrides."""
    base: dict = {
        "display": True,
        "operator": "ADD",
        "source1": 1,
        "source2": 2,
        "scale": 1.0,
        "offset": 0.0,
        "fft_source": 1,
        "fft_window": "HANNing",
        "fft_unit": "VRMS",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Тест 1: display=False → None
# ---------------------------------------------------------------------------

class TestDisplayFalse:
    def test_display_false_returns_none(self) -> None:
        dec = _make_decoded(ch1=np.ones(4), ch2=np.ones(4))
        result = compute_math(dec, _cfg(display=False))
        assert result is None

    def test_display_false_skips_validation(self) -> None:
        """display=False: оператор не валидируется — просто None."""
        dec = _make_decoded(ch1=np.ones(4), ch2=np.ones(4))
        result = compute_math(dec, _cfg(display=False, operator="INVALID"))
        assert result is None


# ---------------------------------------------------------------------------
# Тест 2: отсутствие источника → None
# ---------------------------------------------------------------------------

class TestMissingSource:
    def test_missing_source1_returns_none(self) -> None:
        """CH1 отсутствует → None (не ошибка)."""
        dec = _make_decoded(ch2=np.ones(4))
        result = compute_math(dec, _cfg(operator="ADD", source1=1, source2=2))
        assert result is None

    def test_missing_source2_returns_none(self) -> None:
        """CH2 отсутствует → None."""
        dec = _make_decoded(ch1=np.ones(4))
        result = compute_math(dec, _cfg(operator="ADD", source1=1, source2=2))
        assert result is None

    def test_missing_fft_source_returns_none(self) -> None:
        """FFT источник отсутствует → None."""
        dec = _make_decoded()  # нет каналов
        result = compute_math(dec, _cfg(operator="FFT", fft_source=1))
        assert result is None

    def test_both_channels_present_no_none(self) -> None:
        """Оба канала присутствуют → результат не None."""
        dec = _make_decoded(ch1=np.ones(4), ch2=np.ones(4))
        result = compute_math(dec, _cfg(operator="ADD"))
        assert result is not None


# ---------------------------------------------------------------------------
# Тест 3: ADD
# ---------------------------------------------------------------------------

class TestAdd:
    def test_add_basic(self) -> None:
        a = np.array([1.0, 2.0, 3.0])
        b = np.array([4.0, 5.0, 6.0])
        dec = _make_decoded(ch1=a, ch2=b)
        result = compute_math(dec, _cfg(operator="ADD"))
        assert result is not None
        np.testing.assert_allclose(result.y, [5.0, 7.0, 9.0])

    def test_add_kind_algebraic(self) -> None:
        dec = _make_decoded(ch1=np.ones(4), ch2=np.ones(4))
        result = compute_math(dec, _cfg(operator="ADD"))
        assert result is not None
        assert result.kind == "algebraic"

    def test_add_unit_v(self) -> None:
        dec = _make_decoded(ch1=np.ones(4), ch2=np.ones(4))
        result = compute_math(dec, _cfg(operator="ADD"))
        assert result is not None
        assert result.unit == "V"

    def test_add_x_equals_time(self) -> None:
        n, srate = 6, 500.0
        dec = _make_decoded(ch1=np.ones(n), ch2=np.ones(n), srate=srate)
        result = compute_math(dec, _cfg(operator="ADD"))
        assert result is not None
        np.testing.assert_allclose(result.x, dec.time[:n])

    def test_add_zeros(self) -> None:
        dec = _make_decoded(ch1=np.zeros(4), ch2=np.zeros(4))
        result = compute_math(dec, _cfg(operator="ADD"))
        assert result is not None
        np.testing.assert_allclose(result.y, np.zeros(4))


# ---------------------------------------------------------------------------
# Тест 4: SUBtract
# ---------------------------------------------------------------------------

class TestSubtract:
    def test_subtract_basic(self) -> None:
        a = np.array([5.0, 3.0, 1.0])
        b = np.array([1.0, 1.0, 1.0])
        dec = _make_decoded(ch1=a, ch2=b)
        result = compute_math(dec, _cfg(operator="SUBtract"))
        assert result is not None
        np.testing.assert_allclose(result.y, [4.0, 2.0, 0.0])

    def test_subtract_kind_algebraic(self) -> None:
        dec = _make_decoded(ch1=np.ones(4), ch2=np.zeros(4))
        result = compute_math(dec, _cfg(operator="SUBtract"))
        assert result is not None
        assert result.kind == "algebraic"

    def test_subtract_negative_result(self) -> None:
        a = np.array([1.0, 2.0])
        b = np.array([3.0, 5.0])
        dec = _make_decoded(ch1=a, ch2=b)
        result = compute_math(dec, _cfg(operator="SUBtract"))
        assert result is not None
        np.testing.assert_allclose(result.y, [-2.0, -3.0])


# ---------------------------------------------------------------------------
# Тест 5: MULTiply
# ---------------------------------------------------------------------------

class TestMultiply:
    def test_multiply_basic(self) -> None:
        a = np.array([2.0, 3.0, 4.0])
        b = np.array([5.0, 6.0, 7.0])
        dec = _make_decoded(ch1=a, ch2=b)
        result = compute_math(dec, _cfg(operator="MULTiply"))
        assert result is not None
        np.testing.assert_allclose(result.y, [10.0, 18.0, 28.0])

    def test_multiply_unit_v(self) -> None:
        dec = _make_decoded(ch1=np.ones(4), ch2=np.ones(4))
        result = compute_math(dec, _cfg(operator="MULTiply"))
        assert result is not None
        assert result.unit == "V"

    def test_multiply_by_zero(self) -> None:
        a = np.array([1.0, 2.0, 3.0])
        b = np.array([0.0, 0.0, 0.0])
        dec = _make_decoded(ch1=a, ch2=b)
        result = compute_math(dec, _cfg(operator="MULTiply"))
        assert result is not None
        np.testing.assert_allclose(result.y, [0.0, 0.0, 0.0])


# ---------------------------------------------------------------------------
# Тест 6: DIVision
# ---------------------------------------------------------------------------

class TestDivision:
    def test_division_basic(self) -> None:
        a = np.array([6.0, 9.0, 12.0])
        b = np.array([2.0, 3.0, 4.0])
        dec = _make_decoded(ch1=a, ch2=b)
        result = compute_math(dec, _cfg(operator="DIVision"))
        assert result is not None
        np.testing.assert_allclose(result.y, [3.0, 3.0, 3.0])

    def test_division_by_zero_gives_zero(self) -> None:
        """Где делитель == 0, результат → 0.0 (нет NaN/Inf)."""
        a = np.array([1.0, 2.0, 3.0])
        b = np.array([0.0, 1.0, 0.0])
        dec = _make_decoded(ch1=a, ch2=b)
        result = compute_math(dec, _cfg(operator="DIVision"))
        assert result is not None
        assert result.y[0] == pytest.approx(0.0)
        assert result.y[2] == pytest.approx(0.0)
        assert result.y[1] == pytest.approx(2.0)

    def test_division_all_zero_denominator(self) -> None:
        """Весь делитель нулевой → всё нули, нет предупреждений."""
        a = np.array([1.0, 2.0])
        b = np.array([0.0, 0.0])
        dec = _make_decoded(ch1=a, ch2=b)
        result = compute_math(dec, _cfg(operator="DIVision"))
        assert result is not None
        np.testing.assert_allclose(result.y, [0.0, 0.0])

    def test_division_no_nan(self) -> None:
        """Результат DIVision не содержит NaN."""
        a = np.array([1.0, 0.0, -1.0])
        b = np.array([0.0, 0.0, 0.0])
        dec = _make_decoded(ch1=a, ch2=b)
        result = compute_math(dec, _cfg(operator="DIVision"))
        assert result is not None
        assert not np.any(np.isnan(result.y)), "DIVision не должен давать NaN"

    def test_division_no_inf(self) -> None:
        """Результат DIVision не содержит Inf."""
        a = np.array([1.0])
        b = np.array([0.0])
        dec = _make_decoded(ch1=a, ch2=b)
        result = compute_math(dec, _cfg(operator="DIVision"))
        assert result is not None
        assert not np.any(np.isinf(result.y)), "DIVision не должен давать Inf"


# ---------------------------------------------------------------------------
# Тест 7: разные длины каналов — берём min
# ---------------------------------------------------------------------------

class TestUnequalLengths:
    def test_min_length_used(self) -> None:
        a = np.array([1.0, 2.0, 3.0, 4.0])
        b = np.array([1.0, 1.0])
        dec = DecodedFrame(
            time=np.arange(4, dtype=np.float64) / 100.0,
            channels={1: a, 2: b},
            srate=100.0,
        )
        result = compute_math(dec, _cfg(operator="ADD"))
        assert result is not None
        assert len(result.y) == 2

    def test_min_length_x_aligned(self) -> None:
        """x должен иметь ту же длину, что и y."""
        a = np.array([1.0, 2.0, 3.0, 4.0])
        b = np.array([1.0, 1.0])
        dec = DecodedFrame(
            time=np.arange(4, dtype=np.float64) / 100.0,
            channels={1: a, 2: b},
            srate=100.0,
        )
        result = compute_math(dec, _cfg(operator="SUBtract"))
        assert result is not None
        assert len(result.x) == len(result.y)


# ---------------------------------------------------------------------------
# Тест 8: FFT — пик синуса на правильном бине
# ---------------------------------------------------------------------------

class TestFFT:
    @staticmethod
    def _sine_decoded(
        freq_hz: float = 100.0,
        srate: float = 4000.0,
        n: int = 4096,
        amplitude: float = 1.0,
    ) -> DecodedFrame:
        """Синус известной частоты для проверки FFT."""
        t = np.arange(n, dtype=np.float64) / srate
        s = amplitude * np.sin(2 * np.pi * freq_hz * t)
        return DecodedFrame(time=t, channels={1: s}, srate=srate)

    def test_fft_peak_frequency_rectangle(self) -> None:
        """FFT синуса 100 Гц: argmax freqs ≈ 100 Гц (±5 Гц)."""
        dec = self._sine_decoded(freq_hz=100.0, srate=4000.0, n=4096)
        result = compute_math(
            dec, _cfg(operator="FFT", fft_source=1, fft_window="RECTangle", fft_unit="VRMS")
        )
        assert result is not None
        assert result.kind == "fft"
        peak_freq = float(result.x[int(np.argmax(result.y))])
        assert abs(peak_freq - 100.0) < 5.0, f"Пик FFT={peak_freq:.1f} Гц, ожидалось ≈100 Гц"

    def test_fft_peak_frequency_hanning(self) -> None:
        """FFT с окном Хэннинга также даёт пик ≈100 Гц."""
        dec = self._sine_decoded(freq_hz=100.0, srate=4000.0, n=4096)
        result = compute_math(
            dec, _cfg(operator="FFT", fft_source=1, fft_window="HANNing", fft_unit="VRMS")
        )
        assert result is not None
        peak_freq = float(result.x[int(np.argmax(result.y))])
        assert abs(peak_freq - 100.0) < 5.0, f"HANNing пик FFT={peak_freq:.1f} Гц"

    def test_fft_vrms_unit(self) -> None:
        dec = self._sine_decoded(n=256)
        result = compute_math(dec, _cfg(operator="FFT", fft_unit="VRMS"))
        assert result is not None
        assert result.unit == "Vrms"

    def test_fft_db_unit(self) -> None:
        dec = self._sine_decoded(n=256)
        result = compute_math(dec, _cfg(operator="FFT", fft_unit="DB"))
        assert result is not None
        assert result.unit == "dBV"

    def test_fft_x_is_frequencies(self) -> None:
        """x: [0 … srate/2], длина = n//2 + 1."""
        n, srate = 256, 1000.0
        dec = self._sine_decoded(freq_hz=50.0, srate=srate, n=n)
        result = compute_math(dec, _cfg(operator="FFT"))
        assert result is not None
        assert len(result.x) == n // 2 + 1
        assert result.x[0] == pytest.approx(0.0)
        assert result.x[-1] == pytest.approx(srate / 2.0)

    def test_fft_vrms_amplitude_sine_exact_periods(self) -> None:
        """Синус 1 В (peak) на целом числе периодов: VRMS-пик ≈ 1/√2 ≈ 0.707 В."""
        # f=100, srate=4000, n=4000: 100 точных периодов → нет утечки
        n, srate, freq = 4000, 4000.0, 100.0
        t = np.arange(n, dtype=np.float64) / srate
        s = np.sin(2 * np.pi * freq * t)
        dec = DecodedFrame(time=t, channels={1: s}, srate=srate)
        result = compute_math(
            dec, _cfg(operator="FFT", fft_source=1, fft_window="RECTangle", fft_unit="VRMS")
        )
        assert result is not None
        peak = float(np.max(result.y))
        expected = 1.0 / np.sqrt(2)
        assert abs(peak - expected) < 0.05, f"Пик VRMS={peak:.4f}, ожидается ≈{expected:.4f}"

    def test_fft_db_values_are_finite(self) -> None:
        """DB-режим: нет NaN/Inf в результате."""
        dec = self._sine_decoded(n=256)
        result = compute_math(dec, _cfg(operator="FFT", fft_unit="DB"))
        assert result is not None
        assert np.all(np.isfinite(result.y)), "DB FFT содержит NaN или Inf"

    def test_fft_all_windows_return_result(self) -> None:
        """Все 6 окон дают ненулевой MathResult."""
        dec = self._sine_decoded(n=256)
        windows = ["RECTangle", "HANNing", "HAMMing", "BLACkman", "TRIangle", "FLATtop"]
        for win in windows:
            result = compute_math(dec, _cfg(operator="FFT", fft_window=win))
            assert result is not None, f"Окно {win!r} вернуло None"
            assert result.kind == "fft"

    def test_fft_flattop_returns_result(self) -> None:
        """FLATtop-окно реализовано и возвращает MathResult."""
        dec = self._sine_decoded(n=128)
        result = compute_math(dec, _cfg(operator="FFT", fft_window="FLATtop"))
        assert result is not None
        assert len(result.y) == 128 // 2 + 1


# ---------------------------------------------------------------------------
# Тест 9: валидация ValueError
# ---------------------------------------------------------------------------

class TestValidation:
    def test_unknown_operator_raises_value_error(self) -> None:
        dec = _make_decoded(ch1=np.ones(4), ch2=np.ones(4))
        with pytest.raises(ValueError, match="(?i)operator|оператор"):
            compute_math(dec, _cfg(operator="BADOP"))

    def test_unknown_fft_window_raises_value_error(self) -> None:
        dec = _make_decoded(ch1=np.ones(4))
        with pytest.raises(ValueError, match="(?i)window|окно"):
            compute_math(dec, _cfg(operator="FFT", fft_window="BADWIN"))

    def test_unknown_fft_unit_raises_value_error(self) -> None:
        dec = _make_decoded(ch1=np.ones(4))
        with pytest.raises(ValueError, match="(?i)unit|единиц"):
            compute_math(dec, _cfg(operator="FFT", fft_unit="BADUNIT"))

    def test_valid_operators_do_not_raise(self) -> None:
        dec = _make_decoded(ch1=np.ones(4), ch2=np.ones(4))
        for op in ("ADD", "SUBtract", "MULTiply", "DIVision"):
            # Не должно бросать ValueError
            compute_math(dec, _cfg(operator=op))

    def test_valid_fft_windows_do_not_raise(self) -> None:
        dec = _make_decoded(ch1=np.ones(128))
        for win in ("RECTangle", "HANNing", "HAMMing", "BLACkman", "TRIangle", "FLATtop"):
            compute_math(dec, _cfg(operator="FFT", fft_window=win))

    def test_valid_fft_units_do_not_raise(self) -> None:
        dec = _make_decoded(ch1=np.ones(128))
        for unit in ("VRMS", "DB"):
            compute_math(dec, _cfg(operator="FFT", fft_unit=unit))


# ---------------------------------------------------------------------------
# Тест 10: MathResult — структура и типы
# ---------------------------------------------------------------------------

class TestMathResultStructure:
    def test_algebraic_result_is_math_result(self) -> None:
        dec = _make_decoded(ch1=np.ones(4), ch2=np.ones(4))
        result = compute_math(dec, _cfg(operator="ADD"))
        assert isinstance(result, MathResult)

    def test_algebraic_fields_exist(self) -> None:
        dec = _make_decoded(ch1=np.ones(4), ch2=np.ones(4))
        result = compute_math(dec, _cfg(operator="ADD"))
        assert result is not None
        assert hasattr(result, "kind")
        assert hasattr(result, "x")
        assert hasattr(result, "y")
        assert hasattr(result, "unit")

    def test_algebraic_kind_is_algebraic(self) -> None:
        dec = _make_decoded(ch1=np.ones(4), ch2=np.ones(4))
        for op in ("ADD", "SUBtract", "MULTiply", "DIVision"):
            result = compute_math(dec, _cfg(operator=op))
            assert result is not None
            assert result.kind == "algebraic", f"{op}: kind должен быть 'algebraic'"

    def test_fft_result_kind_is_fft(self) -> None:
        n = 128
        s = np.sin(2 * np.pi * 10 * np.arange(n) / 1000.0)
        dec = DecodedFrame(time=np.arange(n) / 1000.0, channels={1: s}, srate=1000.0)
        result = compute_math(dec, _cfg(operator="FFT"))
        assert result is not None
        assert result.kind == "fft"

    def test_algebraic_x_and_y_same_length(self) -> None:
        dec = _make_decoded(ch1=np.ones(8), ch2=np.ones(8))
        result = compute_math(dec, _cfg(operator="ADD"))
        assert result is not None
        assert len(result.x) == len(result.y)

    def test_fft_x_and_y_same_length(self) -> None:
        n = 64
        dec = DecodedFrame(
            time=np.arange(n) / 1000.0,
            channels={1: np.ones(n)},
            srate=1000.0,
        )
        result = compute_math(dec, _cfg(operator="FFT"))
        assert result is not None
        assert len(result.x) == len(result.y)
