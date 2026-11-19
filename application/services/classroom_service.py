import os
import shutil
from psycopg2 import sql
from psycopg2.extras import Json
from core.config import LOCAL_IMAGE_ROOT, SUPABASE_BUCKET
from core.db import (
    get_db_cursor,
    get_pg_connection,
    release_pg_connection,
    get_cloud_pg_connection,
    supabase,
    is_supabase_available,
    make_payload_json_safe,
    normalize_slot_value,
    get_next_local_id,
    create_dynamic_student_table,
    create_dynamic_attendance_table
)
from core.sync import enqueue_sync
from services.auth_service import encrypt_password


def ensure_base_classrooms_table_local():
    with get_db_cursor(commit=True) as cur:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS public.classrooms (
            id INTEGER PRIMARY KEY,
            college_id INTEGER NOT NULL,
            classroom_name TEXT NOT NULL,
            classroom_table TEXT NOT NULL,
            classroom_faces TEXT NOT NULL,
            camera_input TEXT,
            slot JSONB,
            attendance_table TEXT NOT NULL
        );
        """)
        return True


def add_classroom(college_id, classroom_name, camera_input, slots):
    try:
        ensure_base_classrooms_table_local()
        clean_name = classroom_name.strip().lower()
        safe_name = clean_name.replace(" ", "_")
        classroom_table = f"{safe_name}_table"
        classroom_faces = f"{safe_name}_faces"
        attendance_table = f"{safe_name}_attendance"
        slot_value = normalize_slot_value(slots)

        with get_db_cursor(commit=False) as cur:
            cur.execute("""
                SELECT id
                FROM public.classrooms
                WHERE college_id = %s
                  AND classroom_name = %s
                LIMIT 1
            """, (college_id, clean_name))
            if cur.fetchone():
                return {"error": "Classroom already exists"}

        local_id = get_next_local_id("classrooms")
        if local_id is None:
            return None

        with get_db_cursor(commit=True) as cur:
            cur.execute("""
                INSERT INTO public.classrooms
                (id, college_id, classroom_name, classroom_table, classroom_faces, camera_input, slot, attendance_table)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                local_id,
                college_id,
                clean_name,
                classroom_table,
                classroom_faces,
                str(camera_input),
                Json(slot_value),
                attendance_table
            ))

        create_dynamic_student_table(classroom_table)
        create_dynamic_attendance_table(attendance_table, slot_value)

        created_row = {
            "id": local_id,
            "college_id": college_id,
            "classroom_name": clean_name,
            "classroom_table": classroom_table,
            "classroom_faces": classroom_faces,
            "camera_input": str(camera_input),
            "slot": slot_value,
            "attendance_table": attendance_table
        }

        payload = created_row.copy()
        if is_supabase_available() and supabase:
            try:
                supabase.table("classrooms").upsert(payload).execute()
            except Exception:
                enqueue_sync("classrooms", "insert", "classrooms", payload)
        else:
            enqueue_sync("classrooms", "insert", "classrooms", payload)

        return created_row
    except Exception:
        return None


def get_classroom_full_data_by_name_by_id(classroom_id):
    try:
        with get_db_cursor(commit=False) as cur:
            cur.execute("""
                SELECT id, college_id, classroom_name, classroom_table, classroom_faces, camera_input, slot, attendance_table
                FROM public.classrooms
                WHERE id = %s
                LIMIT 1
            """, (classroom_id,))
            row = cur.fetchone()
            if not row:
                return None
            return {
                "id": row[0],
                "college_id": row[1],
                "classroom_name": row[2],
                "classroom_table": row[3],
                "classroom_faces": row[4],
                "camera_input": row[5],
                "slot": row[6],
                "attendance_table": row[7]
            }
    except Exception:
        return None


def get_classroom_data_by_name(class_name):
    try:
        clean_name = class_name.strip().lower()
        with get_db_cursor(commit=False) as cur:
            cur.execute("""
                SELECT id, college_id, classroom_table, classroom_faces
                FROM public.classrooms
                WHERE classroom_name = %s
                LIMIT 1
            """, (clean_name,))
            row = cur.fetchone()
            if not row:
                return None
            return {
                "id": row[0],
                "college_id": row[1],
                "classroom_table": row[2],
                "classroom_faces": row[3]
            }
    except Exception:
        return None


