import cv2
import json
from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QVBoxLayout,
    QPushButton,
    QDialog,
    QLineEdit,
    QHBoxLayout,
    QMessageBox,
    QFileDialog
)
from PySide6.QtCore import Qt, QObject, Signal
from services.classroom_service import (
    add_classroom,
    add_student_to_classroom
)


class SlotRow(QWidget):
    def __init__(self, removable=False, remove_callback=None):
        super().__init__()
        self.remove_callback = remove_callback
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        self.start_input = QLineEdit("00:00")
        self.start_input.setInputMask("99:99")
        self.start_input.setPlaceholderText("HH:MM")

        self.end_input = QLineEdit("00:00")
        self.end_input.setInputMask("99:99")
        self.end_input.setPlaceholderText("HH:MM")

        layout.addWidget(QLabel("Start:"))
        layout.addWidget(self.start_input)
        layout.addWidget(QLabel("End:"))
        layout.addWidget(self.end_input)

        if removable:
            remove_btn = QPushButton("-")
            remove_btn.setFixedWidth(35)
            remove_btn.clicked.connect(self.remove_self)
            layout.addWidget(remove_btn)

        self.setLayout(layout)

    def remove_self(self):
        if self.remove_callback:
            self.remove_callback(self)

    def get_slot_data(self):
        return {
            "start": self.start_input.text().strip(),
            "end": self.end_input.text().strip()
        }


class CameraInputDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Add Classroom")
        self.resize(420, 480)
        self.slot_rows = []

        self.main_layout = QVBoxLayout(self)

        self.main_layout.addWidget(QLabel("Camera Source (Index or RTSP/HTTP URL):"))
        self.camera_input = QLineEdit()
        self.camera_input.setPlaceholderText("0 or http://.../video")
        self.main_layout.addWidget(self.camera_input)

        self.test_cam_btn = QPushButton("Test Camera Connection")
        self.test_cam_btn.clicked.connect(self.test_camera_stream)
        self.main_layout.addWidget(self.test_cam_btn)

        self.main_layout.addWidget(QLabel("Classroom Name:"))
        self.classroom_name_input = QLineEdit()
        self.classroom_name_input.setPlaceholderText("e.g. class_a")
        self.main_layout.addWidget(self.classroom_name_input)

        slot_header = QHBoxLayout()
        slot_header.addWidget(QLabel("Time Slots:"))
        self.add_slot_btn = QPushButton("+")
        self.add_slot_btn.setFixedWidth(35)
        self.add_slot_btn.clicked.connect(self.add_slot_row)
        slot_header.addWidget(self.add_slot_btn)
        self.main_layout.addLayout(slot_header)

        self.slots_layout = QVBoxLayout()
        self.main_layout.addLayout(self.slots_layout)
        self.add_slot_row(first=True)

        buttons = QHBoxLayout()
        ok_btn = QPushButton("OK")
        cancel_btn = QPushButton("Cancel")
        buttons.addWidget(ok_btn)
        buttons.addWidget(cancel_btn)
        self.main_layout.addLayout(buttons)

        ok_btn.clicked.connect(self.validate_and_accept)
        cancel_btn.clicked.connect(self.reject)

    def test_camera_stream(self):
        cam_source = self.camera_input.text().strip()
        if not cam_source:
            QMessageBox.warning(self, "Camera Test", "Please enter a camera source first.")
            return
        if cam_source.isdigit():
            cam_source = int(cam_source)
        cap = cv2.VideoCapture(cam_source)
        if cap is not None and cap.isOpened():
            ret, _ = cap.read()
            cap.release()
            if ret:
                QMessageBox.information(self, "Camera Test", "Camera connection successful!")
                return
        QMessageBox.critical(self, "Camera Test", "Could not connect to the specified camera.")

    def add_slot_row(self, first=False):
        row = SlotRow(removable=not first, remove_callback=self.remove_slot_row)
        self.slot_rows.append(row)
        self.slots_layout.addWidget(row)

    def remove_slot_row(self, row_widget):
        self.slot_rows.remove(row_widget)
        self.slots_layout.removeWidget(row_widget)
        row_widget.deleteLater()

    def validate_and_accept(self):
        cam_source = self.camera_input.text().strip()
        classroom_name = self.classroom_name_input.text().strip()

        if not cam_source or not classroom_name:
            QMessageBox.warning(self, "Error", "Camera source and classroom name are required.")
            return

        slots = []
        for row in self.slot_rows:
            slot = row.get_slot_data()
            if not slot["start"] or not slot["end"]:
                QMessageBox.warning(self, "Error", "All slot fields must be filled.")
                return
            slots.append(slot)

        self.accept()

    def get_data(self):
        slots = [row.get_slot_data() for row in self.slot_rows]
        return (
            self.camera_input.text().strip(),
            self.classroom_name_input.text().strip(),
            slots
        )


