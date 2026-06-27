"""Тесты для hantek_dso2d15.io.export — CSV / NPY / HDF5 экспорт кадра.

TDD: тесты написаны первыми (RED), до реализации.
Запуск: python -m pytest tests/io/ -q
"""
from __future__ import annotations

import csv
import os
import pathlib

import h5py
import numpy as np
import pytest

from hantek_dso2d15.waveform.decode import DecodedFrame


# ---------------------------------------------------------------------------
# Фикстура: синтетический кадр с 2 каналами
# ---------------------------------------------------------------------------

@pytest.fixture()
def frame() -> DecodedFrame:
    """Детерминированный 2-канальный кадр для всех тестов.

    time  : 5 точек, шаг 1/1000 с
    ch1   : [0.0, 0.5, 1.0, 0.5, 0.0] В
    ch2   : [-1.0, -0.5, 0.0, 0.5, 1.0] В
    srate : 1000.0 Sa/s
    """
    n = 5
    time = np.arange(n, dtype=np.float64) / 1000.0
    ch1 = np.array([0.0, 0.5, 1.0, 0.5, 0.0], dtype=np.float64)
    ch2 = np.array([-1.0, -0.5, 0.0, 0.5, 1.0], dtype=np.float64)
    return DecodedFrame(
        time=time,
        channels={1: ch1, 2: ch2},
        srate=1000.0,
        triggered=True,
        scales={1: 0.5, 2: 0.5},
        offsets={1: 0.0, 2: 0.0},
        timebase=1e-3,
    )


# ---------------------------------------------------------------------------
# Вспомогательная импортируемая функция
# ---------------------------------------------------------------------------

def _import():
    """Ленивый импорт, чтобы тест падал на ImportError, а не на уровне модуля."""
    from hantek_dso2d15.io.export import (
        EXTENSIONS,
        FORMATS,
        capture_filename,
        export_frame,
        write_csv,
        write_hdf5,
        write_npy,
    )
    return FORMATS, EXTENSIONS, write_csv, write_npy, write_hdf5, export_frame, capture_filename


# ---------------------------------------------------------------------------
# Константы модуля
# ---------------------------------------------------------------------------

class TestModuleConstants:
    def test_formats_tuple_contains_three(self) -> None:
        FORMATS, *_ = _import()
        assert set(FORMATS) == {"CSV", "NPY", "HDF5"}

    def test_extensions_keys_match_formats(self) -> None:
        FORMATS, EXTENSIONS, *_ = _import()
        assert set(EXTENSIONS.keys()) == set(FORMATS)

    def test_extension_values(self) -> None:
        _, EXTENSIONS, *_ = _import()
        assert EXTENSIONS["CSV"] == "csv"
        assert EXTENSIONS["NPY"] == "npz"
        assert EXTENSIONS["HDF5"] == "h5"


# ---------------------------------------------------------------------------
# write_csv
# ---------------------------------------------------------------------------

class TestWriteCsv:
    def test_creates_file(self, frame, tmp_path) -> None:
        _, _, write_csv, *_ = _import()
        path = str(tmp_path / "out.csv")
        write_csv(frame, path)
        assert pathlib.Path(path).exists()

    def test_header_correct(self, frame, tmp_path) -> None:
        """Первая строка: time_s,CH1_V,CH2_V (каналы отсортированы)."""
        _, _, write_csv, *_ = _import()
        path = str(tmp_path / "out.csv")
        write_csv(frame, path)
        with open(path, newline="") as f:
            reader = csv.reader(f)
            header = next(reader)
        assert header == ["time_s", "CH1_V", "CH2_V"]

    def test_row_count_equals_len_time_plus_one(self, frame, tmp_path) -> None:
        """Строк всего = len(time) + 1 (заголовок)."""
        _, _, write_csv, *_ = _import()
        path = str(tmp_path / "out.csv")
        write_csv(frame, path)
        lines = pathlib.Path(path).read_text().splitlines()
        assert len(lines) == len(frame.time) + 1

    def test_time_values_round_trip(self, frame, tmp_path) -> None:
        """Значения времени восстанавливаются из CSV с точностью float64."""
        _, _, write_csv, *_ = _import()
        path = str(tmp_path / "out.csv")
        write_csv(frame, path)
        data = np.loadtxt(path, delimiter=",", skiprows=1, usecols=0)
        np.testing.assert_allclose(data, frame.time, rtol=1e-12)

    def test_ch1_values_round_trip(self, frame, tmp_path) -> None:
        _, _, write_csv, *_ = _import()
        path = str(tmp_path / "out.csv")
        write_csv(frame, path)
        data = np.loadtxt(path, delimiter=",", skiprows=1, usecols=1)
        np.testing.assert_allclose(data, frame.channels[1], rtol=1e-12)

    def test_ch2_values_round_trip(self, frame, tmp_path) -> None:
        _, _, write_csv, *_ = _import()
        path = str(tmp_path / "out.csv")
        write_csv(frame, path)
        data = np.loadtxt(path, delimiter=",", skiprows=1, usecols=2)
        np.testing.assert_allclose(data, frame.channels[2], rtol=1e-12)

    def test_delimiter_is_comma(self, frame, tmp_path) -> None:
        _, _, write_csv, *_ = _import()
        path = str(tmp_path / "out.csv")
        write_csv(frame, path)
        first_line = pathlib.Path(path).read_text().splitlines()[0]
        assert "," in first_line
        assert "\t" not in first_line


