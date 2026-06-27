"""SCPI-терминал — интерактивный виджет для ручной отправки команд.

Виджет НЕ обращается к прибору напрямую. Он:
  - принимает ввод пользователя и эмитирует ``commandEntered(str)``;
  - принимает ответы через ``append_response(text, is_error)``;
  - ведёт журнал обмена (QPlainTextEdit, read-only);
  - поддерживает историю команд (стрелки Up/Down в поле ввода).

Реальная отправка — задача worker-а/engine снаружи.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class ScpiTerminal(QWidget):
    """Интерактивный SCPI-терминал.

    Сигналы
    -------
    commandEntered(str)
        Эмитируется при отправке непустой команды (клик «Send» или Enter).
        Передаёт введённый текст без ведущих/хвостовых пробелов.

    Публичный API
    -------------
    append_response(text, is_error=False)
        Добавить ответ прибора в журнал (префикс «< » или «< ERR: »).
    clear_log()
        Очистить журнал.
    """

    commandEntered = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        # --- Журнал обмена ---
        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        font = QFont("Consolas")
        font.setStyleHint(QFont.StyleHint.Monospace)
        # Гарантируем фиксированный шрифт даже если Consolas/JetBrains Mono недоступны
        font.setFixedPitch(True)
        self._log.setFont(font)
        self._log.setPlaceholderText("Журнал SCPI-обмена…")

        # --- Поле ввода ---
        self._input = QLineEdit()
        self._input.setPlaceholderText("SCPI-команда, напр. *IDN?")
        self._input.returnPressed.connect(self._on_send)

        # --- Кнопка Send ---
        self._send = QPushButton("Send")
        self._send.clicked.connect(self._on_send)

        # --- История команд ---
        self._history: list[str] = []
        self._hist_index: int = -1  # -1 = «за концом» (новая строка)

        # Перехватываем стрелки в поле ввода
        self._input.installEventFilter(self)

        # --- Компоновка ---
        input_row = QHBoxLayout()
        input_row.addWidget(self._input)
        input_row.addWidget(self._send)
        input_row.setContentsMargins(0, 0, 0, 0)

        layout = QVBoxLayout(self)
        layout.addWidget(self._log)
        layout.addLayout(input_row)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

    # ------------------------------------------------------------------
    # Внутренние слоты
    # ------------------------------------------------------------------

    def _on_send(self) -> None:
        """Обработать нажатие Send / Enter: валидировать, записать, эмитировать."""
        text = self._input.text().strip()
        if not text:
            return

        # Эхо в журнал
        self._log.appendPlainText(f"> {text}")

        # Добавить в историю; сбросить индекс на «за концом»
        self._history.append(text)
        self._hist_index = len(self._history)  # указывает за последний элемент

        self.commandEntered.emit(text)
        self._input.clear()

    # ------------------------------------------------------------------
    # Публичный API
    # ------------------------------------------------------------------

    def append_response(self, text: str, is_error: bool = False) -> None:
        """Добавить ответ прибора в журнал.

        Parameters
        ----------
        text:
            Текст ответа (может быть многострочным).
        is_error:
            Если True, строка предваряется «< ERR: ».
        """
        if is_error:
            self._log.appendPlainText(f"< ERR: {text}")
        else:
            self._log.appendPlainText(f"< {text}")

    def clear_log(self) -> None:
        """Очистить журнал обмена."""
        self._log.clear()

    # ------------------------------------------------------------------
    # История: обработка стрелок Up/Down через eventFilter
    # ------------------------------------------------------------------

    def eventFilter(self, obj, event) -> bool:  # type: ignore[override]
        """Перехватить Key_Up / Key_Down в поле ввода для листания истории."""
        from PySide6.QtCore import QEvent

        if obj is self._input and event.type() == QEvent.Type.KeyPress:
            key = event.key()
            if key == Qt.Key.Key_Up:
                self._history_up()
                return True
            if key == Qt.Key.Key_Down:
                self._history_down()
                return True

        return super().eventFilter(obj, event)

    def _history_up(self) -> None:
        """Перейти к более старой записи истории."""
        if not self._history:
            return
        # Если за концом — перейти к последнему; иначе — к предыдущему
        if self._hist_index > 0:
            self._hist_index -= 1
        # Если уже на 0 — остаёмся на первом элементе (не выходим за начало)
        self._input.setText(self._history[self._hist_index])

    def _history_down(self) -> None:
        """Перейти к более новой записи истории."""
        if not self._history:
            return
        if self._hist_index < len(self._history) - 1:
            self._hist_index += 1
            self._input.setText(self._history[self._hist_index])
        else:
            # За последней записью — пустое поле (новая строка)
            self._hist_index = len(self._history)
            self._input.clear()
