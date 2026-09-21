# pyrefly: ignore [missing-import]
from fastapi import FastAPI, Request, HTTPException, Form, UploadFile, File, Response, Depends
# pyrefly: ignore [missing-import]
from fastapi.responses import StreamingResponse, RedirectResponse
# pyrefly: ignore [missing-import]
from fastapi.staticfiles import StaticFiles
# pyrefly: ignore [missing-import]
from fastapi.templating import Jinja2Templates  
# pyrefly: ignore [missing-import]
from pydantic import BaseModel
# pyrefly: ignore [missing-import]
from groq import Groq
# pyrefly: ignore [missing-import]
import os
import sys
import csv
import io
import importlib.util
from urllib.parse import quote
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
CAMPUS_ROOT = BASE_DIR.parent

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Load environment variables from all agent folders
load_dotenv(BASE_DIR / ".env")
for agent_name in ["attendance_agent", "resume_agent", "study_agent", "helpdesk_agent"]:
    agent_env = CAMPUS_ROOT / agent_name / ".env"
    if agent_env.exists():
        load_dotenv(agent_env, override=False)

from auth import (
    create_access_token,
    decode_access_token,
    get_current_user_from_request,
    set_auth_cookie,
    clear_auth_cookie,
    require_auth,
    require_role,
    ROLE_LEVELS
)

from utils import (
    router,
    get_classrooms_by_college,
    get_classroom_by_id,
    get_students_from_classroom_table,
    add_student_to_classroom_web,
    student_login,
    teacher_login,
    hod_login,
    hod_signup,
    get_student_dashboard_data,
    get_student_dashboard_data_by_prn,
    get_teachers_by_college,
    add_teacher_by_invite,
    get_college_by_id,
    defaulter_students,
    current_month_range,
    get_attendance_of_class,
    update_attendance_slot,
    update_class_teacher,
    update_defaulter_threshold,
    search, 
    reset_session
    
)

app = FastAPI(title="CampusOS Platform", description="Unified Campus Operating System with AI Agents")
app.include_router(router)

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Backward & forward compatible TemplateResponse wrapper for Starlette/FastAPI
_orig_template_response = templates.TemplateResponse

def _safe_template_response(name_or_request, context_or_name=None, context=None, **kwargs):
    if isinstance(name_or_request, Request):
        return _orig_template_response(request=name_or_request, name=context_or_name, context=context, **kwargs)
    elif isinstance(name_or_request, str) and isinstance(context_or_name, dict):
        req = context_or_name.get("request") or kwargs.get("request")
        return _orig_template_response(request=req, name=name_or_request, context=context_or_name, **kwargs)
    return _orig_template_response(name_or_request, context_or_name, context, **kwargs)

templates.TemplateResponse = _safe_template_response

# ============================================================================
# Mount Sub-Agent Applications (Attendance, Career/Resume, Study, Helpdesk)
# ============================================================================
BASE_DIR = Path(__file__).resolve().parent
CAMPUS_ROOT = BASE_DIR.parent

def _mount_agent_apps(main_app: FastAPI):
    # 1. Attendance Agent
    try:
        att_src = CAMPUS_ROOT / "attendance_agent" / "src"
        att_web = CAMPUS_ROOT / "attendance_agent" / "web"
        if str(att_src) not in sys.path:
            sys.path.insert(0, str(att_src))
        if str(att_web) not in sys.path:
            sys.path.insert(0, str(att_web))
        spec = importlib.util.spec_from_file_location("attendance_web_app", att_web / "app.py")
        att_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(att_mod)
        main_app.mount("/agent/attendance", att_mod.app)
        main_app.mount("/attendance-agent", att_mod.app)
        print("✅ Mounted Attendance Agent at /agent/attendance")
    except Exception as e:
        print(f"⚠️ Failed to mount Attendance Agent: {e}")

    # 2. Career / Resume Agent (ResumeIQ)
    try:
        res_src = CAMPUS_ROOT / "resume_agent" / "src"
        res_web = CAMPUS_ROOT / "resume_agent" / "web"
        if str(res_src) not in sys.path:
            sys.path.insert(0, str(res_src))
        if str(res_web) not in sys.path:
            sys.path.insert(0, str(res_web))
        spec = importlib.util.spec_from_file_location("resume_web_app", res_web / "app.py")
        res_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(res_mod)
        main_app.mount("/agent/career", res_mod.app)
        main_app.mount("/agent/resume", res_mod.app)
        main_app.mount("/career-agent", res_mod.app)
        print("✅ Mounted Career/Resume Agent at /agent/career and /agent/resume")
    except Exception as e:
        print(f"⚠️ Failed to mount Career/Resume Agent: {e}")

    # 3. Study / Learning Agent
    try:
        stu_src = CAMPUS_ROOT / "study_agent" / "src"
        stu_web = CAMPUS_ROOT / "study_agent" / "web"
        if str(stu_src) not in sys.path:
            sys.path.insert(0, str(stu_src))
        if str(stu_web) not in sys.path:
            sys.path.insert(0, str(stu_web))
        spec = importlib.util.spec_from_file_location("study_web_app", stu_web / "app.py")
        stu_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(stu_mod)
        main_app.mount("/agent/study", stu_mod.app)
        main_app.mount("/agent/learning", stu_mod.app)
        main_app.mount("/study-agent", stu_mod.app)
        print("✅ Mounted Study/Learning Agent at /agent/study and /agent/learning")
    except Exception as e:
        print(f"⚠️ Failed to mount Study Agent: {e}")

    # 4. Campus / Helpdesk Agent
    try:
        help_src = CAMPUS_ROOT / "helpdesk_agent" / "src"
        help_web = CAMPUS_ROOT / "helpdesk_agent" / "web"
        if str(help_src) not in sys.path:
            sys.path.insert(0, str(help_src))
        if str(help_web) not in sys.path:
            sys.path.insert(0, str(help_web))
        spec = importlib.util.spec_from_file_location("helpdesk_web_app", help_web / "app.py")
        help_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(help_mod)
        main_app.mount("/agent/campus", help_mod.app)
        main_app.mount("/agent/helpdesk", help_mod.app)
        main_app.mount("/helpdesk-agent", help_mod.app)
        print("✅ Mounted Campus/Helpdesk Agent at /agent/campus and /agent/helpdesk")
    except Exception as e:
        print(f"⚠️ Failed to mount Helpdesk Agent: {e}")

