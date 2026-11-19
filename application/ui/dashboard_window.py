import psutil
from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QVBoxLayout,
    QPushButton,
    QGridLayout,
    QHBoxLayout,
    QMessageBox,
    QScrollArea,
    QSizePolicy
)
from PySide6.QtCore import Qt, QTimer, QThread
from core.db import load_qss_file, is_supabase_available
from core.sync import get_sync_status, process_sync_queue
from services.auth_service import logout
from services.classroom_service import get_classrooms_by_college_id
from ui.camera_widget import CameraWidget
from ui.dialogs import CameraInputDialog, LoadingDialog, AddClassWorker


class Dashboard(QWidget):
    def __init__(self, user_data):
        super().__init__()
        load_qss_file(self, "main_dashboard.qss")
        self.user_data = user_data
        self.college_id = user_data["id"]
        self.user_name = user_data["creator"]

        self.setWindowTitle("AttendMate Dashboard")
        self.resize(1150, 720)

        self.camera_count = 0
        self.camera_widgets = []
        self.pending_classrooms = []

        outer_layout = QVBoxLayout(self)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        outer_layout.addWidget(self.scroll_area)

        self.content_widget = QWidget()
        self.scroll_area.setWidget(self.content_widget)

        self.main_layout = QVBoxLayout(self.content_widget)
        self.main_layout.setContentsMargins(12, 12, 12, 12)
        self.main_layout.setSpacing(10)

        self.navbar_title = QLabel("AttendMate Enterprise AI Engine")
        self.navbar_title.setObjectName("navbarTitle")
        self.navbar_title.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.navbar_title)

        top_bar = QHBoxLayout()
        self.name = QLabel(f"Welcome, {self.user_name}")
        self.name.setObjectName("welcomeLabel")
        self.logout_btn = QPushButton("Logout")
        self.logout_btn.setObjectName("logoutButton")
        self.logout_btn.clicked.connect(self.handle_logout)

        top_bar.addWidget(self.name)
        top_bar.addStretch()
        top_bar.addWidget(self.logout_btn)
        self.main_layout.addLayout(top_bar)

        self.resource_layout = QHBoxLayout()
        self.resource_layout.setSpacing(15)

        self.system_status_label = QLabel("● Safe")
        self.system_status_label.setObjectName("systemStatus")
        self.cpu_label = QLabel("CPU Usage: 0%")
        self.ram_label = QLabel("RAM Usage: 0%")
        self.camera_label = QLabel("Running Classrooms: 0")
        self.sync_status_label = QLabel("● Synced")
        self.sync_status_label.setObjectName("syncStatus")

        self.resource_layout.addWidget(self.system_status_label)
        self.resource_layout.addWidget(self.cpu_label)
        self.resource_layout.addWidget(self.ram_label)
        self.resource_layout.addWidget(self.camera_label)
        self.resource_layout.addWidget(self.sync_status_label)
        self.resource_layout.addStretch()
        self.main_layout.addLayout(self.resource_layout)

        self.grid_layout = QGridLayout()
        self.grid_layout.setColumnStretch(0, 1)
        self.grid_layout.setColumnStretch(1, 1)
        self.grid_layout.setSpacing(12)
        self.main_layout.addLayout(self.grid_layout)

        self.footer = QLabel("© 2026 AttendMate • Next-Gen Attendance Architecture")
        self.footer.setObjectName("footer")
        self.footer.setAlignment(Qt.AlignCenter)
        self.footer.setMinimumHeight(30)
        self.main_layout.addWidget(self.footer)

        self.add_button = QPushButton("Add Camera")
        self.add_button.setFixedSize(360, 200)
        self.add_button.clicked.connect(self.ask_camera)

        self.resource_timer = QTimer()
        self.resource_timer.timeout.connect(self.update_resources)
        self.resource_timer.start(1500)

        self.load_saved_classrooms()
        self.start_saved_cameras_one_by_one()

    def stop_all_cameras(self):
        for cam in self.camera_widgets:
            try:
                cam.worker.stop()
            except Exception:
                pass
        self.camera_widgets.clear()

    def handle_logout(self):
        from ui.login_window import LoginPage
        self.stop_all_cameras()
        logout(self.college_id)
        self.close()
        self.login_window = LoginPage()
        self.login_window.show()

    def update_resources(self):
        cpu = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory().percent

        self.cpu_label.setText(f"CPU Usage: {cpu}%")
        self.ram_label.setText(f"RAM Usage: {ram}%")
        self.camera_label.setText(f"Running Classrooms: {len(self.camera_widgets)}")

        if cpu > 85 or ram > 85:
            self.system_status_label.setText("● High Load")
            color = "red"
        elif cpu > 70 or ram > 70:
            self.system_status_label.setText("● Moderate")
            color = "orange"
        else:
            self.system_status_label.setText("● Safe")
            color = "lightgreen"

        self.system_status_label.setStyleSheet(f"""
            color: {color};
            border: 1px solid #d9dde3;
            border-radius: 8px;
            padding: 6px 10px;
            font-weight: 500;
        """)

        if not is_supabase_available():
            self.sync_status_label.setText("● Offline")
            color = "red"
        else:
            pending = get_sync_status()
            if pending > 0:
                self.sync_status_label.setText(f"● Pending ({pending})")
                color = "orange"
                process_sync_queue()
            else:
                self.sync_status_label.setText("● Synced")
                color = "lightgreen"

        self.sync_status_label.setStyleSheet(f"""
            color: {color};
            border: 1px solid #d9dde3;
            border-radius: 8px;
            padding: 6px 10px;
            font-weight: 500;
        """)

    def load_saved_classrooms(self):
        classrooms = get_classrooms_by_college_id(self.college_id)
        self.pending_classrooms = classrooms if classrooms else []

    def start_saved_cameras_one_by_one(self):
        self.sequential_timer = QTimer()
        self.sequential_timer.timeout.connect(self.load_next_camera)
        self.sequential_timer.start(1800)

    def load_next_camera(self):
        cpu = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory().percent
        if cpu > 85 or ram > 85:
            return

        if not self.pending_classrooms:
            self.sequential_timer.stop()
            self.place_add_button()
            return

        classroom = self.pending_classrooms.pop(0)
        cam_source = classroom["camera_input"]
        classroom_name = classroom["classroom_name"]
        slots = classroom.get("slot", [])

        if str(cam_source).isdigit():
            cam_source = int(cam_source)

        self.add_camera(cam_source, classroom_name, slots)

    def place_add_button(self):
        self.grid_layout.removeWidget(self.add_button)
        row = self.camera_count // 2
        col = self.camera_count % 2
        self.grid_layout.addWidget(self.add_button, row, col)

    def on_classroom_deleted(self, class_name):
        self.camera_widgets = [w for w in self.camera_widgets if w.class_name != class_name]
        self.camera_count = len(self.camera_widgets)
        for i in reversed(range(self.grid_layout.count())):
            item = self.grid_layout.itemAt(i)
            widget = item.widget()
            if widget:
                self.grid_layout.removeWidget(widget)
        for idx, cam in enumerate(self.camera_widgets):
            row = idx // 2
            col = idx % 2
            self.grid_layout.addWidget(cam, row, col)
        self.place_add_button()

    def ask_camera(self):
        dialog = CameraInputDialog()
        if not dialog.exec():
            return
        cam_source, classroom_name, slots = dialog.get_data()
        if not cam_source or not classroom_name:
            return

        self.loading_dialog = LoadingDialog("Setting up classroom database...")
        self.loading_dialog.show()
        self.add_button.setEnabled(False)

        self.add_thread = QThread()
        self.add_worker = AddClassWorker(
            self.college_id,
            classroom_name,
            cam_source,
            slots
        )
        self.add_worker.moveToThread(self.add_thread)
        self.add_thread.started.connect(self.add_worker.run)
        self.add_worker.finished.connect(self.on_add_class_success)
        self.add_worker.error.connect(self.on_add_class_error)

        self.add_worker.finished.connect(self.add_thread.quit)
        self.add_worker.error.connect(self.add_thread.quit)
        self.add_worker.finished.connect(self.add_worker.deleteLater)
        self.add_worker.error.connect(self.add_worker.deleteLater)
        self.add_thread.finished.connect(self.add_thread.deleteLater)
        self.add_thread.start()

    def on_add_class_success(self, data):
        self.add_button.setEnabled(True)
        if hasattr(self, "loading_dialog"):
            self.loading_dialog.close()

        QMessageBox.information(self, "Success", "Classroom created successfully")
        cam_source = data["camera_input"]
        classroom_name = data["classroom_name"]
        slots = data.get("slot", [])
        if str(cam_source).isdigit():
            cam_source = int(cam_source)
        self.add_camera(cam_source, classroom_name, slots)

    def on_add_class_error(self, message):
        self.add_button.setEnabled(True)
        if hasattr(self, "loading_dialog"):
            self.loading_dialog.close()
        QMessageBox.critical(self, "Error", message)

    def add_camera(self, cam_source, classroom_name, slots):
        cam_widget = CameraWidget(cam_source, classroom_name, slots)
        cam_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        cam_widget.classroom_deleted.connect(self.on_classroom_deleted)

        row = self.camera_count // 2
        col = self.camera_count % 2

        self.grid_layout.removeWidget(self.add_button)
        self.grid_layout.addWidget(cam_widget, row, col)
        self.camera_widgets.append(cam_widget)
        self.camera_count += 1
        self.place_add_button()

    def closeEvent(self, event):
        self.resource_timer.stop()
        if hasattr(self, "sequential_timer"):
            self.sequential_timer.stop()
        self.stop_all_cameras()
        event.accept()
