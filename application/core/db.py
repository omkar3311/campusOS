import os
import json
import socket
import psycopg2
from psycopg2 import pool, sql
from contextlib import contextmanager
from datetime import datetime, date
from typing import Optional
from supabase import create_client, Client
from core.config import (
    LOCAL_DB_HOST,
    LOCAL_DB_NAME,
    LOCAL_DB_USER,
    LOCAL_DB_PASSWORD,
    LOCAL_DB_PORT,
    DB_HOST,
    DB_NAME,
    DB_USER,
    DB_PASSWORD,
    DB_PORT,
    SUPABASE_URL,
    SUPABASE_KEY,
    LOCAL_IMAGE_ROOT,
    STYLES_DIR
)

supabase: Optional[Client] = None
if create_client and SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception:
        supabase = None

_local_pool: Optional[pool.ThreadedConnectionPool] = None


def get_local_pool():
    global _local_pool
    if _local_pool is None or _local_pool.closed:
        _local_pool = pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=25,
            host=LOCAL_DB_HOST,
            dbname=LOCAL_DB_NAME,
            user=LOCAL_DB_USER,
            password=LOCAL_DB_PASSWORD,
            port=LOCAL_DB_PORT
        )
    return _local_pool


def get_pg_connection():
    try:
        p = get_local_pool()
        return p.getconn()
    except Exception:
        return psycopg2.connect(
            host=LOCAL_DB_HOST,
            dbname=LOCAL_DB_NAME,
            user=LOCAL_DB_USER,
            password=LOCAL_DB_PASSWORD,
            port=LOCAL_DB_PORT
        )


def release_pg_connection(conn):
    if conn is None:
        return
    try:
        p = get_local_pool()
        p.putconn(conn)
    except Exception:
        try:
            conn.close()
        except Exception:
            pass


@contextmanager
def get_db_cursor(commit=True):
    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        yield cur
        if commit:
            conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        try:
            cur.close()
        except Exception:
            pass
        release_pg_connection(conn)


def get_cloud_pg_connection():
    if not DB_HOST or not DB_NAME or not DB_USER or not DB_PASSWORD:
        return None
    try:
        return psycopg2.connect(
            host=DB_HOST,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT,
            connect_timeout=5
        )
    except Exception:
        return None


def is_internet_available(host="8.8.8.8", port=53, timeout=2):
    try:
        socket.setdefaulttimeout(timeout)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, port))
        s.close()
        return True
    except Exception:
        return False


def is_supabase_available():
    if not is_internet_available():
        return False
    if not supabase:
        return False
    try:
        res = supabase.table("colleges").select("id").limit(1).execute()
        return res is not None
    except Exception:
        return False


def is_cloud_pg_available():
    if not is_internet_available():
        return False
    conn = get_cloud_pg_connection()
    if conn is None:
        return False
    try:
        cur = conn.cursor()
        cur.execute("SELECT 1;")
        cur.fetchone()
        cur.close()
        conn.close()
        return True
    except Exception:
        return False


def load_qss_file(widget, qss_file):
    target_path = qss_file
    if not os.path.isabs(target_path):
        target_path = os.path.join(STYLES_DIR, qss_file)
    if not os.path.exists(target_path):
        parent_style = os.path.join(os.path.dirname(STYLES_DIR), "..", qss_file)
        if os.path.exists(parent_style):
            target_path = parent_style
    if os.path.exists(target_path):
        with open(target_path, "r", encoding="utf-8") as f:
            widget.setStyleSheet(f.read())


def parse_slot_data(slot_value):
    if slot_value is None:
        return []
    if isinstance(slot_value, list):
        return slot_value
    if isinstance(slot_value, str):
        try:
            val = json.loads(slot_value)
            return val if isinstance(val, list) else []
        except Exception:
            return []
    return []


def normalize_slot_value(slot_value):
    return parse_slot_data(slot_value)


