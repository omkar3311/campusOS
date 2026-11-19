import bcrypt
from core.db import get_db_cursor, init_local_database


def encrypt_password(password: str) -> str:
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def check_password(entered_password: str, stored_password: str) -> bool:
    if not entered_password or not stored_password:
        return False
    clean_stored = str(stored_password).strip()
    if clean_stored.startswith("\\x"):
        try:
            clean_stored = bytes.fromhex(clean_stored[2:]).decode("utf-8")
        except Exception:
            pass
    if clean_stored.startswith("$2b$") or clean_stored.startswith("$2a$"):
        try:
            return bcrypt.checkpw(entered_password.encode("utf-8"), clean_stored.encode("utf-8"))
        except Exception:
            return False
    return entered_password == clean_stored


def check_college_login(name, email, college_name, password):
    try:
        with get_db_cursor(commit=False) as cur:
            cur.execute("""
                SELECT id, college_name, creator, creator_email, password
                FROM public.colleges
                WHERE creator = %s
                  AND creator_email = %s
                  AND college_name = %s
                LIMIT 1
            """, (name, email, college_name))
            row = cur.fetchone()
            if not row:
                return None
            stored_pwd = row[4]
            if stored_pwd and not check_password(password, stored_pwd):
                return None
            return {
                "id": row[0],
                "college_name": row[1],
                "creator": row[2],
                "creator_email": row[3]
            }
    except Exception:
        return None


def get_college_names():
    try:
        with get_db_cursor(commit=False) as cur:
            cur.execute("SELECT college_name FROM public.colleges")
            rows = cur.fetchall()
            return sorted(list({row[0] for row in rows if row[0]}))
    except Exception:
        return []


def is_login():
    init_local_database()
    try:
        with get_db_cursor(commit=False) as cur:
            cur.execute("""
                SELECT id, college_name, creator, creator_email, is_login
                FROM public.login
                WHERE is_login = TRUE
                LIMIT 1;
            """)
            row = cur.fetchone()
            if row:
                user_data = {
                    "id": row[0],
                    "college_name": row[1],
                    "creator": row[2],
                    "creator_email": row[3],
                }
                return True, user_data
            return False, None
    except Exception:
        return False, None


def enroll_login(id, college_name, creator, creator_email, password):
    try:
        with get_db_cursor(commit=True) as cur:
            cur.execute("""
                INSERT INTO public.login 
                (id, college_name, creator, creator_email, password, is_login)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (id)
                DO UPDATE SET 
                    is_login = TRUE,
                    college_name = EXCLUDED.college_name,
                    creator = EXCLUDED.creator,
                    creator_email = EXCLUDED.creator_email,
                    password = EXCLUDED.password;
            """, (id, college_name, creator, creator_email, password, True))
        return True
    except Exception:
        return False


def logout(id):
    try:
        with get_db_cursor(commit=True) as cur:
            cur.execute("""
                UPDATE public.login
                SET is_login = FALSE
                WHERE id = %s
            """, (id,))
        return True
    except Exception:
        return False
