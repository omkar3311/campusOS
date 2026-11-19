from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QHBoxLayout,
    QFrame,
    QCompleter,
    QDialog
)
from PySide6.QtCore import Qt, QThread, Signal
from core.db import load_qss_file
from core.sync import startup_sync
from services.auth_service import check_college_login, get_college_names, enroll_login
from ui.dashboard_window import Dashboard


class LoadingDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Please wait")
        self.setFixedSize(320, 100)
        layout = QVBoxLayout(self)
        self.label = QLabel("Synchronizing and setting up classrooms...")
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)


class SyncWorker(QThread):
    finished = Signal()

    def run(self):
        startup_sync()
        self.finished.emit()


class LoginPage(QWidget):
    def __init__(self):
        super().__init__()
        load_qss_file(self, "style.qss")
        self.setWindowTitle("AttendMate Enterprise Login")
        self.resize(600, 480)

        main_layout = QVBoxLayout()
        center_layout = QHBoxLayout()

        self.navbar_title = QLabel("AttendMate")
        self.navbar_title.setObjectName("navbarTitle")
        self.navbar_title.setAlignment(Qt.AlignCenter)

        self.card = QFrame()
        self.card.setObjectName("loginCard")
        self.card.setFixedWidth(340)

        card_layout = QVBoxLayout()
        card_layout.setSpacing(14)

        self.label = QLabel("College Portal Login")
        self.label.setObjectName("title")

        self.name = QLineEdit()
        self.name.setPlaceholderText("Enter Creator Name")

        self.email = QLineEdit()
        self.email.setPlaceholderText("Enter Creator Email")

        self.college_name = QLineEdit()
        self.college_name.setPlaceholderText("Enter College Name")
        college_names = get_college_names()
        self.completer = QCompleter(college_names)
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchContains)
        self.college_name.setCompleter(self.completer)

        self.password = QLineEdit()
        self.password.setPlaceholderText("Enter Password")
        self.password.setEchoMode(QLineEdit.Password)

        self.button = QPushButton("Secure Login")
        self.message = QLabel("")
        self.message.setObjectName("message")

        self.footer = QLabel("© 2026 AttendMate • CampusOS")
        self.footer.setObjectName("footer")
        self.footer.setAlignment(Qt.AlignCenter)

        card_layout.addWidget(self.label)
        card_layout.addWidget(self.name)
        card_layout.addWidget(self.email)
        card_layout.addWidget(self.college_name)
        card_layout.addWidget(self.password)
        card_layout.addWidget(self.button)
        card_layout.addWidget(self.message)
        card_layout.addWidget(self.footer)
        self.card.setLayout(card_layout)

        center_layout.addStretch()
        center_layout.addWidget(self.card)
        center_layout.addStretch()

        main_layout.addWidget(self.navbar_title)
        main_layout.addStretch()
        main_layout.addLayout(center_layout)
        main_layout.addStretch()
        self.setLayout(main_layout)

        self.button.clicked.connect(self.login_msg)
        self.password.returnPressed.connect(self.login_msg)

    def login_msg(self):
        name = self.name.text().strip()
        email = self.email.text().strip()
        college_name = self.college_name.text().strip()
        pwd = self.password.text().strip()

        if not name or not email or not college_name or not pwd:
            self.message.setStyleSheet("color: orange;")
            self.message.setText("Please fill all fields")
            return

        result = check_college_login(name, email, college_name, pwd)
        if result:
            self.message.setStyleSheet("color: lightgreen;")
            self.message.setText("Login successful. Initializing...")

            enroll_login(
                id=result["id"],
                college_name=result["college_name"],
                creator=result["creator"],
                creator_email=result["creator_email"],
                password=pwd
            )

            self.loading = LoadingDialog()
            self.worker = SyncWorker()

            def on_done():
                self.loading.accept()
                self.dashboard = Dashboard(result)
                self.dashboard.show()
                self.close()

            self.worker.finished.connect(on_done)
            self.worker.start()
            self.loading.exec()
        else:
            self.message.setStyleSheet("color: red;")
            self.message.setText("Invalid credentials or unauthorized college")
