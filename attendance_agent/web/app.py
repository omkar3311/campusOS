import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# Ensure src is in python path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent
src_dir = project_root / "src"

load_dotenv(project_root / ".env")
load_dotenv()

if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from attendance_agent.agent import AttendanceAgent
from attendance_agent.attendance import AttendanceService
from attendance_agent.config import settings
from attendance_agent.logger import logger

app = FastAPI(
    title="CampusOS Attendance AI Agent",
    description="SaaS Web UI API for Attendance AI Assistant",
    version="1.0.0",
)

# CORS middleware for development flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store for active agent instances per session_id
AGENT_CACHE: Dict[str, Dict[str, Any]] = {}
ATTENDANCE_CACHE: Dict[str, Dict[str, Any]] = {}


class StudentCredentials(BaseModel):
    student_name: str = Field(default="demo", description="Student Name")
    student_email: str = Field(default="demo@gmail.com", description="Student Email")
    college_id: int = Field(default=1, description="College ID")
    classroom_id: int = Field(default=6, description="Classroom ID")


class ChatRequest(BaseModel):
    session_id: str = Field(default="web-default-session")
    question: str = Field(..., description="User query about attendance")
    student_name: str = Field(default="demo")
    student_email: str = Field(default="demo@gmail.com")
    college_id: int = Field(default=1)
    classroom_id: int = Field(default=6)


class ResetChatRequest(BaseModel):
    session_id: str = Field(...)


class ForecastRequest(BaseModel):
    present: int = Field(..., ge=0)
    absent: int = Field(..., ge=0)
    target_percentage: float = Field(default=75.0, ge=1.0, le=100.0)


def get_cache_key(name: str, email: str, college_id: int, classroom_id: int) -> str:
    return f"{name.strip().lower()}:{email.strip().lower()}:{college_id}:{classroom_id}"


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Attendance AI SaaS Web Backend",
        "llm_model": settings.GROQ_MODEL or settings.GEMINI_MODEL,
        "supabase_configured": bool(settings.SUPABASE_URL and settings.SUPABASE_KEY),
    }


@app.get("/api/config")
async def get_default_config():
    """Returns default student profile and configuration metadata."""
    return {
        "default_student": {
            "name": "demo",
            "email": "demo@gmail.com",
            "college_id": 1,
            "classroom_id": 6,
        },
        "llm": {
            "groq_model": settings.GROQ_MODEL,
            "gemini_model": settings.GEMINI_MODEL,
            "active_provider": "Groq" if settings.GROQ_API_KEY else "Gemini",
        },
        "sample_queries": [
            "What is my overall attendance percentage?",
            "How many classes have I attended vs missed?",
            "Was I present or absent on March 20, 2026?",
            "Who was the teacher for the 01:00 - 02:00 slot on March 19?",
            "Show my attendance summary for March 2026",
            "What is my attendance status for this week?",
            "Am I above the 75% mandatory attendance criteria?",
        ],
    }


@app.post("/api/attendance")
async def get_student_attendance(creds: StudentCredentials):
    """Fetch complete attendance records for a student."""
    cache_key = get_cache_key(
        creds.student_name, creds.student_email, creds.college_id, creds.classroom_id
    )

    try:
        service = AttendanceService()
        data = service.get_attendance(
            student_name=creds.student_name.strip(),
            student_email=creds.student_email.strip(),
            college_id=creds.college_id,
            classroom_id=creds.classroom_id,
        )

        if not data.get("success"):
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "message": data.get("message", "Attendance records not found"),
                },
            )

        ATTENDANCE_CACHE[cache_key] = data
        return data

    except Exception as e:
        logger.exception("Error fetching attendance data")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"Server error: {str(e)}"},
        )


