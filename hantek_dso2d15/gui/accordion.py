"""Переиспользуемый виджет CollapsibleSection — аккордеон.

Заголовок 32px с названием (uppercase) и шевроном ▾/▸.
По клику заголовка разворачивает/сворачивает тело (body).
Используется в правом доке Scope для 8 панелей.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

# ---------------------------------------------------------------------------
# Константы стиля (тёмная тема прибора)
# ---------------------------------------------------------------------------

_HEADER_BG      = "#1B1E24"
_HEADER_FG      = "#AEB4BF"   # текст названия
_CHEVRON_FG     = "#6E747F"   # шеврон

_CHEVRON_EXPANDED  = "▾"   # секция развёрнута
_CHEVRON_COLLAPSED = "▸"   # секция свёрнута

HEADER_HEIGHT = 32         # высота шапки (для клампа высоты свёрнутой секции)
_QWIDGETSIZE_MAX = 16_777_215   # снятие ограничения высоты (Qt-предел)

# QSS применяется через setStyleSheet на экземпляре CollapsibleSection;
# objectName-селекторы изолируют стиль от остальных виджетов приложения.
_HEADER_QSS = f"""
QWidget#CollapsibleHeader {{
    background: {_HEADER_BG};
    border: none;
}}
QLabel#SectionTitle {{
    color: {_HEADER_FG};
    font-size: 11px;
    font-weight: 600;
    background: transparent;
}}
QLabel#SectionChevron {{
    color: {_CHEVRON_FG};
    font-size: 11px;
    background: transparent;
}}
"""


# ---------------------------------------------------------------------------
# Внутренний виджет заголовка
# ---------------------------------------------------------------------------

class _HeaderWidget(QWidget):
    """Кликабельный заголовок секции: название (uppercase) + шеврон справа."""

    clicked: Signal = Signal()

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("CollapsibleHeader")
        self.setFixedHeight(32)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )

        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(4)

        self._title_label = QLabel(title.upper())
        self._title_label.setObjectName("SectionTitle")

        self._chevron_label = QLabel(_CHEVRON_EXPANDED)
        self._chevron_label.setObjectName("SectionChevron")

        lay.addWidget(self._title_label)
        lay.addStretch()
        lay.addWidget(self._chevron_label)

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        super().mousePressEvent(event)
        self.clicked.emit()


# ---------------------------------------------------------------------------
# Публичный виджет
# ---------------------------------------------------------------------------

class CollapsibleSection(QWidget):
    """Виджет-аккордеон: заголовок 32px + тело, скрываемое по клику.

    Args:
        title:    Текст заголовка (автоматически uppercase).
        body:     Дочерний виджет тела секции.
        expanded: Начальное состояние (по умолчанию развёрнут).
        parent:   Родительский QWidget (опционально).

    Signals:
        toggled(bool): Эмитируется при клике по заголовку или при явном
                       вызове ``set_expanded(..., emit=True)``.
                       Значение — новое состояние expanded.
    """

    toggled: Signal = Signal(bool)

    def __init__(
        self,
        title: str,
        body: QWidget,
        expanded: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._body = body
        self._expanded: bool = expanded

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Заголовок — кликабельный виджет
        self._header = _HeaderWidget(title)
        self._header.clicked.connect(self._on_header_clicked)
        lay.addWidget(self._header)

        # Тело секции
        lay.addWidget(body)

        # Применить QSS
        self.setStyleSheet(_HEADER_QSS)

        # Ярлык для удобного доступа тестов к лейблу шеврона
        self._chevron: QLabel = self._header._chevron_label

        # Выставить начальное состояние (без эмиссии сигнала)
        self._apply_state()

    # ------------------------------------------------------------------
    # Приватные методы
    # ------------------------------------------------------------------

    def _apply_state(self) -> None:
        """Синхронизировать видимость body, символ шеврона и кламп высоты.

        В свёрнутом виде секция ограничена высотой шапки — чтобы внутри
        QSplitter свёрнутые секции не растягивались и не «съедали» место.
        """
        self._body.setVisible(self._expanded)
        self._chevron.setText(
            _CHEVRON_EXPANDED if self._expanded else _CHEVRON_COLLAPSED
        )
        if self._expanded:
            self.setMaximumHeight(_QWIDGETSIZE_MAX)
        else:
            self.setMaximumHeight(HEADER_HEIGHT)

    def _on_header_clicked(self) -> None:
        """Обработчик клика по заголовку — переключает состояние."""
        self.set_expanded(not self._expanded, emit=True)

    # ------------------------------------------------------------------
    # Публичный API
    # ------------------------------------------------------------------

    def is_expanded(self) -> bool:
        """Возвращает текущее состояние (True — развёрнут)."""
        return self._expanded

    def set_expanded(self, value: bool, *, emit: bool = False) -> None:
        """Установить состояние развёрнутости.

        Args:
            value: True — развернуть, False — свернуть.
            emit:  Если True — эмитировать ``toggled(value)``.
        """
        self._expanded = value
        self._apply_state()
        if emit:
            self.toggled.emit(value)

    def header(self) -> QWidget:
        """Вернуть виджет заголовка (для objectName/стиля)."""
        return self._header
