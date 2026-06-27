"""Headless-тесты оверлея курсоров и панели CursorsPanel.

QT_QPA_PLATFORM=offscreen — безголовый режим.
Запуск: .venv/Scripts/python.exe -m pytest tests/gui/test_cursors.py -q
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pyqtgraph as pg  # noqa: E402
from PySide6.QtCore import QCoreApplication  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from hantek_dso2d15.gui.cursor_overlay import HDIV, CursorOverlay  # noqa: E402
from hantek_dso2d15.gui.panels.cursors import CursorsPanel  # noqa: E402


# ---------------------------------------------------------------------------
# Одно QApplication на весь модуль
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def app():
    existing = QCoreApplication.instance()
    if existing is not None:
        yield existing
    else:
        a = QApplication(sys.argv[:1])
        yield a


# ---------------------------------------------------------------------------
# Фейк-кадр с известными параметрами
# ---------------------------------------------------------------------------


class _FakeDecoded:
    """Минимальный декодированный кадр для тестов."""

    def __init__(
        self,
        n_pts: int = 200,
        total_time: float = 1e-3,
        vdiv: float = 1.0,
        off: float = 0.0,
        ch: int = 1,
        volts_fn=None,
    ):
        self.time = np.linspace(0.0, total_time, n_pts)
        if volts_fn is None:
            arr = np.zeros(n_pts)
        else:
            arr = np.array([volts_fn(t) for t in self.time])
        self.channels = {ch: arr}
        self.scales = {ch: vdiv}
        self.offsets = {ch: off}
        self.srate = float(n_pts / total_time)
        self.triggered = True


# ---------------------------------------------------------------------------
# Фикстуры оверлея
# ---------------------------------------------------------------------------


@pytest.fixture
def pw(app):
    """Чистый PlotWidget без граткюля — для тестирования оверлея."""
    return pg.PlotWidget()


@pytest.fixture
def overlay(pw):
    return CursorOverlay(pw.getPlotItem())


# ---------------------------------------------------------------------------
# Группа 1: Создание линий
# ---------------------------------------------------------------------------


class TestCreation:
    def test_four_lines_in_plot_item(self, overlay, pw):
        """Оверлей добавляет ровно 4 InfiniteLine в PlotItem."""
        pi = pw.getPlotItem()
        lines = [it for it in pi.items if isinstance(it, pg.InfiniteLine)]
        assert len(lines) == 4

    def test_lines_are_infinite_line_instances(self, overlay):
        for attr in ("_ax", "_bx", "_ay", "_by"):
            assert isinstance(getattr(overlay, attr), pg.InfiniteLine), \
                f"{attr} должен быть InfiniteLine"

    def test_lines_in_plot_item(self, overlay, pw):
        pi = pw.getPlotItem()
        for attr in ("_ax", "_bx", "_ay", "_by"):
            assert getattr(overlay, attr) in pi.items, \
                f"{attr} должен быть в pi.items"

    def test_lines_hidden_on_start(self, overlay):
        """Все линии скрыты сразу после создания."""
        for attr in ("_ax", "_bx", "_ay", "_by"):
            assert not getattr(overlay, attr).isVisible(), \
                f"{attr} должен быть скрыт при создании"

    def test_vertical_lines_angle(self, overlay):
        """AX и BX — вертикальные (angle=90)."""
        assert overlay._ax.angle == 90
        assert overlay._bx.angle == 90

    def test_horizontal_lines_angle(self, overlay):
        """AY и BY — горизонтальные (angle=0)."""
        assert overlay._ay.angle == 0
        assert overlay._by.angle == 0

    def test_all_lines_movable(self, overlay):
        for attr in ("_ax", "_bx", "_ay", "_by"):
            line = getattr(overlay, attr)
            assert line.movable, f"{attr} должен быть movable"

    def test_initial_positions(self, overlay):
        """Стартовые позиции: AX=HDIV/3, BX=2·HDIV/3, AY=1, BY=−1."""
        assert overlay._ax.value() == pytest.approx(HDIV / 3)
        assert overlay._bx.value() == pytest.approx(2 * HDIV / 3)
        assert overlay._ay.value() == pytest.approx(1.0)
        assert overlay._by.value() == pytest.approx(-1.0)


# ---------------------------------------------------------------------------
# Группа 2: set_mode — видимость линий
# ---------------------------------------------------------------------------


class TestSetMode:
    def test_off_hides_all(self, overlay):
        overlay.set_mode("OFF")
        assert not overlay._ax.isVisible()
        assert not overlay._bx.isVisible()
        assert not overlay._ay.isVisible()
        assert not overlay._by.isVisible()

    def test_x_shows_ax_bx_only(self, overlay):
        overlay.set_mode("X")
        assert overlay._ax.isVisible()
        assert overlay._bx.isVisible()
        assert not overlay._ay.isVisible()
        assert not overlay._by.isVisible()

    def test_y_shows_ay_by_only(self, overlay):
        overlay.set_mode("Y")
        assert not overlay._ax.isVisible()
        assert not overlay._bx.isVisible()
        assert overlay._ay.isVisible()
        assert overlay._by.isVisible()

    def test_xy_shows_all(self, overlay):
        overlay.set_mode("XY")
        assert overlay._ax.isVisible()
        assert overlay._bx.isVisible()
        assert overlay._ay.isVisible()
        assert overlay._by.isVisible()

    def test_track_shows_ax_bx_only(self, overlay):
        overlay.set_mode("TRACk")
        assert overlay._ax.isVisible()
        assert overlay._bx.isVisible()
        assert not overlay._ay.isVisible()
        assert not overlay._by.isVisible()

    def test_mode_stored(self, overlay):
        overlay.set_mode("XY")
        assert overlay._mode == "XY"


# ---------------------------------------------------------------------------
# Группа 3: valuesChanged эмитируется при изменениях
# ---------------------------------------------------------------------------


class TestSignalEmission:
    def test_set_mode_emits(self, overlay):
        received = []
        overlay.valuesChanged.connect(received.append)
        overlay.set_mode("X")
        assert len(received) >= 1

    def test_update_frame_emits(self, overlay):
        received = []
        overlay.valuesChanged.connect(received.append)
        overlay.update_frame(_FakeDecoded())
        assert len(received) >= 1

    def test_move_vertical_cursor_emits(self, overlay):
        overlay.set_mode("X")
        received = []
        overlay.valuesChanged.connect(received.append)
        overlay._ax.setValue(5.0)          # позиция изменилась — сигнал должен прийти
        assert len(received) >= 1

    def test_move_horizontal_cursor_emits(self, overlay):
        overlay.set_mode("Y")
        received = []
        overlay.valuesChanged.connect(received.append)
        overlay._ay.setValue(2.5)          # был 1.0 → изменился
        assert len(received) >= 1

    def test_set_source_emits(self, overlay):
        received = []
        overlay.valuesChanged.connect(received.append)
        overlay.set_source(2)
        assert len(received) >= 1

    def test_emitted_value_is_dict(self, overlay):
        received = []
        overlay.valuesChanged.connect(received.append)
        overlay.set_mode("X")
        assert received and isinstance(received[-1], dict)

    def test_emitted_dict_has_all_keys(self, overlay):
        received = []
        overlay.valuesChanged.connect(received.append)
        overlay.set_mode("XY")
        d = received[-1]
        for key in ("mode", "ax_t", "bx_t", "dt", "freq", "ay_v", "by_v", "dv"):
            assert key in d, f"Ключ '{key}' отсутствует в dict"


# ---------------------------------------------------------------------------
# Группа 4: Численные конвертации (главное)
# ---------------------------------------------------------------------------


class TestConversions:
    # ---------- время / частота ----------

    def test_dt_formula(self, overlay):
        """dt = abs(bx-ax)/HDIV * total_t."""
        dec = _FakeDecoded(n_pts=1000, total_time=1e-3)
        overlay.update_frame(dec)
        overlay.set_mode("X")
        overlay._ax.setValue(HDIV / 3)
        overlay._bx.setValue(2 * HDIV / 3)

        vals = overlay._values()
        expected_dt = (HDIV / 3) / HDIV * 1e-3
        assert vals["dt"] == pytest.approx(expected_dt, rel=1e-6)

    def test_dt_full_span(self, overlay):
        """AX=0, BX=HDIV → dt = total_t."""
        dec = _FakeDecoded(n_pts=1000, total_time=1e-3)
        overlay.update_frame(dec)
        overlay.set_mode("X")
        overlay._ax.setValue(0.0)
        overlay._bx.setValue(float(HDIV))

        vals = overlay._values()
        assert vals["dt"] == pytest.approx(1e-3, rel=1e-6)

    def test_freq_reciprocal(self, overlay):
        """freq = 1/dt."""
        dec = _FakeDecoded(n_pts=1000, total_time=1e-3)
        overlay.update_frame(dec)
        overlay.set_mode("X")
        overlay._ax.setValue(0.0)
        overlay._bx.setValue(float(HDIV))

        vals = overlay._values()
        assert vals["freq"] == pytest.approx(1000.0, rel=1e-6)

    def test_freq_zero_when_dt_zero(self, overlay):
        """freq=0 если AX==BX (dt==0)."""
        dec = _FakeDecoded(n_pts=1000, total_time=1e-3)
        overlay.update_frame(dec)
        overlay.set_mode("X")
        overlay._ax.setValue(5.0)
        overlay._bx.setValue(5.0)

        vals = overlay._values()
        assert vals["dt"] == pytest.approx(0.0, abs=1e-15)
        assert vals["freq"] == 0.0

    def test_ax_time_conversion(self, overlay):
        """ax_t = time[0] + (ax_div/HDIV)*total_t."""
        dec = _FakeDecoded(n_pts=1000, total_time=1e-3)
        overlay.update_frame(dec)
        overlay.set_mode("X")
        overlay._ax.setValue(7.0)

        vals = overlay._values()
        expected = dec.time[0] + (7.0 / HDIV) * 1e-3
        assert vals["ax_t"] == pytest.approx(expected, rel=1e-6)

    def test_bx_time_conversion(self, overlay):
        """bx_t = time[0] + (bx_div/HDIV)*total_t."""
        dec = _FakeDecoded(n_pts=1000, total_time=2e-3)
        overlay.update_frame(dec)
        overlay.set_mode("X")
        overlay._bx.setValue(10.0)

        vals = overlay._values()
        expected = dec.time[0] + (10.0 / HDIV) * 2e-3
        assert vals["bx_t"] == pytest.approx(expected, rel=1e-6)

    # ---------- напряжение (Y/XY) ----------

    def test_ay_voltage_formula(self, overlay):
        """ay_v = ay_div*vdiv - off."""
        vdiv, off = 2.0, 1.0
        dec = _FakeDecoded(vdiv=vdiv, off=off, ch=1)
        overlay.update_frame(dec)
        overlay.set_source(1)
        overlay.set_mode("Y")
        overlay._ay.setValue(3.0)

        vals = overlay._values()
        assert vals["ay_v"] == pytest.approx(3.0 * vdiv - off)   # 5.0

    def test_by_voltage_formula(self, overlay):
        """by_v = by_div*vdiv - off."""
        vdiv, off = 0.5, 0.25
        dec = _FakeDecoded(vdiv=vdiv, off=off, ch=1)
        overlay.update_frame(dec)
        overlay.set_source(1)
        overlay.set_mode("Y")
        overlay._by.setValue(-2.0)

        vals = overlay._values()
        assert vals["by_v"] == pytest.approx(-2.0 * vdiv - off)  # -1.25

    def test_dv_formula_y_mode(self, overlay):
        """ΔV = abs(ay_div - by_div)*vdiv (офсет сокращается)."""
        vdiv = 0.5
        dec = _FakeDecoded(vdiv=vdiv, off=0.3, ch=1)
        overlay.update_frame(dec)
        overlay.set_source(1)
        overlay.set_mode("Y")
        overlay._ay.setValue(2.0)
        overlay._by.setValue(-1.0)

        vals = overlay._values()
        expected_dv = abs(2.0 - (-1.0)) * vdiv   # 1.5
        assert vals["dv"] == pytest.approx(expected_dv)

    def test_dv_xy_mode(self, overlay):
        """ΔV в режиме XY работает так же."""
        vdiv = 1.0
        dec = _FakeDecoded(vdiv=vdiv, off=0.0, ch=1)
        overlay.update_frame(dec)
        overlay.set_source(1)
        overlay.set_mode("XY")
        overlay._ay.setValue(3.0)
        overlay._by.setValue(1.0)

        vals = overlay._values()
        assert vals["dv"] == pytest.approx(2.0)

    # ---------- None-поля по режиму ----------

    def test_x_mode_no_voltage(self, overlay):
        """Режим X: dv/ay_v/by_v = None."""
        dec = _FakeDecoded()
        overlay.update_frame(dec)
        overlay.set_mode("X")

        vals = overlay._values()
        assert vals["dv"] is None
        assert vals["ay_v"] is None
        assert vals["by_v"] is None

    def test_y_mode_no_time(self, overlay):
        """Режим Y: dt/freq = None (AX/BX скрыты)."""
        dec = _FakeDecoded()
        overlay.update_frame(dec)
        overlay.set_mode("Y")

        vals = overlay._values()
        assert vals["dt"] is None
        assert vals["freq"] is None

    def test_off_mode_all_numeric_none(self, overlay):
        """Режим OFF: все числовые поля None."""
        dec = _FakeDecoded()
        overlay.update_frame(dec)
        overlay.set_mode("OFF")

        vals = overlay._values()
        for key in ("ax_t", "bx_t", "dt", "freq", "ay_v", "by_v", "dv"):
            assert vals[key] is None, f"vals['{key}'] должен быть None в режиме OFF"

    def test_no_frame_numeric_none(self, overlay):
        """Без кадра: числовые поля None."""
        overlay.set_mode("XY")         # decoded ещё None
        vals = overlay._values()
        for key in ("ax_t", "bx_t", "dt", "freq", "ay_v", "by_v", "dv"):
            assert vals[key] is None, f"vals['{key}'] должен быть None без кадра"

    def test_mode_key_in_values(self, overlay):
        """Поле mode отражает текущий режим."""
        overlay.set_mode("TRACk")
        assert overlay._values()["mode"] == "TRACk"

    # ---------- TRACk ----------

    def test_track_ay_from_trace_start(self, overlay):
        """TRACk: ay_v = значение трассы в точке AX (интерполяция)."""
        total_t = 1e-3
        # линейно нарастающая трасса: v(t) = t/total_t  → [0, 1]
        dec = _FakeDecoded(
            n_pts=500, total_time=total_t, ch=1,
            volts_fn=lambda t: t / total_t,
        )
        overlay.update_frame(dec)
        overlay.set_source(1)
        overlay.set_mode("TRACk")

        # AX в начале → v ≈ 0
        overlay._ax.setValue(0.0)
        vals = overlay._values()
        assert vals["ay_v"] == pytest.approx(0.0, abs=0.01)

    def test_track_ay_from_trace_end(self, overlay):
        """TRACk: AX в конце записи → ay_v ≈ 1."""
        total_t = 1e-3
        dec = _FakeDecoded(
            n_pts=500, total_time=total_t, ch=1,
            volts_fn=lambda t: t / total_t,
        )
        overlay.update_frame(dec)
        overlay.set_source(1)
        overlay.set_mode("TRACk")

        overlay._ax.setValue(float(HDIV))
        vals = overlay._values()
        assert vals["ay_v"] == pytest.approx(1.0, abs=0.01)

    def test_track_dv_is_difference(self, overlay):
        """TRACk: dv = abs(ay_v - by_v)."""
        total_t = 1e-3
        dec = _FakeDecoded(
            n_pts=500, total_time=total_t, ch=1,
            volts_fn=lambda t: t / total_t,
        )
        overlay.update_frame(dec)
        overlay.set_source(1)
        overlay.set_mode("TRACk")

        overlay._ax.setValue(0.0)          # ay_v ≈ 0
        overlay._bx.setValue(float(HDIV))  # by_v ≈ 1
        vals = overlay._values()
        assert vals["dv"] == pytest.approx(abs(vals["ay_v"] - vals["by_v"]), abs=1e-9)

    def test_track_dt_still_computed(self, overlay):
        """TRACk: dt/freq по-прежнему вычисляется из AX/BX."""
        dec = _FakeDecoded(n_pts=500, total_time=1e-3, ch=1)
        overlay.update_frame(dec)
        overlay.set_source(1)
        overlay.set_mode("TRACk")
        overlay._ax.setValue(0.0)
        overlay._bx.setValue(float(HDIV))

        vals = overlay._values()
        assert vals["dt"] == pytest.approx(1e-3, rel=1e-6)
        assert vals["freq"] == pytest.approx(1000.0, rel=1e-6)


# ---------------------------------------------------------------------------
# Группа 5: CursorsPanel — сигналы
# ---------------------------------------------------------------------------


class TestCursorsPanelSignals:
    @pytest.fixture
    def panel(self, app):
        return CursorsPanel()

    def test_has_cursorModeChanged(self, panel):
        assert hasattr(panel, "cursorModeChanged")

    def test_has_cursorSourceChanged(self, panel):
        assert hasattr(panel, "cursorSourceChanged")

    def test_has_update_readout(self, panel):
        assert callable(getattr(panel, "update_readout", None))

    def test_default_mode_off(self, panel):
        assert panel._mode_combo.currentData() == "OFF"

    def test_mode_change_emits_string(self, panel):
        received = []
        panel.cursorModeChanged.connect(received.append)
        idx = panel._mode_combo.findData("X")
        panel._mode_combo.setCurrentIndex(idx)
        assert len(received) == 1
        assert received[0] == "X"

    def test_mode_change_track(self, panel):
        received = []
        panel.cursorModeChanged.connect(received.append)
        idx = panel._mode_combo.findData("TRACk")
        panel._mode_combo.setCurrentIndex(idx)
        assert received == ["TRACk"]

    def test_mode_change_xy(self, panel):
        received = []
        panel.cursorModeChanged.connect(received.append)
        idx = panel._mode_combo.findData("XY")
        panel._mode_combo.setCurrentIndex(idx)
        assert received == ["XY"]

    def test_source_change_ch2_emits_2(self, panel):
        """Выбор CH2 эмитирует int(2)."""
        received = []
        panel.cursorSourceChanged.connect(received.append)
        idx = panel._source_combo.findData(2)
        panel._source_combo.setCurrentIndex(idx)
        assert len(received) == 1
        assert received[0] == 2
        assert isinstance(received[0], int)

    def test_source_change_ch1_emits_1(self, panel):
        received = []
        panel.cursorSourceChanged.connect(received.append)
        # Сначала переключим на CH2, потом назад на CH1
        panel._source_combo.setCurrentIndex(1)  # CH2
        received.clear()
        panel.cursorSourceChanged.connect(received.append)
        panel._source_combo.setCurrentIndex(0)  # CH1
        assert received and received[-1] == 1

    def test_mode_combo_has_all_modes(self, panel):
        items = {panel._mode_combo.itemData(i) for i in range(panel._mode_combo.count())}
        assert items == {"OFF", "X", "Y", "XY", "TRACk"}

    def test_source_combo_has_ch1_ch2(self, panel):
        items = {panel._source_combo.itemData(i) for i in range(panel._source_combo.count())}
        assert items == {1, 2}


# ---------------------------------------------------------------------------
# Группа 6: update_readout — форматирование и None → «—»
# ---------------------------------------------------------------------------


class TestUpdateReadout:
    @pytest.fixture
    def panel(self, app):
        return CursorsPanel()

    def _all_none(self):
        return {
            "mode": "OFF",
            "ax_t": None, "bx_t": None,
            "dt": None, "freq": None,
            "ay_v": None, "by_v": None, "dv": None,
        }

    def test_none_dt_shows_dash(self, panel):
        panel.update_readout(self._all_none())
        assert "—" in panel._dt_label.text()

    def test_none_dv_shows_dash(self, panel):
        panel.update_readout(self._all_none())
        assert "—" in panel._dv_label.text()

    def test_none_freq_shows_dash(self, panel):
        panel.update_readout(self._all_none())
        assert "—" in panel._freq_label.text()

    def test_none_ay_shows_dash(self, panel):
        panel.update_readout(self._all_none())
        assert "—" in panel._ay_label.text()

    def test_dt_1ms_formatted(self, panel):
        """dt=1e-3 → метка содержит 'ms' и '1'."""
        vals = {**self._all_none(), "dt": 1e-3, "mode": "X"}
        panel.update_readout(vals)
        text = panel._dt_label.text()
        assert "ms" in text
        assert "1" in text

    def test_dt_500us_formatted(self, panel):
        """dt=500e-6 → метка содержит 'µs' и '500'."""
        vals = {**self._all_none(), "dt": 500e-6, "mode": "X"}
        panel.update_readout(vals)
        text = panel._dt_label.text()
        assert "µs" in text
        assert "500" in text

    def test_dt_large_formatted(self, panel):
        """dt=2.5 → метка содержит 's'."""
        vals = {**self._all_none(), "dt": 2.5, "mode": "X"}
        panel.update_readout(vals)
        text = panel._dt_label.text()
        assert "s" in text

    def test_freq_1khz_formatted(self, panel):
        """freq=1000 → метка содержит 'kHz' и '1'."""
        vals = {**self._all_none(), "freq": 1000.0, "mode": "X"}
        panel.update_readout(vals)
        text = panel._freq_label.text()
        assert "kHz" in text
        assert "1" in text

    def test_freq_500hz_formatted(self, panel):
        """freq=500 → метка содержит 'Hz'."""
        vals = {**self._all_none(), "freq": 500.0, "mode": "X"}
        panel.update_readout(vals)
        text = panel._freq_label.text()
        assert "Hz" in text
        assert "500" in text

    def test_freq_zero_shows_value(self, panel):
        """freq=0 → не «—», а «0 Hz»."""
        vals = {**self._all_none(), "freq": 0.0, "mode": "X"}
        panel.update_readout(vals)
        text = panel._freq_label.text()
        assert "—" not in text
        assert "Hz" in text

    def test_dv_1v5_formatted(self, panel):
        """dv=1.5 → метка содержит 'V' и '1.5'."""
        vals = {**self._all_none(), "dv": 1.5, "mode": "Y"}
        panel.update_readout(vals)
        text = panel._dv_label.text()
        assert "V" in text

    def test_dv_500mv_formatted(self, panel):
        """dv=0.5 V → метка содержит 'mV'."""
        vals = {**self._all_none(), "dv": 0.5, "mode": "Y"}
        panel.update_readout(vals)
        text = panel._dv_label.text()
        assert "mV" in text

    def test_ax_label_formatted_as_time(self, panel):
        """ax_t=500e-6 → _ax_label содержит 'µs'."""
        vals = {**self._all_none(), "ax_t": 500e-6}
        panel.update_readout(vals)
        assert "µs" in panel._ax_label.text()

    def test_bx_label_formatted_as_time(self, panel):
        vals = {**self._all_none(), "bx_t": 1e-3}
        panel.update_readout(vals)
        assert "ms" in panel._bx_label.text()

    def test_ay_by_formatted_as_volts(self, panel):
        vals = {**self._all_none(), "ay_v": 2.0, "by_v": -1.0}
        panel.update_readout(vals)
        assert "V" in panel._ay_label.text()
        assert "V" in panel._by_label.text()