@app.post("/api/chat")
async def chat_with_agent(req: ChatRequest):
    """Send user query to the LangChain Attendance Agent."""
    student_key = get_cache_key(
        req.student_name, req.student_email, req.college_id, req.classroom_id
    )

    attendance_data = ATTENDANCE_CACHE.get(student_key)

    # If attendance is not cached, fetch it now
    if not attendance_data:
        try:
            service = AttendanceService()
            attendance_data = service.get_attendance(
                student_name=req.student_name.strip(),
                student_email=req.student_email.strip(),
                college_id=req.college_id,
                classroom_id=req.classroom_id,
            )
            if not attendance_data.get("success"):
                return JSONResponse(
                    status_code=400,
                    content={
                        "success": False,
                        "answer": f"Could not load attendance for {req.student_name}. Please verify student credentials.",
                    },
                )
            ATTENDANCE_CACHE[student_key] = attendance_data
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "answer": f"Error connecting to attendance service: {str(e)}",
                },
            )

    # Retrieve or initialize agent for session
    agent_info = AGENT_CACHE.get(req.session_id)
    if not agent_info or agent_info.get("student_key") != student_key:
        try:
            agent_instance = AttendanceAgent(
                attendance_data=attendance_data,
                session_id=req.session_id,
            )
            AGENT_CACHE[req.session_id] = {
                "agent": agent_instance,
                "student_key": student_key,
            }
        except Exception as e:
            logger.exception("Failed to initialize Attendance Agent")
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "answer": f"Could not initialize AI agent: {str(e)}",
                },
            )
    else:
        agent_instance = agent_info["agent"]
        # Update attendance data in case it changed
        agent_instance.attendance_data = attendance_data

    # Query the agent
    try:
        answer = agent_instance.ask(req.question)
        return {
            "success": True,
            "answer": answer,
            "session_id": req.session_id,
        }
    except Exception as e:
        logger.exception("Error executing agent query")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "answer": "Sorry, an error occurred while processing your attendance query.",
            },
        )


@app.post("/api/chat/reset")
async def reset_chat_session(req: ResetChatRequest):
    """Reset session chat memory."""
    if req.session_id in AGENT_CACHE:
        del AGENT_CACHE[req.session_id]
    return {"success": True, "message": f"Session {req.session_id} reset successfully"}


@app.post("/api/forecast")
async def calculate_forecast(req: ForecastRequest):
    """Calculate attendance projections, required classes, and safe bunk buffers."""
    present = req.present
    absent = req.absent
    marked = present + absent
    target = req.target_percentage

    current_pct = round((present / marked * 100), 2) if marked > 0 else 0.0

    classes_needed = 0
    if target < 100:
        numerator = (target * marked) - (100 * present)
        denominator = 100 - target
        if numerator > 0:
            import math
            classes_needed = math.ceil(numerator / denominator)
    elif target == 100:
        classes_needed = 0 if absent == 0 else -1

    safe_skips = 0
    if target > 0 and current_pct >= target:
        numerator_skip = (100 * present) - (target * marked)
        import math
        safe_skips = max(0, math.floor(numerator_skip / target))

    milestones = []
    for milestone_target in [75.0, 80.0, 85.0, 90.0, 95.0]:
        m_needed = 0
        if milestone_target < 100:
            num = (milestone_target * marked) - (100 * present)
            den = 100 - milestone_target
            if num > 0:
                import math
                m_needed = math.ceil(num / den)
        
        m_skips = 0
        if current_pct >= milestone_target:
            num_skip = (100 * present) - (milestone_target * marked)
            import math
            m_skips = max(0, math.floor(num_skip / milestone_target))

        milestones.append({
            "target": milestone_target,
            "status": "Achieved" if current_pct >= milestone_target else "Target",
            "classes_needed": m_needed,
            "safe_skips": m_skips,
        })

    return {
        "current_percentage": current_pct,
        "present": present,
        "absent": absent,
        "total_marked": marked,
        "target_percentage": target,
        "classes_needed_to_reach_target": classes_needed,
        "safe_skips_allowed": safe_skips,
        "milestones": milestones,
        "status_grade": (
            "Excellent" if current_pct >= 85 else
            "Good (Above Criteria)" if current_pct >= 75 else
            "Warning (At Risk)" if current_pct >= 65 else
            "Critical (Shortage)"
        ),
    }


