"""Дизайн-система клиента DSO2D15 — токены и глобальный стиль.

Единый источник цветов/шрифтов/радиусов по авторитетному макету
``design/design_handoff_dso2d15_ui``. Применяется через ``apply_theme(app)``.

SCPI-привязка идёт по frozen reference, а ВИЗУАЛ — пиксель-в-пиксель по макету.
"""
from __future__ import annotations

from PySide6.QtGui import QFont

# ---------------------------------------------------------------------------
# Палитра (Design Tokens → Colors)
# ---------------------------------------------------------------------------
WINDOW_BG = "#0E0F12"     # фон окна, поля ввода
GRATICULE_BG = "#08090B"  # область осциллограммы
DOCK_BG = "#13151A"       # правый док
PANEL_BG = "#1B1E24"      # заголовки-аккордеоны, карточки
INSET_BG = "#16181D"      # тулбар, статус-бар, заголовки таблиц
BORDER = "#2A2D34"        # стандартные 1px границы
BORDER_LIGHT = "#3A3F49"  # обводка чекбоксов/ползунков
DIVIDER = "#22252C"       # разделители панелей/строк

TEXT_PRIMARY = "#E6E9EF"   # значения, акцент
TEXT_SECONDARY = "#C5C9D1" # основной текст
TEXT_MUTED = "#9AA0AC"     # подписи
TEXT_FAINT = "#6E747F"     # капшены, шевроны
TEXT_DISABLED = "#5A606C"

CH1 = "#F2C300"   # жёлтый
CH2 = "#23C8E6"   # cyan (по макету; не зелёный)
MATH = "#C77DFF"  # magenta — math/FFT
CH4 = "#FF7DD8"
CURSOR = "#C5C9D1"

OK_GREEN = "#37D67A"   # run, connected, primary
ERR_RED = "#E5484D"    # stop, errors
WARN_AMBER = "#F5A623" # single, auto sweep, warnings

#: Цветокод трасс/каналов (централизован — импортируют plot/панели).
CH_COLORS = {1: CH1, 2: CH2, 3: MATH, 4: CH4}

# ---------------------------------------------------------------------------
# Типографика
# ---------------------------------------------------------------------------
#: UI-шрифт (Inter в макете; на Windows допустим Segoe UI).
FONT_UI = "Segoe UI"
#: Моноширинный для числовых ридаутов/SCPI (JetBrains Mono → Consolas).
FONT_MONO = "'JetBrains Mono', 'Consolas', monospace"


def _hex_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def rgba(hex_color: str, alpha: float) -> str:
    """``rgba(r,g,b,a)`` из 6-значного hex. Qt QSS НЕ понимает 8-значный
    ``#RRGGBBAA`` (трактует как #AARRGGBB) — поэтому тинты задаём через rgba()."""
    r, g, b = _hex_rgb(hex_color)
    return f"rgba({r},{g},{b},{alpha})"


def app_font() -> QFont:
    """Базовый шрифт приложения (Inter/Segoe UI 9pt)."""
    f = QFont(FONT_UI, 9)
    f.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    return f


