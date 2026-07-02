# CSS/QSS styling variables and themes for Video Downloader Pro.

DARK_THEME_QSS = """
QMainWindow {
    background-color: #0F172A;
}

QWidget {
    color: #F8FAFC;
    font-family: "Segoe UI", "Inter", sans-serif;
    font-size: 13px;
}

/* Header & Sidebar Panels */
QFrame#sidebar, QFrame#detailPanel, QFrame#queuePanel {
    background-color: #1E293B;
    border: 1px solid #334155;
    border-radius: 12px;
}

QLabel#titleLabel {
    font-size: 20px;
    font-weight: bold;
    color: #F8FAFC;
    background: transparent;
}

QLabel#headerText {
    font-size: 15px;
    font-weight: 600;
    color: #38BDF8;
}

/* Input Fields */
QLineEdit {
    background-color: #0F172A;
    border: 1px solid #475569;
    border-radius: 8px;
    padding: 8px 12px;
    color: #F1F5F9;
    selection-background-color: #38BDF8;
}

QLineEdit:focus {
    border: 1px solid #38BDF8;
}

/* Buttons */
QPushButton {
    background-color: #2563EB;
    border: none;
    border-radius: 8px;
    padding: 8px 16px;
    color: #FFFFFF;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #3B82F6;
}

QPushButton:pressed {
    background-color: #1D4ED8;
}

QPushButton:disabled {
    background-color: #475569;
    color: #94A3B8;
}

/* Secondary & Cancel Buttons */
QPushButton#secondaryBtn {
    background-color: #334155;
    border: 1px solid #475569;
}

QPushButton#secondaryBtn:hover {
    background-color: #475569;
}

QPushButton#actionBtn_pause, QPushButton#actionBtn_resume, QPushButton#actionBtn_cancel {
    background-color: #1E293B;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 4px 8px;
    font-size: 11px;
}

QPushButton#actionBtn_pause:hover {
    background-color: #EAB308;
    color: #0F172A;
}

QPushButton#actionBtn_resume:hover {
    background-color: #22C55E;
    color: #FFFFFF;
}

QPushButton#actionBtn_cancel:hover {
    background-color: #EF4444;
    color: #FFFFFF;
}

/* Combo Boxes & Spin Boxes */
QComboBox, QSpinBox {
    background-color: #0F172A;
    border: 1px solid #475569;
    border-radius: 6px;
    padding: 6px 12px;
    color: #F1F5F9;
}

QComboBox:on, QSpinBox:focus {
    border: 1px solid #38BDF8;
}

QComboBox::drop-down {
    border: none;
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 20px;
}

/* List Widgets & Tables */
QListWidget, QTableWidget {
    background-color: #1E293B;
    border: 1px solid #334155;
    border-radius: 8px;
    gridline-color: #334155;
    alternate-background-color: #0F172A;
}

QTableWidget::item {
    padding: 8px;
}

QHeaderView::section {
    background-color: #0F172A;
    color: #94A3B8;
    padding: 6px;
    border: none;
    font-weight: bold;
}

/* Scroll Bars */
QScrollBar:vertical {
    border: none;
    background-color: #0F172A;
    width: 10px;
    margin: 0px;
    border-radius: 5px;
}

QScrollBar::handle:vertical {
    background-color: #475569;
    min-height: 20px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background-color: #38BDF8;
}

/* Progress Bars */
QProgressBar {
    border: 1px solid #334155;
    border-radius: 6px;
    text-align: center;
    background-color: #0F172A;
    font-weight: bold;
}

QProgressBar::chunk {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                      stop:0 #3B82F6, stop:1 #8B5CF6);
    border-radius: 5px;
}

/* Tabs */
QTabWidget::pane {
    border: 1px solid #334155;
    background-color: #1E293B;
    border-radius: 8px;
}

QTabBar::tab {
    background-color: #0F172A;
    border: 1px solid #334155;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    padding: 8px 16px;
    margin-right: 4px;
    color: #94A3B8;
}

QTabBar::tab:selected {
    background-color: #1E293B;
    border-bottom: none;
    color: #F8FAFC;
    font-weight: 600;
}
"""

LIGHT_THEME_QSS = """
QMainWindow {
    background-color: #F1F5F9;
}

QWidget {
    color: #1E293B;
    font-family: "Segoe UI", "Inter", sans-serif;
    font-size: 13px;
}

/* Header & Panels */
QFrame#sidebar, QFrame#detailPanel, QFrame#queuePanel {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 12px;
}

QLabel#titleLabel {
    font-size: 20px;
    font-weight: bold;
    color: #0F172A;
}

QLabel#headerText {
    font-size: 15px;
    font-weight: 600;
    color: #0284C7;
}

/* Inputs */
QLineEdit {
    background-color: #F8FAFC;
    border: 1px solid #CBD5E1;
    border-radius: 8px;
    padding: 8px 12px;
    color: #1E293B;
}

QLineEdit:focus {
    border: 1px solid #0284C7;
}

/* Buttons */
QPushButton {
    background-color: #0284C7;
    border: none;
    border-radius: 8px;
    padding: 8px 16px;
    color: #FFFFFF;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #0369A1;
}

QPushButton:pressed {
    background-color: #075985;
}

QPushButton#secondaryBtn {
    background-color: #E2E8F0;
    border: 1px solid #CBD5E1;
    color: #1E293B;
}

QPushButton#secondaryBtn:hover {
    background-color: #CBD5E1;
}

QPushButton#actionBtn_pause, QPushButton#actionBtn_resume, QPushButton#actionBtn_cancel {
    background-color: #F8FAFC;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 4px 8px;
    font-size: 11px;
}

/* Combos & Spins */
QComboBox, QSpinBox {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 6px 12px;
}

/* Progress Bars */
QProgressBar {
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    text-align: center;
    background-color: #E2E8F0;
}

QProgressBar::chunk {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                      stop:0 #0284C7, stop:1 #3B82F6);
    border-radius: 5px;
}

/* Tabs */
QTabWidget::pane {
    border: 1px solid #CBD5E1;
    background-color: #FFFFFF;
    border-radius: 8px;
}

QTabBar::tab {
    background-color: #E2E8F0;
    border: 1px solid #CBD5E1;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    padding: 8px 16px;
    color: #64748B;
}

QTabBar::tab:selected {
    background-color: #FFFFFF;
    color: #0F172A;
    font-weight: 600;
}
"""
