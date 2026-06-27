"""Headless-тесты панели SweepPanel (Sweep / Multi-capture).

QT_QPA_PLATFORM=offscreen задаётся в tests/conftest.py (session-scope).
Запуск: .venv\\Scripts\\python.exe -m pytest tests/gui/test_sweep_panel.py -q
"""
from __future__ import annotations

import pytest

from hantek_dso2d15.gui.panels.sweep import SweepPanel


# ---------------------------------------------------------------------------
# Фикстура панели (function-scope — каждый тест получает свежую панель)
# ---------------------------------------------------------------------------

@pytest.fixture
def panel():
    return SweepPanel()


# ---------------------------------------------------------------------------
# TestStructure — статическая структура виджета
# ---------------------------------------------------------------------------

class TestStructure:
    def test_has_startRequested_signal(self, panel):
        assert hasattr(panel, "startRequested")

    def test_has_stopRequested_signal(self, panel):
        assert hasattr(panel, "stopRequested")

    def test_has_folderRequested_signal(self, panel):
        assert hasattr(panel, "folderRequested")

    def test_has_config_method(self, panel):
        assert callable(getattr(panel, "config", None))

    def test_has_set_folder_method(self, panel):
        assert callable(getattr(panel, "set_folder", None))

    def test_has_set_progress_method(self, panel):
        assert callable(getattr(panel, "set_progress", None))

    def test_has_set_running_method(self, panel):
        assert callable(getattr(panel, "set_running", None))

    def test_parameter_combo_has_dds_freq(self, panel):
        data = {panel._parameter.itemData(i) for i in range(panel._parameter.count())}
        assert "dds.freq" in data

    def test_parameter_combo_has_dds_amplitude(self, panel):
        data = {panel._parameter.itemData(i) for i in range(panel._parameter.count())}
        assert "dds.amplitude" in data

    def test_fmt_combo_has_csv_npy_hdf5(self, panel):
        data = {panel._fmt.itemData(i) for i in range(panel._fmt.count())}
        assert data == {"CSV", "NPY", "HDF5"}

    def test_fmt_default_is_csv(self, panel):
        assert panel._fmt.currentData() == "CSV"

    def test_dwell_ms_default_is_200(self, panel):
        assert panel._dwell_ms.value() == pytest.approx(200.0)

    def test_btn_stop_disabled_by_default(self, panel):
        assert not panel._btn_stop.isEnabled()

    def test_btn_start_enabled_by_default(self, panel):
        assert panel._btn_start.isEnabled()


# ---------------------------------------------------------------------------
# TestConfig — метод config() возвращает правильную структуру
# ---------------------------------------------------------------------------

class TestConfig:
    def test_config_has_all_keys(self, panel):
        cfg = panel.config()
        for key in ("parameter", "start", "stop", "step", "dwell_s", "fmt", "folder"):
            assert key in cfg, f"Отсутствует ключ '{key}' в config()"

    def test_config_parameter_is_string(self, panel):
        cfg = panel.config()
        assert isinstance(cfg["parameter"], str)

    def test_config_parameter_default_is_dds_freq(self, panel):
        """По умолчанию первый пункт — dds.freq."""
        cfg = panel.config()
        assert cfg["parameter"] == "dds.freq"

    def test_config_start_is_float(self, panel):
        cfg = panel.config()
        assert isinstance(cfg["start"], float)

    def test_config_stop_is_float(self, panel):
        cfg = panel.config()
        assert isinstance(cfg["stop"], float)

    def test_config_step_is_float(self, panel):
        cfg = panel.config()
        assert isinstance(cfg["step"], float)

    def test_config_dwell_s_is_float(self, panel):
        cfg = panel.config()
        assert isinstance(cfg["dwell_s"], float)

    def test_config_dwell_s_equals_dwell_ms_divided_by_1000(self, panel):
        """dwell_s = dwell_ms / 1000 (с дефолтом 200 мс -> 0.2 с)."""
        panel._dwell_ms.setValue(500.0)
        cfg = panel.config()
        assert cfg["dwell_s"] == pytest.approx(0.5)

    def test_config_fmt_is_string(self, panel):
        cfg = panel.config()
        assert isinstance(cfg["fmt"], str)

    def test_config_folder_is_string(self, panel):
        cfg = panel.config()
        assert isinstance(cfg["folder"], str)

    def test_config_reflects_current_parameter(self, panel):
        """config() отдаёт текущий параметр, если изменить комбо."""
        idx = panel._parameter.findData("dds.amplitude")
        panel._parameter.setCurrentIndex(idx)
        cfg = panel.config()
        assert cfg["parameter"] == "dds.amplitude"