_mount_agent_apps(app)


# Authentication Protection Middleware for the 3 Main AI Agents
# (Study, Career, and Attendance require Login; Campus Helpdesk is Public for inquiries)
@app.middleware("http")
async def auth_agent_protection_middleware(request: Request, call_next):
    path = request.url.path

    # Allow static assets to load freely
    if any(path.endswith(ext) for ext in [".css", ".js", ".png", ".jpg", ".jpeg", ".svg", ".ico", ".woff", ".woff2", ".ttf"]):
        return await call_next(request)

    protected_agent_prefixes = [
        "/agent/study", "/agent/learning", "/study-agent",
        "/agent/career", "/agent/resume", "/career-agent",
        "/agent/attendance", "/attendance-agent"
    ]
    if any(path == p or path.startswith(p + "/") for p in protected_agent_prefixes):
        user = get_current_user_from_request(request) or CURRENT_USER
        has_auth = bool(user and user.get("role"))
        # Allow query-param fallback if explicitly passed with user details
        has_query_auth = bool(request.query_params.get("role") or request.query_params.get("prn"))
        if not has_auth and not has_query_auth:
            dest = quote(str(request.url.path) + ("?" + str(request.url.query) if request.url.query else ""))
            return RedirectResponse(url=f"/login?redirect={dest}", status_code=303)

    return await call_next(request)


# Direct Agent Redirect Endpoints (Trailing-slash redirects)
@app.get("/agent/attendance")
def redirect_attendance_no_slash(request: Request):
    query_string = request.url.query
    dest = "/agent/attendance/" + (f"?{query_string}" if query_string else "")
    return RedirectResponse(url=dest, status_code=307)


@app.get("/agent/career")
def redirect_career_no_slash(request: Request):
    query_string = request.url.query
    dest = "/agent/career/" + (f"?{query_string}" if query_string else "")
    return RedirectResponse(url=dest, status_code=307)


@app.get("/agent/resume")
def redirect_resume_no_slash(request: Request):
    query_string = request.url.query
    dest = "/agent/career/" + (f"?{query_string}" if query_string else "")
    return RedirectResponse(url=dest, status_code=307)


@app.get("/agent/study")
def redirect_study_no_slash(request: Request):
    query_string = request.url.query
    dest = "/agent/study/" + (f"?{query_string}" if query_string else "")
    return RedirectResponse(url=dest, status_code=307)


@app.get("/agent/learning")
def redirect_learning_no_slash(request: Request):
    query_string = request.url.query
    dest = "/agent/study/" + (f"?{query_string}" if query_string else "")
    return RedirectResponse(url=dest, status_code=307)


@app.get("/agent/campus")
def redirect_campus_no_slash(request: Request):
    query_string = request.url.query
    dest = "/agent/campus/" + (f"?{query_string}" if query_string else "")
    return RedirectResponse(url=dest, status_code=307)


@app.get("/agent/helpdesk")
def redirect_helpdesk_no_slash(request: Request):
    query_string = request.url.query
    dest = "/agent/helpdesk/" + (f"?{query_string}" if query_string else "")
    return RedirectResponse(url=dest, status_code=307)



CURRENT_COLLEGE = {
    "id": None,
    "college_name": None,
    "creator": None,
    "creator_email": None
}

CURRENT_STUDENT = {
    "name": None,
    "email": None,
    "college_id": None,
    "classroom_id": None
}

CURRENT_USER = {
    "name": None,
    "email": None,
    "role": None,   
    "college_id": None
}


def reset_current_student():
    CURRENT_STUDENT["name"] = None
    CURRENT_STUDENT["email"] = None
    CURRENT_STUDENT["college_id"] = None
    CURRENT_STUDENT["classroom_id"] = None


def reset_current_user():
    CURRENT_USER["name"] = None
    CURRENT_USER["email"] = None
    CURRENT_USER["role"] = None
    CURRENT_USER["college_id"] = None


def reset_current_college():
    CURRENT_COLLEGE["id"] = None
    CURRENT_COLLEGE["college_name"] = None
    CURRENT_COLLEGE["creator"] = None
    CURRENT_COLLEGE["creator_email"] = None


@app.get("/")
def home(request: Request):
    return templates.TemplateResponse(
        "new_home2.html",
        {"request": request}
    )


@app.get("/login")
def login(request: Request):
    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "error": None,
            "success": None,
            "open_panel": False,
            "active_role": "student",
            "active_mode": "login",
        }
    )


@app.get("/campus")
def campus_home(request: Request):
    return templates.TemplateResponse("new_home2.html", {"request": request})


@app.get("/landing")
@app.get("/story")
def story_landing(request: Request):
    return templates.TemplateResponse("landing.html", {"request": request})


@app.get("/logout")
def logout(request: Request, response: Response):
    reset_current_student()
    reset_current_user()
    reset_current_college()
    res = RedirectResponse(url="/", status_code=303)
    clear_auth_cookie(res)
    return res


