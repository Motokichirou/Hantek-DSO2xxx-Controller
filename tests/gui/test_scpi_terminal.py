"""Offscreen-тесты виджета ScpiTerminal.

QT_QPA_PLATFORM=offscreen — устанавливается в tests/conftest.py автоматически.
Запуск: .venv\\Scripts\\python.exe -m pytest tests/gui/test_scpi_terminal.py -q
"""
from __future__ import annotations

import pytest

from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication

from hantek_dso2d15.gui.scpi_terminal import ScpiTerminal


# ---------------------------------------------------------------------------
# Фикстура виджета (function-scope, новый экземпляр на каждый тест)
# ---------------------------------------------------------------------------

@pytest.fixture
def terminal(_qt_app):
    """Создать ScpiTerminal; _qt_app из conftest.py."""
    t = ScpiTerminal()
    return t


# ---------------------------------------------------------------------------
# Вспомогательная функция: эмитировать нажатие клавиши в виджет
# ---------------------------------------------------------------------------

def _press_key(widget, key: Qt.Key) -> None:
    """Отправить KeyPress + KeyRelease событие виджету."""
    press = QKeyEvent(QEvent.Type.KeyPress, key, Qt.KeyboardModifier.NoModifier)
    release = QKeyEvent(QEvent.Type.KeyRelease, key, Qt.KeyboardModifier.NoModifier)
    QApplication.sendEvent(widget, press)
    QApplication.sendEvent(widget, release)


# ---------------------------------------------------------------------------
# Тест 1: структура виджета
# ---------------------------------------------------------------------------

class TestStructure:
    def test_has_commandEntered_signal(self, terminal):
        """ScpiTerminal должен иметь сигнал commandEntered."""
        assert hasattr(terminal, "commandEntered")

    def test_has_log_widget(self, terminal):
        """Должен быть self._log (QPlainTextEdit, read-only)."""
        from PySide6.QtWidgets import QPlainTextEdit
        assert hasattr(terminal, "_log")
        assert isinstance(terminal._log, QPlainTextEdit)
        assert terminal._log.isReadOnly()

    def test_has_input_widget(self, terminal):
        """Должен быть self._input (QLineEdit)."""
        from PySide6.QtWidgets import QLineEdit
        assert hasattr(terminal, "_input")
        assert isinstance(terminal._input, QLineEdit)

    def test_has_send_button(self, terminal):
        """Должен быть self._send (QPushButton)."""
        from PySide6.QtWidgets import QPushButton
        assert hasattr(terminal, "_send")
        assert isinstance(terminal._send, QPushButton)

    def test_has_append_response(self, terminal):
        """Метод append_response должен быть callable."""
        assert callable(getattr(terminal, "append_response", None))

    def test_has_clear_log(self, terminal):
        """Метод clear_log должен быть callable."""
        assert callable(getattr(terminal, "clear_log", None))

    def test_log_monospace_font(self, terminal):
        """Журнал должен использовать моноширинный шрифт.

        Проверяем через QFont.fixedPitch() (запрошенное свойство), а не через
        QFontInfo.fixedPitch() (разрешённое системой) — в offscreen-режиме
        Qt не резолвит шрифты реально, и QFontInfo может ошибаться.
        """
        font = terminal._log.font()
        assert font.fixedPitch(), (
            f"Ожидался моноширинный шрифт (fixedPitch=True), семейство: {font.family()!r}"
        )


# ---------------------------------------------------------------------------
# Тест 2: клик Send — эмиссия, эхо в журнале, очистка поля
# ---------------------------------------------------------------------------

