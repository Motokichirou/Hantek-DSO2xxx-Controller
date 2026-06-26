"""Тесты для hantek_dso2d15.scpi.validation — Task 3 (TDD)."""

import pytest

from hantek_dso2d15.scpi.validation import (
    validate_enum,
    validate_choice,
    parse_bool,
    bool_arg,
    fmt_num,
)


# ---------------------------------------------------------------------------
# validate_enum
# ---------------------------------------------------------------------------

class TestValidateEnum:
    def test_case_insensitive_dc(self):
        assert validate_enum("dc", ("AC", "DC", "GND"), "coupling") == "DC"

    def test_exact_match_preserved(self):
        assert validate_enum("RISIng", ("RISIng", "FALLing", "EITHer"), "slope") == "RISIng"

    def test_slash_literal_ext10(self):
        assert validate_enum("ext/10", ("CHANnel1", "EXT/10"), "src") == "EXT/10"

    def test_case_insensitive_channel(self):
        assert validate_enum("channel1", ("CHANnel1", "EXT/10"), "src") == "CHANnel1"

    def test_unknown_value_raises(self):
        with pytest.raises(ValueError):
            validate_enum("XX", ("AC", "DC", "GND"), "coupling")

    def test_error_contains_name(self):
        with pytest.raises(ValueError, match="coupling"):
            validate_enum("XX", ("AC", "DC", "GND"), "coupling")

    def test_rising_lowercase(self):
        assert validate_enum("rising", ("RISIng", "FALLing", "EITHer"), "slope") == "RISIng"

    def test_falling(self):
        assert validate_enum("FALLing", ("RISIng", "FALLing", "EITHer"), "slope") == "FALLing"


# ---------------------------------------------------------------------------
# validate_choice
# ---------------------------------------------------------------------------

class TestValidateChoice:
    def test_exact_match_int(self):
        assert validate_choice(10, (1, 10, 100, 1000), "probe") == 10

    def test_unknown_raises(self):
        with pytest.raises(ValueError):
            validate_choice(7, (1, 10, 100, 1000), "probe")

    def test_error_contains_name(self):
        with pytest.raises(ValueError, match="probe"):
            validate_choice(7, (1, 10, 100, 1000), "probe")

    def test_exact_match_large(self):
        assert validate_choice(4000000, (4000, 40000, 400000, 4000000, 8000000), "points") == 4000000

    def test_wrong_large_raises(self):
        with pytest.raises(ValueError):
            validate_choice(5000, (4000, 40000, 400000, 4000000, 8000000), "points")

    def test_returns_same_object(self):
        result = validate_choice(10, (1, 10, 100, 1000), "probe")
        assert result == 10
        assert type(result) is type(10)


# ---------------------------------------------------------------------------
# parse_bool
# ---------------------------------------------------------------------------

class TestParseBool:
    def test_one_is_true(self):
        assert parse_bool("1") is True

    def test_zero_is_false(self):
        assert parse_bool("0") is False

    def test_on_is_true(self):
        assert parse_bool("ON") is True

    def test_off_is_false(self):
        assert parse_bool("OFF") is False

    def test_on_with_trailing_space(self):
        assert parse_bool("ON ") is True

    def test_lowercase_on(self):
        assert parse_bool("on") is True

    def test_lowercase_off(self):
        assert parse_bool("off") is False

    def test_unknown_raises(self):
        with pytest.raises(ValueError):
            parse_bool("x")

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            parse_bool("")

    def test_two_raises(self):
        with pytest.raises(ValueError):
            parse_bool("2")


# ---------------------------------------------------------------------------
# bool_arg
# ---------------------------------------------------------------------------

class TestBoolArg:
    def test_true_gives_on(self):
        assert bool_arg(True) == "ON"

    def test_false_gives_off(self):
        assert bool_arg(False) == "OFF"

    def test_int_one_gives_on(self):
        assert bool_arg(1) == "ON"

    def test_int_zero_gives_off(self):
        assert bool_arg(0) == "OFF"

    def test_string_off_lowercase(self):
        assert bool_arg("off") == "OFF"

    def test_string_on_uppercase(self):
        assert bool_arg("ON") == "ON"

    def test_string_one(self):
        assert bool_arg("1") == "ON"

    def test_string_zero(self):
        assert bool_arg("0") == "OFF"

    def test_string_on_mixed_case(self):
        assert bool_arg("On") == "ON"

    def test_invalid_string_raises(self):
        with pytest.raises(ValueError):
            bool_arg("maybe")

    def test_invalid_string_yes_raises(self):
        with pytest.raises(ValueError):
            bool_arg("yes")


# ---------------------------------------------------------------------------
# fmt_num
# ---------------------------------------------------------------------------

class TestFmtNum:
    def test_small_float(self):
        assert fmt_num(5e-4) == "0.0005"

    def test_one(self):
        assert fmt_num(1.0) == "1"

    def test_half(self):
        assert fmt_num(0.5) == "0.5"

    def test_large(self):
        assert fmt_num(1e9) == "1e+09"

    def test_zero(self):
        assert fmt_num(0) == "0"

    def test_int_input(self):
        assert fmt_num(10) == "10"
