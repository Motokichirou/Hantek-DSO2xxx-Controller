"""Headless-тесты MeasurePanel (QT_QPA_PLATFORM=offscreen).

Запуск: .venv/Scripts/python.exe -m pytest tests/gui/test_measure_panel.py -q
"""
from __future__ import annotations

import os
import sys

import pytest

# Безголовый Qt — должно быть установлено ДО создания QApplication
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication  # noqa: E402
from PySide6.QtWidgets import QApplication   # noqa: E402

from hantek_dso2d15.gui.panels.measure import MeasurePanel  # noqa: E402


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
# Фейк-scope: scope.measure.source — строка вида "CHANnel1" / "CHANnel2"
# ---------------------------------------------------------------------------

class _FakeMeasure:
    def __init__(self, source: str = "CHANnel1"):
        self.source = source


class _FakeScope:
    def __init__(self, source: str = "CHANnel1"):
        self.measure = _FakeMeasure(source=source)


# ---------------------------------------------------------------------------
# Фикстура панели (function-scope — свежая для каждого теста)
# ---------------------------------------------------------------------------

@pytest.fixture
def panel(app):
    return MeasurePanel()


# ---------------------------------------------------------------------------
# Тест 1: load_from_scope выставляет Source и НЕ эмитирует measurementsChanged
# ---------------------------------------------------------------------------

class TestLoadFromScope:
    def test_load_does_not_emit(self, panel):
        """load_from_scope не должен эмитировать measurementsChanged."""
        received = []
        panel.measurementsChanged.connect(lambda v: received.append(v))

        panel.load_from_scope(_FakeScope(source="CHANnel1"))

        assert received == [], f"load_from_scope эмитировал: {received}"

    def test_load_sets_ch1(self, panel):
        """После load с CHANnel1 Source-выпадашка указывает на CH1 (data=1)."""
        panel.load_from_scope(_FakeScope(source="CHANnel1"))
        assert panel._source_combo.currentData() == 1

    def test_load_sets_ch2(self, panel):
        """После load с CHANnel2 Source-выпадашка указывает на CH2 (data=2)."""
        panel.load_from_scope(_FakeScope(source="CHANnel2"))
        assert panel._source_combo.currentData() == 2

    def test_load_ch2_does_not_emit(self, panel):
        """Загрузка CH2 тоже не эмитирует сигнал."""
        received = []
        panel.measurementsChanged.connect(lambda v: received.append(v))
        panel.load_from_scope(_FakeScope(source="CHANnel2"))
        assert received == []


# ---------------------------------------------------------------------------
# Тест 2: добавление измерения → measurementsChanged с корректным payload
# ---------------------------------------------------------------------------

class TestAddMeasurement:
    def test_add_emits_signal(self, panel):
        """_add_row эмитирует measurementsChanged."""
        received = []
        panel.measurementsChanged.connect(lambda v: received.append(v))

        panel._add_row(1, "VMAX")

        assert len(received) == 1, f"Ожидался 1 сигнал, получено: {received}"

    def test_add_payload_single(self, panel):
        """Payload первого добавленного измерения — [(1, 'VMAX')]."""
        received = []
        panel.measurementsChanged.connect(lambda v: received.append(v))

        panel._add_row(1, "VMAX")

        assert received[0] == [(1, "VMAX")]

    def test_add_two_items_payload(self, panel):
        """После добавления двух строк payload содержит обе в порядке добавления."""
        received = []
        panel.measurementsChanged.connect(lambda v: received.append(v))

        panel._add_row(1, "VMAX")
        panel._add_row(1, "VMIN")

        assert received[-1] == [(1, "VMAX"), (1, "VMIN")]

    def test_add_ch2_item(self, panel):
        """Добавление измерения на CH2 — payload содержит channel=2."""
        received = []
        panel.measurementsChanged.connect(lambda v: received.append(v))

        panel._add_row(2, "VPP")

        assert received[0] == [(2, "VPP")]

    def test_add_row_appears_in_table(self, panel):
        """После _add_row таблица содержит строку с правильным типом."""
        panel._add_row(1, "VRMS")
        assert panel._table.rowCount() == 1
        text = panel._table.item(0, 0).text()
        assert "Vrms" in text or "VRMS" in text

    def test_add_source_text_in_table(self, panel):
        """Колонка Source содержит метку канала."""
        panel._add_row(2, "VAVG")
        src_text = panel._table.item(0, 1).text()
        assert "CH2" in src_text or "2" in src_text


# ---------------------------------------------------------------------------
# Тест 3: дубликат (один и тот же channel+item) не добавляется
# ---------------------------------------------------------------------------