def get_classroom_full_data_by_name(class_name):
    try:
        clean_name = class_name.strip().lower()
        with get_db_cursor(commit=False) as cur:
            cur.execute("""
                SELECT id, college_id, classroom_name, classroom_table, classroom_faces, camera_input, slot, attendance_table
                FROM public.classrooms
                WHERE classroom_name = %s
                LIMIT 1
            """, (clean_name,))
            row = cur.fetchone()
            if not row:
                return None
            return {
                "id": row[0],
                "college_id": row[1],
                "classroom_name": row[2],
                "classroom_table": row[3],
                "classroom_faces": row[4],
                "camera_input": row[5],
                "slot": row[6],
                "attendance_table": row[7]
            }
    except Exception:
        return None


def get_classrooms_by_college_id(college_id):
    try:
        with get_db_cursor(commit=False) as cur:
            cur.execute("""
                SELECT id, college_id, classroom_name, classroom_table, classroom_faces, camera_input, slot, attendance_table
                FROM public.classrooms
                WHERE college_id = %s
                ORDER BY id ASC
            """, (college_id,))
            rows = cur.fetchall()
            result = []
            for row in rows:
                result.append({
                    "id": row[0],
                    "college_id": row[1],
                    "classroom_name": row[2],
                    "classroom_table": row[3],
                    "classroom_faces": row[4],
                    "camera_input": row[5],
                    "slot": row[6],
                    "attendance_table": row[7]
                })
            return result
    except Exception:
        return []


def delete_classroom(classroom_id):
    try:
        data = get_classroom_full_data_by_name_by_id(classroom_id)
        if not data:
            return False, "Classroom not found"

        classroom_table = data["classroom_table"]
        attendance_table = data["attendance_table"]

        if is_supabase_available() and get_cloud_pg_connection():
            try:
                cloud_conn = get_cloud_pg_connection()
                if cloud_conn:
                    cloud_cur = cloud_conn.cursor()
                    cloud_cur.execute(sql.SQL("DROP TABLE IF EXISTS public.{} CASCADE").format(sql.Identifier(classroom_table)))
                    cloud_cur.execute(sql.SQL("DROP TABLE IF EXISTS public.{} CASCADE").format(sql.Identifier(attendance_table)))
                    cloud_cur.execute("DELETE FROM public.classrooms WHERE id = %s", (classroom_id,))
                    cloud_conn.commit()
                    cloud_cur.close()
                    cloud_conn.close()
            except Exception:
                pass

        with get_db_cursor(commit=True) as cur:
            cur.execute(sql.SQL("DROP TABLE IF EXISTS public.{} CASCADE").format(sql.Identifier(classroom_table)))
            cur.execute(sql.SQL("DROP TABLE IF EXISTS public.{} CASCADE").format(sql.Identifier(attendance_table)))
            cur.execute("DELETE FROM public.classrooms WHERE id = %s", (classroom_id,))

        return True, "Deleted successfully"
    except Exception as e:
        return False, str(e)


def update_classroom(classroom_id, classroom_name, camera_input, slots):
    try:
        clean_name = classroom_name.strip().lower()
        slot_value = normalize_slot_value(slots)

        with get_db_cursor(commit=True) as cur:
            cur.execute("""
                SELECT id, college_id, classroom_table, classroom_faces, attendance_table
                FROM public.classrooms
                WHERE id = %s
                LIMIT 1
            """, (classroom_id,))
            old_row = cur.fetchone()
            if not old_row:
                return None
            old_id, college_id, classroom_table, classroom_faces, attendance_table = old_row

            cur.execute("""
                UPDATE public.classrooms
                SET classroom_name = %s,
                    camera_input = %s,
                    slot = %s
                WHERE id = %s
            """, (clean_name, str(camera_input), Json(slot_value), classroom_id))

        create_dynamic_student_table(classroom_table)
        create_dynamic_attendance_table(attendance_table, slot_value)

        result = {
            "id": classroom_id,
            "college_id": college_id,
            "classroom_name": clean_name,
            "classroom_table": classroom_table,
            "classroom_faces": classroom_faces,
            "attendance_table": attendance_table,
            "camera_input": str(camera_input),
            "slot": slot_value
        }

        if is_supabase_available() and supabase:
            try:
                supabase.table("classrooms").upsert(result).execute()
            except Exception:
                enqueue_sync("classrooms", "update", "classrooms", result)
        else:
            enqueue_sync("classrooms", "update", "classrooms", result)

        return result
    except Exception:
        return None


