from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from services.auth_service import login, normalize_user


class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.logged_in_user = None
        self.next_window = None  # AdminPanel / UserPanel referansı

        self.setWindowTitle("Çalışan Yoklama Sistemi")
        self.setFixedSize(720, 560)

        self.email_input = QLineEdit()
        self.password_input = QLineEdit()
        self.login_button = QPushButton("Giriş Yap")
        self.exit_button = QPushButton("Çıkış")

        self._build_ui()
        self._apply_style()
        self._connect_signals()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(48, 48, 48, 48)
        main_layout.setSpacing(28)

        main_layout.addStretch()

        header_label = QLabel("Çalışan Yoklama Sistemi")
        header_label.setAlignment(Qt.AlignCenter)
        header_label.setObjectName("headerLabel")

        subtitle_label = QLabel("Lütfen giriş yapın")
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setObjectName("subtitleLabel")

        form_frame = QFrame()
        form_frame.setObjectName("formFrame")
        form_layout = QVBoxLayout(form_frame)
        form_layout.setContentsMargins(28, 28, 28, 28)
        form_layout.setSpacing(18)

        self.email_input.setPlaceholderText("email@example.com")
        self.email_input.setClearButtonEnabled(True)
        self.email_input.setMinimumHeight(52)

        self.password_input.setPlaceholderText("Parola")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setClearButtonEnabled(True)
        self.password_input.setMinimumHeight(52)

        email_label = QLabel("Email")
        password_label = QLabel("Parola")

        form_layout.addWidget(email_label)
        form_layout.addWidget(self.email_input)
        form_layout.addWidget(password_label)
        form_layout.addWidget(self.password_input)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(18)
        button_layout.addWidget(self.login_button)
        button_layout.addWidget(self.exit_button)

        main_layout.addWidget(header_label)
        main_layout.addWidget(subtitle_label)
        main_layout.addWidget(form_frame)
        main_layout.addLayout(button_layout)

        main_layout.addStretch()

        self.header_label = header_label
        self.subtitle_label = subtitle_label
        self.form_frame = form_frame

        self.login_button.setObjectName("loginButton")
        self.exit_button.setObjectName("exitButton")
        self.login_button.setMinimumHeight(52)
        self.exit_button.setMinimumHeight(52)

        self.setFont(QFont("Segoe UI", 12))

        self.email_input.setFocus()

    def _apply_style(self):
        self.setStyleSheet("""
            QWidget {
                background: #0f172a;
                color: #e2e8f0;
                font-family: Segoe UI;
                font-size: 14px;
            }

            QLabel#headerLabel {
                font-size: 36px;
                font-weight: 700;
                color: #f8fafc;
            }

            QLabel#subtitleLabel {
                color: #94a3b8;
                font-size: 16px;
                margin-bottom: 8px;
            }

            QFrame#formFrame {
                background: #111827;
                border: 1px solid #334155;
                border-radius: 16px;
            }

            QLabel {
                color: #cbd5e1;
                font-size: 14px;
            }

            QLineEdit {
                background: #0b1220;
                border: 1px solid #334155;
                border-radius: 14px;
                padding: 14px 16px;
                color: #f8fafc;
                selection-background-color: #2563eb;
                font-size: 15px;
            }

            QLineEdit:focus {
                border: 1px solid #60a5fa;
            }

            QPushButton {
                border: none;
                border-radius: 14px;
                padding: 14px 18px;
                font-weight: 600;
                font-size: 15px;
            }

            QPushButton#loginButton {
                background: #2563eb;
                color: white;
            }

            QPushButton#loginButton:hover {
                background: #1d4ed8;
            }

            QPushButton#loginButton:pressed {
                background: #1e40af;
            }

            QPushButton#exitButton {
                background: #334155;
                color: #e2e8f0;
            }

            QPushButton#exitButton:hover {
                background: #475569;
            }

            QPushButton#exitButton:pressed {
                background: #1e293b;
            }
        """)

    def _connect_signals(self):
        self.login_button.clicked.connect(self.handle_login)
        self.exit_button.clicked.connect(self.close)
        self.password_input.returnPressed.connect(self.handle_login)
        self.email_input.returnPressed.connect(self.handle_login)

    def _get_user_role(self, user):
        if isinstance(user, dict):
            return bool(user.get("is_admin", 0))
        return bool(getattr(user, "is_admin", 0))

    def _open_panel(self, user):
        is_admin = self._get_user_role(user)

        if is_admin:
            from ui.admin_panel import AdminPanel
            self.next_window = AdminPanel(user)
        else:
            from ui.user_panel import UserPanel
            self.next_window = UserPanel(user)

        self.next_window.show()
        self.close()

    def handle_login(self):
        email = self.email_input.text().strip().lower()
        password = self.password_input.text()

        if not email or not password:
            QMessageBox.warning(self, "Uyarı", "Email veya parola hatalı.")
            return

        try:
            user = login(email, password)
        except (ValueError, Exception) as e:
            QMessageBox.critical(self, "Hata", f"Giriş sırasında bir hata oluştu:\n{str(e)}")
            return

        if not user:
            QMessageBox.warning(self, "Uyarı", "Email veya parola hatalı.")
            return

        try:
            normalized_user = normalize_user(user)
        except ValueError as e:
            QMessageBox.critical(self, "Hata", f"Kullanıcı verisi hatalı:\n{str(e)}")
            return

        self.logged_in_user = normalized_user
        self._open_panel(normalized_user)