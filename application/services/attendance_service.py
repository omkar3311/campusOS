import csv
from datetime import date
from psycopg2 import sql
from core.db import (
    get_db_cursor,
    create_dynamic_attendance_table,
    make_slot_column_name,
    get_current_active_slot,
    is_supabase_available
)
from core.sync import sync_attendance_date_to_cloud, enqueue_sync
from services.classroom_service import get_classroom_full_data_by_name


def fill_absent_previous_days(class_name):
    try:
        classroom_data = get_classroom_full_data_by_name(class_name)
        if not classroom_data:
            return False

        attendance_table = classroom_data["attendance_table"]
        slots = classroom_data.get("slot", [])
        if not slots:
            return False

        today = date.today()
        slot_columns = [make_slot_column_name(s["start"], s["end"]) for s in slots if "start" in s and "end" in s]
        updated_dates = set()

        with get_db_cursor(commit=True) as cur:
            for col in slot_columns:
                cur.execute(
                    sql.SQL("""
                        UPDATE public.{}
                        SET {} = 'absent'
                        WHERE attendance_date < %s
                          AND {} IS NULL
                        RETURNING attendance_date
                    """).format(
                        sql.Identifier(attendance_table),
                        sql.Identifier(col),
                        sql.Identifier(col)
                    ),
                    (today,)
                )
                rows = cur.fetchall()
                for r in rows:
                    updated_dates.add(str(r[0]))

        for d in updated_dates:
            if is_supabase_available():
                try:
                    sync_attendance_date_to_cloud(attendance_table, d)
                except Exception:
                    enqueue_sync("attendance_sync", "sync_date", attendance_table, {"attendance_date": d})
            else:
                enqueue_sync("attendance_sync", "sync_date", attendance_table, {"attendance_date": d})

        return True
    except Exception:
        return False


def mark_attendance_for_slot(class_name, recognized_students, recognized_teachers):
    try:
        classroom_data = get_classroom_full_data_by_name(class_name)
        if not classroom_data:
            return False

        classroom_table = classroom_data["classroom_table"]
        attendance_table = classroom_data["attendance_table"]
        classroom_id = classroom_data["id"]
        college_id = classroom_data["college_id"]
        slots = classroom_data.get("slot", [])

        create_dynamic_attendance_table(attendance_table, slots)
        _, slot_column = get_current_active_slot(slots)
        if not slot_column:
            return False

        teacher_column = f"{slot_column}_teacher"
        teacher_name = list(recognized_teachers)[0] if recognized_teachers else None
        today = date.today()

        with get_db_cursor(commit=True) as cur:
            cur.execute(
                sql.SQL("SELECT student_name, prn FROM public.{}").format(
                    sql.Identifier(classroom_table)
                )
            )
            students = cur.fetchall()
            if not students:
                return False

            name_to_prn = {
                str(s_name).strip().lower(): str(prn).strip().lower()
                for s_name, prn in students
            }
            recognized_prns = {
                name_to_prn.get(str(x).strip().lower())
                for x in recognized_students
                if name_to_prn.get(str(x).strip().lower())
            }

            for student_name, prn_raw in students:
                prn = str(prn_raw).strip().lower()
                is_recognized = prn in recognized_prns

                cur.execute(
                    sql.SQL("""
                        SELECT {}, {}
                        FROM public.{}
                        WHERE prn = %s AND attendance_date = %s
                    """).format(
                        sql.Identifier(slot_column),
                        sql.Identifier(teacher_column),
                        sql.Identifier(attendance_table)
                    ),
                    (prn, today)
                )
                result = cur.fetchone()
                if result:
                    current_status = result[0]
                    if current_status != "present" and is_recognized:
                        cur.execute(
                            sql.SQL("""
                                UPDATE public.{}
                                SET {} = %s,
                                    {} = %s
                                WHERE prn = %s AND attendance_date = %s
                            """).format(
                                sql.Identifier(attendance_table),
                                sql.Identifier(slot_column),
                                sql.Identifier(teacher_column)
                            ),
                            ("present", teacher_name, prn, today)
                        )
                else:
                    status = "present" if is_recognized else "absent"
                    cur.execute(
                        sql.SQL("""
                            INSERT INTO public.{}
                            (college_id, classroom_id, student_name, prn, attendance_date, {}, {})
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """).format(
                            sql.Identifier(attendance_table),
                            sql.Identifier(slot_column),
                            sql.Identifier(teacher_column)
                        ),
                        (college_id, classroom_id, student_name, prn, today, status, teacher_name)
                    )

        return True
    except Exception:
        return False


def get_attendance_by_date(class_name, attendance_date=None):
    try:
        classroom_data = get_classroom_full_data_by_name(class_name)
        if not classroom_data:
            return []
        attendance_table = classroom_data["attendance_table"]
        if attendance_date is None:
            attendance_date = str(date.today())

        with get_db_cursor(commit=False) as cur:
            cur.execute(
                sql.SQL("SELECT * FROM public.{} WHERE attendance_date = %s ORDER BY id ASC").format(
                    sql.Identifier(attendance_table)
                ),
                (attendance_date,)
            )
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description]
            result = []
            for row in rows:
                result.append(dict(zip(columns, row)))
            return result
    except Exception:
        return []


def export_attendance_to_csv(class_name, file_path):
    try:
        classroom_data = get_classroom_full_data_by_name(class_name)
        if not classroom_data:
            return False, "Classroom not found"
        attendance_table = classroom_data["attendance_table"]

        with get_db_cursor(commit=False) as cur:
            cur.execute(
                sql.SQL("SELECT * FROM public.{} ORDER BY attendance_date DESC, prn ASC").format(
                    sql.Identifier(attendance_table)
                )
            )
            rows = cur.fetchall()
            if not rows:
                return False, "No attendance records found"
            columns = [desc[0] for desc in cur.description]

        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(columns)
            for row in rows:
                writer.writerow(row)

        return True, "Export successful"
    except Exception as e:
        return False, str(e)