# ---------------------------------------------------------------------------
# write_npy  (сохраняет как .npz)
# ---------------------------------------------------------------------------

class TestWriteNpy:
    def test_creates_npz_file(self, frame, tmp_path) -> None:
        _, _, _, write_npy, *_ = _import()
        path = str(tmp_path / "out.npz")
        write_npy(frame, path)
        # np.savez добавляет .npz, если его нет; проверяем любой из вариантов
        assert pathlib.Path(path).exists() or pathlib.Path(path + ".npz").exists()

    def _load(self, frame, tmp_path):
        _, _, _, write_npy, *_ = _import()
        path = str(tmp_path / "out.npz")
        write_npy(frame, path)
        # np.savez может добавить .npz повторно
        if pathlib.Path(path).exists():
            return np.load(path)
        return np.load(path + ".npz")

    def test_time_array_round_trip(self, frame, tmp_path) -> None:
        npz = self._load(frame, tmp_path)
        np.testing.assert_allclose(npz["time"], frame.time, rtol=1e-15)

    def test_ch1_array_round_trip(self, frame, tmp_path) -> None:
        npz = self._load(frame, tmp_path)
        np.testing.assert_allclose(npz["ch1"], frame.channels[1], rtol=1e-15)

    def test_ch2_array_round_trip(self, frame, tmp_path) -> None:
        npz = self._load(frame, tmp_path)
        np.testing.assert_allclose(npz["ch2"], frame.channels[2], rtol=1e-15)

    def test_srate_scalar_stored(self, frame, tmp_path) -> None:
        npz = self._load(frame, tmp_path)
        assert float(npz["srate"]) == pytest.approx(frame.srate)

    def test_timebase_stored_when_not_none(self, frame, tmp_path) -> None:
        """timebase != None → сохраняется как float."""
        npz = self._load(frame, tmp_path)
        assert float(npz["timebase"]) == pytest.approx(frame.timebase)

    def test_timebase_stored_as_nan_when_none(self, tmp_path) -> None:
        """timebase == None → сохраняется как nan."""
        _, _, _, write_npy, *_ = _import()
        f = DecodedFrame(
            time=np.array([0.0]),
            channels={1: np.array([0.0])},
            srate=1.0,
            timebase=None,
        )
        path = str(tmp_path / "out_nan.npz")
        write_npy(f, path)
        npz = np.load(path) if pathlib.Path(path).exists() else np.load(path + ".npz")
        assert np.isnan(float(npz["timebase"]))


# ---------------------------------------------------------------------------
# write_hdf5
# ---------------------------------------------------------------------------

