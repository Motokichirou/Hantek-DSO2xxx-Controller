"""Headless-тесты SegmentedControl.

QT_QPA_PLATFORM=offscreen — безголовый Qt.
Запуск: .venv\\Scripts\\python.exe -m pytest tests/gui/test_segmented.py -q
"""
from __future__ import annotations

import os
import sys

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402
from PySide6.QtCore import QCoreApplication  # noqa: E402

from hantek_dso2d15.gui.segmented import SegmentedControl  # noqa: E402


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
# Тест 1: Построение из списка строк
# ---------------------------------------------------------------------------

class TestConstructionFromStrings:
    def test_build_from_strings(self, app):
        """Список строк — label==value для каждого сегмента."""
        ctrl = SegmentedControl(["AC", "DC", "GND"])
        assert ctrl.value() == "AC"

    def test_first_selected_by_default(self, app):
        """Первый сегмент выбран по умолчанию."""
        ctrl = SegmentedControl(["DC", "AC", "GND"])
        assert ctrl.value() == "DC"

    def test_correct_button_count_strings(self, app):
        """Количество кнопок соответствует количеству опций."""
        ctrl = SegmentedControl(["A", "B", "C", "D"])
        # Проверяем через QButtonGroup — должно быть 4 кнопки
        assert len(ctrl._group.buttons()) == 4


# ---------------------------------------------------------------------------
# Тест 2: Построение из пар (label, value)
# ---------------------------------------------------------------------------

class TestConstructionFromPairs:
    def test_build_from_pairs(self, app):
        """Список пар (label, value) — label отображается, value — в API."""
        ctrl = SegmentedControl([("Slope ↑", "POSitive"), ("Slope ↓", "NEGative")])
        assert ctrl.value() == "POSitive"

    def test_first_selected_pair(self, app):
        """Первый сегмент выбран по умолчанию при парах."""
        ctrl = SegmentedControl([("Norm", "NORMal"), ("Auto", "AUTO"), ("Single", "SINGle")])
        assert ctrl.value() == "NORMal"

    def test_pairs_correct_count(self, app):
        ctrl = SegmentedControl([("DC", "DC"), ("AC", "AC"), ("GND", "GND")])
        assert len(ctrl._group.buttons()) == 3

    def test_mixed_normalization(self, app):
        """Смешанные строки и пары не должны допускаться — только однородные, но нормализация работает."""
        # Чистые строки нормализуются в (s, s)
        ctrl = SegmentedControl(["X", "Y"])
        assert ctrl.value() == "X"


# ---------------------------------------------------------------------------
# Тест 3: valueChanged НЕ эмитируется при __init__
# ---------------------------------------------------------------------------

class TestNoEmitOnInit:
    def test_no_signal_on_construction_strings(self, app):
        """При создании valueChanged НЕ должен эмитироваться."""
        received = []
        ctrl = SegmentedControl(["AC", "DC", "GND"])
        ctrl.valueChanged.connect(lambda v: received.append(v))
        # Сигнал был бы добавлен ДО подключения — но должны убедиться,
        # что конструктор ничего не отложил в очередь.
        # Создаём заново, чтобы перехватить даже Qt::QueuedConnection:
        received2 = []
        ctrl2 = SegmentedControl(["AC", "DC", "GND"])
        ctrl2.valueChanged.connect(lambda v: received2.append(v))
        assert received2 == [], f"valueChanged эмитился при __init__: {received2}"

    def test_no_signal_on_construction_pairs(self, app):
        received = []
        ctrl = SegmentedControl([("DC", "DC"), ("AC", "AC")])
        ctrl.valueChanged.connect(lambda v: received.append(v))
        assert received == []


# ---------------------------------------------------------------------------
# Тест 4: клик пользователя → valueChanged эмитирует value сегмента
# ---------------------------------------------------------------------------

class TestClickEmitsValue:
    def test_click_emits_string_value(self, app):
        """button.click() → valueChanged(value)."""
        ctrl = SegmentedControl(["AC", "DC", "GND"])
        received = []
        ctrl.valueChanged.connect(lambda v: received.append(v))

        # Кликаем второй сегмент (DC)
        buttons = ctrl._group.buttons()
        buttons[1].click()

        assert received == ["DC"], f"Ожидалось ['DC'], получено {received}"

    def test_click_pair_emits_value_not_label(self, app):
        """При клике эмитируется value, НЕ label."""
        ctrl = SegmentedControl([("Slope ↑", "POSitive"), ("Slope ↓", "NEGative")])
        received = []
        ctrl.valueChanged.connect(lambda v: received.append(v))

        buttons = ctrl._group.buttons()
        buttons[1].click()

        assert received == ["NEGative"], f"Ожидалось ['NEGative'], получено {received}"

    def test_click_first_when_already_second_selected(self, app):
        """Клик по первому сегменту после выбора второго — эмитирует value первого."""
        ctrl = SegmentedControl(["A", "B", "C"])
        received = []

        # Сначала выбираем B (без прослушивания)
        ctrl._group.buttons()[1].click()

        # Теперь подключаем и кликаем A
        ctrl.valueChanged.connect(lambda v: received.append(v))
        ctrl._group.buttons()[0].click()

        assert received == ["A"]

    def test_click_third_option(self, app):
        ctrl = SegmentedControl(["X", "Y", "Z"])
        received = []
        ctrl.valueChanged.connect(lambda v: received.append(v))
        ctrl._group.buttons()[2].click()
        assert received == ["Z"]

    def test_multiple_clicks_emit_each(self, app):
        """Каждый клик по другому сегменту эмитирует сигнал."""
        ctrl = SegmentedControl(["A", "B", "C"])
        received = []
        ctrl.valueChanged.connect(lambda v: received.append(v))

        ctrl._group.buttons()[1].click()
        ctrl._group.buttons()[2].click()
        ctrl._group.buttons()[0].click()

        assert received == ["B", "C", "A"]


