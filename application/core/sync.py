import os
import json
import requests
from psycopg2 import sql
from psycopg2.extras import Json
from core.config import LOCAL_IMAGE_ROOT, SUPABASE_BUCKET
from core.db import (
    get_db_cursor,
    get_pg_connection,
    release_pg_connection,
    supabase,
    is_supabase_available,
    make_payload_json_safe,
    normalize_slot_value,
    create_dynamic_student_table_in_connection,
    create_dynamic_attendance_table_in_connection,
    init_local_database
)


def enqueue_sync(entity_type, operation, target_name, payload):
    try:
        safe_payload = make_payload_json_safe(payload)
        with get_db_cursor(commit=True) as cur:
            cur.execute("""
                INSERT INTO public.sync_queue (entity_type, operation, target_name, payload, status)
                VALUES (%s, %s, %s, %s, 'pending')
            """, (
                entity_type,
                operation,
                target_name,
                json.dumps(safe_payload, default=str)
            ))
        return True
    except Exception:
        return False


def get_pending_sync_jobs(limit=100):
    try:
        with get_db_cursor(commit=False) as cur:
            cur.execute("""
                SELECT id, entity_type, operation, target_name, payload
                FROM public.sync_queue
                WHERE status IN ('pending', 'failed')
                ORDER BY id ASC
                LIMIT %s
            """, (limit,))
            return cur.fetchall()
    except Exception:
        return []


def mark_sync_done(sync_id):
    try:
        with get_db_cursor(commit=True) as cur:
            cur.execute("""
                UPDATE public.sync_queue
                SET status = 'done',
                    updated_at = NOW()
                WHERE id = %s
            """, (sync_id,))
        return True
    except Exception:
        return False


def mark_sync_failed(sync_id, error_message):
    try:
        with get_db_cursor(commit=True) as cur:
            cur.execute("""
                UPDATE public.sync_queue
                SET status = 'failed',
                    retry_count = retry_count + 1,
                    error_message = %s,
                    updated_at = NOW()
                WHERE id = %s
            """, (str(error_message), sync_id))
        return True
    except Exception:
        return False


def get_sync_status():
    try:
        with get_db_cursor(commit=False) as cur:
            cur.execute("""
                SELECT COUNT(*) 
                FROM public.sync_queue 
                WHERE status IN ('pending', 'failed')
            """)
            count = cur.fetchone()[0]
            return count
    except Exception:
        return -1


def sync_cloud_images_to_local():
    if not is_supabase_available() or not supabase:
        return False
    try:
        classrooms = supabase.table("classrooms").select("*").execute().data or []
        for classroom in classrooms:
            folder_name = classroom.get("classroom_faces")
            if not folder_name:
                continue
            local_folder = os.path.join(LOCAL_IMAGE_ROOT, folder_name)
            os.makedirs(local_folder, exist_ok=True)
            try:
                files = supabase.storage.from_(SUPABASE_BUCKET).list(folder_name) or []
                for file in files:
                    file_name = file.get("name")
                    if not file_name or file_name.startswith("."):
                        continue
                    local_path = os.path.join(local_folder, file_name)
                    if os.path.exists(local_path):
                        continue
                    storage_path = f"{folder_name}/{file_name}"
                    data = supabase.storage.from_(SUPABASE_BUCKET).download(storage_path)
                    with open(local_path, "wb") as f:
                        f.write(data)
            except Exception:
                continue

        teachers = supabase.table("teachers").select("*").execute().data or []
        teacher_folder = os.path.join(LOCAL_IMAGE_ROOT, "teachers_faces")
        os.makedirs(teacher_folder, exist_ok=True)

        for teacher in teachers:
            img_url = teacher.get("img_url")
            teacher_name = teacher.get("teacher_name")
            if not img_url or not teacher_name:
                continue
            file_name = teacher_name.strip().lower().replace(" ", "_") + ".jpg"
            local_path = os.path.join(teacher_folder, file_name)
            if os.path.exists(local_path):
                continue
            try:
                resp = requests.get(img_url, timeout=5)
                if resp.status_code == 200:
                    with open(local_path, "wb") as f:
                        f.write(resp.content)
            except Exception:
                continue
        return True
    except Exception:
        return False