@app.post("/auth")
def auth_action(
    request: Request,
    response: Response,
    role: str = Form(...),
    mode: str = Form(...),

    student_name: str = Form(""),
    student_email: str = Form(""),
    student_password: str = Form(""),
    student_college_id: str = Form(""),
    student_classroom_id: str = Form(""),

    teacher_college_id: str = Form(""),
    teacher_name: str = Form(""),
    teacher_email: str = Form(""),
    teacher_password: str = Form(""),

    hod_login_name: str = Form(""),
    hod_login_college_name: str = Form(""),
    hod_login_email: str = Form(""),
    hod_login_password: str = Form(""),

    hod_signup_name: str = Form(""),
    hod_signup_college_name: str = Form(""),
    hod_signup_email: str = Form(""),
    hod_signup_password: str = Form(""),
):
    if role == "student":
        result = student_login(
            name=student_name,
            email=student_email,
            password=student_password,
            college_id=student_college_id,
            classroom_id=student_classroom_id,
        )

        if not result:
            return templates.TemplateResponse(
                "login.html",
                {
                    "request": request,
                    "error": "Student not found in that classroom. You are not enrolled.",
                    "success": None,
                    "open_panel": True,
                    "active_role": "student",
                    "active_mode": "login",
                }
            )

        reset_current_user()

        CURRENT_STUDENT["name"] = student_name.strip()
        CURRENT_STUDENT["email"] = student_email.strip()
        CURRENT_STUDENT["college_id"] = int(student_college_id)
        CURRENT_STUDENT["classroom_id"] = int(student_classroom_id)

        token = create_access_token({
            "sub": str(result.get("prn") or student_email.strip()),
            "name": student_name.strip(),
            "email": student_email.strip(),
            "role": "student",
            "college_id": int(student_college_id),
            "classroom_id": int(student_classroom_id),
            "prn": str(result.get("prn") or "")
        })

        resp = RedirectResponse(url="/student/dashboard", status_code=303)
        set_auth_cookie(resp, token)
        return resp

    if role == "teacher":
        result = teacher_login(
            college_id=teacher_college_id,
            teacher_name=teacher_name,
            email=teacher_email,
            password=teacher_password,
        )

        if not result:
            return templates.TemplateResponse(
                "login.html",
                {
                    "request": request,
                    "error": "Teacher login failed.",
                    "success": None,
                    "open_panel": True,
                    "active_role": "teacher",
                    "active_mode": "login",
                }
            )

        reset_current_student()

        CURRENT_USER["name"] = teacher_name.strip()
        CURRENT_USER["email"] = teacher_email.strip()
        CURRENT_USER["role"] = "teacher"
        CURRENT_USER["college_id"] = result["college_id"]

        CURRENT_COLLEGE["id"] = result["college_id"]
        CURRENT_COLLEGE["college_name"] = "College"
        CURRENT_COLLEGE["creator"] = teacher_name.strip()
        CURRENT_COLLEGE["creator_email"] = teacher_email.strip()

        token = create_access_token({
            "sub": teacher_email.strip(),
            "name": teacher_name.strip(),
            "email": teacher_email.strip(),
            "role": "teacher",
            "college_id": int(result["college_id"])
        })

        resp = RedirectResponse(url="/dashboard", status_code=303)
        set_auth_cookie(resp, token)
        return resp

    if role == "hod" and mode == "login":
        result = hod_login(
            name=hod_login_name,
            college_name=hod_login_college_name,
            email=hod_login_email,
            password=hod_login_password,
        )

        if not result:
            return templates.TemplateResponse(
                "login.html",
                {
                    "request": request,
                    "error": "HOD / Principal login failed.",
                    "success": None,
                    "open_panel": True,
                    "active_role": "hod",
                    "active_mode": "login",
                }
            )

        reset_current_student()

        CURRENT_USER["name"] = hod_login_name.strip()
        CURRENT_USER["email"] = hod_login_email.strip()
        CURRENT_USER["role"] = "hod"
        CURRENT_USER["college_id"] = result["id"]

        CURRENT_COLLEGE["id"] = result["id"]
        CURRENT_COLLEGE["college_name"] = result["college_name"]
        CURRENT_COLLEGE["creator"] = result["creator"]
        CURRENT_COLLEGE["creator_email"] = result["creator_email"]

        token = create_access_token({
            "sub": hod_login_email.strip(),
            "name": hod_login_name.strip(),
            "email": hod_login_email.strip(),
            "role": "hod",
            "college_id": int(result["id"]),
            "college_name": result["college_name"]
        })

        resp = RedirectResponse(url="/dashboard", status_code=303)
        set_auth_cookie(resp, token)
        return resp

    if role == "hod" and mode == "signup":
        result = hod_signup(
            name=hod_signup_name,
            college_name=hod_signup_college_name,
            email=hod_signup_email,
            password=hod_signup_password,
        )

        if not result:
            return templates.TemplateResponse(
                "login.html",
                {
                    "request": request,
                    "error": "Signup failed. College or HOD may already exist.",
                    "success": None,
                    "open_panel": True,
                    "active_role": "hod",
                    "active_mode": "signup",
                }
            )

        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "error": None,
                "success": "HOD account created successfully. Now log in.",
                "open_panel": True,
                "active_role": "hod",
                "active_mode": "login",
            }
        )

    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "error": "Invalid request.",
            "success": None,
            "open_panel": True,
            "active_role": "student",
            "active_mode": "login",
        }
    )
@app.get("/teacher/invite/{college_id}")
def teacher_invite_page(request: Request, college_id: int):
    college = get_college_by_id(int(college_id))
    invite_url = str(request.url)
    return templates.TemplateResponse(
        "teacher_invite_login.html",
        {
            "request": request,
            "college_id": college_id,
            "college_name": college["college_name"] if college else "Campus",
            "invite_url": invite_url,
            "error": None,
            "success": None,
        }
    )

@app.post("/teacher/invite/{college_id}")
async def teacher_invite_signup(
    request: Request,
    college_id: int,
    teacher_name: str = Form(...),
    teacher_email: str = Form(...),
    teacher_password: str = Form(...),
    teacher_image: UploadFile = File(None),
):
    result = add_teacher_by_invite(
        college_id=college_id,
        teacher_name=teacher_name.strip(),
        email=teacher_email.strip(),
        password=teacher_password.strip(),
    )

    college = get_college_by_id(int(college_id))
    college_name = college["college_name"] if college else "Campus"
    invite_url = str(request.url)

    if not result:
        return templates.TemplateResponse(
            "teacher_invite_login.html",
            {
                "request": request,
                "college_id": college_id,
                "college_name": college_name,
                "invite_url": invite_url,
                "error": "Teacher signup failed. Email may already exist or college is invalid.",
                "success": None,
            },
            status_code=400
        )

    # Handle teacher photo upload (optional)
    teacher_id = result.get("id")
    if teacher_image and teacher_image.filename and teacher_id:
        try:
            from utils import upload_student_image_bytes, supabase as _supabase
            file_bytes = await teacher_image.read()
            if file_bytes:
                img_url, _ = upload_student_image_bytes(
                    folder_name="teachers",
                    student_prn=f"teacher_{teacher_id}",
                    file_name=teacher_image.filename,
                    file_bytes=file_bytes
                )
                if img_url:
                    _supabase.table("teachers").update({"img_url": img_url}).eq("id", teacher_id).execute()
        except Exception as e:
            print("Teacher image upload error (non-fatal):", e)

    reset_current_student()

    CURRENT_USER["name"] = teacher_name.strip()
    CURRENT_USER["email"] = teacher_email.strip()
    CURRENT_USER["role"] = "teacher"
    CURRENT_USER["college_id"] = int(college_id)

    if not college:
        return templates.TemplateResponse(
            "teacher_invite_login.html",
            {
                "request": request,
                "college_id": college_id,
                "college_name": college_name,
                "invite_url": invite_url,
                "error": "College not found.",
                "success": None,
            },
            status_code=404
        )

    token = create_access_token({
        "sub": teacher_email.strip(),
        "name": teacher_name.strip(),
        "email": teacher_email.strip(),
        "role": "teacher",
        "college_id": int(college_id)
    })

    resp = RedirectResponse(url="/dashboard", status_code=303)
    set_auth_cookie(resp, token)
    return resp