class TestSendButton:
    def test_click_send_emits_commandEntered(self, terminal):
        """Клик Send → commandEntered(text)."""
        received = []
        terminal.commandEntered.connect(received.append)

        terminal._input.setText("*IDN?")
        terminal._send.click()

        assert received == ["*IDN?"]

    def test_click_send_logs_echo(self, terminal):
        """Клик Send → журнал содержит «> *IDN?»."""
        terminal._input.setText("*IDN?")
        terminal._send.click()

        log_text = terminal._log.toPlainText()
        assert "> *IDN?" in log_text

    def test_click_send_clears_input(self, terminal):
        """После Send поле ввода пусто."""
        terminal._input.setText("*IDN?")
        terminal._send.click()

        assert terminal._input.text() == ""

    def test_send_multiple_commands(self, terminal):
        """Несколько отправок — несколько записей в журнале."""
        terminal._input.setText("CMD1")
        terminal._send.click()
        terminal._input.setText("CMD2")
        terminal._send.click()

        log_text = terminal._log.toPlainText()
        assert "> CMD1" in log_text
        assert "> CMD2" in log_text


# ---------------------------------------------------------------------------
# Тест 3: returnPressed — то же поведение, что и Send
# ---------------------------------------------------------------------------

class TestReturnPressed:
    def test_return_emits_commandEntered(self, terminal):
        """Enter в поле ввода → commandEntered(text)."""
        received = []
        terminal.commandEntered.connect(received.append)

        terminal._input.setText("MEAS:FREQ?")
        _press_key(terminal._input, Qt.Key.Key_Return)

        assert received == ["MEAS:FREQ?"]

    def test_return_logs_echo(self, terminal):
        """Enter в поле ввода → журнал содержит «> MEAS:FREQ?»."""
        terminal._input.setText("MEAS:FREQ?")
        _press_key(terminal._input, Qt.Key.Key_Return)

        assert "> MEAS:FREQ?" in terminal._log.toPlainText()

    def test_return_clears_input(self, terminal):
        """После Enter поле ввода пусто."""
        terminal._input.setText("MEAS:FREQ?")
        _press_key(terminal._input, Qt.Key.Key_Return)

        assert terminal._input.text() == ""


# ---------------------------------------------------------------------------
# Тест 4: пустой и пробельный ввод — ничего не происходит
# ---------------------------------------------------------------------------

class TestEmptyInput:
    def test_empty_does_not_emit(self, terminal):
        """Пустой ввод → commandEntered НЕ эмитируется."""
        received = []
        terminal.commandEntered.connect(received.append)

        terminal._input.setText("")
        terminal._send.click()

        assert received == []

    def test_whitespace_does_not_emit(self, terminal):
        """Пробельный ввод → commandEntered НЕ эмитируется."""
        received = []
        terminal.commandEntered.connect(received.append)

        terminal._input.setText("   \t  ")
        terminal._send.click()

        assert received == []

    def test_empty_does_not_grow_log(self, terminal):
        """Пустой ввод → журнал не растёт."""
        log_before = terminal._log.toPlainText()
        terminal._input.setText("")
        terminal._send.click()
        assert terminal._log.toPlainText() == log_before

    def test_whitespace_does_not_grow_log(self, terminal):
        """Пробельный ввод → журнал не растёт."""
        log_before = terminal._log.toPlainText()
        terminal._input.setText("   ")
        terminal._send.click()
        assert terminal._log.toPlainText() == log_before


# ---------------------------------------------------------------------------
# Тест 5: append_response — добавляет «< …» в журнал
# ---------------------------------------------------------------------------

class TestAppendResponse:
    def test_normal_response(self, terminal):
        """append_response добавляет «< ответ» в журнал."""
        terminal.append_response("HANTEK,DSO2D15,1234,V1.0")
        log_text = terminal._log.toPlainText()
        assert "< HANTEK,DSO2D15,1234,V1.0" in log_text

    def test_error_response_has_err_mark(self, terminal):
        """append_response(is_error=True) содержит пометку ERR."""
        terminal.append_response("Timeout", is_error=True)
        log_text = terminal._log.toPlainText()
        # Должна быть пометка «ERR» где-то в строке с ответом
        assert "ERR" in log_text
        assert "Timeout" in log_text

    def test_error_prefix_format(self, terminal):
        """Ошибка → строка вида «< ERR: Timeout»."""
        terminal.append_response("Timeout", is_error=True)
        log_text = terminal._log.toPlainText()
        assert "< ERR: Timeout" in log_text

    def test_normal_no_err_mark(self, terminal):
        """Нормальный ответ НЕ содержит «ERR»."""
        terminal.append_response("OK")
        log_text = terminal._log.toPlainText()
        assert "ERR" not in log_text

    def test_multiline_response(self, terminal):
        """Многострочный ответ сохраняется как есть."""
        terminal.append_response("line1\nline2\nline3")
        log_text = terminal._log.toPlainText()
        assert "line1" in log_text
        assert "line2" in log_text
        assert "line3" in log_text


