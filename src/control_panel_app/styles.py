from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtGui import QColor, QPalette


DEFAULT_COMPACT_UI = True


@dataclass(frozen=True, slots=True)
class UiProfile:
    default_width: int
    default_height: int
    min_width: int
    min_height: int
    dashboard_breakpoint: int
    dashboard_tab_min: tuple[int, int]
    settings_tab_min: tuple[int, int]
    inventory_tab_min: tuple[int, int]
    help_tab_min: tuple[int, int]
    dashboard_main_sizes_horizontal: tuple[int, int]
    dashboard_main_sizes_vertical: tuple[int, int]
    dashboard_side_sizes: tuple[int, int]


STANDARD_UI_PROFILE = UiProfile(
    default_width=1360,
    default_height=860,
    min_width=860,
    min_height=620,
    dashboard_breakpoint=1220,
    dashboard_tab_min=(980, 920),
    settings_tab_min=(980, 760),
    inventory_tab_min=(1180, 860),
    help_tab_min=(900, 720),
    dashboard_main_sizes_horizontal=(900, 460),
    dashboard_main_sizes_vertical=(620, 340),
    dashboard_side_sizes=(420, 320),
)


COMPACT_UI_PROFILE = UiProfile(
    default_width=1180,
    default_height=720,
    min_width=760,
    min_height=540,
    dashboard_breakpoint=1080,
    dashboard_tab_min=(840, 760),
    settings_tab_min=(820, 660),
    inventory_tab_min=(980, 760),
    help_tab_min=(820, 620),
    dashboard_main_sizes_horizontal=(760, 380),
    dashboard_main_sizes_vertical=(520, 300),
    dashboard_side_sizes=(360, 250),
)


def get_ui_profile(compact: bool) -> UiProfile:
    return COMPACT_UI_PROFILE if compact else STANDARD_UI_PROFILE


def build_app_palette() -> QPalette:
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor("#f4f7fb"))
    palette.setColor(QPalette.WindowText, QColor("#172233"))
    palette.setColor(QPalette.Base, QColor("#ffffff"))
    palette.setColor(QPalette.AlternateBase, QColor("#eef3f9"))
    palette.setColor(QPalette.ToolTipBase, QColor("#ffffff"))
    palette.setColor(QPalette.ToolTipText, QColor("#172233"))
    palette.setColor(QPalette.Text, QColor("#172233"))
    palette.setColor(QPalette.Button, QColor("#ffffff"))
    palette.setColor(QPalette.ButtonText, QColor("#172233"))
    palette.setColor(QPalette.BrightText, QColor("#ffffff"))
    palette.setColor(QPalette.Highlight, QColor("#2374e1"))
    palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))
    palette.setColor(QPalette.Link, QColor("#2374e1"))
    palette.setColor(QPalette.PlaceholderText, QColor("#6b7280"))
    return palette