def make_json_safe(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8")
        except Exception:
            return value.hex()
    if isinstance(value, set):
        return list(value)
    return value


def make_payload_json_safe(payload):
    if not isinstance(payload, dict):
        return payload
    safe = {}
    for k, v in payload.items():
        if isinstance(v, dict):
            safe[k] = make_payload_json_safe(v)
        elif isinstance(v, list):
            safe[k] = [make_json_safe(x) for x in v]
        else:
            safe[k] = make_json_safe(v)
    return safe


def make_slot_column_name(start_time: str, end_time: str) -> str:
    safe_start = str(start_time).strip().replace(":", "_")
    safe_end = str(end_time).strip().replace(":", "_")
    return f"slot_{safe_start}_{safe_end}"


def get_current_active_slot(slots):
    parsed = parse_slot_data(slots)
    if not parsed:
        return None, None
    now = datetime.now().time()
    for s in parsed:
        try:
            start_t = datetime.strptime(s["start"], "%H:%M").time()
            end_t = datetime.strptime(s["end"], "%H:%M").time()
            if start_t <= now <= end_t:
                col = make_slot_column_name(s["start"], s["end"])
                return s, col
        except Exception:
            continue
    return None, None


def table_exists_in_connection(conn, table_name):
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name = %s
            );
        """, (table_name,))
        row = cur.fetchone()
        return bool(row[0]) if row else False
    finally:
        cur.close()


def set_camera_status(classroom_name, camera_input, is_open):
    with get_db_cursor(commit=True) as cur:
        cur.execute("""
            INSERT INTO public.camera_status (classroom_name, camera_input, is_open)
            VALUES (%s, %s, %s)
            ON CONFLICT (classroom_name)
            DO UPDATE SET
                camera_input = EXCLUDED.camera_input,
                is_open = EXCLUDED.is_open;
        """, (classroom_name, str(camera_input), bool(is_open)))
        return True


def get_camera_status(classroom_name):
    try:
        with get_db_cursor(commit=False) as cur:
            cur.execute("""
                SELECT is_open 
                FROM public.camera_status
                WHERE classroom_name = %s
                LIMIT 1;
            """, (classroom_name,))
            row = cur.fetchone()
            if row is not None:
                return bool(row[0])
            return True
    except Exception:
        return True


def init_local_database():
    os.makedirs(LOCAL_IMAGE_ROOT, exist_ok=True)
    with get_db_cursor(commit=True) as cur:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS public.colleges (
            id INTEGER PRIMARY KEY,
            college_name TEXT NOT NULL,
            creator TEXT,
            creator_email TEXT,
            password TEXT
        );
        """)
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
        cur.execute("""
        CREATE TABLE IF NOT EXISTS public.local_id_counters (
            table_name TEXT PRIMARY KEY,
            last_id INTEGER NOT NULL DEFAULT 0
        );
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS public.sync_queue (
            id SERIAL PRIMARY KEY,
            entity_type TEXT NOT NULL,
            operation TEXT NOT NULL,
            target_name TEXT NOT NULL,
            payload TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            retry_count INTEGER NOT NULL DEFAULT 0,
            error_message TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );
        """)
        cur.execute("""
        CREATE INDEX IF NOT EXISTS sync_queue_status_idx
        ON public.sync_queue(status);
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS public.camera_status (
            id SERIAL PRIMARY KEY,
            classroom_name TEXT UNIQUE,
            camera_input TEXT,
            is_open BOOLEAN DEFAULT TRUE
        );
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS public.teachers (
            id INTEGER PRIMARY KEY,
            college_id INTEGER NOT NULL,
            teacher_name TEXT NOT NULL,
            email TEXT,
            role TEXT,
            password TEXT,
            img_url TEXT
        );
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS public.login (
            id INTEGER PRIMARY KEY,
            college_name TEXT NOT NULL,
            creator TEXT,
            creator_email TEXT,
            password TEXT,
            is_login BOOLEAN DEFAULT FALSE
        );
        """)
    return True


def get_next_local_id(table_name):
    with get_db_cursor(commit=True) as cur:
        cur.execute("""
            INSERT INTO public.local_id_counters (table_name, last_id)
            VALUES (%s, 1)
            ON CONFLICT (table_name)
            DO UPDATE SET last_id = public.local_id_counters.last_id + 1
            RETURNING last_id;
        """, (table_name,))
        row = cur.fetchone()
        return row[0]


def create_dynamic_student_table_in_connection(conn, table_name):
    cur = conn.cursor()
    try:
        cur.execute(sql.SQL("""
            CREATE TABLE IF NOT EXISTS public.{} (
                id SERIAL PRIMARY KEY,
                college_id INTEGER NOT NULL,
                classroom_id INTEGER NOT NULL,
                student_name TEXT NOT NULL,
                prn TEXT UNIQUE,
                img_url TEXT,
                password TEXT,
                email TEXT
            );
        """).format(sql.Identifier(table_name)))
        conn.commit()
        return True
    finally:
        cur.close()


def create_dynamic_attendance_table_in_connection(conn, table_name, slots):
    cur = conn.cursor()
    try:
        cur.execute(sql.SQL("""
            CREATE TABLE IF NOT EXISTS public.{} (
                id SERIAL PRIMARY KEY,
                college_id INTEGER NOT NULL,
                classroom_id INTEGER NOT NULL,
                student_name TEXT NOT NULL,
                prn TEXT NOT NULL,
                attendance_date DATE NOT NULL
            );
        """).format(sql.Identifier(table_name)))
        parsed_slots = parse_slot_data(slots)
        for s in parsed_slots:
            col = make_slot_column_name(s.get("start"), s.get("end"))
            teacher_col = f"{col}_teacher"
            cur.execute(sql.SQL("""
                ALTER TABLE public.{}
                ADD COLUMN IF NOT EXISTS {} TEXT;
            """).format(sql.Identifier(table_name), sql.Identifier(col)))
            cur.execute(sql.SQL("""
                ALTER TABLE public.{}
                ADD COLUMN IF NOT EXISTS {} TEXT;
            """).format(sql.Identifier(table_name), sql.Identifier(teacher_col)))
        cur.execute(sql.SQL("""
            ALTER TABLE public.{}
            ADD COLUMN IF NOT EXISTS audit JSONB;
        """).format(sql.Identifier(table_name)))
        index_name = f"{table_name}_prn_date_idx"
        cur.execute(sql.SQL("""
            CREATE UNIQUE INDEX IF NOT EXISTS {} ON public.{} (prn, attendance_date);
        """).format(sql.Identifier(index_name), sql.Identifier(table_name)))
        conn.commit()
        return True
    finally:
        cur.close()


def create_dynamic_student_table(table_name):
    conn = get_pg_connection()
    try:
        return create_dynamic_student_table_in_connection(conn, table_name)
    finally:
        release_pg_connection(conn)


def create_dynamic_attendance_table(table_name, slots):
    conn = get_pg_connection()
    try:
        return create_dynamic_attendance_table_in_connection(conn, table_name, slots)
    finally:
        release_pg_connection(conn)
