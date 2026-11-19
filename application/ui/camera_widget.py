import cv2
import time
from datetime import datetime
from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QPushButton, QHBoxLayout
from PySide6.QtGui import QImage, QPixmap
from ai.engine import FaceRecognitionEngine
from services.attendance_service import mark_attendance_for_slot, fill_absent_previous_days
from core.db import get_camera_status, set_camera_status
from ui.student_window import Student


def is_slot_active(slots):
    if not slots:
        return True
    now = datetime.now().time()
    for slot in slots:
        try:
            start_time = datetime.strptime(slot["start"], "%H:%M").time()
            end_time = datetime.strptime(slot["end"], "%H:%M").time()
            if start_time <= now <= end_time:
                return True
        except Exception:
            continue
    return False


class CameraWorker(QThread):
    frame_ready = Signal(object, object)
    people_ready = Signal(list)
    status_ready = Signal(str)

    def __init__(self, camera_source, class_name, slots=None):
        super().__init__()
        self.camera_source = camera_source
        self.class_name = class_name
        self.slots = slots or []
        self.running = True
        self.camera_enabled = True
        self.recognizer = FaceRecognitionEngine(self.class_name)
        self.recognized_students = set()
        self.recognized_teachers = set()
        self.last_db_write = 0
        self.db_write_interval = 25

    def run(self):
        self.recognizer.load_known_faces()
        fill_absent_previous_days(self.class_name)
        cap = None

        while self.running:
            if not self.camera_enabled:
                if cap is not None and cap.isOpened():
                    cap.release()
                    cap = None
                self.status_ready.emit("Camera OFF")
                self.people_ready.emit([])
                self.recognized_students.clear()
                self.msleep(100)
                continue

            if cap is None or not cap.isOpened():
                src = self.camera_source
                if str(src).isdigit():
                    src = int(src)
                cap = cv2.VideoCapture(src)
                if not cap.isOpened():
                    self.status_ready.emit("Camera Offline / Connecting...")
                    self.msleep(1000)
                    continue

            ret, frame = cap.read()
            if not ret or frame is None:
                self.msleep(50)
                continue

            frame = cv2.flip(frame, 1)
            people = []

            if is_slot_active(self.slots):
                frame, students, teachers, people = self.recognizer.detect_and_recognize(frame)
                self.status_ready.emit("Recognition ON")
                for name in students:
                    if name:
                        self.recognized_students.add(name)
                self.recognized_teachers.clear()
                for name in teachers:
                    if name:
                        self.recognized_teachers.add(name)

                now = time.time()
                if self.recognized_students and (now - self.last_db_write >= self.db_write_interval):
                    try:
                        ok = mark_attendance_for_slot(
                            self.class_name,
                            self.recognized_students,
                            self.recognized_teachers
                        )
                    except Exception:
                        ok = False
                    self.last_db_write = now
            else:
                self.status_ready.emit("Recognition OFF (Slot Inactive)")
                self.recognized_students.clear()

            display_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = display_rgb.shape
            bytes_per_line = ch * w
            qimg = QImage(display_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888).copy()

            self.frame_ready.emit(frame, qimg)
            self.people_ready.emit(people)
            self.msleep(25)

        if cap is not None and cap.isOpened():
            cap.release()

    def set_camera_enabled(self, enabled):
        self.camera_enabled = enabled
        if not enabled:
            self.recognized_students.clear()
            self.people_ready.emit([])

    def stop(self):
        self.running = False
        self.quit()
        self.wait(1500)


