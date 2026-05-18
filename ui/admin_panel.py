import re
from datetime import date

from PyQt5.QtCore import QDate, Qt
from PyQt5.QtGui import QFont, QColor, QBrush, QPalette
from PyQt5.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDoubleSpinBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QFrame,
    QHeaderView,
)

from services import attendance_service, employee_service, payroll_service
import services.exceptions as service_exceptions

AuthenticationError = getattr(service_exceptions, "AuthenticationError", Exception)
AuthorizationError = getattr(service_exceptions, "AuthorizationError", Exception)
DatabaseError = getattr(service_exceptions, "DatabaseError", Exception)
DuplicateAttendanceError = getattr(service_exceptions, "DuplicateAttendanceError", Exception)
EmployeeNotFoundError = getattr(service_exceptions, "EmployeeNotFoundError", Exception)
ValidationError = getattr(service_exceptions, "ValidationError", Exception)
NotFoundError = getattr(service_exceptions, "NotFoundError", EmployeeNotFoundError)


class AdminPanel(QWidget):
    PANEL_BACKGROUND = "#0b1220"
    PANEL_SURFACE = "#101a2b"
    PANEL_SURFACE_ALT = "#0e1728"
    PANEL_BORDER = "#22324f"
    PANEL_TEXT = "#e5eefb"
    PANEL_MUTED_TEXT = "#95a8c7"
    PANEL_ACCENT = "#2e6bff"

    TABLE_BASE_COLOR = "#111b2e"
    TABLE_ALT_COLOR = "#0e1728"
    TABLE_BORDER_COLOR = "#22324f"
    TABLE_GRID_COLOR = "#24344f"
    TABLE_TEXT_COLOR = "#e5eefb"
    TABLE_MUTED_TEXT_COLOR = "#aab4c3"
    TABLE_SELECTION_COLOR = "#284b93"
    TABLE_SELECTION_TEXT_COLOR = "#ffffff"
    TABLE_HEADER_COLOR = "#17253d"
    TABLE_HEADER_TEXT_COLOR = "#dce7f7"

    def __init__(self, user):
        super().__init__()

        self.user = user
        self._employee_cache = []
        self._employee_lookup = {}
        self._attendance_rows = []
        self._payroll_rows = []
        
        # Edit mode state
        self._edit_mode = False
        self._editing_employee_id = None

        self.setWindowTitle("Çalışan Yoklama Sistemi | Admin Paneli")
        self.resize(1500, 900)

        self._build_ui()
        self._apply_style()
        self._connect_signals()

        if not self._is_admin_user():
            self._show_message(
                "Yetki Uyarısı",
                "Bu ekran yalnızca admin kullanıcılar içindir.",
                QMessageBox.Warning,
            )
            self.setEnabled(False)
            self.close()
            return

        self._refresh_all()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        header_frame = QFrame()
        header_frame.setObjectName("headerFrame")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(8, 4, 8, 10)
        header_layout.setSpacing(14)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)

        self.title_label = QLabel("Admin Paneli")
        self.title_label.setObjectName("titleLabel")

        self.subtitle_label = QLabel(self._build_user_caption())
        self.subtitle_label.setObjectName("subtitleLabel")

        title_box.addWidget(self.title_label)
        title_box.addWidget(self.subtitle_label)

        header_layout.addLayout(title_box)
        header_layout.addStretch()

        self.logout_button = QPushButton("Çıkış Yap")
        self.logout_button.setObjectName("secondaryButton")

        self.close_button = QPushButton("Kapat")
        self.close_button.setObjectName("dangerButton")

        header_layout.addWidget(self.logout_button)
        header_layout.addWidget(self.close_button)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setTabPosition(QTabWidget.North)
        self.tabs.setElideMode(Qt.ElideNone)

        self._build_dashboard_tab()
        self._build_employees_tab()
        self._build_attendance_tab()
        self._build_payroll_tab()

        main_layout.addWidget(header_frame)
        main_layout.addWidget(self.tabs)

    def _apply_style(self):
        self.setFont(QFont("Segoe UI", 11))
        self.setStyleSheet(
            """
            QWidget {
                background: #0b1220;
                color: #e5eefb;
            }

            QFrame#headerFrame {
                background: transparent;
                border: none;
            }

            QGroupBox {
                background: #101a2b;
                border: 1px solid #22324f;
                border-radius: 14px;
                margin-top: 16px;
                padding-top: 16px;
            }

            QTabWidget::pane {
                background: #101a2b;
                border: none;
                top: -1px;
                border-radius: 0 0 12px 12px;
            }

            QLabel#titleLabel {
                font-size: 30px;
                font-weight: 700;
                color: #f8fbff;
            }

            QLabel#subtitleLabel {
                color: #8ea2c7;
                font-size: 14px;
            }

            QLabel {
                color: #d7e3f5;
                font-size: 15px;
                background: transparent;
            }

            QLineEdit,
            QComboBox,
            QDateEdit,
            QDoubleSpinBox,
            QSpinBox {
                background: #0a1324;
                border: 1px solid #30415f;
                border-radius: 12px;
                padding: 12px 14px;
                color: #f4f7fb;
                selection-background-color: #2e6bff;
                font-size: 15px;
            }

            QLineEdit:focus,
            QComboBox:focus,
            QDateEdit:focus,
            QDoubleSpinBox:focus,
            QSpinBox:focus {
                border: 1px solid #62a0ff;
            }

            QComboBox::drop-down {
                border: 0px;
                width: 24px;
            }

            QComboBox QAbstractItemView {
                background: #0a1324;
                border: 1px solid #30415f;
                selection-background-color: #2e6bff;
                color: #f4f7fb;
            }

            QPushButton {
                border: none;
                border-radius: 12px;
                padding: 12px 18px;
                font-weight: 600;
                color: white;
                font-size: 15px;
            }

            QPushButton#primaryButton {
                background: #2e6bff;
            }

            QPushButton#primaryButton:hover {
                background: #2458d6;
            }

            QPushButton#secondaryButton {
                background: #2a3a57;
            }

            QPushButton#secondaryButton:hover {
                background: #35486a;
            }

            QPushButton#dangerButton {
                background: #8b2f3a;
            }

            QPushButton#dangerButton:hover {
                background: #a23a47;
            }

            QPushButton#activateButton {
                background: #2e8b57;
            }

            QPushButton#activateButton:hover {
                background: #247645;
            }

            QPushButton#deactivateButton {
                background: #b33a3a;
            }

            QPushButton#deactivateButton:hover {
                background: #9b2d2d;
            }

            QTabBar::tab {
                background: #101a2b;
                color: #9fb0cc;
                padding: 14px 24px;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
                margin-right: 4px;
                margin-bottom: 0px;
                border: 1px solid transparent;
                min-height: 28px;
                font-size: 18px;
                font-weight: 600;
            }

            QTabBar::tab:selected {
                background: #16253b;
                color: #ffffff;
            }

            QGroupBox {
                font-weight: 600;
                margin-top: 12px;
                padding-top: 18px;
            }

            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
            }

            QTableWidget::item {
                padding: 10px 8px;
            }

            QLabel#statTitleLabel {
                color: #8ea2c7;
                font-size: 20px;
                font-weight: 600;
                background: transparent;
            }

            QLabel#statValueLabel {
                color: #ffffff;
                font-size: 52px;
                font-weight: 700;
                background: transparent;
            }
            """
        )

    def _connect_signals(self):
        self.logout_button.clicked.connect(self._handle_logout)
        self.close_button.clicked.connect(self.close)
        self.refresh_employees_button.clicked.connect(self._load_employees)
        self.refresh_attendance_button.clicked.connect(self._load_attendance)
        self.refresh_payroll_button.clicked.connect(self._load_payroll)
        self.add_employee_button.clicked.connect(self._handle_add_employee)
        self.edit_employee_button.clicked.connect(self._handle_update_employee)
        self.cancel_edit_button.clicked.connect(self._handle_cancel_edit)
        self.add_attendance_button.clicked.connect(self._handle_add_attendance)
        self.calculate_payroll_button.clicked.connect(self._handle_calculate_payroll)
        self.deactivate_employee_button.clicked.connect(self._handle_deactivate_employee)
        self.activate_employee_button.clicked.connect(self._handle_activate_employee)

        self.search_input.textChanged.connect(self._load_employees)
        self.employee_filter_combo.currentIndexChanged.connect(self._load_employees)
        self.payroll_employee_combo.currentIndexChanged.connect(self._load_payroll)
        self.payroll_month_combo.currentIndexChanged.connect(self._load_payroll)
        self.payroll_year_spin.valueChanged.connect(self._load_payroll)
        
        # Edit on double-click
        self.employees_table.doubleClicked.connect(self._handle_employee_double_click)

    def _build_dashboard_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(18)

        summary_frame = QFrame()
        summary_layout = QGridLayout(summary_frame)
        summary_layout.setSpacing(18)
        summary_layout.setColumnStretch(0, 1)
        summary_layout.setColumnStretch(1, 1)
        summary_layout.setRowStretch(0, 1)
        summary_layout.setRowStretch(1, 1)

        self.total_employee_card = self._build_stat_card("Toplam Çalışan", "0", accent="#2e6bff", surface="#101a2b")
        self.active_employee_card = self._build_stat_card("Aktif Çalışan", "0", accent="#2e8b57", surface="#0f1b2a")
        self.month_attendance_card = self._build_stat_card("Bu Ay Yoklama", "0", accent="#7c93c7", surface="#10192a")
        self.month_payroll_card = self._build_stat_card("Bu Ay Tahmini Maaş", "₺0.00", accent="#4f7cff", surface="#0f1a2a")

        summary_layout.addWidget(self.total_employee_card, 0, 0)
        summary_layout.addWidget(self.active_employee_card, 0, 1)
        summary_layout.addWidget(self.month_attendance_card, 1, 0)
        summary_layout.addWidget(self.month_payroll_card, 1, 1)

        layout.addWidget(summary_frame, 1)

        self.tabs.addTab(tab, "Kontrol Paneli")

    def _build_employees_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        filter_group = QGroupBox("Filtreler")
        filter_layout = QHBoxLayout(filter_group)
        filter_layout.setContentsMargins(14, 18, 14, 14)
        filter_layout.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Çalışan ara: ad, soyad, email, departman, pozisyon")

        self.employee_filter_combo = QComboBox()
        self.employee_filter_combo.addItems(["Tümü", "Aktif", "Pasif"])

        self.refresh_employees_button = QPushButton("Yenile")
        self.refresh_employees_button.setObjectName("secondaryButton")
        self.deactivate_employee_button = QPushButton("Devre Dışı Bırak")
        self.deactivate_employee_button.setObjectName("deactivateButton")
        self.activate_employee_button = QPushButton("Etkinleştir")
        self.activate_employee_button.setObjectName("activateButton")

        filter_layout.addWidget(self.search_input, 3)
        filter_layout.addWidget(self.employee_filter_combo, 1)
        filter_layout.addWidget(self.refresh_employees_button, 0)
        filter_layout.addWidget(self.activate_employee_button, 0)
        filter_layout.addWidget(self.deactivate_employee_button, 0)

        form_group = QGroupBox("Yeni Çalışan")
        form_layout = QGridLayout(form_group)
        form_layout.setContentsMargins(14, 18, 14, 14)
        form_layout.setHorizontalSpacing(12)
        form_layout.setVerticalSpacing(10)

        self.first_name_input = QLineEdit()
        self.last_name_input = QLineEdit()
        self.email_input = QLineEdit()
        self.department_input = QLineEdit()
        self.position_input = QLineEdit()
        self.password_input = QLineEdit()
        self.hourly_rate_input = QDoubleSpinBox()
        self.is_admin_input = QComboBox()
        self.add_employee_button = QPushButton("Çalışan Ekle")
        self.edit_employee_button = QPushButton("Çalışanı Düzenle")
        self.cancel_edit_button = QPushButton("İptal")

        self.first_name_input.setPlaceholderText("Ad")
        self.last_name_input.setPlaceholderText("Soyad")
        self.email_input.setPlaceholderText("email@company.com")
        self.department_input.setPlaceholderText("Departman")
        self.position_input.setPlaceholderText("Pozisyon")
        self.password_input.setPlaceholderText("Parola")
        self.password_input.setEchoMode(QLineEdit.Password)

        self.hourly_rate_input.setRange(0, 100000)
        self.hourly_rate_input.setDecimals(2)
        self.hourly_rate_input.setSuffix(" ₺/saat")
        self.hourly_rate_input.setSingleStep(5)

        self.is_admin_input.addItems(["Normal Kullanıcı", "Admin"])

        self.add_employee_button.setObjectName("primaryButton")
        self.edit_employee_button.setObjectName("primaryButton")
        self.edit_employee_button.setVisible(False)
        self.cancel_edit_button.setObjectName("secondaryButton")
        self.cancel_edit_button.setVisible(False)

        form_layout.addWidget(QLabel("Ad"), 0, 0)
        form_layout.addWidget(self.first_name_input, 0, 1)
        form_layout.addWidget(QLabel("Soyad"), 0, 2)
        form_layout.addWidget(self.last_name_input, 0, 3)

        form_layout.addWidget(QLabel("Email"), 1, 0)
        form_layout.addWidget(self.email_input, 1, 1)
        form_layout.addWidget(QLabel("Departman"), 1, 2)
        form_layout.addWidget(self.department_input, 1, 3)

        form_layout.addWidget(QLabel("Pozisyon"), 2, 0)
        form_layout.addWidget(self.position_input, 2, 1)
        form_layout.addWidget(QLabel("Saatlik Ücret"), 2, 2)
        form_layout.addWidget(self.hourly_rate_input, 2, 3)

        form_layout.addWidget(QLabel("Parola"), 3, 0)
        form_layout.addWidget(self.password_input, 3, 1)
        form_layout.addWidget(QLabel("Rol"), 3, 2)
        form_layout.addWidget(self.is_admin_input, 3, 3)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.add_employee_button)
        button_layout.addWidget(self.edit_employee_button)
        button_layout.addWidget(self.cancel_edit_button)
        button_layout.addStretch()

        form_layout.addLayout(button_layout, 4, 0, 1, 4)

        self.employees_table = QTableWidget(0, 8)
        self.employees_table.setHorizontalHeaderLabels(
            [
                "ID",
                "Ad Soyad",
                "Email",
                "Departman",
                "Pozisyon",
                "Saatlik Ücret",
                "Durum",
                "Rol",
            ]
        )
        self._configure_table_widget(self.employees_table)

        layout.addWidget(filter_group)
        layout.addWidget(form_group)
        layout.addWidget(self.employees_table, 1)

        self.tabs.addTab(tab, "Çalışanlar")

    def _build_attendance_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        form_group = QGroupBox("Yoklama Kaydı")
        form_layout = QGridLayout(form_group)
        form_layout.setContentsMargins(14, 18, 14, 14)
        form_layout.setHorizontalSpacing(12)
        form_layout.setVerticalSpacing(10)

        self.attendance_employee_combo = QComboBox()
        self.attendance_date_edit = QDateEdit()
        self.attendance_status_combo = QComboBox()
        self.work_hours_input = QDoubleSpinBox()
        self.overtime_hours_input = QDoubleSpinBox()
        self.add_attendance_button = QPushButton("Kaydet")
        self.refresh_attendance_button = QPushButton("Refresh")

        self.attendance_date_edit.setCalendarPopup(True)
        self.attendance_date_edit.setDate(QDate.currentDate())
        self.attendance_date_edit.setDisplayFormat("yyyy-MM-dd")

        self.attendance_status_combo.addItems(["Var", "Yok", "İzin"])

        self.work_hours_input.setRange(0, 24)
        self.work_hours_input.setDecimals(2)
        self.work_hours_input.setSingleStep(0.5)
        self.work_hours_input.setSuffix(" h")

        self.overtime_hours_input.setRange(0, 24)
        self.overtime_hours_input.setDecimals(2)
        self.overtime_hours_input.setSingleStep(0.5)
        self.overtime_hours_input.setSuffix(" h")

        self.add_attendance_button.setObjectName("primaryButton")
        self.refresh_attendance_button.setObjectName("secondaryButton")

        form_layout.addWidget(QLabel("Çalışan"), 0, 0)
        form_layout.addWidget(self.attendance_employee_combo, 0, 1)
        form_layout.addWidget(QLabel("Tarih"), 0, 2)
        form_layout.addWidget(self.attendance_date_edit, 0, 3)

        form_layout.addWidget(QLabel("Durum"), 1, 0)
        form_layout.addWidget(self.attendance_status_combo, 1, 1)
        form_layout.addWidget(QLabel("Çalışma Saati"), 1, 2)
        form_layout.addWidget(self.work_hours_input, 1, 3)

        form_layout.addWidget(QLabel("Mesai Saati"), 2, 0)
        form_layout.addWidget(self.overtime_hours_input, 2, 1)
        form_layout.addWidget(self.refresh_attendance_button, 2, 2)
        form_layout.addWidget(self.add_attendance_button, 2, 3)

        self.attendance_table = QTableWidget(0, 6)
        self.attendance_table.setHorizontalHeaderLabels(
            ["ID", "Çalışan", "Tarih", "Durum", "Çalışma Saati", "Mesai"]
        )
        self._configure_table_widget(self.attendance_table)

        layout.addWidget(form_group)
        layout.addWidget(self.attendance_table, 1)

        self.tabs.addTab(tab, "Yoklama")

    def _build_payroll_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        form_group = QGroupBox("Maaş Hesaplama")
        form_layout = QGridLayout(form_group)
        form_layout.setContentsMargins(14, 18, 14, 14)
        form_layout.setHorizontalSpacing(12)
        form_layout.setVerticalSpacing(10)

        self.payroll_employee_combo = QComboBox()
        self.payroll_month_combo = QComboBox()
        self.payroll_year_spin = QSpinBox()
        self.calculate_payroll_button = QPushButton("Maaş Hesapla")
        self.refresh_payroll_button = QPushButton("Refresh")

        for month in range(1, 13):
            self.payroll_month_combo.addItem(f"{month:02d}", month)

        current_year = date.today().year
        self.payroll_year_spin.setRange(current_year - 10, current_year + 10)
        self.payroll_year_spin.setValue(current_year)

        self.calculate_payroll_button.setObjectName("primaryButton")
        self.refresh_payroll_button.setObjectName("secondaryButton")

        form_layout.addWidget(QLabel("Employee"), 0, 0)
        form_layout.addWidget(self.payroll_employee_combo, 0, 1)
        form_layout.addWidget(QLabel("Ay"), 0, 2)
        form_layout.addWidget(self.payroll_month_combo, 0, 3)

        form_layout.addWidget(QLabel("Year"), 1, 0)
        form_layout.addWidget(self.payroll_year_spin, 1, 1)
        form_layout.addWidget(self.refresh_payroll_button, 1, 2)
        form_layout.addWidget(self.calculate_payroll_button, 1, 3)

        result_group = QGroupBox("Sonuç")
        result_layout = QGridLayout(result_group)
        result_layout.setContentsMargins(14, 18, 14, 14)
        result_layout.setHorizontalSpacing(12)
        result_layout.setVerticalSpacing(8)

        self.payroll_employee_name_label = QLabel("-")
        self.payroll_period_label = QLabel("-")
        self.payroll_work_hours_label = QLabel("0")
        self.payroll_overtime_hours_label = QLabel("0")
        self.payroll_normal_salary_label = QLabel("₺0.00")
        self.payroll_overtime_salary_label = QLabel("₺0.00")
        self.payroll_total_salary_label = QLabel("₺0.00")

        result_layout.addWidget(QLabel("Çalışan"), 0, 0)
        result_layout.addWidget(self.payroll_employee_name_label, 0, 1)
        result_layout.addWidget(QLabel("Dönem"), 0, 2)
        result_layout.addWidget(self.payroll_period_label, 0, 3)

        result_layout.addWidget(QLabel("Normal Saatler"), 1, 0)
        result_layout.addWidget(self.payroll_work_hours_label, 1, 1)
        result_layout.addWidget(QLabel("Mesai Saatleri"), 1, 2)
        result_layout.addWidget(self.payroll_overtime_hours_label, 1, 3)

        result_layout.addWidget(QLabel("Normal Maaş"), 2, 0)
        result_layout.addWidget(self.payroll_normal_salary_label, 2, 1)
        result_layout.addWidget(QLabel("Mesai Maaşı"), 2, 2)
        result_layout.addWidget(self.payroll_overtime_salary_label, 2, 3)

        result_layout.addWidget(QLabel("Toplam Maaş"), 3, 0)
        result_layout.addWidget(self.payroll_total_salary_label, 3, 1)

        self.payroll_table = QTableWidget(0, 6)
        self.payroll_table.setHorizontalHeaderLabels(
            ["Çalışan", "Dönem", "Çalışma Saati", "Mesai", "Normal Maaş", "Toplam Maaş"]
        )
        self._configure_table_widget(self.payroll_table)

        layout.addWidget(form_group)
        layout.addWidget(result_group)
        layout.addWidget(self.payroll_table, 1)

        self.tabs.addTab(tab, "Maaş")

    def _build_stat_card(self, title, value, accent="#2e6bff", surface="#101a2b"):
        frame = QFrame()
        frame.setObjectName("statCard")
        frame.setMinimumHeight(180)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignCenter)

        frame.setStyleSheet(
            f"""
            QFrame#statCard {{
                background: {surface};
                border: 1px solid {self.TABLE_BORDER_COLOR};
                border-radius: 18px;
            }}
            """
        )

        title_label = QLabel(title)
        title_label.setObjectName("statTitleLabel")
        title_label.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        title_label.setAutoFillBackground(False)

        value_label = QLabel(value)
        value_label.setObjectName("statValueLabel")
        value_label.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        value_label.setAutoFillBackground(False)

        layout.addWidget(title_label)
        layout.addStretch(1)
        layout.addWidget(value_label)
        layout.addStretch(1)

        frame.title_label = title_label
        frame.value_label = value_label
        return frame

    def _configure_table_widget(self, table):
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSelectionMode(QTableWidget.SingleSelection)
        table.setSortingEnabled(False)
        table.setShowGrid(True)
        table.verticalHeader().setDefaultSectionSize(36)
        table.horizontalHeader().setMinimumSectionSize(120)

        table.setStyleSheet(
            f"""
            QTableWidget {{
                background-color: {self.TABLE_BASE_COLOR};
                alternate-background-color: {self.TABLE_ALT_COLOR};
                gridline-color: {self.TABLE_GRID_COLOR};
                color: {self.TABLE_TEXT_COLOR};
                selection-background-color: {self.TABLE_SELECTION_COLOR};
                selection-color: {self.TABLE_SELECTION_TEXT_COLOR};
                border: 1px solid {self.TABLE_BORDER_COLOR};
                border-radius: 12px;
            }}

            QTableWidget::item {{
                padding: 6px;
                color: {self.TABLE_TEXT_COLOR};
                background-color: transparent;
            }}

            QTableWidget::item:alternate {{
                background-color: {self.TABLE_ALT_COLOR};
            }}

            QTableWidget::item:selected {{
                background-color: {self.TABLE_SELECTION_COLOR};
                color: {self.TABLE_SELECTION_TEXT_COLOR};
            }}

            QTableWidget::item:selected:!active {{
                background-color: {self.TABLE_SELECTION_COLOR};
                color: {self.TABLE_SELECTION_TEXT_COLOR};
            }}

            QHeaderView::section {{
                background: {self.TABLE_HEADER_COLOR};
                color: {self.TABLE_HEADER_TEXT_COLOR};
                padding: 12px 10px;
                border: none;
                border-right: 1px solid {self.TABLE_GRID_COLOR};
                border-bottom: 1px solid {self.TABLE_GRID_COLOR};
                font-weight: 700;
                font-size: 15px;
            }}
            """
        )

        palette = table.palette()
        palette.setColor(QPalette.Base, QColor(self.TABLE_BASE_COLOR))
        palette.setColor(QPalette.AlternateBase, QColor(self.TABLE_ALT_COLOR))
        palette.setColor(QPalette.Text, QColor(self.TABLE_TEXT_COLOR))
        palette.setColor(QPalette.ButtonText, QColor(self.TABLE_TEXT_COLOR))
        palette.setColor(QPalette.Highlight, QColor(self.TABLE_SELECTION_COLOR))
        palette.setColor(QPalette.HighlightedText, QColor(self.TABLE_SELECTION_TEXT_COLOR))
        table.setPalette(palette)

        header = table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(QHeaderView.Stretch)
        header.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        header.setHighlightSections(False)
        table.verticalHeader().setVisible(False)

    def _is_admin_user(self):
        return bool(self._get_user_value("is_admin", 0))

    def _get_user_value(self, key, default=None):
        """Get value from user dict."""
        if not isinstance(self.user, dict):
            return default
        return self.user.get(key, default)

    def _build_user_caption(self):
        name = self._get_user_value("first_name", "")
        surname = self._get_user_value("last_name", "")
        email = self._get_user_value("email", "")

        full_name = " ".join(part for part in [str(name).strip(), str(surname).strip()] if part)
        if not full_name:
            full_name = str(email).strip() or "Admin user"

        if email:
            return f"{full_name} • {email}"
        return full_name

    def _employee_label(self, employee):
        employee_id = self._row_get(employee, "employee_id", 0)
        first_name = self._row_get(employee, "first_name", "")
        last_name = self._row_get(employee, "last_name", "")
        status = "Active" if self._safe_int(self._row_get(employee, "active", 1), 1) == 1 else "Inactive"
        return f"{employee_id} - {first_name} {last_name} ({status})"

    def _row_get(self, row, key, default=None):
        if row is None:
            return default
        if isinstance(row, dict):
            return row.get(key, default)
        try:
            return row[key]
        except Exception:
            try:
                return row[key]
            except Exception:
                return getattr(row, key, default)

    def _format_money(self, value):
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            numeric = 0.0
        return f"₺{numeric:,.2f}"

    def _safe_float(self, value, default=0.0):
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def _safe_int(self, value, default=0):
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def _set_card_value(self, card, value):
        if hasattr(card, "value_label"):
            card.value_label.setText(str(value))

    def _set_table_rows(self, table, rows, columns):
        table.setRowCount(0)
        for row_index, row in enumerate(rows):
            table.insertRow(row_index)
            for column_index, column in enumerate(columns):
                try:
                    value = column(row)
                except Exception:
                    value = ""

                item = QTableWidgetItem("" if value is None else str(value))
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                table.setItem(row_index, column_index, item)

    def _validate_email(self, email):
        return bool(re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", email or ""))

    def _refresh_all(self):
        self._load_employees()
        self._load_attendance()
        self._load_payroll()
        self._load_dashboard()

    def _load_dashboard(self):
        employees = self._employee_cache or self._fetch_employees()
        current_date = date.today()
        current_month = current_date.month
        current_year = current_date.year

        total_employee_count = len(employees)
        active_employee_count = sum(1 for employee in employees if self._safe_int(self._row_get(employee, "active", 1), 1) == 1)
        month_attendance_count = self._count_monthly_attendance(current_month, current_year)
        month_payroll_total = self._calculate_total_monthly_payroll(current_month, current_year, employees)

        self._set_card_value(self.total_employee_card, total_employee_count)
        self._set_card_value(self.active_employee_card, active_employee_count)
        self._set_card_value(self.month_attendance_card, month_attendance_count)
        self._set_card_value(self.month_payroll_card, self._format_money(month_payroll_total))

    def _load_employees(self):
        employees = self._fetch_employees()
        self._employee_cache = employees
        self._employee_lookup = {self._safe_int(self._row_get(employee, "employee_id")): employee for employee in employees}

        self._refresh_employee_comboboxes(employees)

        query = self.search_input.text().strip().lower()
        filter_value = self.employee_filter_combo.currentText()

        filtered = []
        for employee in employees:
            employee_text = " ".join(
                [
                    str(self._row_get(employee, "first_name", "")),
                    str(self._row_get(employee, "last_name", "")),
                    str(self._row_get(employee, "email", "")),
                    str(self._row_get(employee, "department", "")),
                    str(self._row_get(employee, "position", "")),
                ]
            ).lower()

            is_active = self._safe_int(self._row_get(employee, "active", 1), 1) == 1

            if query and query not in employee_text:
                continue

            if filter_value == "Active" and not is_active:
                continue

            if filter_value == "Inactive" and is_active:
                continue

            filtered.append(employee)

        self._set_table_rows(
            self.employees_table,
            filtered,
            [
                lambda row: self._row_get(row, "employee_id", ""),
                lambda row: f"{self._row_get(row, 'first_name', '')} {self._row_get(row, 'last_name', '')}".strip(),
                lambda row: self._row_get(row, "email", ""),
                lambda row: self._row_get(row, "department", ""),
                lambda row: self._row_get(row, "position", ""),
                lambda row: f"{self._safe_float(self._row_get(row, 'hourly_rate', 0.0)):.2f}",
                lambda row: "Active" if self._safe_int(self._row_get(row, "active", 1), 1) == 1 else "Inactive",
                lambda row: "Admin" if self._safe_int(self._row_get(row, "is_admin", 0), 0) == 1 else "User",
            ],
        )
        self._style_employee_rows()


    def _get_selected_employee_id_from_table(self):
        # Return currently selected employee_id from employees_table or None
        try:
            selected = self.employees_table.selectionModel().selectedRows()
            if not selected:
                return None
            row_idx = selected[0].row()
            item = self.employees_table.item(row_idx, 0)
            if not item:
                return None
            return self._safe_int(item.text(), None)
        except Exception:
            return None


    def _handle_deactivate_employee(self):
        try:
            employee_id = self._get_selected_employee_id_from_table()
            if not employee_id:
                raise ValidationError("Lütfen bir çalışan seçin.")

            reply = QMessageBox.question(
                self,
                "Onay",
                "Are you sure you want to deactivate this employee?",
                QMessageBox.Yes | QMessageBox.No,
            )

            if reply != QMessageBox.Yes:
                return

            employee_service.deactivate_employee(self.user, employee_id)
            self._show_message("Başarılı", "Çalışan devre dışı bırakıldı.")
            self._refresh_all()
        except (ValidationError, AuthorizationError, EmployeeNotFoundError, NotFoundError) as exc:
            self._show_message("İşlem Hatası", str(exc), QMessageBox.Warning)
        except Exception as exc:
            self._show_message("Beklenmeyen Hata", f"İşlem tamamlanamadı:\n{exc}", QMessageBox.Critical)


    def _handle_activate_employee(self):
        try:
            employee_id = self._get_selected_employee_id_from_table()
            if not employee_id:
                raise ValidationError("Lütfen bir çalışan seçin.")

            reply = QMessageBox.question(
                self,
                "Onay",
                "Are you sure you want to activate this employee?",
                QMessageBox.Yes | QMessageBox.No,
            )

            if reply != QMessageBox.Yes:
                return

            employee_service.activate_employee(self.user, employee_id)
            self._show_message("Başarılı", "Çalışan aktifleştirildi.")
            self._refresh_all()
        except (ValidationError, AuthorizationError, EmployeeNotFoundError, NotFoundError) as exc:
            self._show_message("İşlem Hatası", str(exc), QMessageBox.Warning)
        except Exception as exc:
            self._show_message("Beklenmeyen Hata", f"İşlem tamamlanamadı:\n{exc}", QMessageBox.Critical)


    def _style_employee_rows(self):
        row_count = self.employees_table.rowCount()
        for r in range(row_count):
            id_item = self.employees_table.item(r, 0)
            if id_item is None:
                continue

            eid = self._safe_int(id_item.text(), None)
            employee = self._employee_lookup.get(eid)
            active = self._safe_int(self._row_get(employee, "active", 1), 1) if employee is not None else 1
            foreground_color = self.TABLE_TEXT_COLOR if active == 1 else self.TABLE_MUTED_TEXT_COLOR

            for c in range(self.employees_table.columnCount()):
                item = self.employees_table.item(r, c)
                if item is None:
                    continue
                item.setForeground(QBrush(QColor(foreground_color)))

    def _load_attendance(self):
        rows = self._attendance_rows or self._fetch_attendance_rows()
        self._attendance_rows = rows

        current_date = date.today()
        current_month = current_date.month
        current_year = current_date.year

        filtered = [row for row in rows if self._attendance_date_matches(row, current_year, current_month)]

        self._set_table_rows(
            self.attendance_table,
            filtered,
            [
                lambda row: self._row_get(row, "attendance_id", ""),
                lambda row: self._attendance_employee_name(self._row_get(row, "employee_id"), row),
                lambda row: self._row_get(row, "work_date", ""),
                lambda row: self._row_get(row, "status", ""),
                lambda row: self._row_get(row, "work_hours", 0),
                lambda row: self._row_get(row, "overtime_hours", 0),
            ],
        )

    def _load_payroll(self):
        employees = self._employee_cache or self._fetch_employees()
        selected_employee_id = self._get_selected_employee_id(self.payroll_employee_combo)
        current_month = self._safe_int(self.payroll_month_combo.currentData(), self.payroll_month_combo.currentIndex() + 1)
        current_year = self.payroll_year_spin.value()

        payroll_rows = []

        if selected_employee_id:
            result = self._calculate_monthly_payroll(selected_employee_id, current_month, current_year, quiet=True)
            if result:
                payroll_rows.append(result)
                self._update_payroll_summary(result)
            else:
                self._clear_payroll_summary()
        else:
            self._clear_payroll_summary()
            for employee in employees:
                employee_id = self._safe_int(self._row_get(employee, "employee_id"))
                result = self._calculate_monthly_payroll(employee_id, current_month, current_year, quiet=True)
                if result:
                    payroll_rows.append(result)

        self._payroll_rows = payroll_rows
        self._set_table_rows(
            self.payroll_table,
            payroll_rows,
            [
                lambda row: self._row_get(row, "employee_name", self._attendance_employee_name(self._row_get(row, "employee_id"))),
                lambda row: f"{self._row_get(row, 'month', current_month):02d}/{self._row_get(row, 'year', current_year)}",
                lambda row: f"{self._safe_float(self._row_get(row, 'total_work_hours', 0.0)):.2f}",
                lambda row: f"{self._safe_float(self._row_get(row, 'total_overtime_hours', 0.0)):.2f}",
                lambda row: self._format_money(self._row_get(row, 'normal_salary', 0.0)),
                lambda row: self._format_money(self._row_get(row, 'total_salary', 0.0)),
            ],
        )

    def _handle_add_employee(self):
        try:
            # Collect raw values and let service layer validators handle validation
            first_name = self.first_name_input.text()
            last_name = self.last_name_input.text()
            email = self.email_input.text()
            department = self.department_input.text()
            position = self.position_input.text()
            hourly_rate = self.hourly_rate_input.value()
            password = self.password_input.text()
            is_admin = 1 if self.is_admin_input.currentIndex() == 1 else 0

            employee_service.create_employee(
                current_user=self.user,
                first_name=first_name,
                last_name=last_name,
                email=email,
                department=department,
                position=position,
                hourly_rate=hourly_rate,
                password=password,
                is_admin=is_admin,
            )

            self._show_message("Başarılı", "Çalışan başarıyla eklendi.")
            self._clear_employee_form()
            self._refresh_all()

        except (ValidationError, AuthorizationError, DatabaseError, EmployeeNotFoundError, NotFoundError) as exc:
            self._show_message("İşlem Hatası", str(exc), QMessageBox.Warning)
        except Exception as exc:
            self._show_message("Beklenmeyen Hata", f"Çalışan eklenemedi:\n{exc}", QMessageBox.Critical)

    def _handle_employee_double_click(self, index):
        """Handle double-click on employee table row to edit."""
        try:
            row = index.row()
            if row < 0:
                return
            
            # Get employee_id from first column
            employee_id_item = self.employees_table.item(row, 0)
            if not employee_id_item:
                return
            
            employee_id = self._safe_int(employee_id_item.text(), None)
            if not employee_id:
                raise ValidationError("Çalışan ID alınamadı.")
            
            # Load employee data
            employee = employee_service.get_employee_by_id(self.user, employee_id)
            if not employee:
                raise EmployeeNotFoundError(f"Çalışan bulunamadı: {employee_id}")
            
            # Populate form with employee data
            self._populate_edit_form(employee)
            
            # Switch to edit mode
            self._enter_edit_mode(employee_id)
            
        except (ValidationError, EmployeeNotFoundError) as exc:
            self._show_message("İşlem Hatası", str(exc), QMessageBox.Warning)
        except Exception as exc:
            self._show_message("Beklenmeyen Hata", f"Düzenleme başlatılamadı:\n{exc}", QMessageBox.Critical)

    def _populate_edit_form(self, employee):
        """Fill form fields with employee data."""
        self.first_name_input.setText(str(self._row_get(employee, "first_name", "")).strip())
        self.last_name_input.setText(str(self._row_get(employee, "last_name", "")).strip())
        self.email_input.setText(str(self._row_get(employee, "email", "")).strip())
        self.department_input.setText(str(self._row_get(employee, "department", "")).strip())
        self.position_input.setText(str(self._row_get(employee, "position", "")).strip())
        
        hourly_rate = self._safe_float(self._row_get(employee, "hourly_rate", 0.0))
        self.hourly_rate_input.setValue(hourly_rate)
        
        is_admin = self._safe_int(self._row_get(employee, "is_admin", 0))
        self.is_admin_input.setCurrentIndex(1 if is_admin == 1 else 0)
        
        # Clear password field (not required for edit)
        self.password_input.clear()

    def _enter_edit_mode(self, employee_id):
        """Switch UI to edit mode."""
        self._edit_mode = True
        self._editing_employee_id = employee_id
        
        # Hide add button, show edit/cancel buttons
        self.add_employee_button.setVisible(False)
        self.edit_employee_button.setVisible(True)
        self.cancel_edit_button.setVisible(True)
        
        # Disable password field for edit (optional)
        self.password_input.setPlaceholderText("Boş bırakın (değişiklik yapılmayacak)")
        self.password_input.setEnabled(True)

    def _handle_update_employee(self):
        """Handle update employee button click."""
        try:
            if not self._edit_mode or not self._editing_employee_id:
                raise ValidationError("Edit modu aktif değil.")
            
            employee_id = self._editing_employee_id
            
            # Get form data (raw) and let service validators run
            first_name = self.first_name_input.text()
            last_name = self.last_name_input.text()
            email = self.email_input.text()
            department = self.department_input.text()
            position = self.position_input.text()
            hourly_rate = self.hourly_rate_input.value()
            is_admin = 1 if self.is_admin_input.currentIndex() == 1 else 0

            # Build update data (only include non-empty fields)
            updated_data = {}

            if first_name and first_name.strip():
                updated_data["first_name"] = first_name
            if last_name and last_name.strip():
                updated_data["last_name"] = last_name
            if email and email.strip():
                updated_data["email"] = email
            if department and department.strip():
                updated_data["department"] = department
            if position and position.strip():
                updated_data["position"] = position

            # Always include hourly_rate and is_admin
            updated_data["hourly_rate"] = hourly_rate
            updated_data["is_admin"] = is_admin
            
            if not updated_data:
                raise ValidationError("Güncellenecek veri yok.")
            
            # Call service to update
            employee_service.update_employee(
                current_user=self.user,
                employee_id=employee_id,
                updated_data=updated_data
            )
            
            self._show_message("Başarılı", "Çalışan bilgileri güncellendi.")
            self._exit_edit_mode()
            self._refresh_all()
            
        except (ValidationError, AuthorizationError, EmployeeNotFoundError, DatabaseError, NotFoundError) as exc:
            self._show_message("İşlem Hatası", str(exc), QMessageBox.Warning)
        except Exception as exc:
            self._show_message("Beklenmeyen Hata", f"Çalışan güncellenemedi:\n{exc}", QMessageBox.Critical)

    def _handle_cancel_edit(self):
        """Handle cancel edit button click."""
        reply = QMessageBox.question(
            self,
            "İşlemi İptal Et",
            "Değişiklikleri İptal Etmek İstiyor Musunuz?",
            QMessageBox.Yes | QMessageBox.No,
        )
        
        if reply == QMessageBox.Yes:
            self._exit_edit_mode()

    def _exit_edit_mode(self):
        """Exit edit mode and return to add mode."""
        self._edit_mode = False
        self._editing_employee_id = None
        
        # Show add button, hide edit/cancel buttons
        self.add_employee_button.setVisible(True)
        self.edit_employee_button.setVisible(False)
        self.cancel_edit_button.setVisible(False)
        
        # Reset password field
        self.password_input.setPlaceholderText("Parola")
        
        # Clear form
        self._clear_employee_form()

    def _handle_add_attendance(self):
        try:
            employee_id = self._get_selected_employee_id(self.attendance_employee_combo)
            if not employee_id:
                raise ValidationError("Lütfen bir çalışan seçin.")

            work_date = self.attendance_date_edit.date().toString("yyyy-MM-dd")
            status = self.attendance_status_combo.currentText().strip()
            work_hours = self.work_hours_input.value()
            overtime_hours = self.overtime_hours_input.value()

            if work_hours < 0:
                raise ValidationError("Work hours negatif olamaz.")
            if overtime_hours < 0:
                raise ValidationError("Overtime hours negatif olamaz.")
            if status not in {"present", "absent", "leave"}:
                raise ValidationError("Geçersiz attendance durumu.")
            if status == "present" and work_hours == 0:
                raise ValidationError("Present kayıt için çalışma saati girilmelidir.")

            attendance_service.add_attendance(
                current_user=self.user,
                employee_id=employee_id,
                work_date=work_date,
                status=status,
                work_hours=work_hours,
                overtime_hours=overtime_hours,
            )

            self._show_message("Başarılı", "Yoklama kaydı eklendi.")
            self._clear_attendance_form()
            self._refresh_all()

        except DuplicateAttendanceError as exc:
            self._show_message("Mükerrer Kayıt", str(exc), QMessageBox.Warning)
        except (ValidationError, AuthorizationError, NotFoundError) as exc:
            self._show_message("İşlem Hatası", str(exc), QMessageBox.Warning)
        except Exception as exc:
            self._show_message("Beklenmeyen Hata", f"Yoklama eklenemedi:\n{exc}", QMessageBox.Critical)

    def _handle_calculate_payroll(self):
        try:
            employee_id = self._get_selected_employee_id(self.payroll_employee_combo)
            if not employee_id:
                raise ValidationError("Lütfen bir çalışan seçin.")

            month = self._safe_int(self.payroll_month_combo.currentData(), self.payroll_month_combo.currentIndex() + 1)
            year = self.payroll_year_spin.value()

            if month < 1 or month > 12:
                raise ValidationError("Geçersiz ay seçimi.")
            if year < 2000:
                raise ValidationError("Geçersiz yıl seçimi.")

            result = self._calculate_monthly_payroll(employee_id, month, year)
            if not result:
                raise NotFoundError("Bu dönem için payroll kaydı bulunamadı.")

            self._update_payroll_summary(result)
            self._show_message("Başarılı", "Maaş hesaplandı.")
            self._load_payroll()

        except (ValidationError, AuthorizationError, NotFoundError) as exc:
            self._show_message("İşlem Hatası", str(exc), QMessageBox.Warning)
        except Exception as exc:
            self._show_message("Beklenmeyen Hata", f"Maaş hesaplanamadı:\n{exc}", QMessageBox.Critical)

    def _handle_logout(self):
        try:
            from ui.login_window import LoginWindow

            self.next_window = LoginWindow()
            self.next_window.show()
            self.close()
        except Exception as exc:
            self._show_message("Çıkış Hatası", f"Logout işlemi tamamlanamadı:\n{exc}", QMessageBox.Critical)

    def _show_message(self, title, text, icon=QMessageBox.Information):
        box = QMessageBox(self)
        box.setWindowTitle(title)
        box.setText(text)
        box.setIcon(icon)
        box.exec_()

    def _fetch_employees(self):
        try:
            employees = employee_service.get_all_employees(self.user)
            return list(employees or [])
        except Exception as exc:
            self._show_message("Veri Hatası", f"Çalışan listesi alınamadı:\n{exc}", QMessageBox.Critical)
            return []

    def _fetch_attendance_rows(self):
        try:
            fetch_all = getattr(attendance_service, "get_all_attendance", None)
            if callable(fetch_all):
                return list(fetch_all(self.user) or [])

            current_date = date.today()
            fetch_month = getattr(attendance_service, "get_attendance_by_month", None)
            if callable(fetch_month):
                return list(fetch_month(self.user, current_date.month, current_date.year) or [])

            return []
        except Exception as exc:
            self._show_message("Veri Hatası", f"Yoklama kayıtları alınamadı:\n{exc}", QMessageBox.Critical)
            return []

    def _calculate_monthly_payroll(self, employee_id, month, year, quiet=False):
        try:
            # Use calculate_monthly_payroll (has authorization)
            result = payroll_service.calculate_monthly_payroll(self.user, employee_id, month, year)
            if result is None:
                raise NotFoundError("Bu dönem için payroll kaydı bulunamadı.")
            return result
        except Exception:
            if quiet:
                return None
            raise

    def _calculate_total_monthly_payroll(self, month, year, employees=None):
        employees = employees if employees is not None else self._fetch_employees()
        total = 0.0
        for employee in employees:
            employee_id = self._safe_int(self._row_get(employee, "employee_id"))
            result = self._calculate_monthly_payroll(employee_id, month, year, quiet=True)
            if result:
                total += self._safe_float(self._row_get(result, "total_salary", 0.0))
        return total

    def _count_monthly_attendance(self, month, year):
        rows = self._attendance_rows or self._fetch_attendance_rows()
        return sum(1 for row in rows if self._attendance_date_matches(row, year, month))

    def _attendance_date_matches(self, row, year, month):
        work_date = str(self._row_get(row, "work_date", ""))
        return len(work_date) >= 7 and work_date[:4] == f"{year}" and work_date[5:7] == f"{month:02d}"

    def _attendance_employee_name(self, employee_id, row=None):
        if row is not None:
            first_name = self._row_get(row, "first_name", "")
            last_name = self._row_get(row, "last_name", "")
            full_name = f"{first_name} {last_name}".strip()
            if full_name:
                return full_name

        employee = self._employee_lookup.get(self._safe_int(employee_id))
        if not employee:
            return f"Employee #{employee_id}"
        first_name = self._row_get(employee, "first_name", "")
        last_name = self._row_get(employee, "last_name", "")
        return f"{first_name} {last_name}".strip() or f"Employee #{employee_id}"

    def _refresh_employee_comboboxes(self, employees):
        employee_items = [
            (self._employee_label(employee), self._safe_int(self._row_get(employee, "employee_id")))
            for employee in employees
        ]

        for combo in (self.attendance_employee_combo, self.payroll_employee_combo):
            current_value = combo.currentData() if combo.count() else None
            combo.blockSignals(True)
            combo.clear()
            combo.addItem("All Employees", None)
            for label, employee_id in employee_items:
                combo.addItem(label, employee_id)
            if current_value is not None:
                index = combo.findData(current_value)
                if index >= 0:
                    combo.setCurrentIndex(index)
            combo.blockSignals(False)

    def _get_selected_employee_id(self, combo):
        if combo.count() == 0:
            return None
        data = combo.currentData()
        if data in (None, ""):
            return None
        return self._safe_int(data, None)

    def _clear_employee_form(self):
        self.first_name_input.clear()
        self.last_name_input.clear()
        self.email_input.clear()
        self.department_input.clear()
        self.position_input.clear()
        self.password_input.clear()
        self.hourly_rate_input.setValue(0.0)
        self.is_admin_input.setCurrentIndex(0)

    def _clear_attendance_form(self):
        self.attendance_date_edit.setDate(QDate.currentDate())
        self.attendance_status_combo.setCurrentIndex(0)
        self.work_hours_input.setValue(0.0)
        self.overtime_hours_input.setValue(0.0)

    def _clear_payroll_summary(self):
        self.payroll_employee_name_label.setText("-")
        self.payroll_period_label.setText("-")
        self.payroll_work_hours_label.setText("0")
        self.payroll_overtime_hours_label.setText("0")
        self.payroll_normal_salary_label.setText("₺0.00")
        self.payroll_overtime_salary_label.setText("₺0.00")
        self.payroll_total_salary_label.setText("₺0.00")

    def _update_payroll_summary(self, result):
        employee_name = self._row_get(result, "employee_name", "-")
        month = self._safe_int(self._row_get(result, "month", 0))
        year = self._safe_int(self._row_get(result, "year", 0))

        self.payroll_employee_name_label.setText(str(employee_name))
        self.payroll_period_label.setText(f"{month:02d}/{year}")
        self.payroll_work_hours_label.setText(f"{self._safe_float(self._row_get(result, 'total_work_hours', 0.0)):.2f}")
        self.payroll_overtime_hours_label.setText(f"{self._safe_float(self._row_get(result, 'total_overtime_hours', 0.0)):.2f}")
        self.payroll_normal_salary_label.setText(self._format_money(self._row_get(result, 'normal_salary', 0.0)))
        self.payroll_overtime_salary_label.setText(self._format_money(self._row_get(result, 'overtime_salary', 0.0)))
        self.payroll_total_salary_label.setText(self._format_money(self._row_get(result, 'total_salary', 0.0)))

