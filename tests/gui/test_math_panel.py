"""Headless-тесты панели MathPanel.

QT_QPA_PLATFORM=offscreen гарантирует безголовый режим.
Запуск: .venv/Scripts/python.exe -m pytest tests/gui/test_math_panel.py -q
"""
from __future__ import annotations

import os
import sys

import pytest

# Безголовый Qt — до создания QApplication
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402
from PySide6.QtCore import QCoreApplication  # noqa: E402

from hantek_dso2d15.gui.panels.math import MathPanel  # noqa: E402


# ---------------------------------------------------------------------------
# Одно приложение на весь модуль
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
# Фикстура панели (function-scope: каждый тест получает чистую панель)
# ---------------------------------------------------------------------------

@pytest.fixture
def panel(app):
    return MathPanel()


# ---------------------------------------------------------------------------
# Тест 1: дефолты и отсутствие эмиссии при создании
# ---------------------------------------------------------------------------

class TestDefaults:
    def test_no_emission_on_init(self, app) -> None:
        """__init__ не должен эмитировать mathConfigChanged ни синхронно,
        ни через отложенные события."""
        received: list = []
        p = MathPanel()
        p.mathConfigChanged.connect(lambda cfg: received.append(cfg))
        # Обработаем отложенные Qt-события
        QApplication.processEvents()
        assert received == [], f"__init__ эмитировал {len(received)} раз(а)"

    def test_default_display_false(self, panel) -> None:
        assert panel.config()["display"] is False

    def test_default_operator_add(self, panel) -> None:
        assert panel.config()["operator"] == "ADD"

    def test_default_source1_ch1(self, panel) -> None:
        assert panel.config()["source1"] == 1

    def test_default_source2_ch2(self, panel) -> None:
        assert panel.config()["source2"] == 2

    def test_default_scale_1(self, panel) -> None:
        assert panel.config()["scale"] == pytest.approx(1.0)

    def test_default_offset_0(self, panel) -> None:
        assert panel.config()["offset"] == pytest.approx(0.0)

    def test_default_fft_source_ch1(self, panel) -> None:
        assert panel.config()["fft_source"] == 1

    def test_default_fft_window_hanning(self, panel) -> None:
        assert panel.config()["fft_window"] == "HANNing"

    def test_default_fft_unit_vrms(self, panel) -> None:
        assert panel.config()["fft_unit"] == "VRMS"


# ---------------------------------------------------------------------------
# Тест 2: config() содержит все обязательные ключи
# ---------------------------------------------------------------------------

class TestConfigKeys:
    _REQUIRED = frozenset({
        "display", "operator", "source1", "source2",
        "scale", "offset", "fft_source", "fft_window", "fft_unit",
    })

    def test_config_has_all_keys(self, panel) -> None:
        cfg = panel.config()
        missing = self._REQUIRED - set(cfg.keys())
        assert not missing, f"Отсутствующие ключи config(): {missing}"

    def test_config_display_is_bool(self, panel) -> None:
        assert isinstance(panel.config()["display"], bool)

    def test_config_operator_is_str(self, panel) -> None:
        assert isinstance(panel.config()["operator"], str)

    def test_config_source1_is_int(self, panel) -> None:
        assert isinstance(panel.config()["source1"], int)

    def test_config_source2_is_int(self, panel) -> None:
        assert isinstance(panel.config()["source2"], int)

    def test_config_scale_is_float(self, panel) -> None:
        assert isinstance(panel.config()["scale"], float)

    def test_config_fft_source_is_int(self, panel) -> None:
        assert isinstance(panel.config()["fft_source"], int)

    def test_config_fft_window_is_str(self, panel) -> None:
        assert isinstance(panel.config()["fft_window"], str)

    def test_config_fft_unit_is_str(self, panel) -> None:
        assert isinstance(panel.config()["fft_unit"], str)


# ---------------------------------------------------------------------------
# Тест 3: смена контрола → mathConfigChanged с обновлённым словарём
# ---------------------------------------------------------------------------