@app.get("/api/analytics")
async def get_analytics(
    student_name: str = Query(default="demo"),
    student_email: str = Query(default="demo@gmail.com"),
    college_id: int = Query(default=1),
    classroom_id: int = Query(default=6),
):
    """Compute rich statistical analytics for charts and dashboard cards."""
    cache_key = get_cache_key(student_name, student_email, college_id, classroom_id)
    data = ATTENDANCE_CACHE.get(cache_key)

    if not data:
        service = AttendanceService()
        data = service.get_attendance(student_name, student_email, college_id, classroom_id)
        if data.get("success"):
            ATTENDANCE_CACHE[cache_key] = data

    if not data or not data.get("success"):
        raise HTTPException(status_code=404, detail="Student attendance data not found")

    attendance = data.get("attendance", {})
    summary = data.get("summary", {})

    teacher_stats: Dict[str, Dict[str, int]] = {}
    day_stats: Dict[str, Dict[str, int]] = {
        "Monday": {"present": 0, "absent": 0},
        "Tuesday": {"present": 0, "absent": 0},
        "Wednesday": {"present": 0, "absent": 0},
        "Thursday": {"present": 0, "absent": 0},
        "Friday": {"present": 0, "absent": 0},
        "Saturday": {"present": 0, "absent": 0},
        "Sunday": {"present": 0, "absent": 0},
    }
    monthly_stats: Dict[str, Dict[str, int]] = {}

    sorted_dates = sorted(attendance.keys())

    from datetime import datetime
    for date_str in sorted_dates:
        day_record = attendance[date_str]
        slots = day_record.get("slots", [])

        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            day_name = dt.strftime("%A")
            month_key = dt.strftime("%b %Y")
        except Exception:
            day_name = "Unknown"
            month_key = "Other"

        if month_key not in monthly_stats:
            monthly_stats[month_key] = {"present": 0, "absent": 0, "total": 0}

        for s in slots:
            status = s.get("status", "").lower()
            teacher = (s.get("teacher") or "Unassigned").strip()
            if not teacher or teacher == "-":
                teacher = "Unassigned"

            if teacher not in teacher_stats:
                teacher_stats[teacher] = {"present": 0, "absent": 0, "total": 0}

            if status == "present":
                teacher_stats[teacher]["present"] += 1
                teacher_stats[teacher]["total"] += 1
                monthly_stats[month_key]["present"] += 1
                monthly_stats[month_key]["total"] += 1
                if day_name in day_stats:
                    day_stats[day_name]["present"] += 1
            elif status == "absent":
                teacher_stats[teacher]["absent"] += 1
                teacher_stats[teacher]["total"] += 1
                monthly_stats[month_key]["absent"] += 1
                monthly_stats[month_key]["total"] += 1
                if day_name in day_stats:
                    day_stats[day_name]["absent"] += 1

    teachers_list = []
    for t_name, t_data in teacher_stats.items():
        total = t_data["total"]
        pct = round((t_data["present"] / total * 100), 1) if total > 0 else 0
        teachers_list.append({
            "teacher": t_name,
            "present": t_data["present"],
            "absent": t_data["absent"],
            "total": total,
            "percentage": pct,
        })
    teachers_list.sort(key=lambda x: x["total"], reverse=True)

    current_streak = 0
    max_present_streak = 0
    temp_streak = 0
    for d in sorted_dates:
        d_slots = attendance[d].get("slots", [])
        day_all_present = len(d_slots) > 0 and all(slot.get("status") == "present" for slot in d_slots)
        if day_all_present:
            temp_streak += 1
            max_present_streak = max(max_present_streak, temp_streak)
        else:
            temp_streak = 0

    for d in reversed(sorted_dates):
        d_slots = attendance[d].get("slots", [])
        if len(d_slots) > 0 and all(slot.get("status") == "present" for slot in d_slots):
            current_streak += 1
        else:
            break

    return {
        "summary": summary,
        "teachers": teachers_list,
        "day_of_week": day_stats,
        "monthly_trend": [
            {
                "month": m,
                "present": val["present"],
                "absent": val["absent"],
                "percentage": round(val["present"] / val["total"] * 100, 1) if val["total"] > 0 else 0,
            }
            for m, val in monthly_stats.items()
        ],
        "streaks": {
            "current_streak_days": current_streak,
            "max_present_streak_days": max_present_streak,
        },
        "total_days_recorded": len(attendance),
    }


# Static files mount
web_dir = Path(__file__).resolve().parent
css_dir = web_dir / "css"
js_dir = web_dir / "js"

css_dir.mkdir(parents=True, exist_ok=True)
js_dir.mkdir(parents=True, exist_ok=True)

app.mount("/css", StaticFiles(directory=str(css_dir)), name="css")
app.mount("/js", StaticFiles(directory=str(js_dir)), name="js")


@app.get("/")
async def serve_index():
    """Serves the single SaaS HTML application page."""
    index_file = web_dir / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="index.html not found in web directory")
    return FileResponse(str(index_file))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True, app_dir=str(web_dir))
