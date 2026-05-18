import sys

from PyQt5.QtWidgets import QApplication

from database.db import init_db
from ui.login_window import LoginWindow


def main():
    init_db()

    app = QApplication(sys.argv)

    window = LoginWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()