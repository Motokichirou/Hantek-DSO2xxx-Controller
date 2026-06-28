"""Headless-тесты панели GeneratorPanel (DDS-генератор).

QT_QPA_PLATFORM=offscreen гарантирует безголовый режим (задаётся в conftest).
Запуск: .venv\\Scripts\\python.exe -m pytest tests/gui/test_generator_panel.py -q
"""
from __future__ import annotations

import types

import pytest

from hantek_dso2d15.gui.panels.generator import GeneratorPanel


# ---------------------------------------------------------------------------
# Фейк-scope
# ---------------------------------------------------------------------------

def _make_scope(**overrides):
    """Фейк-объект scope с атрибутом .dds, несущим все нужные поля."""
    dds = types.SimpleNamespace(
        output=False,
        type="SINE",
        freq=1000.0,
        amplitude=1.0,
        offset=0.0,
        duty=50.0,
        mod_enable=False,
        mod_type="AM",
        mod_wave="SINE",
        mod_freq=100.0,
        mod_depth=50.0,
        burst_enable=False,
        burst_type="N_CYCLE",
        burst_count=1,
    )
    for k, v in overrides.items():
        setattr(dds, k, v)
    return types.SimpleNamespace(dds=dds)


# ---------------------------------------------------------------------------
# Фикстура панели (function-scope — каждый тест получает свежую панель)
# ---------------------------------------------------------------------------

@pytest.fixture
def panel():
    return GeneratorPanel()


# ---------------------------------------------------------------------------
# TestStructure — статическая структура виджета
# ---------------------------------------------------------------------------

class TestStructure:
    def test_has_settingChanged(self, panel):
        assert hasattr(panel, "settingChanged")

    def test_has_load_from_scope(self, panel):
        assert callable(getattr(panel, "load_from_scope", None))

    def test_type_combo_has_all_literals(self, panel):
        data = set(panel._type._button_map.keys())
        assert data == set(GeneratorPanel.TYPES)

    def test_mod_type_combo_has_all_literals(self, panel):
        data = {panel._mod_type.itemData(i) for i in range(panel._mod_type.count())}
        assert data == set(GeneratorPanel.MOD_TYPES)

    def test_mod_wave_combo_has_all_literals(self, panel):
        data = {panel._mod_wave.itemData(i) for i in range(panel._mod_wave.count())}
        assert data == set(GeneratorPanel.MOD_WAVES)

    def test_burst_type_combo_has_all_literals(self, panel):
        data = {panel._burst_type.itemData(i) for i in range(panel._burst_type.count())}
        assert data == set(GeneratorPanel.BURST_TYPES)

    def test_freq_range_min(self, panel):
        assert panel._freq.minimum() == pytest.approx(1.0)

    def test_freq_range_max(self, panel):
        assert panel._freq.maximum() == pytest.approx(25e6)

    def test_amplitude_range(self, panel):
        assert panel._amplitude.minimum() == pytest.approx(0.001)
        assert panel._amplitude.maximum() == pytest.approx(7.0)

    def test_offset_range(self, panel):
        assert panel._offset.minimum() == pytest.approx(-2.5)
        assert panel._offset.maximum() == pytest.approx(2.5)

    def test_duty_range(self, panel):
        assert panel._duty.minimum() == pytest.approx(0.0)
        assert panel._duty.maximum() == pytest.approx(99.0)

    def test_burst_count_range(self, panel):
        assert panel._burst_count.minimum() == 1
        assert panel._burst_count.maximum() == 1_000_000


# ---------------------------------------------------------------------------
# TestLoadFromScope — загрузка из scope
# ---------------------------------------------------------------------------