@app.get("/student/invite/{college_id}/{classroom_id}")
def student_invite_page(request: Request, college_id: int, classroom_id: int):
    classroom = get_classroom_by_id(classroom_id)
    college = get_college_by_id(college_id)
    invite_url = str(request.url)
    return templates.TemplateResponse(
        "student_invite_login.html",
        {
            "request": request,
            "college_id": college_id,
            "classroom_id": classroom_id,
            "classroom_name": classroom["classroom_name"] if classroom else "Classroom",
            "college_name": college["college_name"] if college else "Campus",
            "invite_url": invite_url,
            "error": None,
            "success": None,
        }
    )
    
@app.post("/student/invite/{college_id}/{classroom_id}")
async def student_invite_submit(
    request: Request,
    college_id: int,
    classroom_id: int,
    student_name: str = Form(...),
    prn: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    image: UploadFile = File(...)
):
    classroom = get_classroom_by_id(classroom_id)

    if not classroom:
        raise HTTPException(status_code=404, detail="Classroom not found")

    if classroom["college_id"] != college_id:
        raise HTTPException(status_code=403, detail="This classroom does not belong to this college")

    result = await add_student_to_classroom_web(
        classroom=classroom,
        student_name=student_name.strip(),
        student_prn=prn.strip(),
        email=email.strip(),
        password=password.strip(),
        upload_file=image
    )

    college = get_college_by_id(college_id)
    invite_url = str(request.base_url).rstrip("/") + f"/student/invite/{college_id}/{classroom_id}"

    if not result:
        return templates.TemplateResponse(
            "student_invite_login.html",
            {
                "request": request,
                "college_id": college_id,
                "classroom_id": classroom_id,
                "classroom_name": classroom["classroom_name"] if classroom else "Classroom",
                "college_name": college["college_name"] if college else "Campus",
                "invite_url": invite_url,
                "error": "Failed to join classroom.",
                "success": None,
            },
            status_code=400
        )

    return templates.TemplateResponse(
        "student_invite_login.html",
        {
            "request": request,
            "college_id": college_id,
            "classroom_id": classroom_id,
            "classroom_name": classroom["classroom_name"] if classroom else "Classroom",
            "college_name": college["college_name"] if college else "Campus",
            "invite_url": invite_url,
            "error": None,
            "success": "Student account created successfully! You can now log in from the home page.",
        }
    )
    
@app.post("/student/invite/login")
def student_invite_login(
    request: Request,
    college_id: str = Form(...),
    classroom_id: str = Form(...),
    student_name: str = Form(...),
    student_email: str = Form(...),
    student_password: str = Form(...),
):
    result = student_login(
        name=student_name,
        email=student_email,
        password=student_password,
        college_id=college_id,
        classroom_id=classroom_id,
    )

    if not result:
        return templates.TemplateResponse(
            "student_invite_login.html",
            {
                "request": request,
                "college_id": college_id,
                "classroom_id": classroom_id,
                "error": "Student login failed. Check your details.",
                "success": None,
            }
        )

    token = create_access_token({
        "sub": str(result.get("prn") or student_email.strip()),
        "name": student_name.strip(),
        "email": student_email.strip(),
        "role": "student",
        "college_id": int(college_id),
        "classroom_id": int(classroom_id),
        "prn": str(result.get("prn") or "")
    })

    resp = RedirectResponse(url="/student/dashboard", status_code=303)
    set_auth_cookie(resp, token)
    return resp


@app.get("/student")
@app.get("/student/dashboard")
def student_dashboard(request: Request):
    user = get_current_user_from_request(request)
    if not user:
        if CURRENT_STUDENT.get("name") and CURRENT_STUDENT.get("college_id") is not None:
            user = {**CURRENT_STUDENT, "role": "student"}
        else:
            return RedirectResponse(url="/login", status_code=303)

    student_name = user.get("name") or user.get("student_name")
    student_email = user.get("email") or user.get("student_email")
    college_id = user.get("college_id")
    classroom_id = user.get("classroom_id")

    if not student_name or not student_email or college_id is None or classroom_id is None:
        return RedirectResponse(url="/login", status_code=303)

    dashboard_data = get_student_dashboard_data(
        student_name=student_name,
        student_email=student_email,
        college_id=college_id,
        classroom_id=classroom_id,
    )

    if not dashboard_data:
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "error": "Unable to load student dashboard.",
                "success": None,
                "open_panel": True,
                "active_role": "student",
                "active_mode": "login",
            }
        )

    attendance = dashboard_data.get("attendance", {})

    chart_labels = []
    present_chart_data = []
    absent_chart_data = []
    pending_chart_data = []

    month_labels = []
    month_values = []

    streak = 0
    active_streak = True

    for date, data in attendance.items():

        slots = data.get("slots", [])

        present_count = 0
        absent_count = 0
        pending_count = 0

        all_present = True

        for row in slots:

            status = row.get("status", "").lower()

            if status == "present":
                present_count += 1
            elif status == "absent":
                absent_count += 1
                all_present = False
            else:
                pending_count += 1
                all_present = False

        chart_labels.append(date)
        present_chart_data.append(present_count)
        absent_chart_data.append(absent_count)
        pending_chart_data.append(pending_count)

        total = present_count + absent_count + pending_count
        perc = round((present_count / total) * 100, 2) if total > 0 else 0

        month_labels.append(date)
        month_values.append(perc)

        if active_streak and all_present:
            streak += 1
        else:
            active_streak = False

    attendance_percent = dashboard_data.get("attendance_percent", 0)

    class_average_percent = round(min(100, attendance_percent ), 2)

    if attendance_percent >= 90:
        rank = "A"
    elif attendance_percent >= 80:
        rank = "B"
    elif attendance_percent >= 70:
        rank = "C"
    else:
        rank = "D"

    safe_slots_needed = 0 if attendance_percent >= 75 else int((75 - attendance_percent) / 2) + 1

    predicted_percent = round((attendance_percent * 0.7) + (month_values[-1] * 0.3), 2) if month_values else attendance_percent

    if attendance_percent >= class_average_percent:
        progress_message = "You are performing above class average."
    else:
        progress_message = "You are below class average. Improvement possible."

    if attendance_percent < 75:
        risk_message = "You are in defaulter risk zone."
    else:
        risk_message = "You are currently in safe attendance zone."

    goal_message = f"Need {safe_slots_needed} more present slots to stay safe."

    college = get_college_by_id(college_id) if college_id else None

    return templates.TemplateResponse(
        "student.html",
        {
            "request": request,
            **dashboard_data,
            "chart_labels": chart_labels,
            "present_chart_data": present_chart_data,
            "absent_chart_data": absent_chart_data,
            "pending_chart_data": pending_chart_data,

            "month_labels": month_labels,
            "month_values": month_values,
            "class_average_percent": class_average_percent,
            "rank": rank,
            "streak": streak,
            "safe_slots_needed": safe_slots_needed,
            "predicted_percent": predicted_percent,
            "progress_message": progress_message,
            "risk_message": risk_message,
            "goal_message": goal_message,
            "current_role": "student",
            "viewer_name": None,
            "viewer_role": None,
            "college_name": college["college_name"] if college else None,
            "class_teacher": dashboard_data.get("class_teacher"),
        }
    )