# ---------------------------------------------------------------------------
# TestStartSignal — btn_start эмитит startRequested(config_dict)
# ---------------------------------------------------------------------------

class TestStartSignal:
    def test_btn_start_emits_startRequested(self, panel):
        received = []
        panel.startRequested.connect(lambda cfg: received.append(cfg))

        panel._btn_start.click()

        assert len(received) == 1, f"Ожидался 1 сигнал startRequested, получено {len(received)}"

    def test_startRequested_payload_is_dict(self, panel):
        received = []
        panel.startRequested.connect(lambda cfg: received.append(cfg))

        panel._btn_start.click()

        assert isinstance(received[0], dict), "Payload startRequested должен быть dict"

    def test_startRequested_payload_has_all_keys(self, panel):
        received = []
        panel.startRequested.connect(lambda cfg: received.append(cfg))

        panel._btn_start.click()

        cfg = received[0]
        for key in ("parameter", "start", "stop", "step", "dwell_s", "fmt", "folder"):
            assert key in cfg, f"Ключ '{key}' отсутствует в payload startRequested"

    def test_startRequested_dwell_s_is_dwell_ms_over_1000(self, panel):
        """Payload содержит dwell_s как dwell_ms / 1000."""
        panel._dwell_ms.setValue(400.0)

        received = []
        panel.startRequested.connect(lambda cfg: received.append(cfg))
        panel._btn_start.click()

        assert received[0]["dwell_s"] == pytest.approx(0.4)

    def test_startRequested_parameter_is_dds_freq_by_default(self, panel):
        received = []
        panel.startRequested.connect(lambda cfg: received.append(cfg))
        panel._btn_start.click()
        assert received[0]["parameter"] == "dds.freq"

    def test_startRequested_payload_matches_config(self, panel):
        """Payload startRequested совпадает с config()."""
        panel._dwell_ms.setValue(300.0)
        panel.set_folder("/tmp/sweep_out")

        expected = panel.config()

        received = []
        panel.startRequested.connect(lambda cfg: received.append(cfg))
        panel._btn_start.click()

        assert received[0] == expected


# ---------------------------------------------------------------------------
# TestStopSignal — btn_stop эмитит stopRequested
# ---------------------------------------------------------------------------

class TestStopSignal:
    def test_btn_stop_emits_stopRequested_when_enabled(self, panel):
        # Включим кнопку вручную (обычно через set_running(True))
        panel._btn_stop.setEnabled(True)

        received = []
        panel.stopRequested.connect(lambda: received.append(True))

        panel._btn_stop.click()

        assert len(received) == 1, "btn_stop должна эмитировать stopRequested"

    def test_btn_stop_emits_via_set_running(self, panel):
        received = []
        panel.stopRequested.connect(lambda: received.append(True))

        panel.set_running(True)
        panel._btn_stop.click()

        assert len(received) == 1


# ---------------------------------------------------------------------------
# TestFolderSignal — кнопка «…» эмитит folderRequested
# ---------------------------------------------------------------------------

class TestFolderSignal:
    def test_folder_button_emits_folderRequested(self, panel):
        received = []
        panel.folderRequested.connect(lambda: received.append(True))

        panel._btn_folder.click()

        assert len(received) == 1, "Кнопка '…' должна эмитировать folderRequested"

    def test_folder_button_no_dialog(self, panel):
        """Клик кнопки папки НЕ открывает QFileDialog (проверка по отсутствию исключений
        в headless-режиме offscreen — если бы диалог открывался, тест завис бы)."""
        received = []
        panel.folderRequested.connect(lambda: received.append(True))
        # Если диалог открывается — тест зависнет; он должен вернуться мгновенно
        panel._btn_folder.click()
        assert len(received) == 1


# ---------------------------------------------------------------------------
# TestSetFolder — set_folder выставляет текст поля без эмиссии
# ---------------------------------------------------------------------------

class TestSetFolder:
    def test_set_folder_sets_text(self, panel):
        panel.set_folder("/home/user/sweep_data")
        assert panel._folder_edit.text() == "/home/user/sweep_data"

    def test_set_folder_empty_string(self, panel):
        panel.set_folder("")
        assert panel._folder_edit.text() == ""

    def test_set_folder_does_not_emit_signals(self, panel):
        """set_folder не должен эмитировать никаких сигналов."""
        received_start = []
        received_stop = []
        received_folder = []
        panel.startRequested.connect(lambda c: received_start.append(c))
        panel.stopRequested.connect(lambda: received_stop.append(True))
        panel.folderRequested.connect(lambda: received_folder.append(True))

        panel.set_folder("/some/path")

        assert received_start == []
        assert received_stop == []
        assert received_folder == []