def pull_cloud_base_to_local():
    if not is_supabase_available() or not supabase:
        return False
    conn = get_pg_connection()
    try:
        colleges = supabase.table("colleges").select("*").execute().data or []
        classrooms = supabase.table("classrooms").select("*").execute().data or []
        teachers = supabase.table("teachers").select("*").execute().data or []

        with conn.cursor() as cur:
            for row in colleges:
                cur.execute("""
                    INSERT INTO public.colleges (id, college_name, creator, creator_email, password)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (id)
                    DO UPDATE SET
                        college_name = EXCLUDED.college_name,
                        creator = EXCLUDED.creator,
                        creator_email = EXCLUDED.creator_email,
                        password = EXCLUDED.password
                """, (
                    row["id"],
                    row.get("college_name"),
                    row.get("creator"),
                    row.get("creator_email"),
                    row.get("password")
                ))

            for row in classrooms:
                slot_value = normalize_slot_value(row.get("slot"))
                cur.execute("""
                    INSERT INTO public.classrooms
                    (id, college_id, classroom_name, classroom_table, classroom_faces, camera_input, slot, attendance_table)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id)
                    DO UPDATE SET
                        college_id = EXCLUDED.college_id,
                        classroom_name = EXCLUDED.classroom_name,
                        classroom_table = EXCLUDED.classroom_table,
                        classroom_faces = EXCLUDED.classroom_faces,
                        camera_input = EXCLUDED.camera_input,
                        slot = EXCLUDED.slot,
                        attendance_table = EXCLUDED.attendance_table
                """, (
                    row["id"],
                    row.get("college_id"),
                    row.get("classroom_name"),
                    row.get("classroom_table"),
                    row.get("classroom_faces"),
                    row.get("camera_input"),
                    Json(slot_value),
                    row.get("attendance_table")
                ))

            for row in teachers:
                cur.execute("""
                    INSERT INTO public.teachers
                    (id, college_id, teacher_name, email, role, password, img_url)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id)
                    DO UPDATE SET
                        college_id = EXCLUDED.college_id,
                        teacher_name = EXCLUDED.teacher_name,
                        email = EXCLUDED.email,
                        role = EXCLUDED.role,
                        password = EXCLUDED.password,
                        img_url = EXCLUDED.img_url
                """, (
                    row["id"],
                    row.get("college_id"),
                    row.get("teacher_name"),
                    row.get("email"),
                    row.get("role"),
                    row.get("password"),
                    row.get("img_url")
                ))
            conn.commit()

        for row in classrooms:
            classroom_table = row.get("classroom_table")
            attendance_table = row.get("attendance_table")
            slots = row.get("slot")
            if classroom_table:
                create_dynamic_student_table_in_connection(conn, classroom_table)
            if attendance_table:
                create_dynamic_attendance_table_in_connection(conn, attendance_table, slots)

        return True
    except Exception:
        conn.rollback()
        return False
    finally:
        release_pg_connection(conn)


def sync_attendance_date_to_cloud(attendance_table, attendance_date):
    if not is_supabase_available() or not supabase:
        return False
    try:
        with get_db_cursor(commit=False) as cur:
            cur.execute(
                sql.SQL("SELECT * FROM public.{} WHERE attendance_date = %s").format(
                    sql.Identifier(attendance_table)
                ),
                (attendance_date,)
            )
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description]

        for row in rows:
            payload = dict(zip(columns, row))
            safe_payload = make_payload_json_safe(payload)
            supabase.table(attendance_table).upsert(safe_payload).execute()

        sync_cloud_images_to_local()
        return True
    except Exception:
        return False


def process_sync_queue():
    if not is_supabase_available() or not supabase:
        return False
    jobs = get_pending_sync_jobs(200)
    if not jobs:
        return True

    for job in jobs:
        sync_id, entity_type, operation, target_name, payload_text = job
        try:
            payload = json.loads(payload_text) if payload_text else {}
            if entity_type == "classrooms" and operation == "insert":
                existing = (
                    supabase.table("classrooms")
                    .select("id")
                    .eq("college_id", payload["college_id"])
                    .eq("classroom_name", payload["classroom_name"])
                    .limit(1)
                    .execute()
                )
                if existing.data:
                    supabase.table("classrooms").update(payload).eq("id", existing.data[0]["id"]).execute()
                else:
                    supabase.table("classrooms").insert(payload).execute()

            elif entity_type == "classrooms" and operation == "update":
                cloud_id = payload.get("id")
                update_payload = payload.copy()
                update_payload.pop("id", None)
                if cloud_id:
                    supabase.table("classrooms").update(update_payload).eq("id", cloud_id).execute()
                else:
                    existing = (
                        supabase.table("classrooms")
                        .select("id")
                        .eq("college_id", payload["college_id"])
                        .eq("classroom_name", payload["classroom_name"])
                        .limit(1)
                        .execute()
                    )
                    if existing.data:
                        supabase.table("classrooms").update(update_payload).eq("id", existing.data[0]["id"]).execute()
                    else:
                        supabase.table("classrooms").insert(update_payload).execute()

            elif entity_type == "dynamic_table" and operation == "insert":
                supabase.table(target_name).insert(payload).execute()

            elif entity_type == "dynamic_table" and operation == "upsert":
                supabase.table(target_name).upsert(payload).execute()

            elif entity_type == "storage_upload" and operation == "upload_file":
                folder_name = payload["folder_name"]
                local_path = payload["local_path"]
                file_name = payload["file_name"]
                ext = os.path.splitext(local_path)[1].lower()
                content_type = "image/png" if ext == ".png" else "image/jpeg"
                storage_path = f"{folder_name}/{file_name}"
                with open(local_path, "rb") as f:
                    file_bytes = f.read()
                supabase.storage.from_(SUPABASE_BUCKET).upload(
                    path=storage_path,
                    file=file_bytes,
                    file_options={"content-type": content_type, "upsert": "true"}
                )

            elif entity_type == "attendance_sync" and operation == "sync_date":
                ok = sync_attendance_date_to_cloud(target_name, payload["attendance_date"])
                if not ok:
                    raise Exception("Attendance sync failed")

            mark_sync_done(sync_id)
        except Exception as e:
            mark_sync_failed(sync_id, str(e))
    return True


def startup_sync():
    try:
        init_local_database()
        pull_cloud_base_to_local()
        sync_cloud_images_to_local()
        process_sync_queue()
        return True
    except Exception:
        return False