@app.get("/main_dashboard")
@app.get("/dashboard")
def dashboard(request: Request):
    user = get_current_user_from_request(request)
    if not user:
        if CURRENT_USER.get("college_id") and CURRENT_USER.get("role"):
            user = CURRENT_USER
        elif CURRENT_STUDENT.get("college_id"):
            user = {**CURRENT_STUDENT, "role": "student"}
        else:
            return RedirectResponse(url="/login", status_code=303)

    if user.get("role") == "student":
        return RedirectResponse(url="/student/dashboard", status_code=303)

    if user.get("role") not in ["hod", "teacher"]:
        return RedirectResponse(url="/login", status_code=303)

    college_id = user["college_id"]
    college = get_college_by_id(college_id) or CURRENT_COLLEGE
    classrooms = get_classrooms_by_college(college_id)
    teachers = get_teachers_by_college(college_id) if user.get("role") == "hod" else []

    classroom_data = {}

    total_students = 0
    total_defaulters = 0
    total_present = 0
    total_absent = 0

    class_performance = []
    teacher_stats = {}
    slot_stats = {}
    daily_map = {}

    for classroom in classrooms:

        classroom_id = classroom["id"]

        students = get_students_from_classroom_table(classroom["classroom_table"])
        defaulters = defaulter_students(classroom["college_id"], classroom_id) or []

        student_count = len(students)
        defaulter_count = len([d for d in defaulters if d["defaulter"] == "YES"])

        total_students += student_count
        total_defaulters += defaulter_count

        attendance_rows = get_attendance_of_class(classroom["attendance_table"])
        rows = attendance_rows.data or []

        present = 0
        absent = 0

        for row in rows:

            row_date = str(row.get("attendance_date"))

            if row_date not in daily_map:
                daily_map[row_date] = {"present":0,"absent":0}

            for key, value in row.items():

                if key.startswith("slot_") and not key.endswith("_teacher"):

                    val = str(value).lower()

                    teacher_name = row.get(f"{key}_teacher", "Unknown")

                    if key not in slot_stats:
                        slot_stats[key] = {"present":0,"absent":0}

                    if teacher_name not in teacher_stats:
                        teacher_stats[teacher_name] = {"present":0,"absent":0}

                    if val == "present":
                        present += 1
                        total_present += 1
                        daily_map[row_date]["present"] += 1
                        slot_stats[key]["present"] += 1
                        teacher_stats[teacher_name]["present"] += 1

                    elif val == "absent":
                        absent += 1
                        total_absent += 1
                        daily_map[row_date]["absent"] += 1
                        slot_stats[key]["absent"] += 1
                        teacher_stats[teacher_name]["absent"] += 1

        total = present + absent
        percent = round((present / total * 100), 2) if total > 0 else 0

        class_performance.append({
            "class": classroom["classroom_name"],
            "percent": percent,
            "defaulters": defaulter_count
        })

        classroom_data[classroom_id] = {
            "student_count": student_count,
            "defaulter_count": defaulter_count
        }

    overall_percent = round(
        (total_present / (total_present + total_absent) * 100), 2
    ) if (total_present + total_absent) > 0 else 0

    best_class = max(class_performance, key=lambda x:x["percent"], default=None)
    worst_class = min(class_performance, key=lambda x:x["percent"], default=None)

    avg_class_attendance = round(
        sum(x["percent"] for x in class_performance) / len(class_performance),2
    ) if class_performance else 0

    trend_labels = sorted(daily_map.keys())
    trend_values = []

    for d in trend_labels:
        p = daily_map[d]["present"]
        a = daily_map[d]["absent"]
        total = p + a
        perc = round((p/total*100),2) if total > 0 else 0
        trend_values.append(perc)

    teacher_board = []

    for t,v in teacher_stats.items():
        total = v["present"] + v["absent"]
        perc = round((v["present"]/total*100),2) if total>0 else 0
        teacher_board.append({"teacher":t,"percent":perc})

    teacher_board = sorted(teacher_board,key=lambda x:x["percent"],reverse=True)

    slot_board = []

    for s,v in slot_stats.items():
        total = v["present"] + v["absent"]
        perc = round((v["present"]/total*100),2) if total>0 else 0
        slot_board.append({"slot":s,"percent":perc})

    prediction = round(sum(trend_values[-5:]) / len(trend_values[-5:]),2) if trend_values else overall_percent

    alerts = []

    if overall_percent < 75:
        alerts.append("Overall attendance below 75%")

    if total_defaulters > 10:
        alerts.append("High defaulter count detected")

    if worst_class:
        alerts.append(f"Needs attention: {worst_class['class']}")

    return templates.TemplateResponse(
        "main_dashboard.html",
        {
            "request": request,
            "college": college,
            "classrooms": classrooms,
            "classroom_data": classroom_data,
            "classroom_count": len(classrooms),
            "student_count": total_students,
            "defaulter_count": total_defaulters,
            "teacher_count": len(teachers),
            "current_role": user["role"],
            "current_user_name": user.get("name"),
            "current_user_email": user.get("email"),
            "overall_percent": overall_percent,
            "best_class": best_class,
            "worst_class": worst_class,
            "avg_class_attendance": avg_class_attendance,
            "class_performance": class_performance,
            "trend_labels": trend_labels,
            "trend_values": trend_values,
            "teacher_board": teacher_board[:5],
            "slot_board": slot_board,
            "prediction": prediction,
            "alerts": alerts
        }
    )

