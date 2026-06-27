"""Математика осциллограмм на стороне клиента (из наших сэмпл-буферов).

Поддерживаемые операторы (SCPI-литералы, frozen reference §6):
  Алгебра : ADD, SUBtract, MULTiply, DIVision
  Спектр  : FFT

Окна FFT (SCPI-литералы): RECTangle, HANNing, HAMMing, BLACkman, TRIangle, FLATtop
Единицы FFT (SCPI-литералы): VRMS, DB

Функция compute_math — чистая (без I/O и состояния), пригодна для тестирования
без приборного железа и без Qt.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from hantek_dso2d15.waveform.decode import DecodedFrame

# ---------------------------------------------------------------------------
# Допустимые значения (frozen SCPI-reference §6 — не менять без hardware-verify)
# ---------------------------------------------------------------------------

_ALGEBRAIC_OPS: frozenset[str] = frozenset({"ADD", "SUBtract", "MULTiply", "DIVision"})
_FFT_OPS: frozenset[str] = frozenset({"FFT"})
_ALL_OPS: frozenset[str] = _ALGEBRAIC_OPS | _FFT_OPS

_FFT_WINDOWS: frozenset[str] = frozenset(
    {"RECTangle", "HANNing", "HAMMing", "BLACkman", "TRIangle", "FLATtop"}
)
_FFT_UNITS: frozenset[str] = frozenset({"VRMS", "DB"})


# ---------------------------------------------------------------------------
# Результирующий тип
# ---------------------------------------------------------------------------

@dataclass
class MathResult:
    """Результат математической операции над каналами осциллографа.

    Attributes
    ----------
    kind:
        ``"algebraic"`` — алгебраическая операция (x в секундах, y в вольтах);
        ``"fft"`` — спектральный анализ (x в Гц, y — амплитуда).
    x:
        Ось X: время (сек) для algebraic, частоты (Гц) для fft.
    y:
        Значения: вольты (V) для algebraic, Vrms или dBV для fft.
    unit:
        Единица: ``"V"`` / ``"Vrms"`` / ``"dBV"``.
    """

    kind: str
    x: np.ndarray
    y: np.ndarray
    unit: str


# ---------------------------------------------------------------------------
# Вспомогательные функции окон FFT
# ---------------------------------------------------------------------------

def _flattop_window(n: int) -> np.ndarray:
    """Стандартное плоское окно (5-term flat-top, коэффициенты Heinzel 2002).

    Коэффициенты совпадают с scipy.signal.windows.flattop.
    Используется для амплитудно-точного анализа синусоид.
    """
    if n <= 1:
        return np.ones(n, dtype=np.float64)
    a0, a1, a2, a3, a4 = (
        0.21557895, 0.41663158, 0.277263158, 0.083578947, 0.006947368
    )
    idx = np.arange(n, dtype=np.float64)
    w = (
        a0
        - a1 * np.cos(2.0 * np.pi * idx / (n - 1))
        + a2 * np.cos(4.0 * np.pi * idx / (n - 1))
        - a3 * np.cos(6.0 * np.pi * idx / (n - 1))
        + a4 * np.cos(8.0 * np.pi * idx / (n - 1))
    )
    return w


def _make_window(name: str, n: int) -> np.ndarray:
    """Построить оконную функцию по SCPI-литералу.

    Raises
    ------
    ValueError
        Если имя окна не входит в допустимый список frozen reference §6.
    """
    if name == "RECTangle":
        return np.ones(n, dtype=np.float64)
    if name == "HANNing":
        return np.hanning(n)
    if name == "HAMMing":
        return np.hamming(n)
    if name == "BLACkman":
        return np.blackman(n)
    if name == "TRIangle":
        return np.bartlett(n)
    if name == "FLATtop":
        return _flattop_window(n)
    raise ValueError(
        f"Неизвестное FFT-окно: {name!r}. "
        f"Допустимые: {sorted(_FFT_WINDOWS)}"
    )


# ---------------------------------------------------------------------------
# Публичная функция
# ---------------------------------------------------------------------------

def compute_math(decoded: DecodedFrame, config: dict) -> MathResult | None:
    """Вычислить математическую трассу из декодированного кадра.

    Parameters
    ----------
    decoded:
        Декодированный кадр с полями ``.channels`` (dict int→np.ndarray),
        ``.time`` (np.ndarray, сек) и ``.srate`` (Гц).
    config:
        Словарь настроек Math-панели. Обязательные ключи::

            display   : bool     — включена ли Math-трасса
            operator  : str      — ADD / SUBtract / MULTiply / DIVision / FFT
            source1   : int      — номер канала CH1..CH4 для алгебры
            source2   : int      — номер канала CH1..CH4 для алгебры
            scale     : float    — В/дел (не применяется здесь, для рендера)
            offset    : float    — смещение В (не применяется здесь, для рендера)
            fft_source: int      — номер канала для FFT
            fft_window: str      — RECTangle / HANNing / HAMMing / BLACkman /
                                   TRIangle / FLATtop
            fft_unit  : str      — VRMS / DB

    Returns
    -------
    MathResult | None
        ``None`` если:
        - ``config["display"]`` не задан или ``False``
        - нужный источник отсутствует в ``decoded.channels``

    Raises
    ------
    ValueError
        На неизвестном operator, fft_window или fft_unit
        (только при display=True).
    """
    # Быстрый выход — трасса выключена
    if not config.get("display", False):
        return None

    operator: str = config["operator"]
    if operator not in _ALL_OPS:
        raise ValueError(
            f"Неизвестный оператор: {operator!r}. "
            f"Допустимые: {sorted(_ALL_OPS)}"
        )

    # -----------------------------------------------------------------------
    # Алгебраические операции
    # -----------------------------------------------------------------------
    if operator in _ALGEBRAIC_OPS:
        src1: int = config["source1"]
        src2: int = config["source2"]
        if src1 not in decoded.channels or src2 not in decoded.channels:
            return None

        a = decoded.channels[src1]
        b = decoded.channels[src2]
        L = min(len(a), len(b))
        a, b = a[:L], b[:L]
        t = decoded.time[:L]

        if operator == "ADD":
            y = a + b
        elif operator == "SUBtract":
            y = a - b
        elif operator == "MULTiply":
            y = a * b
        else:  # DIVision — защита от деления на ноль
            with np.errstate(divide="ignore", invalid="ignore"):
                y = np.where(b == 0.0, 0.0, a / b)

        return MathResult(kind="algebraic", x=t, y=y, unit="V")

    # -----------------------------------------------------------------------
    # FFT
    # -----------------------------------------------------------------------
    fft_unit: str = config["fft_unit"]
    if fft_unit not in _FFT_UNITS:
        raise ValueError(
            f"Неизвестная единица FFT: {fft_unit!r}. "
            f"Допустимые: {sorted(_FFT_UNITS)}"
        )

    fft_window: str = config["fft_window"]
    if fft_window not in _FFT_WINDOWS:
        raise ValueError(
            f"Неизвестное FFT-окно: {fft_window!r}. "
            f"Допустимые: {sorted(_FFT_WINDOWS)}"
        )

    fft_src: int = config["fft_source"]
    if fft_src not in decoded.channels:
        return None

    s = decoded.channels[fft_src]
    n = len(s)
    win = _make_window(fft_window, n)
    sw = s * win
    X = np.fft.rfft(sw)
    freqs = np.fft.rfftfreq(n, d=1.0 / decoded.srate)

    # Амплитуда single-sided с компенсацией суммы окна
    amp = 2.0 * np.abs(X) / np.sum(win)

    if fft_unit == "VRMS":
        y = amp / np.sqrt(2.0)
        unit = "Vrms"
    else:  # DB
        y = 20.0 * np.log10(np.maximum(amp / np.sqrt(2.0), 1e-12))
        unit = "dBV"

    return MathResult(kind="fft", x=freqs, y=y, unit=unit)
