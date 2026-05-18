# ui/user_panel.py

from datetime import datetime
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QMessageBox,
    QSpinBox,
    QFrame,
    QGroupBox,
    QHeaderView,
)

from services.attendance_service import (
    get_employee_attendance,
    get_attendance_by_month,
)
from services.payroll_service import get_employee_monthly_payroll
import services.exceptions as service_exceptions

AuthorizationError = getattr(service_exceptions, "AuthorizationError", Exception)
ValidationError = getattr(service_exceptions, "ValidationError", Exception)
EmployeeNotFoundError = getattr(service_exceptions, "EmployeeNotFoundError", Exception)
DuplicateAttendanceError = getattr(service_exceptions, "DuplicateAttendanceError", Exception)


class UserPanel(QWidget):
    def __init__(self, user):
        super().__init__()
        
        self.user = user
        
        try:
            self.employee_id = self._extract_employee_id()
        except ValueError as e:
            self._show_message("Error", str(e), QMessageBox.Critical)
            self.close()
            return
        
        self.setWindowTitle("Çalışan Paneli")
        self.resize(1400, 850)
        
        # UI components
        self.tab_widget = None
        self.dashboard_widgets = {}
        self.attendance_table = None
        self.payroll_table = None
        
        # Payroll fields
        self.payroll_widgets = {}
        
        # Filter controls
        self.attendance_month = None
        self.attendance_year = None
        self.payroll_month = None
        self.payroll_year = None
        
        # Button references
        self.attendance_refresh_btn = None
        self.payroll_calculate_btn = None
        self.refresh_all_btn = None
        self.logout_btn = None
        self.close_btn = None
        
        self._build_ui()
        self._apply_style()
        self._connect_signals()
        self._load_initial_data()
    
    def _extract_employee_id(self):
        """Extract employee_id from user dict."""
        if not isinstance(self.user, dict):
            raise ValueError("User must be a dict.")
        
        emp_id = self.user.get("employee_id")
        
        if not emp_id:
            raise ValueError("Employee ID not found in user data.")
        
        return emp_id
    
    def _get_user_field(self, field_name, default=""):
        """Safely get user field from dict or object."""
        if isinstance(self.user, dict):
            return self.user.get(field_name, default)
        return getattr(self.user, field_name, default)
    
    def _build_ui(self):
        """Build main UI structure."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Header
        header = self._create_header()
        main_layout.addWidget(header)
        
        # Tab Widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setDocumentMode(True)
        self.tab_widget.setElideMode(Qt.ElideNone)
        self._configure_tab_widget()
        
        # Tabs
        self.tab_widget.addTab(self._create_dashboard_tab(), "Kontrol Paneli")
        self.tab_widget.addTab(self._create_attendance_tab(), "Yoklama")
        self.tab_widget.addTab(self._create_payroll_tab(), "Maaş")
        
        main_layout.addWidget(self.tab_widget)
        
        # Footer
        footer = self._create_footer()
        main_layout.addWidget(footer)
    
    def _create_header(self):
        """Create header widget with user info."""
        header = QFrame()
        header.setObjectName("headerFrame")
        header.setMinimumHeight(96)
        
        layout = QVBoxLayout(header)
        layout.setContentsMargins(30, 24, 30, 24)
        layout.setSpacing(8)
        
        user_name = self._get_user_field("first_name", "User")
        user_last_name = self._get_user_field("last_name", "")
        full_name = f"{user_name} {user_last_name}".strip()
        user_email = self._get_user_field("email", "")
        
        title_label = QLabel(f"Hoşgeldiniz, {full_name}")
        title_label.setObjectName("headerTitle")
        title_label.setFont(QFont("Segoe UI", 34, QFont.Bold))
        
        subtitle_label = QLabel(f"ID: {self.employee_id} | {user_email}")
        subtitle_label.setObjectName("headerSubtitle")
        subtitle_label.setFont(QFont("Segoe UI", 17))
        
        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)
        
        return header

    def _configure_tab_widget(self):
        """Configure the main tab bar so long labels fit cleanly."""
        tab_bar = self.tab_widget.tabBar()
        tab_bar.setExpanding(True)
        tab_bar.setUsesScrollButtons(False)
        tab_bar.setMovable(False)
    
    def _create_dashboard_tab(self):
        """Create Dashboard tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(26, 26, 26, 26)
        layout.setSpacing(20)
        
        # User Info Group
        user_group = self._create_user_info_group()
        layout.addWidget(user_group)
        
        # Summary Boxes
        summary_layout = QVBoxLayout()
        summary_layout.setSpacing(18)

        top_row = QHBoxLayout()
        top_row.setSpacing(18)
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(18)
        
        self.dashboard_widgets["monthly_hours"] = self._create_summary_box(
            "Bu Ay Çalışma Saati", "0 h"
        )
        self.dashboard_widgets["monthly_overtime"] = self._create_summary_box(
            "Bu Ay Mesai", "0 h"
        )
        self.dashboard_widgets["estimated_salary"] = self._create_summary_box(
            "Tahmini Aylık Maaş", "₺0.00"
        )
        self.dashboard_widgets["last_attendance"] = self._create_summary_box(
            "Son Yoklama", "Kayıt yok"
        )
        
        top_row.addWidget(self.dashboard_widgets["monthly_hours"])
        top_row.addWidget(self.dashboard_widgets["monthly_overtime"])
        bottom_row.addWidget(self.dashboard_widgets["estimated_salary"])
        bottom_row.addWidget(self.dashboard_widgets["last_attendance"])

        summary_layout.addLayout(top_row)
        summary_layout.addLayout(bottom_row)

        layout.addLayout(summary_layout)
        layout.addStretch()
        
        return widget
    
    def _create_user_info_group(self):
        """Create user information group."""
        group = QGroupBox("Bilgilerim")
        group.setObjectName("infoGroup")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        
        info_data = [
            ("Çalışan ID", str(self.employee_id)),
            ("Ad Soyad", f"{self._get_user_field('first_name')} {self._get_user_field('last_name')}"),
            ("Email", self._get_user_field("email")),
            ("Departman", self._get_user_field("department", "N/A")),
            ("Pozisyon", self._get_user_field("position", "N/A")),
        ]

        grid = QFrame()
        grid.setObjectName("infoGridFrame")
        grid_layout = QVBoxLayout(grid)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        grid_layout.setSpacing(10)

        for label_text, value_text in info_data:
            row_layout = QHBoxLayout()
            row_layout.setSpacing(14)
            label = QLabel(f"{label_text}:")
            label.setMinimumWidth(150)
            label.setFont(QFont("Segoe UI", 16, QFont.Bold))
            value = QLabel(value_text)
            value.setFont(QFont("Segoe UI", 16))
            value.setWordWrap(True)
            row_layout.addWidget(label)
            row_layout.addWidget(value, 1)
            grid_layout.addLayout(row_layout)

        layout.addWidget(grid)
        
        return group
    
    def _create_summary_box(self, title, value):
        """Create a summary info box."""
        box = QFrame()
        box.setObjectName("summaryBox")
        box.setMinimumHeight(200)
        layout = QVBoxLayout(box)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignCenter)
        
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        title_label.setFont(QFont("Segoe UI", 21, QFont.Bold))
        title_label.setObjectName("summaryTitle")
        
        value_label = QLabel(value)
        value_label.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        value_label.setFont(QFont("Segoe UI", 52, QFont.Bold))
        value_label.setObjectName("summaryValue")
        
        layout.addWidget(title_label)
        layout.addStretch(1)
        layout.addWidget(value_label)
        layout.addStretch(1)
        
        # Store reference for updates
        box.value_label = value_label
        
        return box
    
    def _create_attendance_tab(self):
        """Create Attendance Records tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(26, 26, 26, 26)
        layout.setSpacing(18)
        
        # Filter Layout
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(18)
        
        month_label = QLabel("Ay:")
        month_label.setFont(QFont("Segoe UI", 15, QFont.Bold))
        filter_layout.addWidget(month_label)
        self.attendance_month = QSpinBox()
        self.attendance_month.setMinimum(1)
        self.attendance_month.setMaximum(12)
        self.attendance_month.setValue(datetime.now().month)
        self.attendance_month.setMaximumWidth(110)
        self.attendance_month.setMinimumHeight(44)
        filter_layout.addWidget(self.attendance_month)
        
        year_label = QLabel("Yıl:")
        year_label.setFont(QFont("Segoe UI", 15, QFont.Bold))
        filter_layout.addWidget(year_label)
        self.attendance_year = QSpinBox()
        self.attendance_year.setMinimum(2020)
        self.attendance_year.setMaximum(2100)
        self.attendance_year.setValue(datetime.now().year)
        self.attendance_year.setMaximumWidth(120)
        self.attendance_year.setMinimumHeight(44)
        filter_layout.addWidget(self.attendance_year)
        
        refresh_btn = QPushButton("Yenile")
        refresh_btn.setMinimumHeight(46)
        filter_layout.addWidget(refresh_btn)
        
        filter_layout.addStretch()
        layout.addLayout(filter_layout)
        
        # Table
        self.attendance_table = QTableWidget()
        self.attendance_table.setColumnCount(5)
        self.attendance_table.setHorizontalHeaderLabels([
            "Tarih", "Durum", "Çalışma Saati", "Mesai Saati", "Detaylar"
        ])
        self._configure_table(
            self.attendance_table,
            column_widths=[150, 120, 150, 170, None],
            centered_columns={0, 1, 2, 3},
            row_height=50,
            header_height=46,
        )
        layout.addWidget(self.attendance_table)
        
        # Store button reference
        self.attendance_refresh_btn = refresh_btn
        
        return widget
    
    def _create_payroll_tab(self):
        """Create Payroll tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(26, 26, 26, 26)
        layout.setSpacing(18)
        
        # Control Layout
        control_layout = QHBoxLayout()
        control_layout.setSpacing(18)
        
        month_label = QLabel("Ay:")
        month_label.setFont(QFont("Segoe UI", 15, QFont.Bold))
        control_layout.addWidget(month_label)
        self.payroll_month = QSpinBox()
        self.payroll_month.setMinimum(1)
        self.payroll_month.setMaximum(12)
        self.payroll_month.setValue(datetime.now().month)
        self.payroll_month.setMaximumWidth(110)
        self.payroll_month.setMinimumHeight(44)
        control_layout.addWidget(self.payroll_month)
        
        year_label = QLabel("Yıl:")
        year_label.setFont(QFont("Segoe UI", 15, QFont.Bold))
        control_layout.addWidget(year_label)
        self.payroll_year = QSpinBox()
        self.payroll_year.setMinimum(2020)
        self.payroll_year.setMaximum(2100)
        self.payroll_year.setValue(datetime.now().year)
        self.payroll_year.setMaximumWidth(120)
        self.payroll_year.setMinimumHeight(44)
        control_layout.addWidget(self.payroll_year)
        
        calculate_btn = QPushButton("Hesapla")
        calculate_btn.setMinimumHeight(46)
        control_layout.addWidget(calculate_btn)
        
        control_layout.addStretch()
        layout.addLayout(control_layout)
        
        # Results Group
        results_group = QGroupBox("Maaş Özeti")
        results_group.setObjectName("resultsGroup")
        results_layout = QVBoxLayout(results_group)
        results_layout.setContentsMargins(20, 20, 20, 20)
        results_layout.setSpacing(12)
        
        result_items = [
            ("normal_work_hours", "Normal Çalışma Saati", "0 h"),
            ("overtime_hours", "Mesai Saati", "0 h"),
            ("normal_salary", "Normal Maaş", "₺0.00"),
            ("overtime_salary", "Mesai Maaşı", "₺0.00"),
            ("total_salary", "Toplam Maaş", "₺0.00"),
        ]
        
        for key, label, default_value in result_items:
            row_layout = QHBoxLayout()
            label_widget = QLabel(f"{label}:")
            label_widget.setMinimumWidth(210)
            label_widget.setFont(QFont("Segoe UI", 16, QFont.Bold))
            value_widget = QLabel(default_value)
            value_widget.setFont(QFont("Segoe UI", 16))
            row_layout.addWidget(label_widget)
            row_layout.addWidget(value_widget, 1)
            row_layout.addStretch()
            results_layout.addLayout(row_layout)
            self.payroll_widgets[key] = value_widget
        
        layout.addWidget(results_group)
        
        # Table for historical/monthly data
        self.payroll_table = QTableWidget()
        self.payroll_table.setColumnCount(5)
        self.payroll_table.setHorizontalHeaderLabels([
            "Month", "Work Hours", "Overtime Hours", "Normal Salary", "Total Salary"
        ])
        self._configure_table(
            self.payroll_table,
            column_widths=[120, 140, 160, 160, None],
            centered_columns={0, 1, 2, 3, 4},
            row_height=46,
            header_height=42,
        )
        layout.addWidget(self.payroll_table)
        
        # Store button reference
        self.payroll_calculate_btn = calculate_btn
        
        return widget
    
    def _create_footer(self):
        """Create footer with action buttons."""
        footer = QFrame()
        footer.setObjectName("footerFrame")
        footer.setMinimumHeight(76)
        
        layout = QHBoxLayout(footer)
        layout.setContentsMargins(22, 14, 22, 14)
        layout.setSpacing(14)
        
        refresh_all_btn = QPushButton("Refresh All")
        logout_btn = QPushButton("Logout")
        close_btn = QPushButton("Close")

        for button in (refresh_all_btn, logout_btn, close_btn):
            button.setMinimumHeight(46)
        
        layout.addStretch()
        layout.addWidget(refresh_all_btn)
        layout.addWidget(logout_btn)
        layout.addWidget(close_btn)
        
        # Store button references
        self.refresh_all_btn = refresh_all_btn
        self.logout_btn = logout_btn
        self.close_btn = close_btn
        
        return footer
    
    def _apply_style(self):
        """Apply dark theme styling."""
        self.setFont(QFont("Segoe UI", 11))
        self.setStyleSheet("""
            QWidget {
                background: #0f172a;
                color: #e2e8f0;
                font-family: Segoe UI;
                font-size: 14px;
            }
            
            QFrame#headerFrame {
                background: #101a2b;
                border-bottom: 1px solid #22324f;
            }
            
            QLabel#headerTitle {
                color: #f8fafc;
                font-weight: 700;
                font-size: 34px;
            }
            
            QLabel#headerSubtitle {
                color: #94a3b8;
                font-size: 17px;
            }
            
            QFrame#footerFrame {
                background: #101a2b;
                border-top: 1px solid #22324f;
            }
            
            QTabWidget::pane {
                border: none;
                background: #101a2b;
            }
            
            QTabBar::tab {
                background: #101a2b;
                color: #cbd5e1;
                min-width: 160px;
                padding: 16px 24px;
                border: none;
                margin-right: 4px;
                min-height: 58px;
                font-size: 17px;
                font-weight: 600;
            }
            
            QTabBar::tab:selected {
                background: #2563eb;
                color: #fff;
            }
            
            QTabBar::tab:hover {
                background: #334155;
            }
            
            QGroupBox {
                color: #e2e8f0;
                border: 1px solid #22324f;
                border-radius: 14px;
                margin-top: 14px;
                padding-top: 14px;
                background: #101a2b;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px 0 6px;
            }
            
            QGroupBox#infoGroup {
                background: #101a2b;
            }
            
            QGroupBox#resultsGroup {
                background: #101a2b;
            }
            
            QFrame#summaryBox {
                background: #101a2b;
                border: 1px solid #22324f;
                border-radius: 16px;
            }
            
            QLabel#summaryTitle {
                color: #94a3b8;
                font-size: 21px;
                font-weight: 600;
                background: transparent;
            }
            
            QLabel#summaryValue {
                color: #ffffff;
                background: transparent;
            }
            
            QPushButton {
                background: #2563eb;
                color: white;
                border: none;
                border-radius: 12px;
                padding: 12px 18px;
                font-weight: 600;
                font-size: 15px;
            }
            
            QPushButton:hover {
                background: #1d4ed8;
            }
            
            QPushButton:pressed {
                background: #1e40af;
            }
            
            QSpinBox {
                background: #0f172a;
                color: #f8fafc;
                border: 1px solid #30415f;
                border-radius: 8px;
                padding: 8px 10px;
                font-size: 16px;
                min-height: 44px;
            }
            
            QSpinBox:focus {
                border: 1px solid #60a5fa;
            }
            
            QTableWidget {
                background: #101a2b;
                gridline-color: #22324f;
                border: 1px solid #22324f;
                border-radius: 12px;
                font-size: 16px;
            }
            
            QTableWidget::item {
                padding: 10px;
            }
            
            QTableWidget::item:selected {
                background: #2563eb;
            }
            
            QTableWidget::item:alternate {
                background: #0f172a;
            }
            
            QHeaderView::section {
                background: #17253d;
                color: #cbd5e1;
                padding: 12px 10px;
                border: none;
                border-right: 1px solid #22324f;
                font-weight: 700;
                font-size: 16px;
            }
            
            QScrollBar:vertical {
                background: #0f172a;
                width: 12px;
            }
            
            QScrollBar::handle:vertical {
                background: #475569;
                border-radius: 6px;
            }
            
            QScrollBar::handle:vertical:hover {
                background: #64748b;
            }
        """)
    
    def _connect_signals(self):
        """Connect signals for user interactions."""
        self.attendance_refresh_btn.clicked.connect(self._handle_attendance_refresh)
        self.payroll_calculate_btn.clicked.connect(self._handle_payroll_calculate)
        self.refresh_all_btn.clicked.connect(self._refresh_all)
        self.logout_btn.clicked.connect(self._handle_logout)
        self.close_btn.clicked.connect(self.close)
    
    def _load_initial_data(self):
        """Load initial data when panel opens."""
        try:
            self._load_dashboard()
            self._load_attendance()
        except (AuthorizationError, ValidationError, EmployeeNotFoundError) as e:
            self._show_message("Error", f"Failed to load data: {str(e)}", QMessageBox.Warning)
        except Exception as e:
            self._show_message("Unexpected Error", f"An unexpected error occurred: {str(e)}", QMessageBox.Critical)
    
    def _load_dashboard(self):
        """Load dashboard data for current month."""
        try:
            current_month = datetime.now().month
            current_year = datetime.now().year
            
            # Get attendance records for current month (now requires current_user)
            records = get_attendance_by_month(self.user, current_month, current_year)
            
            total_hours = 0
            total_overtime = 0
            last_attendance = None
            
            for record in records:
                if record["employee_id"] == self.employee_id:
                    total_hours += record["work_hours"] or 0
                    total_overtime += record["overtime_hours"] or 0
                    if last_attendance is None or record["work_date"] > last_attendance:
                        last_attendance = record["work_date"]
            
            # Get payroll estimate (now requires current_user)
            payroll = get_employee_monthly_payroll(
                self.user,
                self.employee_id,
                current_month,
                current_year
            )
            
            estimated_salary = "₺0.00"
            if payroll:
                estimated_salary = f"₺{payroll['total_salary']:.2f}"
            
            # Update dashboard widgets
            self.dashboard_widgets["monthly_hours"].value_label.setText(f"{total_hours} h")
            self.dashboard_widgets["monthly_overtime"].value_label.setText(f"{total_overtime} h")
            self.dashboard_widgets["estimated_salary"].value_label.setText(estimated_salary)
            
            last_date_str = str(last_attendance) if last_attendance else "No record"
            self.dashboard_widgets["last_attendance"].value_label.setText(last_date_str)
            
        except (ValidationError, AuthorizationError, EmployeeNotFoundError) as e:
            self._show_message("Data Error", str(e), QMessageBox.Warning)
        except Exception as e:
            self._show_message("Unexpected Error", f"An error occurred: {str(e)}", QMessageBox.Critical)
    
    def _load_attendance(self):
        """Load attendance records for selected month."""
        try:
            month = self.attendance_month.value()
            year = self.attendance_year.value()
            
            records = get_attendance_by_month(self.user, month, year)
            
            # Filter for current user only (service already filters for non-admin)
            user_records = [r for r in records if r["employee_id"] == self.employee_id]
            
            self.attendance_table.setRowCount(len(user_records))
            
            if not user_records:
                # Show empty state
                self.attendance_table.setRowCount(1)
                empty_item = self._create_table_item(
                    "No records found for selected period",
                    centered=False,
                    color="#94a3b8",
                )
                self.attendance_table.setItem(0, 0, empty_item)
            else:
                for row, record in enumerate(user_records):
                    date_item = self._create_table_item(str(record["work_date"]), centered=True)
                    status_item = self._create_table_item(record["status"].upper(), centered=True)
                    hours_item = self._create_table_item(f"{record['work_hours']} h", centered=True)
                    overtime_item = self._create_table_item(f"{record['overtime_hours']} h", centered=True)
                    
                    if record["status"] == "present":
                        details_item = self._create_table_item("Present", centered=False)
                        status_item.setForeground(QColor("#10b981"))
                    elif record["status"] == "absent":
                        details_item = self._create_table_item("Absent", centered=False)
                        status_item.setForeground(QColor("#ef4444"))
                    else:
                        details_item = self._create_table_item("Leave", centered=False)
                        status_item.setForeground(QColor("#f59e0b"))
                    
                    self.attendance_table.setItem(row, 0, date_item)
                    self.attendance_table.setItem(row, 1, status_item)
                    self.attendance_table.setItem(row, 2, hours_item)
                    self.attendance_table.setItem(row, 3, overtime_item)
                    self.attendance_table.setItem(row, 4, details_item)
            
        except (ValidationError, AuthorizationError, EmployeeNotFoundError) as e:
            self._show_message("Data Error", str(e), QMessageBox.Warning)
        except Exception as e:
            self._show_message("Unexpected Error", f"An error occurred: {str(e)}", QMessageBox.Critical)
    
    def _load_payroll(self):
        """Load payroll data for selected month."""
        try:
            month = self.payroll_month.value()
            year = self.payroll_year.value()
            
            payroll = get_employee_monthly_payroll(self.user, self.employee_id, month, year)
            
            if payroll:
                self.payroll_widgets["normal_work_hours"].setText(
                    f"{payroll['total_work_hours']} h"
                )
                self.payroll_widgets["overtime_hours"].setText(
                    f"{payroll['total_overtime_hours']} h"
                )
                self.payroll_widgets["normal_salary"].setText(
                    f"₺{payroll['normal_salary']:.2f}"
                )
                self.payroll_widgets["overtime_salary"].setText(
                    f"₺{payroll['overtime_salary']:.2f}"
                )
                self.payroll_widgets["total_salary"].setText(
                    f"₺{payroll['total_salary']:.2f}"
                )
            else:
                # Reset if no data
                self.payroll_widgets["normal_work_hours"].setText("0 h")
                self.payroll_widgets["overtime_hours"].setText("0 h")
                self.payroll_widgets["normal_salary"].setText("₺0.00")
                self.payroll_widgets["overtime_salary"].setText("₺0.00")
                self.payroll_widgets["total_salary"].setText("₺0.00")
            
            # Clear previous table data
            self._populate_payroll_table(payroll)
            
        except (ValidationError, AuthorizationError, EmployeeNotFoundError) as e:
            self._show_message("Data Error", str(e), QMessageBox.Warning)
        except Exception as e:
            self._show_message("Unexpected Error", f"An error occurred: {str(e)}", QMessageBox.Critical)
    
    def _handle_attendance_refresh(self):
        """Refresh attendance records."""
        self._load_attendance()
    
    def _configure_table(self, table, column_widths=None, centered_columns=None, row_height=36, header_height=34):
        """Configure table widget with common settings."""
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSelectionMode(QTableWidget.SingleSelection)
        table.setAlternatingRowColors(True)
        table.setShowGrid(True)
        table.setWordWrap(False)
        table.setFont(QFont("Segoe UI", 16))

        header = table.horizontalHeader()
        header.setDefaultAlignment(Qt.AlignCenter)
        header.setStretchLastSection(False)
        header.setHighlightSections(False)
        header.setFixedHeight(header_height)
        header.setSectionResizeMode(QHeaderView.Interactive)

        vertical_header = table.verticalHeader()
        vertical_header.setDefaultSectionSize(row_height)
        vertical_header.setVisible(False)

        if column_widths:
            for index, width in enumerate(column_widths):
                if width is None:
                    header.setSectionResizeMode(index, QHeaderView.Stretch)
                else:
                    header.setSectionResizeMode(index, QHeaderView.Fixed)
                    table.setColumnWidth(index, width)

        if centered_columns:
            table._centered_columns = set(centered_columns)

    def _create_table_item(self, text, centered=False, color=None):
        item = QTableWidgetItem("" if text is None else str(text))
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        item.setTextAlignment(Qt.AlignCenter if centered else (Qt.AlignLeft | Qt.AlignVCenter))
        if color is not None:
            item.setForeground(QColor(color))
        return item
    
    def _populate_payroll_table(self, payroll):
        """Populate payroll history table."""
        if payroll:
            self.payroll_table.setRowCount(1)
            month_str = f"{payroll['month']:02}/{payroll['year']}"
            
            month_item = self._create_table_item(month_str, centered=True)
            hours_item = self._create_table_item(f"{payroll['total_work_hours']} h", centered=True)
            overtime_item = self._create_table_item(f"{payroll['total_overtime_hours']} h", centered=True)
            salary_item = self._create_table_item(f"₺{payroll['normal_salary']:.2f}", centered=True)
            total_item = self._create_table_item(f"₺{payroll['total_salary']:.2f}", centered=True)
            
            self.payroll_table.setItem(0, 0, month_item)
            self.payroll_table.setItem(0, 1, hours_item)
            self.payroll_table.setItem(0, 2, overtime_item)
            self.payroll_table.setItem(0, 3, salary_item)
            self.payroll_table.setItem(0, 4, total_item)
        else:
            self.payroll_table.setRowCount(1)
            empty_item = self._create_table_item("No payroll data for selected period", centered=False, color="#94a3b8")
            self.payroll_table.setItem(0, 0, empty_item)
    
    def _handle_payroll_calculate(self):
        """Calculate and load payroll."""
        self._load_payroll()
    
    def _refresh_all(self):
        """Refresh all data."""
        try:
            self._load_dashboard()
            self._load_attendance()
            self._load_payroll()
            self._show_message("Success", "All data refreshed successfully")
        except Exception as e:
            self._show_message("Error", f"Failed to refresh data: {str(e)}", QMessageBox.Warning)
    
    def _handle_logout(self):
        """Handle logout."""
        reply = QMessageBox.question(
            self,
            "Confirm Logout",
            "Are you sure you want to logout?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                from ui.login_window import LoginWindow
                self.next_window = LoginWindow()
                self.next_window.show()
                self.close()
            except Exception as e:
                self._show_message("Logout Error", f"Logout failed: {str(e)}", QMessageBox.Critical)
    
    def _show_message(self, title, text, icon=QMessageBox.Information):
        """Show a message box."""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(title)
        msg_box.setText(text)
        msg_box.setIcon(icon)
        msg_box.setStyleSheet("""
            QMessageBox {
                background: #0f172a;
            }
            QMessageBox QLabel {
                color: #e2e8f0;
            }
            QMessageBox QPushButton {
                min-width: 60px;
                padding: 6px 12px;
            }
        """)
        msg_box.exec_()