class TestDuplicate:
    def test_duplicate_not_added_no_signal(self, panel):
        """Повторное добавление того же (channel, item) — сигнал НЕ эмитируется повторно."""
        received = []
        panel.measurementsChanged.connect(lambda v: received.append(v))

        panel._add_row(1, "VMAX")
        panel._add_row(1, "VMAX")  # дубликат

        assert len(received) == 1, f"Дубликат вызвал лишний сигнал: {received}"

    def test_duplicate_not_added_row_count(self, panel):
        """После двух одинаковых добавлений в таблице ровно 1 строка."""
        panel._add_row(1, "VMAX")
        panel._add_row(1, "VMAX")
        assert panel._table.rowCount() == 1
        assert len(panel._rows) == 1

    def test_same_item_different_channel_allowed(self, panel):
        """VMAX на CH1 и VMAX на CH2 — это разные строки."""
        received = []
        panel.measurementsChanged.connect(lambda v: received.append(v))

        panel._add_row(1, "VMAX")
        panel._add_row(2, "VMAX")

        assert panel._table.rowCount() == 2
        assert len(panel._rows) == 2
        assert received[-1] == [(1, "VMAX"), (2, "VMAX")]

    def test_different_items_same_channel_allowed(self, panel):
        """VMAX и VMIN на одном канале — допустимо."""
        panel._add_row(1, "VMAX")
        panel._add_row(1, "VMIN")
        assert len(panel._rows) == 2


# ---------------------------------------------------------------------------
# Тест 4: удаление строки → measurementsChanged с обновлённым списком
# ---------------------------------------------------------------------------

class TestRemoveMeasurement:
    def test_remove_emits_signal(self, panel):
        """_remove_row эмитирует measurementsChanged."""
        panel._add_row(1, "VMAX")
        received = []
        panel.measurementsChanged.connect(lambda v: received.append(v))
        panel._remove_row(0)
        assert len(received) == 1

    def test_remove_first_payload_updated(self, panel):
        """Удаление первой строки из двух — payload содержит только вторую."""
        panel._add_row(1, "VMAX")
        panel._add_row(1, "VMIN")
        received = []
        panel.measurementsChanged.connect(lambda v: received.append(v))
        panel._remove_row(0)
        assert received == [[(1, "VMIN")]]

    def test_remove_last_payload_empty(self, panel):
        """Удаление единственной строки — payload пустой список."""
        panel._add_row(1, "VMAX")
        received = []
        panel.measurementsChanged.connect(lambda v: received.append(v))
        panel._remove_row(0)
        assert received == [[]]

    def test_remove_decrements_row_count(self, panel):
        """После удаления количество строк в таблице уменьшается."""
        panel._add_row(1, "VMAX")
        panel._add_row(1, "VMIN")
        panel._remove_row(1)
        assert panel._table.rowCount() == 1
        assert panel._rows == [(1, "VMAX")]

    def test_remove_by_pair(self, panel):
        """_remove_row_by_pair удаляет строку по (channel, item)."""
        panel._add_row(1, "VMAX")
        panel._add_row(1, "VMIN")
        received = []
        panel.measurementsChanged.connect(lambda v: received.append(v))
        panel._remove_row_by_pair(1, "VMAX")
        assert panel._rows == [(1, "VMIN")]
        assert received == [[(1, "VMIN")]]

    def test_remove_by_pair_missing_noop(self, panel):
        """_remove_row_by_pair с несуществующей парой — молча ничего не делает."""
        panel._add_row(1, "VMAX")
        received = []
        panel.measurementsChanged.connect(lambda v: received.append(v))
        panel._remove_row_by_pair(2, "VMAX")  # канал не совпадает
        assert received == []  # сигнал не эмитировался


# ---------------------------------------------------------------------------
# Тест 5: update_values обновляет Value по (channel, item)
# ---------------------------------------------------------------------------