def build_app_chrome_stylesheet() -> str:
    return """
            QWidget {
                color: #172233;
            }
            QDialog, QMessageBox {
                background: #f4f7fb;
            }
            QMessageBox QLabel {
                color: #172233;
            }
            QMessageBox QPushButton,
            QDialog QPushButton {
                color: #172233;
                background: #ffffff;
                border: 1px solid #d0d9e7;
            }
            QMessageBox QPushButton:hover,
            QDialog QPushButton:hover {
                background: #f8fbff;
                border-color: #98b4df;
            }
            QPushButton:disabled,
            QMessageBox QPushButton:disabled,
            QDialog QPushButton:disabled {
                color: #94a3b8;
                background: #f1f5f9;
                border-color: #d9e2ef;
            }
            QLineEdit, QComboBox, QPlainTextEdit, QTableWidget, QDoubleSpinBox, QSpinBox {
                color: #172233;
                background: #ffffff;
                selection-background-color: #dbeafe;
            }
            QLineEdit:disabled,
            QComboBox:disabled,
            QPlainTextEdit:disabled,
            QTableWidget:disabled,
            QDoubleSpinBox:disabled,
            QSpinBox:disabled {
                color: #94a3b8;
                background: #f8fafc;
            }
            QTableView::item:selected,
            QTableWidget::item:selected {
                background: #dbeafe;
                color: #172233;
            }
            QTableView::item:selected:active,
            QTableWidget::item:selected:active {
                background: #bfdbfe;
                color: #172233;
            }
            QTableView::item:selected:!active,
            QTableWidget::item:selected:!active {
                background: #e2e8f0;
                color: #334155;
            }
            QHeaderView::section,
            QTableCornerButton::section {
                color: #172233;
                background: #eef3f9;
                border: 0;
                border-bottom: 1px solid #d0d9e7;
            }
            QTabWidget::pane {
                background: #ffffff;
                border: 1px solid #d9e2ef;
            }
            QTabBar::tab {
                background: #e9eef6;
                color: #334155;
            }
            QTabBar::tab:selected {
                background: #ffffff;
                color: #172233;
            }
            QTabBar::tab:!selected {
                background: #e9eef6;
                color: #475569;
            }
            QMenu {
                background: #ffffff;
                color: #172233;
                border: 1px solid #d0d9e7;
            }
            QMenu::item:selected {
                background: #dbeafe;
                color: #172233;
            }
            """