class TestWriteHdf5:
    def test_creates_h5_file(self, frame, tmp_path) -> None:
        _, _, _, _, write_hdf5, *_ = _import()
        path = str(tmp_path / "out.h5")
        write_hdf5(frame, path)
        assert pathlib.Path(path).exists()

    def test_time_dataset_round_trip(self, frame, tmp_path) -> None:
        _, _, _, _, write_hdf5, *_ = _import()
        path = str(tmp_path / "out.h5")
        write_hdf5(frame, path)
        with h5py.File(path, "r") as hf:
            np.testing.assert_allclose(hf["time"][:], frame.time, rtol=1e-15)

    def test_ch1_dataset_round_trip(self, frame, tmp_path) -> None:
        _, _, _, _, write_hdf5, *_ = _import()
        path = str(tmp_path / "out.h5")
        write_hdf5(frame, path)
        with h5py.File(path, "r") as hf:
            np.testing.assert_allclose(hf["ch1"][:], frame.channels[1], rtol=1e-15)

    def test_ch2_dataset_round_trip(self, frame, tmp_path) -> None:
        _, _, _, _, write_hdf5, *_ = _import()
        path = str(tmp_path / "out.h5")
        write_hdf5(frame, path)
        with h5py.File(path, "r") as hf:
            np.testing.assert_allclose(hf["ch2"][:], frame.channels[2], rtol=1e-15)

    def test_srate_attribute_present(self, frame, tmp_path) -> None:
        _, _, _, _, write_hdf5, *_ = _import()
        path = str(tmp_path / "out.h5")
        write_hdf5(frame, path)
        with h5py.File(path, "r") as hf:
            assert "srate" in hf.attrs
            assert float(hf.attrs["srate"]) == pytest.approx(frame.srate)

    def test_triggered_attribute_present(self, frame, tmp_path) -> None:
        _, _, _, _, write_hdf5, *_ = _import()
        path = str(tmp_path / "out.h5")
        write_hdf5(frame, path)
        with h5py.File(path, "r") as hf:
            assert "triggered" in hf.attrs
            assert bool(hf.attrs["triggered"]) is True

    def test_timebase_attribute_when_not_none(self, frame, tmp_path) -> None:
        """timebase задан → атрибут 'timebase' присутствует и равен значению."""
        _, _, _, _, write_hdf5, *_ = _import()
        path = str(tmp_path / "out_tb.h5")
        write_hdf5(frame, path)
        with h5py.File(path, "r") as hf:
            assert "timebase" in hf.attrs
            assert float(hf.attrs["timebase"]) == pytest.approx(frame.timebase)

    def test_timebase_absent_when_none(self, tmp_path) -> None:
        """timebase=None → атрибут 'timebase' не записывается."""
        _, _, _, _, write_hdf5, *_ = _import()
        f = DecodedFrame(
            time=np.array([0.0]),
            channels={1: np.array([0.0])},
            srate=1.0,
            timebase=None,
        )
        path = str(tmp_path / "out_notb.h5")
        write_hdf5(f, path)
        with h5py.File(path, "r") as hf:
            assert "timebase" not in hf.attrs

    def test_h5_file_valid(self, frame, tmp_path) -> None:
        """Файл открывается h5py без ошибок."""
        _, _, _, _, write_hdf5, *_ = _import()
        path = str(tmp_path / "out_valid.h5")
        write_hdf5(frame, path)
        with h5py.File(path, "r") as hf:
            assert hf is not None


# ---------------------------------------------------------------------------
# export_frame  (диспетчер)
# ---------------------------------------------------------------------------

class TestExportFrame:
    def test_dispatch_csv(self, frame, tmp_path) -> None:
        *_, export_frame, _ = _import()
        path = str(tmp_path / "out.csv")
        export_frame(frame, path, "CSV")
        assert pathlib.Path(path).exists()

    def test_dispatch_npy(self, frame, tmp_path) -> None:
        *_, export_frame, _ = _import()
        path = str(tmp_path / "out.npz")
        export_frame(frame, path, "NPY")
        assert pathlib.Path(path).exists() or pathlib.Path(path + ".npz").exists()

    def test_dispatch_hdf5(self, frame, tmp_path) -> None:
        *_, export_frame, _ = _import()
        path = str(tmp_path / "out.h5")
        export_frame(frame, path, "HDF5")
        assert pathlib.Path(path).exists()

    def test_invalid_fmt_raises_value_error(self, frame, tmp_path) -> None:
        *_, export_frame, _ = _import()
        path = str(tmp_path / "out.xml")
        with pytest.raises(ValueError, match="XML"):
            export_frame(frame, path, "XML")

    def test_unknown_fmt_empty_string(self, frame, tmp_path) -> None:
        *_, export_frame, _ = _import()
        with pytest.raises(ValueError):
            export_frame(frame, str(tmp_path / "x"), "")


# ---------------------------------------------------------------------------
# capture_filename
# ---------------------------------------------------------------------------

class TestCaptureFilename:
    def test_csv_index_007(self, tmp_path) -> None:
        *_, capture_filename = _import()
        result = capture_filename(str(tmp_path), 7, "CSV")
        assert result == str(tmp_path / "capture_007.csv")

    def test_npy_index_001(self, tmp_path) -> None:
        *_, capture_filename = _import()
        result = capture_filename(str(tmp_path), 1, "NPY")
        assert result == str(tmp_path / "capture_001.npz")

    def test_hdf5_index_042(self, tmp_path) -> None:
        *_, capture_filename = _import()
        result = capture_filename(str(tmp_path), 42, "HDF5")
        assert result == str(tmp_path / "capture_042.h5")

    def test_zero_padded_three_digits(self, tmp_path) -> None:
        *_, capture_filename = _import()
        result = capture_filename(str(tmp_path), 0, "CSV")
        assert os.path.basename(result) == "capture_000.csv"

    def test_large_index_no_truncation(self, tmp_path) -> None:
        """Индекс > 999 — не обрезается нулями, просто шире."""
        *_, capture_filename = _import()
        result = capture_filename(str(tmp_path), 1234, "CSV")
        assert os.path.basename(result) == "capture_1234.csv"