def upload_student_image(folder_name, student_name, file_path):
    try:
        ext = os.path.splitext(file_path)[1].lower()
        if not ext:
            ext = ".jpg"
        safe_name = student_name.strip().lower().replace(" ", "_")
        file_name = f"{safe_name}{ext}"

        local_folder = os.path.join(LOCAL_IMAGE_ROOT, folder_name)
        os.makedirs(local_folder, exist_ok=True)
        local_path = os.path.join(local_folder, file_name)
        shutil.copyfile(file_path, local_path)

        if is_supabase_available() and supabase:
            try:
                content_type = "image/png" if ext == ".png" else "image/jpeg"
                storage_path = f"{folder_name}/{file_name}"
                with open(local_path, "rb") as f:
                    file_bytes = f.read()
                try:
                    supabase.storage.from_(SUPABASE_BUCKET).upload(
                        path=storage_path,
                        file=file_bytes,
                        file_options={"content-type": content_type, "upsert": "true"}
                    )
                except Exception:
                    pass
                public_url = supabase.storage.from_(SUPABASE_BUCKET).get_public_url(storage_path)
                if public_url:
                    return public_url, file_name
            except Exception:
                pass

        enqueue_sync("storage_upload", "upload_file", folder_name, {
            "folder_name": folder_name,
            "file_name": file_name,
            "local_path": local_path
        })
        return local_path, file_name
    except Exception:
        return None, None


def insert_student_into_dynamic_table(table_name, college_id, classroom_id, student_name, img_url, student_prn, password, email):
    try:
        with get_db_cursor(commit=True) as cur:
            cur.execute(
                sql.SQL("SELECT id FROM public.{} WHERE prn = %s LIMIT 1").format(
                    sql.Identifier(table_name)
                ),
                (student_prn,)
            )
            if cur.fetchone():
                return None

            cur.execute(
                sql.SQL("""
                    INSERT INTO public.{}
                    (college_id, classroom_id, student_name, img_url, prn, password, email)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, college_id, classroom_id, student_name, img_url, prn, password, email
                """).format(sql.Identifier(table_name)),
                (college_id, classroom_id, student_name, img_url, student_prn, password, email)
            )
            row = cur.fetchone()

        result = {
            "id": row[0],
            "college_id": row[1],
            "classroom_id": row[2],
            "student_name": row[3],
            "img_url": row[4],
            "prn": row[5],
            "password": row[6],
            "email": row[7]
        }

        payload = make_payload_json_safe(result.copy())
        if is_supabase_available() and supabase:
            try:
                supabase.table(table_name).insert(payload).execute()
            except Exception:
                enqueue_sync("dynamic_table", "insert", table_name, payload)
        else:
            enqueue_sync("dynamic_table", "insert", table_name, payload)

        return result
    except Exception:
        return None


def add_student_to_classroom(class_name, student_name, file_path, student_prn, password, email):
    try:
        classroom_data = get_classroom_data_by_name(class_name)
        if not classroom_data:
            return None

        classroom_id = classroom_data["id"]
        college_id = classroom_data["college_id"]
        classroom_table = classroom_data["classroom_table"]
        classroom_faces = classroom_data["classroom_faces"]

        create_dynamic_student_table(classroom_table)
        img_url, _ = upload_student_image(classroom_faces, student_name, file_path)
        if not img_url:
            return None

        hashed_pwd = encrypt_password(password)
        inserted = insert_student_into_dynamic_table(
            classroom_table,
            college_id,
            classroom_id,
            student_name,
            img_url,
            student_prn,
            hashed_pwd,
            email
        )
        return inserted
    except Exception:
        return None