class TestSignalEmission:
    def test_display_check_emits(self, panel) -> None:
        """Включение checkbox → mathConfigChanged."""
        received: list = []
        panel.mathConfigChanged.connect(lambda cfg: received.append(cfg))
        panel._display.setChecked(True)
        assert len(received) >= 1, "setChecked(True) не эмитировал mathConfigChanged"

    def test_display_config_updated(self, panel) -> None:
        """Конфиг в сигнале содержит display=True после включения."""
        received: list = []
        panel.mathConfigChanged.connect(lambda cfg: received.append(cfg))
        panel._display.setChecked(True)
        assert received, "Сигнал не был эмитирован"
        assert received[-1]["display"] is True

    def test_operator_change_emits(self, panel) -> None:
        """Смена оператора → mathConfigChanged."""
        received: list = []
        panel.mathConfigChanged.connect(lambda cfg: received.append(cfg))
        idx = panel._operator.findData("SUBtract")
        panel._operator.setCurrentIndex(idx)
        assert len(received) >= 1, "Смена оператора не эмитировала сигнал"

    def test_operator_config_updated(self, panel) -> None:
        """Конфиг содержит выбранный оператор."""
        panel._operator.setCurrentIndex(panel._operator.findData("ADD"))  # сброс
        received: list = []
        panel.mathConfigChanged.connect(lambda cfg: received.append(cfg))
        panel._operator.setCurrentIndex(panel._operator.findData("FFT"))
        assert received, "Сигнал не был эмитирован"
        assert received[-1]["operator"] == "FFT"

    def test_source1_change_emits(self, panel) -> None:
        received: list = []
        panel.mathConfigChanged.connect(lambda cfg: received.append(cfg))
        panel._source1.setCurrentIndex(1)  # CH2
        assert len(received) >= 1

    def test_source2_change_emits(self, panel) -> None:
        received: list = []
        panel.mathConfigChanged.connect(lambda cfg: received.append(cfg))
        panel._source2.setCurrentIndex(0)  # вернуть к CH1
        assert len(received) >= 1

    def test_fft_window_change_emits(self, panel) -> None:
        received: list = []
        panel.mathConfigChanged.connect(lambda cfg: received.append(cfg))
        panel._fft_window.setCurrentIndex(panel._fft_window.findData("HAMMing"))
        assert len(received) >= 1

    def test_fft_window_config_updated(self, panel) -> None:
        """Конфиг содержит новое окно после смены."""
        panel._fft_window.setCurrentIndex(panel._fft_window.findData("HANNing"))  # сброс
        received: list = []
        panel.mathConfigChanged.connect(lambda cfg: received.append(cfg))
        panel._fft_window.setCurrentIndex(panel._fft_window.findData("BLACkman"))
        assert received, "Сигнал не был эмитирован"
        assert received[-1]["fft_window"] == "BLACkman"

    def test_fft_unit_change_emits(self, panel) -> None:
        received: list = []
        panel.mathConfigChanged.connect(lambda cfg: received.append(cfg))
        panel._fft_unit.setCurrentIndex(panel._fft_unit.findData("DB"))
        assert len(received) >= 1

    def test_emitted_config_has_all_required_keys(self, panel) -> None:
        """Сигнал несёт словарь со всеми обязательными ключами."""
        required = {
            "display", "operator", "source1", "source2",
            "scale", "offset", "fft_source", "fft_window", "fft_unit",
        }
        received: list = []
        panel.mathConfigChanged.connect(lambda cfg: received.append(cfg))
        panel._display.setChecked(not panel._display.isChecked())
        assert received, "Сигнал не был эмитирован"
        missing = required - set(received[-1].keys())
        assert not missing, f"В сигнале отсутствуют ключи: {missing}"


# ---------------------------------------------------------------------------
# Тест 4: структура виджета
# ---------------------------------------------------------------------------

class TestPanelStructure:
    def test_has_math_config_changed_signal(self, panel) -> None:
        assert hasattr(panel, "mathConfigChanged")

    def test_has_config_method(self, panel) -> None:
        assert callable(getattr(panel, "config", None))

    def test_operator_combo_has_all_ops(self, panel) -> None:
        items = {panel._operator.itemData(i) for i in range(panel._operator.count())}
        assert items == {"ADD", "SUBtract", "MULTiply", "DIVision", "FFT"}

    def test_source1_combo_has_ch1_ch2(self, panel) -> None:
        items = {panel._source1.itemData(i) for i in range(panel._source1.count())}
        assert items == {1, 2}

    def test_source2_combo_has_ch1_ch2(self, panel) -> None:
        items = {panel._source2.itemData(i) for i in range(panel._source2.count())}
        assert items == {1, 2}

    def test_fft_source_combo_has_ch1_ch2(self, panel) -> None:
        items = {panel._fft_source.itemData(i) for i in range(panel._fft_source.count())}
        assert items == {1, 2}

    def test_fft_window_combo_has_6_windows(self, panel) -> None:
        items = {panel._fft_window.itemData(i) for i in range(panel._fft_window.count())}
        assert items == {"RECTangle", "HANNing", "HAMMing", "BLACkman", "TRIangle", "FLATtop"}

    def test_fft_unit_combo_has_vrms_and_db(self, panel) -> None:
        items = {panel._fft_unit.itemData(i) for i in range(panel._fft_unit.count())}
        assert items == {"VRMS", "DB"}
