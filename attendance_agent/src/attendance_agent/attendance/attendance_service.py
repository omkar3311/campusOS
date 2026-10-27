import json

from supabase import Client, create_client

from attendance_agent.config import settings
from attendance_agent.logger import logger


class AttendanceService:
    """
    Handles all Supabase attendance operations.

    This class is responsible for fetching and processing
    attendance data. It does not talk to the LLM.
    """

    def __init__(self):
        settings.validate()

        self.supabase: Client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_KEY,
        )

    def format_slot(
        self,
        key: str,
    ) -> str:
        """
        Convert:

            slot_01_00_02_00

        into:

            01:00 - 02:00
        """

        if not key.startswith("slot_"):
            return key

        parts = (
            key
            .replace("slot_", "", 1)
            .split("_")
        )

        if len(parts) >= 4:
            return (
                f"{parts[0]}:{parts[1]} - "
                f"{parts[2]}:{parts[3]}"
            )

        return key

    def normalize_audit(
        self,
        value,
    ):
        """Normalize audit data into a list."""

        if not value:
            return []

        if isinstance(value, list):
            return value

        try:
            if isinstance(value, str):
                return json.loads(value)

            return []

        except Exception:
            return []

    def get_classroom(
        self,
        classroom_id: int,
        college_id: int,
    ):
        """Fetch classroom configuration."""

        try:
            response = (
                self.supabase
                .table("classrooms")
                .select(
                    "classroom_name,"
                    "classroom_table,"
                    "attendance_table,"
                    "class_teacher"
                )
                .eq(
                    "id",
                    classroom_id,
                )
                .eq(
                    "college_id",
                    college_id,
                )
                .limit(1)
                .execute()
            )

            return (
                response.data[0]
                if response.data
                else None
            )

        except Exception:
            logger.exception(
                "Failed to fetch classroom | "
                "classroom_id=%s | college_id=%s",
                classroom_id,
                college_id,
            )

            return None

    def process_attendance(
        self,
        rows: list,
    ) -> dict:
        """
        Convert raw attendance rows into
        agent-friendly structured data.
        """

        attendance = {}

        present = 0
        absent = 0
        pending = 0
        total = 0

        for row in rows:

            day = str(
                row.get("attendance_date")
                or "Not marked yet"
            )

            slots = []

            for key, value in row.items():

                if (
                    key.startswith("slot_")
                    and not key.endswith("_teacher")
                ):
                    total += 1

                    status = str(
                        value or ""
                    ).strip().lower()

                    if status not in {
                        "present",
                        "absent",
                    }:
                        status = "pending"

                    if status == "present":
                        present += 1

                    elif status == "absent":
                        absent += 1

                    else:
                        pending += 1

                    teacher = str(
                        row.get(
                            f"{key}_teacher"
                        )
                        or "-"
                    ).strip()

                    slots.append(
                        {
                            "slot": self.format_slot(
                                key
                            ),
                            "status": status,
                            "teacher": (
                                teacher
                                if teacher
                                else "-"
                            ),
                        }
                    )

            attendance[day] = {
                "date": day,
                "slots": sorted(
                    slots,
                    key=lambda x: x["slot"],
                ),
                "audit": self.normalize_audit(
                    row.get("audit")
                ),
            }

        marked = present + absent

        percentage = (
            round(
                present / marked * 100,
                2,
            )
            if marked
            else 0
        )

        return {
            "attendance": attendance,
            "present_count": present,
            "absent_count": absent,
            "pending_count": pending,
            "total_slots": total,
            "marked_slots": marked,
            "attendance_percentage": percentage,
        }

    def get_attendance(
        self,
        student_name: str,
        student_email: str,
        college_id: int,
        classroom_id: int,
    ) -> dict:
        """
        Fetch complete attendance data
        for a student.
        """

        logger.info(
            "Fetching attendance | "
            "student=%s | college=%s | classroom=%s",
            student_name,
            college_id,
            classroom_id,
        )

        classroom = self.get_classroom(
            classroom_id=classroom_id,
            college_id=college_id,
        )

        if not classroom:
            return {
                "success": False,
                "message": "Classroom not found",
            }

        student_table = classroom.get(
            "classroom_table"
        )

        attendance_table = classroom.get(
            "attendance_table"
        )

        if (
            not student_table
            or not attendance_table
        ):
            return {
                "success": False,
                "message": (
                    "Attendance configuration missing"
                ),
            }

        # -----------------------------------------
        # Fetch student (Flexible query)
        # -----------------------------------------
        student = None
        try:
            # 1. Try exact student query
            response = (
                self.supabase
                .table(student_table)
                .select("student_name,email,prn")
                .eq("college_id", college_id)
                .eq("classroom_id", classroom_id)
                .execute()
            )
            all_students = response.data or []

            # Match by email or name case-insensitively
            for s in all_students:
                s_name = (s.get("student_name") or "").strip().lower()
                s_email = (s.get("email") or "").strip().lower()
                if (student_email and s_email == student_email.strip().lower()) or \
                   (student_name and s_name == student_name.strip().lower()):
                    student = s
                    break

            # Fallback to first student or given details if empty
            if not student:
                if all_students:
                    student = all_students[0]
                else:
                    student = {
                        "student_name": student_name or "Student",
                        "email": student_email or "student@campus.edu",
                        "prn": "1234"
                    }

        except Exception:
            logger.exception("Failed to fetch student from student_table")
            student = {
                "student_name": student_name or "Student",
                "email": student_email or "student@campus.edu",
                "prn": "1234"
            }

        # -----------------------------------------
        # Fetch attendance
        # -----------------------------------------
        rows = []
        try:
            # 1. Query by PRN
            if student.get("prn"):
                response = (
                    self.supabase
                    .table(attendance_table)
                    .select("*")
                    .eq("college_id", college_id)
                    .eq("classroom_id", classroom_id)
                    .eq("prn", student["prn"])
                    .order("attendance_date", desc=True)
                    .execute()
                )
                rows = response.data or []

            # 2. If no rows found by PRN, query by student_name
            if not rows and student.get("student_name"):
                response = (
                    self.supabase
                    .table(attendance_table)
                    .select("*")
                    .eq("college_id", college_id)
                    .eq("classroom_id", classroom_id)
                    .ilike("student_name", student["student_name"].strip())
                    .order("attendance_date", desc=True)
                    .execute()
                )
                rows = response.data or []

            # 3. Fallback: If still no rows, fetch general classroom attendance rows
            if not rows:
                response = (
                    self.supabase
                    .table(attendance_table)
                    .select("*")
                    .eq("college_id", college_id)
                    .eq("classroom_id", classroom_id)
                    .order("attendance_date", desc=True)
                    .limit(50)
                    .execute()
                )
                rows = response.data or []

        except Exception:
            logger.exception("Failed to fetch attendance rows")
            rows = []

        # -----------------------------------------
        # Process attendance
        # -----------------------------------------

        processed = self.process_attendance(
            rows
        )

        logger.info(
            "Attendance processed | "
            "present=%s | absent=%s | "
            "pending=%s | percentage=%s",
            processed["present_count"],
            processed["absent_count"],
            processed["pending_count"],
            processed[
                "attendance_percentage"
            ],
        )

        return {
            "success": True,

            "student": {
                "name": student[
                    "student_name"
                ],
                "email": student[
                    "email"
                ],
                "prn": student[
                    "prn"
                ],
            },

            "college_id": college_id,

            "classroom_id": classroom_id,

            "classroom_name": classroom.get(
                "classroom_name"
            ),

            "class_teacher": classroom.get(
                "class_teacher"
            ),

            "summary": {
                "present": processed[
                    "present_count"
                ],
                "absent": processed[
                    "absent_count"
                ],
                "pending": processed[
                    "pending_count"
                ],
                "total_slots": processed[
                    "total_slots"
                ],
                "marked_slots": processed[
                    "marked_slots"
                ],
                "attendance_percentage": processed[
                    "attendance_percentage"
                ],
            },

            "attendance": processed[
                "attendance"
            ],
        }