def build_stylesheet(compact: bool) -> str:
    metrics = {
        "toolbar_spacing": "6px" if compact else "8px",
        "toolbar_padding": "4px" if compact else "6px",
        "group_radius": "10px" if compact else "12px",
        "group_margin_top": "10px" if compact else "12px",
        "group_title_left": "10px" if compact else "12px",
        "metric_radius": "12px" if compact else "14px",
        "card_padding": "10px 12px 10px 12px" if compact else "12px 14px 12px 14px",
        "section_radius": "10px" if compact else "12px",
        "section_padding": "2px 6px 6px 6px" if compact else "4px 8px 8px 8px",
        "title_size": "24px" if compact else "30px",
        "subtitle_size": "12px" if compact else "13px",
        "metric_title_size": "11px" if compact else "12px",
        "metric_value_size": "18px" if compact else "22px",
        "metric_helper_size": "10px" if compact else "11px",
        "selection_padding": "8px 10px" if compact else "10px 12px",
        "toolbutton_padding": "4px 2px" if compact else "6px 2px",
        "tab_padding": "7px 12px" if compact else "10px 18px",
        "button_height": "26px" if compact else "34px",
        "button_max_height": "26px" if compact else "34px",
        "button_radius": "7px" if compact else "9px",
        "button_padding": "2px 7px" if compact else "5px 10px",
        "button_font_size": "12px" if compact else "13px",
        "input_radius": "8px" if compact else "10px",
        "header_padding": "6px" if compact else "8px",
        "table_item_padding": "2px 4px" if compact else "4px 6px",
    }
    return f"""
            QMainWindow {{
                background: #f4f7fb;
            }}
            QToolBar {{
                spacing: {metrics["toolbar_spacing"]};
                padding: {metrics["toolbar_padding"]};
                background: #ffffff;
                border-bottom: 1px solid #d9e2ef;
            }}
            QLabel#appTitle {{
                font-size: {metrics["title_size"]};
                font-weight: 800;
                color: #172233;
            }}
            QLabel#appSubtitle {{
                color: #536173;
                font-size: {metrics["subtitle_size"]};
            }}
            QGroupBox {{
                font-weight: 600;
                border: 1px solid #d9e2ef;
                border-radius: {metrics["group_radius"]};
                margin-top: {metrics["group_margin_top"]};
                background: #ffffff;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: {metrics["group_title_left"]};
                padding: 0 6px;
            }}
            QFrame#metricCard {{
                border-radius: {metrics["metric_radius"]};
                border: 1px solid #d9e2ef;
                background: #ffffff;
            }}
            QFrame#collapsibleSection {{
                border: 1px solid #d9e2ef;
                border-radius: {metrics["section_radius"]};
                background: #ffffff;
                padding: {metrics["section_padding"]};
            }}
            QFrame[accent="green"] {{
                border-left: 5px solid #1f9d64;
            }}
            QFrame[accent="blue"] {{
                border-left: 5px solid #2374e1;
            }}
            QFrame[accent="orange"] {{
                border-left: 5px solid #d97706;
            }}
            QLabel#metricTitle {{
                color: #5b6472;
                font-size: {metrics["metric_title_size"]};
                font-weight: 600;
            }}
            QLabel#metricValue {{
                color: #172233;
                font-size: {metrics["metric_value_size"]};
                font-weight: 700;
            }}
            QLabel#metricHelper {{
                color: #6b7280;
                font-size: {metrics["metric_helper_size"]};
            }}
            QLabel#selectionSummary {{
                color: #334155;
                background: #f8fafc;
                border: 1px solid #d9e2ef;
                border-radius: {metrics["section_radius"]};
                padding: {metrics["selection_padding"]};
            }}
            QToolButton {{
                border: 0;
                font-weight: 700;
                color: #172233;
                background: transparent;
                text-align: left;
                padding: {metrics["toolbutton_padding"]};
            }}
            QTabWidget::pane {{
                border: 1px solid #d9e2ef;
                background: #ffffff;
                border-radius: 12px;
                top: -1px;
            }}
            QTabBar::tab {{
                background: #e9eef6;
                color: #334155;
                padding: {metrics["tab_padding"]};
                margin-right: 4px;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }}
            QTabBar::tab:selected {{
                background: #ffffff;
                font-weight: 700;
            }}
            QPushButton {{
                min-height: {metrics["button_height"]};
                max-height: {metrics["button_max_height"]};
                border-radius: {metrics["button_radius"]};
                border: 1px solid #d0d9e7;
                background: #ffffff;
                padding: {metrics["button_padding"]};
                font-size: {metrics["button_font_size"]};
            }}
            QPushButton:hover {{
                background: #f8fbff;
                border-color: #98b4df;
            }}
            QPushButton:disabled {{
                color: #94a3b8;
                background: #f1f5f9;
                border-color: #d9e2ef;
            }}
            QPushButton#primary {{
                background: #2374e1;
                color: white;
                border-color: #2374e1;
                font-weight: 700;
            }}
            QPushButton#primary:hover {{
                background: #1b63c4;
            }}
            QPushButton#primary:disabled {{
                color: #e2e8f0;
                background: #93c5fd;
                border-color: #93c5fd;
            }}
            QLineEdit, QComboBox, QPlainTextEdit, QTableWidget, QDoubleSpinBox, QSpinBox {{
                border: 1px solid #d0d9e7;
                border-radius: {metrics["input_radius"]};
                background: #ffffff;
                selection-background-color: #dbeafe;
            }}
            QLineEdit:disabled, QComboBox:disabled, QPlainTextEdit:disabled, QTableWidget:disabled, QDoubleSpinBox:disabled, QSpinBox:disabled {{
                color: #94a3b8;
                background: #f8fafc;
            }}
            QTableView::item {{
                padding: {metrics["table_item_padding"]};
            }}
            QTableView::item:selected, QTableWidget::item:selected {{
                background: #dbeafe;
                color: #172233;
            }}
            QTableView::item:selected:active, QTableWidget::item:selected:active {{
                background: #bfdbfe;
            }}
            QTableView::item:selected:!active, QTableWidget::item:selected:!active {{
                background: #e2e8f0;
                color: #334155;
            }}
            QHeaderView::section {{
                background: #eef3f9;
                border: 0;
                border-bottom: 1px solid #d0d9e7;
                padding: {metrics["header_padding"]};
                font-weight: 700;
            }}
            """