class TestLoadFromScope:
    def test_does_not_emit_settingChanged(self, panel):
        """load_from_scope не должен эмитировать settingChanged."""
        received = []
        panel.settingChanged.connect(lambda p, v: received.append((p, v)))
        panel.load_from_scope(_make_scope())
        assert received == [], f"load_from_scope эмитировал: {received}"

    def test_sets_output_true(self, panel):
        panel.load_from_scope(_make_scope(output=True))
        assert panel._output.isChecked() is True

    def test_sets_output_false(self, panel):
        panel.load_from_scope(_make_scope(output=False))
        assert panel._output.isChecked() is False

    def test_sets_type(self, panel):
        panel.load_from_scope(_make_scope(type="SQUAre"))
        assert panel._type.value() == "SQUAre"

    def test_sets_freq(self, panel):
        panel.load_from_scope(_make_scope(freq=5000.0))
        assert panel._freq.value() == pytest.approx(5000.0)

    def test_sets_amplitude(self, panel):
        panel.load_from_scope(_make_scope(amplitude=2.5))
        assert panel._amplitude.value() == pytest.approx(2.5)

    def test_sets_offset(self, panel):
        panel.load_from_scope(_make_scope(offset=-1.2))
        assert panel._offset.value() == pytest.approx(-1.2)

    def test_sets_duty(self, panel):
        panel.load_from_scope(_make_scope(duty=30.0))
        assert panel._duty.value() == pytest.approx(30.0)

    def test_sets_mod_enable(self, panel):
        panel.load_from_scope(_make_scope(mod_enable=True))
        assert panel._mod_enable.isChecked() is True

    def test_sets_mod_type(self, panel):
        panel.load_from_scope(_make_scope(mod_type="FM"))
        assert panel._mod_type.currentData() == "FM"

    def test_sets_mod_wave(self, panel):
        panel.load_from_scope(_make_scope(mod_wave="RAMP"))
        assert panel._mod_wave.currentData() == "RAMP"

    def test_sets_mod_freq(self, panel):
        panel.load_from_scope(_make_scope(mod_freq=500.0))
        assert panel._mod_freq.value() == pytest.approx(500.0)

    def test_sets_mod_depth(self, panel):
        panel.load_from_scope(_make_scope(mod_depth=75.0))
        assert panel._mod_depth.value() == pytest.approx(75.0)

    def test_sets_burst_enable(self, panel):
        panel.load_from_scope(_make_scope(burst_enable=True))
        assert panel._burst_enable.isChecked() is True

    def test_sets_burst_type(self, panel):
        panel.load_from_scope(_make_scope(burst_type="INFInit"))
        assert panel._burst_type.currentData() == "INFInit"

    def test_sets_burst_count(self, panel):
        panel.load_from_scope(_make_scope(burst_count=100))
        assert panel._burst_count.value() == 100


# ---------------------------------------------------------------------------
# TestOutputSignal — чекбокс Выход ON
# ---------------------------------------------------------------------------

class TestOutputSignal:
    def test_output_check_emits_true(self, panel):
        panel.load_from_scope(_make_scope(output=False))
        received = []
        panel.settingChanged.connect(lambda p, v: received.append((p, v)))
        panel._output.setChecked(True)
        assert len(received) == 1
        assert received[0] == ("dds.output", True)

    def test_output_uncheck_emits_false(self, panel):
        panel.load_from_scope(_make_scope(output=True))
        received = []
        panel.settingChanged.connect(lambda p, v: received.append((p, v)))
        panel._output.setChecked(False)
        assert len(received) == 1
        assert received[0] == ("dds.output", False)

    def test_output_value_is_bool(self, panel):
        panel.load_from_scope(_make_scope(output=False))
        received = []
        panel.settingChanged.connect(lambda p, v: received.append((p, v)))
        panel._output.setChecked(True)
        assert isinstance(received[0][1], bool)


# ---------------------------------------------------------------------------
# TestTypeSignal — комбо тип волны
# ---------------------------------------------------------------------------

class TestTypeSignal:
    def test_change_type_emits_literal(self, panel):
        panel.load_from_scope(_make_scope(type="SINE"))
        received = []
        panel.settingChanged.connect(lambda p, v: received.append((p, v)))
        panel._type._button_map["SQUAre"].click()
        assert len(received) == 1
        assert received[0] == ("dds.type", "SQUAre")

    def test_type_value_is_string(self, panel):
        panel.load_from_scope(_make_scope(type="SINE"))
        received = []
        panel.settingChanged.connect(lambda p, v: received.append((p, v)))
        panel._type._button_map["RAMP"].click()
        assert received and isinstance(received[0][1], str)

    def test_change_type_all_literals(self, panel):
        """Все 10 типов правильно эмитируются кликом по плитке."""
        for literal in GeneratorPanel.TYPES:
            other = "RAMP" if literal != "RAMP" else "SINE"
            panel.load_from_scope(_make_scope(type=other))
            received = []
            panel.settingChanged.connect(lambda p, v, r=received: r.append((p, v)))
            panel._type._button_map[literal].click()
            panel.settingChanged.disconnect()
            assert received and received[0][1] == literal, (
                f"Ожидался литерал {literal!r}, получили {received}"
            )


# ---------------------------------------------------------------------------
# TestFreqSignal — spinbox частоты (editingFinished)
# ---------------------------------------------------------------------------