@app.get("/staff")
def staff_dashboard(request: Request):
    user = get_current_user_from_request(request) or CURRENT_USER
    if not user or not user.get("college_id"):
        return RedirectResponse(url="/login", status_code=303)
    if user.get("role") != "hod":
        if user.get("role") == "teacher":
            return RedirectResponse(url="/dashboard", status_code=303)
        return RedirectResponse(url="/student/dashboard", status_code=303)

    college = get_college_by_id(user["college_id"]) or CURRENT_COLLEGE
    teachers = get_teachers_by_college(user["college_id"])
    teacher_invite_link = f"http://127.0.0.1:8000/teacher/invite/{user['college_id']}"

    return templates.TemplateResponse(
        "staff_dashboard.html",
        {
            "request": request,
            "college": college,
            "teachers": teachers,
            "teacher_count": len(teachers),
            "teacher_invite_link": teacher_invite_link,
            "current_user_name": user.get("name"),
            "current_user_email": user.get("email"),
            "current_role": user.get("role"),
            "error_message": None,
            "success_message": None,
        }
    )
    
@app.post("/classroom/{classroom_id}/set-defaulter")
def set_defaulter(
    request: Request,
    classroom_id: int,
    defaulter: int = Form(...)
):
    user = get_current_user_from_request(request) or CURRENT_USER
    if not user or user.get("role") not in ["teacher", "hod"]:
        raise HTTPException(status_code=403, detail="Unauthorized")

    result = update_defaulter_threshold(classroom_id, defaulter)

    if not result:
        raise HTTPException(status_code=400, detail="Update failed")

    return RedirectResponse(url=f"/classroom/{classroom_id}", status_code=303)

@app.post("/classroom/{classroom_id}/set-teacher")
def set_teacher(
    request: Request,
    classroom_id: int,
    class_teacher: str = Form(...)
):
    user = get_current_user_from_request(request) or CURRENT_USER
    if not user or user.get("role") != "hod":
        raise HTTPException(status_code=403, detail="Unauthorized: Only HOD can assign class teachers")

    result = update_class_teacher(
        classroom_id,
        class_teacher.strip(),
        user["college_id"]
    )

    if not result:
        raise HTTPException(status_code=400, detail="Update failed")

    return RedirectResponse(url=f"/classroom/{classroom_id}", status_code=303)

@app.get("/classroom/{classroom_id}")
def classroom_dashboard(request: Request, classroom_id: int):
    user = get_current_user_from_request(request) or CURRENT_USER
    if not user or not user.get("college_id") or not user.get("role"):
        return RedirectResponse(url="/login", status_code=303)

    if user.get("role") == "student":
        return RedirectResponse(url="/student/dashboard", status_code=303)

    if user.get("role") not in ["hod", "teacher"]:
        return RedirectResponse(url="/login", status_code=303)

    classroom = get_classroom_by_id(classroom_id)

    if not classroom:
        raise HTTPException(status_code=404, detail="Classroom not found")

    if classroom["college_id"] != user["college_id"]:
        raise HTTPException(status_code=403, detail="Unauthorized")

    students = get_students_from_classroom_table(classroom["classroom_table"])
    defaulters = defaulter_students(classroom["college_id"], classroom_id) or []

    defaulter_map = {d["prn"]: d["defaulter"] for d in defaulters}

    for student in students:
        student["defaulter"] = defaulter_map.get(student.get("prn"), "NO")

    defaulter_count = sum(1 for s in students if s["defaulter"] == "YES")

    attendance_res = get_attendance_of_class(classroom["attendance_table"])
    rows = attendance_res.data or []

    total_present = 0
    total_absent = 0

    daily_map = {}
    slot_map = {}
    student_map = {}

    for row in rows:

        date = str(row.get("attendance_date"))

        if date not in daily_map:
            daily_map[date] = {"present":0,"absent":0}

        prn = str(row.get("prn"))

        if prn not in student_map:
            student_map[prn] = {"present":0,"absent":0}

        for key, value in row.items():

            if key.startswith("slot_") and not key.endswith("_teacher"):

                status = str(value).lower()

                if key not in slot_map:
                    slot_map[key] = {"present":0,"absent":0}

                if status == "present":
                    total_present += 1
                    daily_map[date]["present"] += 1
                    slot_map[key]["present"] += 1
                    student_map[prn]["present"] += 1

                elif status == "absent":
                    total_absent += 1
                    daily_map[date]["absent"] += 1
                    slot_map[key]["absent"] += 1
                    student_map[prn]["absent"] += 1

    overall_percent = round(
        (total_present / (total_present + total_absent)) * 100, 2
    ) if (total_present + total_absent) > 0 else 0

    trend_labels = sorted(daily_map.keys())
    trend_values = []

    for d in trend_labels:
        p = daily_map[d]["present"]
        a = daily_map[d]["absent"]
        t = p + a
        trend_values.append(round((p / t) * 100, 2) if t > 0 else 0)

    slot_labels = []
    slot_values = []

    for k,v in slot_map.items():
        t = v["present"] + v["absent"]
        slot_labels.append(k.replace("slot_","").replace("_"," "))
        slot_values.append(round((v["present"]/t)*100,2) if t > 0 else 0)

    weak_students = []

    for student in students:
        prn = str(student["prn"])
        stats = student_map.get(prn, {"present":0,"absent":0})
        t = stats["present"] + stats["absent"]
        perc = round((stats["present"]/t)*100,2) if t > 0 else 0

        weak_students.append({
            "name": student["student_name"],
            "percent": perc
        })

    weak_students = sorted(weak_students,key=lambda x:x["percent"])[:5]

    prediction = round(sum(trend_values[-5:]) / len(trend_values[-5:]),2) if trend_values else overall_percent

    alerts = []

    if overall_percent < 75:
        alerts.append("Class attendance below 75%")

    if defaulter_count > 5:
        alerts.append("High defaulter count in class")

    if weak_students:
        alerts.append(f"Lowest attendance: {weak_students[0]['name']}")

    base_url = str(request.base_url).rstrip("/")
    student_join_link = f"http://127.0.0.1:8000/student/invite/{user['college_id']}/{classroom['id']}"
    teachers = get_teachers_by_college(user["college_id"])
    college = get_college_by_id(user["college_id"]) or CURRENT_COLLEGE

    return templates.TemplateResponse(
        "class_dashboard.html",
        {
            "request": request,
            "college": college,
            "classroom": classroom,
            "students": students,
            "defualters_count": defaulter_count,
            "student_count": len(students),
            "current_role": user["role"],
            "current_user_name": user.get("name"),
            "current_user_email": user.get("email"),
            "student_join_link": student_join_link,
            "teachers": teachers,

            "overall_percent": overall_percent,
            "trend_labels": trend_labels,
            "trend_values": trend_values,
            "slot_labels": slot_labels,
            "slot_values": slot_values,
            "weak_students": weak_students,
            "prediction": prediction,
            "alerts": alerts,

            "error_message": None,
            "success_message": None
        }
    )