class CameraWidget(QWidget):
    classroom_deleted = Signal(str)

    def __init__(self, camera_source, class_name, slots=None):
        super().__init__()
        self.camera_source = camera_source
        self.class_name = class_name
        self.slots = slots or []
        self.people = []
        self.student_page = None
        self.camera_on = get_camera_status(self.class_name)

        self.setFixedSize(360, 320)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        self.title = QLabel(f"Class: {class_name}")
        self.title.setFixedHeight(24)
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setStyleSheet("font-size: 13px; font-weight: bold;")

        self.status_label = QLabel("Checking slot...")
        self.status_label.setFixedHeight(20)
        self.status_label.setAlignment(Qt.AlignCenter)

        self.label = QLabel("Starting camera...")
        self.label.setFixedSize(348, 230)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("background-color: black; color: white; border: 1px solid #444;")

        self.student_button = QPushButton("See Students")
        self.student_button.setFixedSize(120, 28)

        self.camera_toggle_button = QPushButton("Turn Camera OFF")
        self.camera_toggle_button.setFixedSize(120, 28)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.student_button)
        button_layout.addWidget(self.camera_toggle_button)
        button_layout.addStretch()

        layout.addWidget(self.title)
        layout.addWidget(self.status_label)
        layout.addWidget(self.label)
        layout.addLayout(button_layout)

        if not self.camera_on:
            self.camera_toggle_button.setText("Turn Camera ON")
            self.label.setText("Camera is OFF")
            self.label.setStyleSheet("background-color: black; color: red; border: 1px solid #444; font-weight: bold;")
            self.status_label.setText("Camera OFF")
            self.status_label.setStyleSheet("color: red; font-weight: bold; font-size: 11px;")
        else:
            self.camera_toggle_button.setText("Turn Camera OFF")
            self.label.setText("Starting camera...")

        self.worker = CameraWorker(camera_source, class_name, self.slots)
        self.worker.set_camera_enabled(self.camera_on)
        self.worker.frame_ready.connect(self.update_frame)
        self.worker.people_ready.connect(self.update_people)
        self.worker.status_ready.connect(self.update_status)
        self.worker.start()

        self.student_button.clicked.connect(self.open_student_page)
        self.camera_toggle_button.clicked.connect(self.toggle_camera)

    def update_status(self, text):
        self.status_label.setText(text)
        if "ON" in text:
            self.status_label.setStyleSheet("color: green; font-weight: bold; font-size: 11px;")
        elif "OFF" in text or "Inactive" in text:
            self.status_label.setStyleSheet("color: orange; font-weight: bold; font-size: 11px;")
        else:
            self.status_label.setStyleSheet("color: red; font-weight: bold; font-size: 11px;")

    def update_frame(self, raw_frame, qimg):
        if not self.camera_on:
            return
        pixmap = QPixmap.fromImage(qimg).scaled(
            self.label.width(),
            self.label.height(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.label.setPixmap(pixmap)
        if self.student_page is not None and self.student_page.isVisible():
            self.student_page.update_frame_qimg(qimg)

    def update_people(self, people):
        self.people = people
        if self.student_page is not None and self.student_page.isVisible():
            self.student_page.update_table(people)

    def toggle_camera(self):
        self.camera_on = not self.camera_on
        set_camera_status(self.class_name, self.camera_source, self.camera_on)
        self.worker.set_camera_enabled(self.camera_on)

        if self.camera_on:
            self.camera_toggle_button.setText("Turn Camera OFF")
            self.label.setStyleSheet("background-color: black; color: white; border: 1px solid #444;")
            self.label.setText("Starting camera...")
        else:
            self.camera_toggle_button.setText("Turn Camera ON")
            self.label.clear()
            self.label.setText("Camera is OFF")
            self.label.setStyleSheet("background-color: black; color: red; border: 1px solid #444; font-weight: bold;")
            if self.student_page is not None:
                self.student_page.update_table([])

    def open_student_page(self):
        if self.student_page is None:
            self.student_page = Student(self.camera_source, self.class_name, recognizer=self.worker.recognizer)
            self.student_page.classroom_deleted.connect(self.handle_classroom_deleted)
        self.student_page.show()
        self.student_page.raise_()
        self.student_page.activateWindow()

    def handle_classroom_deleted(self):
        self.worker.stop()
        self.classroom_deleted.emit(self.class_name)
        self.close()

    def closeEvent(self, event):
        self.worker.stop()
        if self.student_page is not None:
            self.student_page.close()
        event.accept()