class TestFreqSignal:
    def test_freq_emits_on_editing_finished(self, panel):
        panel.load_from_scope(_make_scope(freq=1000.0))
        received = []
        panel.settingChanged.connect(lambda p, v: received.append((p, v)))
        panel._freq.setValue(5000.0)
        panel._freq.editingFinished.emit()
        assert len(received) == 1
        assert received[0][0] == "dds.freq"
        assert received[0][1] == pytest.approx(5000.0)
        assert isinstance(received[0][1], float)

    def test_freq_no_emit_from_setValue_alone(self, panel):
        """setValue без editingFinished не должен эмитировать."""
        panel.load_from_scope(_make_scope(freq=1000.0))
        received = []
        panel.settingChanged.connect(lambda p, v: received.append((p, v)))
        # blockSignals на spinbox — чтобы editingFinished не выстрелил автоматически
        panel._freq.blockSignals(True)
        panel._freq.setValue(9999.0)
        panel._freq.blockSignals(False)
        assert received == []


# ---------------------------------------------------------------------------
# TestAmplitudeSignal
# ---------------------------------------------------------------------------

class TestAmplitudeSignal:
    def test_amplitude_emits_float(self, panel):
        panel.load_from_scope(_make_scope(amplitude=1.0))
        received = []
        panel.settingChanged.connect(lambda p, v: received.append((p, v)))
        panel._amplitude.setValue(3.5)
        panel._amplitude.editingFinished.emit()
        assert len(received) == 1
        assert received[0] == ("dds.amplitude", pytest.approx(3.5))
        assert isinstance(received[0][1], float)


# ---------------------------------------------------------------------------
# TestOffsetSignal
# ---------------------------------------------------------------------------

class TestOffsetSignal:
    def test_offset_emits_float(self, panel):
        panel.load_from_scope(_make_scope(offset=0.0))
        received = []
        panel.settingChanged.connect(lambda p, v: received.append((p, v)))
        panel._offset.setValue(-1.5)
        panel._offset.editingFinished.emit()
        assert len(received) == 1
        assert received[0] == ("dds.offset", pytest.approx(-1.5))
        assert isinstance(received[0][1], float)


# ---------------------------------------------------------------------------
# TestDutySignal
# ---------------------------------------------------------------------------

class TestDutySignal:
    def test_duty_emits_float(self, panel):
        panel.load_from_scope(_make_scope(duty=50.0))
        received = []
        panel.settingChanged.connect(lambda p, v: received.append((p, v)))
        panel._duty.setValue(25.0)
        panel._duty.editingFinished.emit()
        assert len(received) == 1
        assert received[0] == ("dds.duty", pytest.approx(25.0))
        assert isinstance(received[0][1], float)


# ---------------------------------------------------------------------------
# TestModSignals — подгруппа модуляции
# ---------------------------------------------------------------------------

class TestModSignals:
    def test_mod_enable_emits_bool(self, panel):
        panel.load_from_scope(_make_scope(mod_enable=False))
        received = []
        panel.settingChanged.connect(lambda p, v: received.append((p, v)))
        panel._mod_enable.setChecked(True)
        assert len(received) == 1
        assert received[0] == ("dds.mod_enable", True)
        assert isinstance(received[0][1], bool)

    def test_mod_type_emits_literal_fm(self, panel):
        panel.load_from_scope(_make_scope(mod_type="AM"))
        received = []
        panel.settingChanged.connect(lambda p, v: received.append((p, v)))
        panel._mod_type.setCurrentIndex(panel._mod_type.findData("FM"))
        assert len(received) == 1
        assert received[0] == ("dds.mod_type", "FM")

    def test_mod_type_emits_literal_am(self, panel):
        panel.load_from_scope(_make_scope(mod_type="FM"))
        received = []
        panel.settingChanged.connect(lambda p, v: received.append((p, v)))
        panel._mod_type.setCurrentIndex(panel._mod_type.findData("AM"))
        assert len(received) == 1
        assert received[0] == ("dds.mod_type", "AM")

    def test_mod_wave_emits_literal(self, panel):
        panel.load_from_scope(_make_scope(mod_wave="SINE"))
        received = []
        panel.settingChanged.connect(lambda p, v: received.append((p, v)))
        panel._mod_wave.setCurrentIndex(panel._mod_wave.findData("RAMP"))
        assert len(received) == 1
        assert received[0] == ("dds.mod_wave", "RAMP")

    def test_mod_freq_emits_float(self, panel):
        panel.load_from_scope(_make_scope(mod_freq=100.0))
        received = []
        panel.settingChanged.connect(lambda p, v: received.append((p, v)))
        panel._mod_freq.setValue(500.0)
        panel._mod_freq.editingFinished.emit()
        assert len(received) == 1
        assert received[0] == ("dds.mod_freq", pytest.approx(500.0))
        assert isinstance(received[0][1], float)

    def test_mod_depth_emits_float(self, panel):
        panel.load_from_scope(_make_scope(mod_depth=50.0))
        received = []
        panel.settingChanged.connect(lambda p, v: received.append((p, v)))
        panel._mod_depth.setValue(80.0)
        panel._mod_depth.editingFinished.emit()
        assert len(received) == 1
        assert received[0] == ("dds.mod_depth", pytest.approx(80.0))
        assert isinstance(received[0][1], float)