@app.post("/classroom/{classroom_id}/add-student")
async def add_student_web(
    request: Request,
    classroom_id: int,
    student_name: str = Form(...),
    prn: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    image: UploadFile = File(...)
):
    user = get_current_user_from_request(request) or CURRENT_USER
    if not user or not user.get("college_id") or user.get("role") not in ["teacher", "hod"]:
        return RedirectResponse(url="/login", status_code=303)

    classroom = get_classroom_by_id(classroom_id)

    if not classroom:
        raise HTTPException(status_code=404, detail="Classroom not found")

    if classroom["college_id"] != user["college_id"]:
        raise HTTPException(status_code=403, detail="This classroom does not belong to current college")

    student_name = student_name.strip()
    prn = prn.strip()
    email = email.strip()
    password = password.strip()

    students = get_students_from_classroom_table(classroom["classroom_table"])
    base_url = str(request.base_url).rstrip("/")
    student_join_link = f"{base_url}/student/join?classroom_id={classroom_id}"
    teacher_join_link = f"{base_url}/teacher/join"
    college = get_college_by_id(user["college_id"]) or CURRENT_COLLEGE

    if not student_name or not prn or not email or not password:
        return templates.TemplateResponse(
            "class_dashboard.html",
            {
                "request": request,
                "college": college,
                "classroom": classroom,
                "students": students,
                "student_count": len(students),
                "error_message": "All fields are required.",
                "success_message": None,
                "current_role": user["role"],
                "current_user_name": user.get("name"),
                "current_user_email": user.get("email"),
                "student_join_link": student_join_link,
                "teacher_join_link": teacher_join_link,
            },
            status_code=400
        )

    if not image or not image.filename:
        return templates.TemplateResponse(
            "class_dashboard.html",
            {
                "request": request,
                "college": college,
                "classroom": classroom,
                "students": students,
                "student_count": len(students),
                "error_message": "Please select an image.",
                "success_message": None,
                "current_role": user["role"],
                "current_user_name": user.get("name"),
                "current_user_email": user.get("email"),
                "student_join_link": student_join_link,
                "teacher_join_link": teacher_join_link,
            },
            status_code=400
        )

    result = await add_student_to_classroom_web(
        classroom=classroom,
        student_name=student_name,
        student_prn=prn,
        email=email,
        password=password,
        upload_file=image
    )

    if not result:
        students = get_students_from_classroom_table(classroom["classroom_table"])
        return templates.TemplateResponse(
            "class_dashboard.html",
            {
                "request": request,
                "college": college,
                "classroom": classroom,
                "students": students,
                "student_count": len(students),
                "error_message": "Failed to add student.",
                "success_message": None,
                "current_role": user["role"],
                "current_user_name": user.get("name"),
                "current_user_email": user.get("email"),
                "student_join_link": student_join_link,
                "teacher_join_link": teacher_join_link,
            },
            status_code=500
        )

    return RedirectResponse(
        url=f"/classroom/{classroom_id}",
        status_code=303
    )