# ---------------------------------------------------------------------------
# TestSetProgress — set_progress обновляет бар и лейбл
# ---------------------------------------------------------------------------

class TestSetProgress:
    def test_set_progress_updates_bar(self, panel):
        panel.set_progress(42, 100)
        assert panel._progress_bar.value() == 42

    def test_set_progress_updates_label(self, panel):
        panel.set_progress(42, 100)
        assert "42" in panel._progress_label.text()
        assert "100" in panel._progress_label.text()

    def test_set_progress_label_format(self, panel):
        panel.set_progress(7, 50)
        text = panel._progress_label.text()
        assert "7" in text and "50" in text

    def test_set_progress_zero_total_bar_is_zero(self, panel):
        panel.set_progress(0, 0)
        assert panel._progress_bar.value() == 0

    def test_set_progress_done_equals_total(self, panel):
        panel.set_progress(100, 100)
        assert panel._progress_bar.value() == 100

    def test_set_progress_partial(self, panel):
        panel.set_progress(1, 4)
        assert panel._progress_bar.value() == 25

    def test_set_progress_label_contains_прогресс(self, panel):
        panel.set_progress(3, 10)
        text = panel._progress_label.text()
        assert "Прогресс" in text or "прогресс" in text.lower()


# ---------------------------------------------------------------------------
# TestSetRunning — set_running управляет доступностью контролов
# ---------------------------------------------------------------------------

class TestSetRunning:
    def test_set_running_true_disables_start(self, panel):
        panel.set_running(True)
        assert not panel._btn_start.isEnabled()

    def test_set_running_true_enables_stop(self, panel):
        panel.set_running(True)
        assert panel._btn_stop.isEnabled()

    def test_set_running_true_disables_parameter(self, panel):
        panel.set_running(True)
        assert not panel._parameter.isEnabled()

    def test_set_running_true_disables_start_spinbox(self, panel):
        panel.set_running(True)
        assert not panel._start.isEnabled()

    def test_set_running_true_disables_stop_spinbox(self, panel):
        panel.set_running(True)
        assert not panel._stop.isEnabled()

    def test_set_running_true_disables_step_spinbox(self, panel):
        panel.set_running(True)
        assert not panel._step.isEnabled()

    def test_set_running_true_disables_dwell(self, panel):
        panel.set_running(True)
        assert not panel._dwell_ms.isEnabled()

    def test_set_running_true_disables_fmt(self, panel):
        panel.set_running(True)
        assert not panel._fmt.isEnabled()

    def test_set_running_false_enables_start(self, panel):
        panel.set_running(True)
        panel.set_running(False)
        assert panel._btn_start.isEnabled()

    def test_set_running_false_disables_stop(self, panel):
        panel.set_running(True)
        panel.set_running(False)
        assert not panel._btn_stop.isEnabled()

    def test_set_running_false_enables_parameter(self, panel):
        panel.set_running(True)
        panel.set_running(False)
        assert panel._parameter.isEnabled()

    def test_set_running_false_enables_start_spinbox(self, panel):
        panel.set_running(True)
        panel.set_running(False)
        assert panel._start.isEnabled()

    def test_set_running_false_enables_fmt(self, panel):
        panel.set_running(True)
        panel.set_running(False)
        assert panel._fmt.isEnabled()


# ---------------------------------------------------------------------------
# TestNoEmitOnControlChange — смена контролов НЕ эмитит ничего
# ---------------------------------------------------------------------------

class TestNoEmitOnControlChange:
    def _collect(self, panel):
        received = []
        panel.startRequested.connect(lambda c: received.append(("start", c)))
        panel.stopRequested.connect(lambda: received.append(("stop",)))
        panel.folderRequested.connect(lambda: received.append(("folder",)))
        return received

    def test_changing_parameter_combo_no_emit(self, panel):
        received = self._collect(panel)
        idx = panel._parameter.findData("dds.amplitude")
        panel._parameter.setCurrentIndex(idx)
        assert received == []

    def test_changing_fmt_combo_no_emit(self, panel):
        received = self._collect(panel)
        idx = panel._fmt.findData("HDF5")
        panel._fmt.setCurrentIndex(idx)
        assert received == []

    def test_typing_in_folder_edit_no_emit(self, panel):
        received = self._collect(panel)
        panel._folder_edit.setText("/some/path")
        assert received == []