class EditClassroomDialog(QDialog):
    def __init__(self, classroom_data):
        super().__init__()
        self.classroom_data = classroom_data
        self.setWindowTitle("Edit Classroom")
        self.resize(450, 300)

        layout = QVBoxLayout(self)

        self.class_name_input = QLineEdit()
        self.class_name_input.setPlaceholderText("Enter classroom name")
        self.class_name_input.setText(classroom_data.get("classroom_name", ""))
        layout.addWidget(QLabel("Classroom Name"))
        layout.addWidget(self.class_name_input)

        self.camera_input = QLineEdit()
        self.camera_input.setPlaceholderText("Enter camera input")
        self.camera_input.setText(str(classroom_data.get("camera_input", "")))
        layout.addWidget(QLabel("Camera Input"))
        layout.addWidget(self.camera_input)

        self.slot_input = QLineEdit()
        self.slot_input.setPlaceholderText('Example: [{"start":"01:00","end":"02:00"}]')
        slot_value = classroom_data.get("slot", "")
        if isinstance(slot_value, list):
            self.slot_input.setText(json.dumps(slot_value))
        else:
            self.slot_input.setText(str(slot_value))
        layout.addWidget(QLabel("Slots JSON"))
        layout.addWidget(self.slot_input)

        self.save_btn = QPushButton("Update Classroom")
        self.save_btn.clicked.connect(self.validate_and_accept)
        layout.addWidget(self.save_btn)

    def validate_and_accept(self):
        class_name = self.class_name_input.text().strip()
        camera_input = self.camera_input.text().strip()
        slot_text = self.slot_input.text().strip()

        if not class_name or not camera_input or not slot_text:
            QMessageBox.warning(self, "Missing Data", "Please fill all fields.")
            return

        try:
            parsed = json.loads(slot_text)
            if not isinstance(parsed, list):
                raise ValueError
        except Exception:
            QMessageBox.warning(self, "Invalid Data", "Slots must be a valid JSON list.")
            return

        self.accept()

    def get_data(self):
        return {
            "classroom_name": self.class_name_input.text().strip(),
            "camera_input": self.camera_input.text().strip(),
            "slot": json.loads(self.slot_input.text().strip())
        }


class AddStudentDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Add Student")
        self.resize(420, 320)
        self.image_path = ""

        layout = QVBoxLayout(self)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter student name")
        layout.addWidget(self.name_input)

        self.prn_input = QLineEdit()
        self.prn_input.setPlaceholderText("Enter student PRN")
        layout.addWidget(self.prn_input)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Enter student email")
        layout.addWidget(self.email_input)

        self.pass_input = QLineEdit()
        self.pass_input.setPlaceholderText("Enter student password")
        self.pass_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.pass_input)

        self.image_label = QLabel("No image selected")
        self.image_label.setWordWrap(True)
        layout.addWidget(self.image_label)

        self.select_btn = QPushButton("Select Image")
        self.select_btn.clicked.connect(self.select_image)
        layout.addWidget(self.select_btn)

        self.ok_btn = QPushButton("Add Student")
        self.ok_btn.clicked.connect(self.validate_and_accept)
        layout.addWidget(self.ok_btn)

    def select_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Student Image",
            "",
            "Images (*.png *.jpg *.jpeg)"
        )
        if file_path:
            self.image_path = file_path
            self.image_label.setText(file_path)

    def validate_and_accept(self):
        student_name = self.name_input.text().strip()
        prn = self.prn_input.text().strip()
        email = self.email_input.text().strip()
        password = self.pass_input.text().strip()

        if not student_name or not prn or not email or not password or not self.image_path:
            QMessageBox.warning(self, "Missing Data", "Please fill all fields and select an image.")
            return

        self.accept()

    def get_data(self):
        return {
            "student_name": self.name_input.text().strip(),
            "prn": self.prn_input.text().strip(),
            "email": self.email_input.text().strip(),
            "image_path": self.image_path,
            "password": self.pass_input.text().strip(),
        }


class LoadingDialog(QDialog):
    def __init__(self, message="Processing..."):
        super().__init__()
        self.setWindowTitle("Please Wait")
        self.setModal(True)
        self.setFixedSize(300, 100)
        layout = QVBoxLayout(self)
        label = QLabel(message)
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        self.setWindowFlags(Qt.Dialog | Qt.CustomizeWindowHint | Qt.WindowTitleHint)


class AddClassWorker(QObject):
    finished = Signal(object)
    error = Signal(str)

    def __init__(self, college_id, classroom_name, cam_source, slots):
        super().__init__()
        self.college_id = college_id
        self.classroom_name = classroom_name
        self.cam_source = cam_source
        self.slots = slots

    def run(self):
        try:
            result = add_classroom(
                college_id=self.college_id,
                classroom_name=self.classroom_name,
                camera_input=self.cam_source,
                slots=self.slots
            )
            if result and "error" not in result:
                self.finished.emit(result)
            elif result and "error" in result:
                self.error.emit(result["error"])
            else:
                self.error.emit("Failed to add classroom")
        except Exception as e:
            self.error.emit(str(e))


class AddStudentWorker(QObject):
    finished = Signal(object)
    error = Signal(str)

    def __init__(self, class_name, student_name, image_path, student_prn, password, student_email, recognizer):
        super().__init__()
        self.class_name = class_name
        self.student_name = student_name
        self.image_path = image_path
        self.student_prn = student_prn
        self.password = password
        self.student_email = student_email
        self.recognizer = recognizer

    def run(self):
        try:
            result = add_student_to_classroom(
                self.class_name,
                self.student_name,
                self.image_path,
                self.student_prn,
                self.password,
                self.student_email
            )
            if result:
                try:
                    if self.recognizer:
                        self.recognizer.reload_known_faces()
                except Exception:
                    pass
                self.finished.emit(result)
            else:
                self.error.emit("Failed to add student (PRN may already exist)")
        except Exception as e:
            self.error.emit(str(e))