@app.get("/student/view/{classroom_id}/{prn}")
def view_student_page(request: Request, classroom_id: int, prn: str):
    user = get_current_user_from_request(request) or CURRENT_USER
    if not user or not user.get("college_id") or not user.get("role"):
        return RedirectResponse(url="/login", status_code=303)

    if user.get("role") == "student" and str(user.get("prn")) != str(prn):
        return RedirectResponse(url="/student/dashboard", status_code=303)

    classroom = get_classroom_by_id(classroom_id)

    if not classroom:
        raise HTTPException(status_code=404, detail="Classroom not found")

    if classroom["college_id"] != user["college_id"]:
        raise HTTPException(status_code=403, detail="Unauthorized classroom access")

    dashboard_data = get_student_dashboard_data_by_prn(
        college_id=classroom["college_id"],
        classroom_id=classroom_id,
        prn=prn
    )

    if not dashboard_data:
        raise HTTPException(status_code=404, detail="Student dashboard not found")

    attendance = dashboard_data.get("attendance", {})

    chart_labels = []
    present_chart_data = []
    absent_chart_data = []
    pending_chart_data = []

    month_labels = []
    month_values = []

    streak = 0
    streak_open = True

    for date, data in attendance.items():

        slots = data.get("slots", [])

        p = 0
        a = 0
        pe = 0
        full_present = True

        for row in slots:

            status = row.get("status", "").lower()

            if status == "present":
                p += 1
            elif status == "absent":
                a += 1
                full_present = False
            else:
                pe += 1
                full_present = False

        chart_labels.append(date)
        present_chart_data.append(p)
        absent_chart_data.append(a)
        pending_chart_data.append(pe)

        total = p + a + pe
        day_percent = round((p / total) * 100, 2) if total > 0 else 0

        month_labels.append(date)
        month_values.append(day_percent)

        if streak_open and full_present:
            streak += 1
        else:
            streak_open = False

    attendance_percent = dashboard_data.get("attendance_percent", 0)

    class_average_percent = round(min(100, attendance_percent + 5), 2)

    if attendance_percent >= 90:
        rank = 1
    elif attendance_percent >= 80:
        rank = 3
    elif attendance_percent >= 70:
        rank = 5
    else:
        rank = 9

    safe_slots_needed = 0 if attendance_percent >= 75 else int((75 - attendance_percent) / 2) + 1

    predicted_percent = round(
        (attendance_percent * 0.7) + ((month_values[-1] if month_values else attendance_percent) * 0.3),
        2
    )

    progress_message = (
        "Student is above class average."
        if attendance_percent >= class_average_percent
        else "Student is below class average."
    )

    risk_message = (
        "Safe attendance zone."
        if attendance_percent >= 75
        else "Defaulter risk zone."
    )

    goal_message = f"Needs {safe_slots_needed} more present slots for safe zone."
    college = get_college_by_id(user["college_id"]) or CURRENT_COLLEGE

    return templates.TemplateResponse(
        "student.html",
        {
            "request": request,
            **dashboard_data,

            "class_teacher": classroom["class_teacher"],
            "current_role": user["role"],
            "viewer_name": user.get("name"),
            "viewer_role": user.get("role"),
            "college_name": college.get("college_name") if college else None,

            "chart_labels": chart_labels,
            "present_chart_data": present_chart_data,
            "absent_chart_data": absent_chart_data,
            "pending_chart_data": pending_chart_data,

            "month_labels": month_labels,
            "month_values": month_values,

            "class_average_percent": class_average_percent,
            "rank": rank,
            "streak": streak,
            "safe_slots_needed": safe_slots_needed,
            "predicted_percent": predicted_percent,

            "progress_message": progress_message,
            "risk_message": risk_message,
            "goal_message": goal_message
        }
    )

@app.post("/attendance/update")
async def update_attendance(
    request: Request,
    classroom_id: int = Form(...),
    prn: str = Form(...),
    attendance_date: str = Form(...),
    slot_label: str = Form(...),
    new_status: str = Form(...)
):
    user = get_current_user_from_request(request) or CURRENT_USER
    if not user or user.get("role") not in ["teacher", "hod"]:
        raise HTTPException(status_code=403, detail="Unauthorized")

    success = update_attendance_slot(
        college_id=user["college_id"],
        classroom_id=classroom_id,
        prn=prn,
        attendance_date=attendance_date,
        slot_label=slot_label,
        new_status=new_status,
        teacher_name=user.get("name") or "Teacher"
    )

    if not success:
        raise HTTPException(status_code=400, detail="Update failed")

    return {"message": "Attendance updated"}

@app.get("/classroom/{classroom_id}/export/csv")
def export_classroom_csv(request: Request, classroom_id: int):
    user = get_current_user_from_request(request) or CURRENT_USER
    if not user or not user.get("college_id") or user.get("role") not in ["teacher", "hod"]:
        return RedirectResponse(url="/login", status_code=303)

    classroom = get_classroom_by_id(classroom_id)

    if not classroom:
        raise HTTPException(status_code=404, detail="Classroom not found")

    if classroom["college_id"] != user["college_id"]:
        raise HTTPException(status_code=403, detail="Unauthorized")

    classroom_table = classroom["classroom_table"]
    attendance_table = classroom["attendance_table"]

    students_res = get_students_from_classroom_table(classroom_table)

    students = {s["prn"]: s for s in (students_res or [])}

    attendance_res = get_attendance_of_class(attendance_table)
    attendance_rows = attendance_res.data or []
    attendance_rows = sorted(
    attendance_rows,
    key=lambda x: (
        str(x.get("prn", ""))
    )
)
    slot_columns = set()
    for row in attendance_rows:
        for key in row.keys():
            if key.startswith("slot_"):
                slot_columns.add(key)

    slot_columns = sorted(slot_columns)

    def format_slot(slot):
        return slot.replace("slot_", "").replace("_", ":")

    formatted_slots = [format_slot(s) for s in slot_columns]

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "Student Name", "PRN", "Email", "Date", *formatted_slots
    ])

    for row in attendance_rows:
        prn = row.get("prn")
        student = students.get(prn, {})

        csv_row = [
            student.get("student_name", ""),
            prn,
            student.get("email", ""),
            row.get("attendance_date", "")
        ]

        for slot in slot_columns:
            csv_row.append(row.get(slot, "pending"))

        writer.writerow(csv_row)

    output.seek(0)

    safe_classroom_name = classroom["classroom_name"].replace(" ", "_").lower()

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={safe_classroom_name}_attendance.csv"
        }
    )
    
load_dotenv()

groq = Groq(api_key=os.getenv("API_KEY"))

class ChatRequest(BaseModel):
    query: str
    file_name: str
    session_id: str


@app.post("/chat/groq")
def chat_groq(request: ChatRequest):

    contexts = search(
        request.file_name,
        request.query,
        request.session_id
    )

    context = "\n".join(contexts)

    model_name = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
    try:
        response = groq.chat.completions.create(
            model=model_name,
            messages=[
                {
                    "role": "system",
                    "content": "You are the CampusOS Intelligent Assistant. Provide accurate, helpful, and concise answers based on the provided CampusOS context."
                },
                {
                    "role": "user",
                    "content": f"""Context:
{context}

Question:
{request.query}

Answer:"""
                }
            ],
            temperature=0.3
        )
        answer = response.choices[0].message.content
    except Exception as e:
        # Fallback to qwen3.6-27b or error message
        try:
            response = groq.chat.completions.create(
                model="openai/gpt-oss-20b",
                messages=[
                    {"role": "system", "content": "You are the CampusOS Assistant."},
                    {"role": "user", "content": f"Context:\n{context}\n\nQuestion:\n{request.query}\n\nAnswer:"}
                ],
                temperature=0.3
            )
            answer = response.choices[0].message.content
        except Exception:
            answer = f"I found the relevant information in the CampusOS guide:\n\n{context[:600]}" if context else "I could not find specific details for your query. Please refer to the CampusOS manual or contact your college administrator."

    return {
        "answer": answer
    }

@app.post("/reset")
def reset(session_id: str):
    reset_session(session_id)
    return {"message": "session reset"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

