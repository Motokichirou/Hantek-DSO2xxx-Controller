"""Экспорт декодированного кадра осциллографа в файл.

Поддерживаемые форматы: CSV, NPY (→ .npz), HDF5 (→ .h5).
Модуль не зависит от Qt, SCPI и транспортного слоя — чистый файловый I/O.

Основной пользователь: механизм сохранения в engine/gui.
"""
from __future__ import annotations

import csv
import os

import h5py
import numpy as np

from hantek_dso2d15.waveform.decode import DecodedFrame

# Поддерживаемые форматы экспорта
FORMATS: tuple[str, ...] = ("CSV", "NPY", "HDF5")

# Расширения файлов для каждого формата
EXTENSIONS: dict[str, str] = {
    "CSV": "csv",
    "NPY": "npz",
    "HDF5": "h5",
}


def write_csv(frame: DecodedFrame, path: str) -> None:
    """Сохранить кадр в CSV-файл.

    Формат:
      - Первая строка — заголовок: ``time_s,CH1_V,CH2_V,...``
        (каналы в порядке sorted(frame.channels)).
      - Последующие строки: значения времени и напряжений.
      - Разделитель — запятая; длина по frame.time.

    Parameters
    ----------
    frame:
        Декодированный кадр.
    path:
        Путь к выходному файлу (включая имя).
    """
    sorted_channels = sorted(frame.channels.keys())
    header = ["time_s"] + [f"CH{ch}_V" for ch in sorted_channels]

    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for i, t in enumerate(frame.time):
            # Преобразуем в plain Python float, чтобы избежать repr вида
            # "np.float64(0.0)" в NumPy 2.x — CSV должен содержать числа.
            row = [float(t)] + [float(frame.channels[ch][i]) for ch in sorted_channels]
            writer.writerow(row)


def write_npy(frame: DecodedFrame, path: str) -> None:
    """Сохранить кадр в NPZ-файл (numpy savez).

    Содержимое архива:
      - ``time`` — массив временной оси (float64).
      - ``ch{n}`` — массив напряжений канала n для каждого канала.
      - ``srate`` — частота дискретизации (скаляр).
      - ``timebase`` — развёртка (с/дел); если ``None``, сохраняется как ``nan``.

    Parameters
    ----------
    frame:
        Декодированный кадр.
    path:
        Путь к выходному файлу; ``np.savez`` добавит ``.npz`` автоматически,
        если расширение уже есть — не дублирует.
    """
    # Убрать .npz из пути, чтобы np.savez не создал path.npz.npz
    save_path = path[:-4] if path.endswith(".npz") else path

    timebase_val = float("nan") if frame.timebase is None else frame.timebase

    channel_arrays = {f"ch{ch}": arr for ch, arr in frame.channels.items()}

    np.savez(
        save_path,
        time=frame.time,
        srate=np.float64(frame.srate),
        timebase=np.float64(timebase_val),
        **channel_arrays,
    )


def write_hdf5(frame: DecodedFrame, path: str) -> None:
    """Сохранить кадр в HDF5-файл.

    Структура файла:
      - Датасет ``time`` — временная ось.
      - Датасеты ``ch{n}`` — напряжения по каналам.
      - Атрибуты корневой группы: ``srate``, ``triggered``.
      - Атрибут ``timebase`` добавляется только если ``frame.timebase is not None``.

    Parameters
    ----------
    frame:
        Декодированный кадр.
    path:
        Путь к выходному файлу.
    """
    with h5py.File(path, "w") as hf:
        # Временная ось
        hf.create_dataset("time", data=frame.time)

        # Каналы
        for ch, arr in frame.channels.items():
            hf.create_dataset(f"ch{ch}", data=arr)

        # Атрибуты
        hf.attrs["srate"] = frame.srate
        hf.attrs["triggered"] = frame.triggered

        # timebase пишем только если задан
        if frame.timebase is not None:
            hf.attrs["timebase"] = frame.timebase


def export_frame(frame: DecodedFrame, path: str, fmt: str) -> None:
    """Экспортировать кадр в файл в указанном формате.

    Parameters
    ----------
    frame:
        Декодированный кадр.
    path:
        Путь к выходному файлу.
    fmt:
        Формат экспорта — один из ``FORMATS`` (``"CSV"``, ``"NPY"``, ``"HDF5"``).

    Raises
    ------
    ValueError
        Если ``fmt`` не входит в ``FORMATS``.
    """
    if fmt not in FORMATS:
        raise ValueError(
            f"Неизвестный формат экспорта: {fmt!r}. "
            f"Допустимые значения: {FORMATS}"
        )
    if fmt == "CSV":
        write_csv(frame, path)
    elif fmt == "NPY":
        write_npy(frame, path)
    elif fmt == "HDF5":
        write_hdf5(frame, path)


def capture_filename(folder: str, index: int, fmt: str) -> str:
    """Сформировать стандартное имя файла захвата.

    Parameters
    ----------
    folder:
        Каталог для сохранения.
    index:
        Порядковый номер захвата (форматируется с нулями до 3 цифр).
    fmt:
        Формат из ``FORMATS``; определяет расширение через ``EXTENSIONS``.

    Returns
    -------
    str
        Полный путь вида ``folder/capture_007.csv``.

    Examples
    --------
    >>> capture_filename("/data", 7, "CSV")
    '/data/capture_007.csv'
    """
    ext = EXTENSIONS[fmt]
    filename = f"capture_{index:03d}.{ext}"
    return os.path.join(folder, filename)
