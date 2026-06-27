"""Окно отображения развёртки — какой срез памяти показывать на графике.

Прибор применяет s/дел как зум своего экрана в окно ``n_divs × s/дел``, тогда как
выгрузка ``PRIVate:WAVeform:DATA:ALL?`` отдаёт всю память (напр. 4000 точек). Чтобы
график вёл себя как осциллограф (смена s/дел видимо зумит), показываем не всю
память, а центральное окно ``n_divs × timebase`` секунд.

Функция чистая (без Qt/SCPI), полностью тестируется. Полный буфер сохраняется у
вызывающего — для курсоров/измерений/сохранения берётся весь кадр, срез только
для рисовки.
"""
from __future__ import annotations

#: Горизонтальных делений на экране (как в plot_widget).
HDIV: int = 14


def compute_window(n_pts: int, srate: float, timebase: float | None,
                   n_divs: int = HDIV) -> tuple[int, int]:
    """Вернуть полуинтервал ``(start, end)`` сэмплов для показа окна развёртки.

    Окно = ``n_divs × timebase`` секунд = ``round(n_divs × timebase × srate)``
    сэмплов, центрированное вокруг середины записи. Если окно ≥ памяти (медленная
    развёртка), либо ``timebase``/``srate`` неинформативны — возвращает всю память
    ``(0, n_pts)``.

    Гарантирует ширину окна ≥ 2 сэмплов и нахождение среза в ``[0, n_pts]``.
    """
    if not timebase or timebase <= 0 or srate <= 0 or n_pts <= 0:
        return (0, n_pts)
    window = round(n_divs * timebase * srate)
    if window >= n_pts:
        return (0, n_pts)
    if window < 2:
        window = 2
    mid = n_pts // 2
    start = mid - window // 2
    # клампим срез в границы памяти, сохраняя ширину window
    if start < 0:
        start = 0
    if start + window > n_pts:
        start = n_pts - window
    return (start, start + window)