# ---------------------------------------------------------------------------
# TestModDepthLabel — динамическая подпись поля глубины/девиации
# ---------------------------------------------------------------------------

class TestModDepthLabel:
    def test_am_label_contains_глубина(self, panel):
        """При mod_type=AM подпись содержит 'Глубина'."""
        panel.load_from_scope(_make_scope(mod_type="AM"))
        assert "Глубина" in panel._mod_depth_label.text(), (
            f"AM: ожидалась 'Глубина', получили {panel._mod_depth_label.text()!r}"
        )

    def test_fm_label_contains_девиация(self, panel):
        """При mod_type=FM подпись содержит 'Девиация'."""
        panel.load_from_scope(_make_scope(mod_type="FM"))
        assert "Девиация" in panel._mod_depth_label.text(), (
            f"FM: ожидалась 'Девиация', получили {panel._mod_depth_label.text()!r}"
        )

    def test_change_mod_type_updates_label(self, panel):
        """Смена mod_type через комбо сразу меняет подпись."""
        panel.load_from_scope(_make_scope(mod_type="AM"))
        panel._mod_type.setCurrentIndex(panel._mod_type.findData("FM"))
        assert "Девиация" in panel._mod_depth_label.text()

    def test_change_back_restores_label(self, panel):
        """Переключение обратно в AM восстанавливает 'Глубина'."""
        panel.load_from_scope(_make_scope(mod_type="FM"))
        panel._mod_type.setCurrentIndex(panel._mod_type.findData("AM"))
        assert "Глубина" in panel._mod_depth_label.text()


# ---------------------------------------------------------------------------
# TestBurstSignals — подгруппа Burst
# ---------------------------------------------------------------------------

class TestBurstSignals:
    def test_burst_enable_emits_bool(self, panel):
        panel.load_from_scope(_make_scope(burst_enable=False))
        received = []
        panel.settingChanged.connect(lambda p, v: received.append((p, v)))
        panel._burst_enable.setChecked(True)
        assert len(received) == 1
        assert received[0] == ("dds.burst_enable", True)
        assert isinstance(received[0][1], bool)

    def test_burst_type_emits_infinit(self, panel):
        panel.load_from_scope(_make_scope(burst_type="N_CYCLE"))
        received = []
        panel.settingChanged.connect(lambda p, v: received.append((p, v)))
        panel._burst_type.setCurrentIndex(panel._burst_type.findData("INFInit"))
        assert len(received) == 1
        assert received[0] == ("dds.burst_type", "INFInit")

    def test_burst_type_emits_n_cycle(self, panel):
        panel.load_from_scope(_make_scope(burst_type="INFInit"))
        received = []
        panel.settingChanged.connect(lambda p, v: received.append((p, v)))
        panel._burst_type.setCurrentIndex(panel._burst_type.findData("N_CYCLE"))
        assert len(received) == 1
        assert received[0] == ("dds.burst_type", "N_CYCLE")

    def test_burst_count_emits_int(self, panel):
        panel.load_from_scope(_make_scope(burst_count=1))
        received = []
        panel.settingChanged.connect(lambda p, v: received.append((p, v)))
        panel._burst_count.setValue(50)
        panel._burst_count.editingFinished.emit()
        assert len(received) == 1
        assert received[0] == ("dds.burst_count", 50)
        assert isinstance(received[0][1], int)

    def test_burst_trigger_button_emits(self, panel):
        """Кнопка 'Запустить пакет' эмитирует ("dds.burst_trigger", True)."""
        received = []
        panel.settingChanged.connect(lambda p, v: received.append((p, v)))
        panel._burst_trigger_btn.click()
        assert len(received) == 1
        assert received[0] == ("dds.burst_trigger", True)

    def test_burst_trigger_value_is_bool_true(self, panel):
        received = []
        panel.settingChanged.connect(lambda p, v: received.append((p, v)))
        panel._burst_trigger_btn.click()
        assert isinstance(received[0][1], bool)
        assert received[0][1] is True