# ---------------------------------------------------------------------------
# Глобальный стиль (QSS)
# ---------------------------------------------------------------------------
STYLESHEET = f"""
QMainWindow, QWidget {{ background: {WINDOW_BG}; color: {TEXT_SECONDARY};
    font-family: '{FONT_UI}', sans-serif; font-size: 11px; }}

/* Тулбар (48px) */
QToolBar {{ background: {INSET_BG}; border: none; border-bottom: 1px solid {BORDER};
    spacing: 8px; padding: 7px 10px; }}

/* Поля / выпадашки (control field 26px) */
QComboBox {{ background: {WINDOW_BG}; border: 1px solid {BORDER}; border-radius: 4px;
    padding: 4px 8px; color: {TEXT_PRIMARY}; min-height: 18px; }}
QComboBox#resources {{ min-width: 320px; }}
QComboBox::drop-down {{ border: none; width: 18px; }}
QComboBox::down-arrow {{ width: 0; height: 0; border-left: 4px solid transparent;
    border-right: 4px solid transparent; border-top: 5px solid {TEXT_MUTED}; margin-right: 6px; }}
QComboBox QAbstractItemView {{ background: {PANEL_BG}; color: {TEXT_PRIMARY};
    border: 1px solid {BORDER}; selection-background-color: rgba(55,214,122,0.16); outline: none; }}

QDoubleSpinBox, QSpinBox, QLineEdit {{ background: {WINDOW_BG}; border: 1px solid {BORDER};
    border-radius: 4px; padding: 3px 18px 3px 6px; color: {TEXT_PRIMARY}; min-height: 18px; }}
QLineEdit {{ padding: 3px 6px; }}
QDoubleSpinBox::up-button, QSpinBox::up-button {{ subcontrol-origin: border;
    subcontrol-position: top right; width: 16px; border-left: 1px solid {BORDER};
    background: {PANEL_BG}; border-top-right-radius: 4px; }}
QDoubleSpinBox::down-button, QSpinBox::down-button {{ subcontrol-origin: border;
    subcontrol-position: bottom right; width: 16px; border-left: 1px solid {BORDER};
    background: {PANEL_BG}; border-bottom-right-radius: 4px; }}
QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover,
QSpinBox::up-button:hover, QSpinBox::down-button:hover {{ background: {BORDER}; }}
QDoubleSpinBox::up-arrow, QSpinBox::up-arrow {{ width: 0; height: 0;
    border-left: 4px solid transparent; border-right: 4px solid transparent;
    border-bottom: 5px solid {TEXT_MUTED}; }}
QDoubleSpinBox::down-arrow, QSpinBox::down-arrow {{ width: 0; height: 0;
    border-left: 4px solid transparent; border-right: 4px solid transparent;
    border-top: 5px solid {TEXT_MUTED}; }}

QCheckBox {{ color: {TEXT_MUTED}; spacing: 6px; }}
QCheckBox::indicator {{ width: 14px; height: 14px; border: 1px solid {BORDER_LIGHT};
    border-radius: 3px; background: {WINDOW_BG}; }}
QCheckBox::indicator:checked {{ background: {OK_GREEN}; border-color: {OK_GREEN}; }}

/* Кнопки */
QPushButton {{ background: {PANEL_BG}; border: 1px solid {BORDER}; border-radius: 5px;
    padding: 6px 14px; color: {TEXT_SECONDARY}; font-weight: 600; }}
QPushButton:hover {{ border-color: {BORDER_LIGHT}; }}
QPushButton:disabled {{ color: {TEXT_DISABLED}; }}
QPushButton#run {{ background: rgba(55,214,122,0.16); border-color: #2F4A3C; color: {OK_GREEN}; }}
QPushButton#stop {{ background: rgba(229,72,77,0.16); border-color: #5A2A2C; color: {ERR_RED}; }}
QPushButton#single {{ color: {WARN_AMBER}; border-color: #6A521E; }}
QPushButton#log:checked {{ background: rgba(229,72,77,0.20); border-color: #5A2A2C; color: {ERR_RED}; }}
QPushButton#scpi:checked {{ background: rgba(55,214,122,0.16); border-color: #2F4A3C; color: {OK_GREEN}; }}

/* Статус-бар (28px, моно) */
QStatusBar {{ background: {INSET_BG}; color: {TEXT_FAINT};
    font-family: {FONT_MONO}; font-size: 11px; }}
QStatusBar::item {{ border: none; }}

/* Док и табы */
QDockWidget {{ color: {TEXT_MUTED}; titlebar-close-icon: none; titlebar-normal-icon: none; }}
QDockWidget::title {{ background: {INSET_BG}; padding: 5px 10px; }}
QTabWidget::pane {{ border: none; background: {DOCK_BG}; }}
QTabBar::tab {{ background: {INSET_BG}; color: #7A808C; padding: 9px 16px; border: none;
    font-weight: 600; }}
QTabBar::tab:selected {{ color: {TEXT_PRIMARY}; border-bottom: 2px solid {OK_GREEN};
    background: {DOCK_BG}; }}

/* Заголовок-секция панели (32px, uppercase) */
QLabel#section {{ background: {PANEL_BG}; color: #AEB4BF; font-weight: 600;
    padding: 8px 12px; letter-spacing: 0.7px; }}

/* Подгруппы (модуляция/burst) */
QGroupBox {{ border: 1px solid {BORDER}; border-radius: 6px; margin-top: 10px;
    padding: 8px; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 8px; padding: 0 4px;
    color: {TEXT_MUTED}; }}

/* Прогресс-бар (sweep) */
QProgressBar {{ background: {WINDOW_BG}; border: 1px solid {BORDER}; border-radius: 4px;
    height: 8px; text-align: center; color: {TEXT_FAINT}; }}
QProgressBar::chunk {{ background: {OK_GREEN}; border-radius: 3px; }}

/* Таблица (измерения) */
QTableWidget {{ background: {WINDOW_BG}; gridline-color: {DIVIDER};
    color: {TEXT_SECONDARY}; border: 1px solid {BORDER}; }}
QHeaderView::section {{ background: {INSET_BG}; color: {TEXT_FAINT};
    border: none; padding: 4px; font-weight: 600; }}

/* SCPI-терминал */
QPlainTextEdit {{ background: {GRATICULE_BG}; color: {TEXT_SECONDARY};
    border: 1px solid {BORDER}; font-family: {FONT_MONO}; font-size: 12px; }}

/* Скроллбары */
QScrollBar:vertical {{ background: {WINDOW_BG}; width: 10px; margin: 0; }}
QScrollBar::handle:vertical {{ background: {BORDER}; border-radius: 5px; min-height: 24px; }}
QScrollBar::handle:vertical:hover {{ background: {BORDER_LIGHT}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
"""


def apply_theme(app) -> None:
    """Применить шрифт и глобальный стиль к QApplication."""
    app.setFont(app_font())
    app.setStyleSheet(STYLESHEET)