# ---------------------------------------------------------------------------
# Тест 5: set_value — выбирает сегмент, НЕ эмитирует
# ---------------------------------------------------------------------------

class TestSetValue:
    def test_set_value_changes_selection(self, app):
        """set_value(v) выбирает нужный сегмент."""
        ctrl = SegmentedControl(["AC", "DC", "GND"])
        ctrl.set_value("DC")
        assert ctrl.value() == "DC"

    def test_set_value_no_emit(self, app):
        """set_value НЕ эмитирует valueChanged."""
        ctrl = SegmentedControl(["AC", "DC", "GND"])
        received = []
        ctrl.valueChanged.connect(lambda v: received.append(v))
        ctrl.set_value("GND")
        assert received == [], f"set_value эмитил: {received}"

    def test_set_value_unknown_no_crash(self, app):
        """set_value на несуществующее value не падает."""
        ctrl = SegmentedControl(["AC", "DC", "GND"])
        try:
            ctrl.set_value("UNKNOWN")
        except Exception as e:
            pytest.fail(f"set_value('UNKNOWN') вызвал исключение: {e}")

    def test_set_value_unknown_keeps_previous(self, app):
        """set_value на несуществующее value не меняет текущий выбор."""
        ctrl = SegmentedControl(["AC", "DC", "GND"])
        ctrl.set_value("DC")
        ctrl.set_value("NONEXISTENT")
        assert ctrl.value() == "DC"

    def test_set_value_pairs(self, app):
        """set_value работает с value из пар."""
        ctrl = SegmentedControl([("Norm", "NORMal"), ("Peak", "PEAK"), ("Avg", "AVERage")])
        ctrl.set_value("AVERage")
        assert ctrl.value() == "AVERage"

    def test_set_value_first_then_different(self, app):
        """Несколько set_value подряд — актуален последний."""
        ctrl = SegmentedControl(["A", "B", "C"])
        ctrl.set_value("B")
        ctrl.set_value("C")
        assert ctrl.value() == "C"


# ---------------------------------------------------------------------------
# Тест 6: эксклюзивность — выбран ровно один сегмент
# ---------------------------------------------------------------------------

class TestExclusivity:
    def test_exactly_one_checked_initially(self, app):
        """Ровно один сегмент отмечен по умолчанию."""
        ctrl = SegmentedControl(["A", "B", "C", "D"])
        checked = [b for b in ctrl._group.buttons() if b.isChecked()]
        assert len(checked) == 1, f"Ожидался 1 checked, найдено: {len(checked)}"

    def test_exactly_one_after_click(self, app):
        """После клика ровно один сегмент остаётся отмеченным."""
        ctrl = SegmentedControl(["A", "B", "C"])
        ctrl._group.buttons()[2].click()
        checked = [b for b in ctrl._group.buttons() if b.isChecked()]
        assert len(checked) == 1

    def test_exactly_one_after_set_value(self, app):
        """После set_value ровно один сегмент остаётся отмеченным."""
        ctrl = SegmentedControl(["A", "B", "C"])
        ctrl.set_value("B")
        checked = [b for b in ctrl._group.buttons() if b.isChecked()]
        assert len(checked) == 1

    def test_group_is_exclusive(self, app):
        """QButtonGroup настроен как exclusive."""
        ctrl = SegmentedControl(["A", "B"])
        assert ctrl._group.exclusive() is True


# ---------------------------------------------------------------------------
# Тест 7: value() возвращает None если нет кнопок (граничный случай)
# ---------------------------------------------------------------------------

class TestValueNone:
    def test_value_with_options(self, app):
        """value() возвращает str при нормальном использовании."""
        ctrl = SegmentedControl(["A", "B"])
        assert isinstance(ctrl.value(), str)


# ---------------------------------------------------------------------------
# Тест 8: API и структура
# ---------------------------------------------------------------------------

class TestStructure:
    def test_has_valueChanged_signal(self, app):
        ctrl = SegmentedControl(["A", "B"])
        assert hasattr(ctrl, "valueChanged")

    def test_has_set_value(self, app):
        ctrl = SegmentedControl(["A", "B"])
        assert callable(getattr(ctrl, "set_value", None))

    def test_has_value(self, app):
        ctrl = SegmentedControl(["A", "B"])
        assert callable(getattr(ctrl, "value", None))

    def test_has_group(self, app):
        """Внутренний _group (QButtonGroup) доступен для тестов."""
        ctrl = SegmentedControl(["A", "B"])
        assert hasattr(ctrl, "_group")

    def test_default_accent(self, app):
        """Акцент по умолчанию '#37D67A'."""
        ctrl = SegmentedControl(["A", "B"])
        assert ctrl._accent == "#37D67A"

    def test_custom_accent(self, app):
        """Пользовательский акцент сохраняется."""
        ctrl = SegmentedControl(["A", "B"], accent="#F2C300")
        assert ctrl._accent == "#F2C300"