# ---------------------------------------------------------------------------
# Тест 6: история команд — стрелки UP/DOWN
# ---------------------------------------------------------------------------

class TestCommandHistory:
    def _send(self, terminal, cmd: str) -> None:
        """Ввести и отправить команду."""
        terminal._input.setText(cmd)
        terminal._send.click()

    def test_up_arrow_restores_last_command(self, terminal):
        """Key_Up после отправки cmd1, cmd2 → подставляет cmd2."""
        self._send(terminal, "CMD1")
        self._send(terminal, "CMD2")
        _press_key(terminal._input, Qt.Key.Key_Up)
        assert terminal._input.text() == "CMD2"

    def test_up_twice_restores_earlier_command(self, terminal):
        """Key_Up дважды → подставляет cmd1."""
        self._send(terminal, "CMD1")
        self._send(terminal, "CMD2")
        _press_key(terminal._input, Qt.Key.Key_Up)
        _press_key(terminal._input, Qt.Key.Key_Up)
        assert terminal._input.text() == "CMD1"

    def test_down_after_up_restores_later(self, terminal):
        """Key_Up → Key_Down → возвращает cmd2."""
        self._send(terminal, "CMD1")
        self._send(terminal, "CMD2")
        _press_key(terminal._input, Qt.Key.Key_Up)   # → CMD2
        _press_key(terminal._input, Qt.Key.Key_Up)   # → CMD1
        _press_key(terminal._input, Qt.Key.Key_Down) # → CMD2
        assert terminal._input.text() == "CMD2"

    def test_down_past_end_gives_empty(self, terminal):
        """Key_Down за последней записью → пустое поле."""
        self._send(terminal, "CMD1")
        self._send(terminal, "CMD2")
        _press_key(terminal._input, Qt.Key.Key_Up)   # → CMD2
        _press_key(terminal._input, Qt.Key.Key_Down) # → пусто (за концом)
        assert terminal._input.text() == ""

    def test_up_on_empty_history_does_not_crash(self, terminal):
        """Key_Up на пустой истории — не падает, поле не меняется."""
        # История пуста; ничего не отправляли
        try:
            _press_key(terminal._input, Qt.Key.Key_Up)
        except Exception as exc:
            pytest.fail(f"Key_Up на пустой истории вызвал исключение: {exc}")
        # Поле по-прежнему пусто
        assert terminal._input.text() == ""

    def test_up_at_beginning_stays_at_first(self, terminal):
        """Key_Up на первой записи → остаётся на первой (не выходит за начало)."""
        self._send(terminal, "ONLY_CMD")
        _press_key(terminal._input, Qt.Key.Key_Up)  # → ONLY_CMD
        _press_key(terminal._input, Qt.Key.Key_Up)  # ещё раз — остаётся
        assert terminal._input.text() == "ONLY_CMD"


# ---------------------------------------------------------------------------
# Тест 7: clear_log
# ---------------------------------------------------------------------------

class TestClearLog:
    def test_clear_log_empties_log(self, terminal):
        """clear_log очищает журнал."""
        terminal.append_response("Что-то в журнале")
        terminal.clear_log()
        assert terminal._log.toPlainText() == ""

    def test_clear_log_on_empty_does_not_crash(self, terminal):
        """clear_log на пустом журнале не падает."""
        try:
            terminal.clear_log()
        except Exception as exc:
            pytest.fail(f"clear_log на пустом журнале вызвал исключение: {exc}")