class TestUpdateValues:
    def test_update_non_none_shows_value(self, panel):
        """update_values с числом → ячейка Value НЕ '—'."""
        panel._add_row(1, "VMAX")
        panel.update_values([{"channel": 1, "item": "VMAX", "value": 1.5}])
        text = panel._table.item(0, 2).text()
        assert text != "—", f"Ожидалось значение, получено '—'"

    def test_update_none_shows_dash(self, panel):
        """update_values с value=None → '—'."""
        panel._add_row(1, "VMAX")
        panel.update_values([{"channel": 1, "item": "VMAX", "value": None}])
        assert panel._table.item(0, 2).text() == "—"

    def test_update_initial_dash(self, panel):
        """После add_row, без update, ячейка Value = '—'."""
        panel._add_row(1, "VMAX")
        assert panel._table.item(0, 2).text() == "—"

    def test_update_unknown_channel_item_ignored(self, panel):
        """Запись с несуществующим (channel, item) игнорируется, без ошибок."""
        panel._add_row(1, "VMAX")
        panel.update_values([{"channel": 99, "item": "FAKE", "value": 1.0}])
        # Нет исключения; VMAX по-прежнему "—"
        assert panel._table.item(0, 2).text() == "—"

    def test_update_duty_shows_percent(self, panel):
        """PDUTy форматируется с '%'."""
        panel._add_row(1, "PDUTy")
        panel.update_values([{"channel": 1, "item": "PDUTy", "value": 50.0}])
        text = panel._table.item(0, 2).text()
        assert "%" in text, f"Ожидался '%', получено: {text!r}"

    def test_update_ndutycycle_shows_percent(self, panel):
        """NDUTy форматируется с '%'."""
        panel._add_row(1, "NDUTy")
        panel.update_values([{"channel": 1, "item": "NDUTy", "value": 30.5}])
        text = panel._table.item(0, 2).text()
        assert "%" in text

    def test_update_frequency_not_dash(self, panel):
        """FREQuency с ненулевым значением → не '—'."""
        panel._add_row(1, "FREQuency")
        panel.update_values([{"channel": 1, "item": "FREQuency", "value": 1000.0}])
        text = panel._table.item(0, 2).text()
        assert text != "—"

    def test_update_two_rows_independently(self, panel):
        """update_values обновляет обе строки правильно."""
        panel._add_row(1, "VMAX")
        panel._add_row(1, "VMIN")
        panel.update_values([
            {"channel": 1, "item": "VMAX", "value": 2.0},
            {"channel": 1, "item": "VMIN", "value": -1.0},
        ])
        t0 = panel._table.item(0, 2).text()
        t1 = panel._table.item(1, 2).text()
        assert t0 != "—", f"Строка 0 должна иметь значение, получено: {t0!r}"
        assert t1 != "—", f"Строка 1 должна иметь значение, получено: {t1!r}"

    def test_update_empty_payload_noop(self, panel):
        """update_values с пустым payload — ничего не меняется, ошибок нет."""
        panel._add_row(1, "VMAX")
        panel.update_values([])
        assert panel._table.item(0, 2).text() == "—"

    def test_update_does_not_emit_measurementsChanged(self, panel):
        """update_values НЕ эмитирует measurementsChanged."""
        panel._add_row(1, "VMAX")
        received = []
        panel.measurementsChanged.connect(lambda v: received.append(v))
        panel.update_values([{"channel": 1, "item": "VMAX", "value": 1.5}])
        assert received == [], "update_values не должен эмитировать measurementsChanged"


# ---------------------------------------------------------------------------
# Тест 6: структура панели
# ---------------------------------------------------------------------------

class TestPanelStructure:
    def test_has_measurementsChanged_signal(self, panel):
        assert hasattr(panel, "measurementsChanged")

    def test_has_load_from_scope(self, panel):
        assert callable(getattr(panel, "load_from_scope", None))

    def test_has_update_values(self, panel):
        assert callable(getattr(panel, "update_values", None))

    def test_has_add_row(self, panel):
        assert callable(getattr(panel, "_add_row", None))

    def test_has_remove_row(self, panel):
        assert callable(getattr(panel, "_remove_row", None))

    def test_source_combo_has_ch1(self, panel):
        items = [panel._source_combo.itemData(i) for i in range(panel._source_combo.count())]
        assert 1 in items, "Source-выпадашка должна содержать CH1 (data=1)"

    def test_source_combo_has_ch2(self, panel):
        items = [panel._source_combo.itemData(i) for i in range(panel._source_combo.count())]
        assert 2 in items, "Source-выпадашка должна содержать CH2 (data=2)"

    def test_source_combo_no_math(self, panel):
        """MATH в Source-выпадашку пока не добавляется (отложено до math-панели)."""
        texts = [panel._source_combo.itemText(i) for i in range(panel._source_combo.count())]
        assert "MATH" not in texts

    def test_initial_rows_empty(self, panel):
        """При создании панели активных измерений нет."""
        assert panel._rows == []
        assert panel._table.rowCount() == 0

    def test_table_has_four_columns(self, panel):
        assert panel._table.columnCount() == 4

    def test_has_stats_reset_signal(self, panel):
        assert hasattr(panel, "statsResetRequested")

    def test_reset_button_emits_signal(self, panel):
        """Клик по «Сброс ст.» эмитирует statsResetRequested."""
        received = []
        panel.statsResetRequested.connect(lambda: received.append(True))
        panel._reset_btn.click()
        assert received == [True]
