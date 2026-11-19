import os
from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QHBoxLayout,
    QVBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QFileDialog,
    QMessageBox,
    QApplication
)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt, QThread, Signal
from core.db import load_qss_file
from services.classroom_service import (
    get_classroom_full_data_by_name,
    update_classroom,
    delete_classroom
)
from services.attendance_service import export_attendance_to_csv
from ui.dialogs import EditClassroomDialog, AddStudentDialog, AddStudentWorker


class Student(QWidget):
    classroom_deleted = Signal()

    def __init__(self, camera_source, class_name, recognizer):
        super().__init__()
        load_qss_file(self, "student_dashboard.qss")
        self.camera_source = camera_source
        self.class_name = class_name
        self.recognizer = recognizer

        self.setWindowTitle(f"Classroom: {class_name}")
        self.resize(1050, 600)

        outer_layout = QVBoxLayout(self)

        self.navbar_title = QLabel("AttendMate Student Management")
        self.navbar_title.setObjectName("navbarTitle")
        self.navbar_title.setAlignment(Qt.AlignCenter)
        outer_layout.addWidget(self.navbar_title)

        main_layout = QHBoxLayout()
        left_layout = QVBoxLayout()

        self.camera_label = QLabel("Camera Feed")
        self.camera_label.setAlignment(Qt.AlignCenter)
        self.camera_label.setFixedSize(520, 360)
        self.camera_label.setStyleSheet("""
            QLabel {
                border: 2px solid #444;
                border-radius: 10px;
                background-color: #111;
                color: #bbb;
                font-size: 16px;
            }
        """)
        left_layout.addWidget(self.camera_label, alignment=Qt.AlignCenter)

        self.edit_classroom_btn = QPushButton("Edit Classroom")
        self.edit_classroom_btn.setFixedHeight(38)
        self.edit_classroom_btn.clicked.connect(self.open_edit_classroom_dialog)
        left_layout.addWidget(self.edit_classroom_btn)

        self.add_student_btn = QPushButton("Add New Student")
        self.add_student_btn.setFixedHeight(38)
        self.add_student_btn.clicked.connect(self.open_add_student_dialog)
        left_layout.addWidget(self.add_student_btn)

        self.export_btn = QPushButton("Export Attendance (CSV)")
        self.export_btn.setFixedHeight(38)
        self.export_btn.clicked.connect(self.export_attendance)
        left_layout.addWidget(self.export_btn)

        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(self.status_label)
        left_layout.addStretch()

        self.delete_classroom_btn = QPushButton("Delete Classroom")
        self.delete_classroom_btn.setFixedHeight(38)
        self.delete_classroom_btn.clicked.connect(self.handle_delete_classroom)
        left_layout.addWidget(self.delete_classroom_btn)

        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Track ID", "Identified Person"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #444;
                border-radius: 8px;
                gridline-color: #555;
                font-size: 14px;
            }
        """)

        main_layout.addLayout(left_layout, 2)
        main_layout.addWidget(self.table, 1)
        outer_layout.addLayout(main_layout)

        self.footer = QLabel("© 2026 AttendMate")
        self.footer.setObjectName("footer")
        self.footer.setAlignment(Qt.AlignCenter)
        outer_layout.addWidget(self.footer)

        self.present_students = {}
        self.unknown_tracks = {}
        self.add_student_thread = None
        self.add_student_worker = None

    def export_attendance(self):
        default_name = f"{self.class_name}_attendance_export.csv"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Attendance CSV",
            os.path.join(os.path.expanduser("~"), default_name),
            "CSV Files (*.csv)"
        )
        if not file_path:
            return
        ok, msg = export_attendance_to_csv(self.class_name, file_path)
        if ok:
            QMessageBox.information(self, "Export Successful", f"Saved to:\n{file_path}")
        else:
            QMessageBox.critical(self, "Export Failed", msg)

    def handle_delete_classroom(self):
        classroom_data = get_classroom_full_data_by_name(self.class_name)
        if not classroom_data:
            QMessageBox.critical(self, "Error", "Classroom not found")
            return

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            "Are you sure you want to delete this classroom?\nAll local and cloud records will be removed.",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        self.status_label.setText("Deleting classroom...")
        self.delete_classroom_btn.setEnabled(False)
        QApplication.processEvents()

        success, message = delete_classroom(classroom_data["id"])
        if success:
            QMessageBox.information(self, "Success", "Classroom deleted successfully")
            self.classroom_deleted.emit()
            self.close()
        else:
            QMessageBox.critical(self, "Error", message)
            self.delete_classroom_btn.setEnabled(True)
            self.status_label.setText("")

    def open_edit_classroom_dialog(self):
        classroom_data = get_classroom_full_data_by_name(self.class_name)
        if not classroom_data:
            QMessageBox.critical(self, "Error", "Failed to fetch classroom data")
            return

        dialog = EditClassroomDialog(classroom_data)
        if dialog.exec():
            data = dialog.get_data()
            result = update_classroom(
                classroom_data["id"],
                data["classroom_name"],
                data["camera_input"],
                data["slot"]
            )
            if result:
                self.class_name = data["classroom_name"]
                self.setWindowTitle(f"Classroom: {self.class_name}")
                QMessageBox.information(self, "Success", "Classroom updated successfully")
            else:
                QMessageBox.critical(self, "Error", "Failed to update classroom")

    def open_add_student_dialog(self):
        dialog = AddStudentDialog()
        if not dialog.exec():
            return
        data = dialog.get_data()
        self.add_student_btn.setEnabled(False)
        self.add_student_btn.setText("Adding...")
        self.status_label.setText("Saving student image and record...")

        self.add_student_thread = QThread()
        self.add_student_worker = AddStudentWorker(
            self.class_name,
            data["student_name"],
            data["image_path"],
            data["prn"],
            data["password"],
            data["email"],
            self.recognizer
        )
        self.add_student_worker.moveToThread(self.add_student_thread)
        self.add_student_thread.started.connect(self.add_student_worker.run)
        self.add_student_worker.finished.connect(self.on_add_student_success)
        self.add_student_worker.error.connect(self.on_add_student_error)

        self.add_student_worker.finished.connect(self.add_student_thread.quit)
        self.add_student_worker.error.connect(self.add_student_thread.quit)
        self.add_student_worker.finished.connect(self.add_student_worker.deleteLater)
        self.add_student_worker.error.connect(self.add_student_worker.deleteLater)
        self.add_student_thread.finished.connect(self.add_student_thread.deleteLater)
        self.add_student_thread.start()

    def on_add_student_success(self, result):
        self.add_student_btn.setEnabled(True)
        self.add_student_btn.setText("Add New Student")
        self.status_label.setText("")
        QMessageBox.information(self, "Success", "Student added successfully")

    def on_add_student_error(self, message):
        self.add_student_btn.setEnabled(True)
        self.add_student_btn.setText("Add New Student")
        self.status_label.setText("")
        QMessageBox.critical(self, "Error", message)

    def update_frame_qimg(self, qimg):
        pixmap = QPixmap.fromImage(qimg).scaled(
            self.camera_label.width(),
            self.camera_label.height(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.camera_label.setPixmap(pixmap)

    def update_table(self, people):
        current_unknown = set()
        for item in people:
            track_id = item[0]
            name = item[1]
            if name:
                self.present_students[name] = track_id
                if track_id in self.unknown_tracks:
                    del self.unknown_tracks[track_id]
            else:
                self.unknown_tracks[track_id] = True
                current_unknown.add(track_id)

        for track_id in list(self.unknown_tracks.keys()):
            if track_id not in current_unknown:
                del self.unknown_tracks[track_id]

        rows = []
        for name, track_id in self.present_students.items():
            rows.append((track_id, name))
        for track_id in self.unknown_tracks.keys():
            rows.append((track_id, "Unknown (Detecting...)"))

        self.table.setRowCount(len(rows))
        for row, (track_id, name) in enumerate(rows):
            self.table.setItem(row, 0, QTableWidgetItem(str(track_id)))
            self.table.setItem(row, 1, QTableWidgetItem(str(name)))
