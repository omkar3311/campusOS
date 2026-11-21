import os
import re
import sys
import json
import shutil
import uuid
import logging
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv

from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from pydantic import BaseModel

# Add project src to sys.path so we can import resume_agent without modifying existing code
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
SRC_DIR = PROJECT_ROOT / "src"

load_dotenv(PROJECT_ROOT / ".env")
load_dotenv()

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from resume_agent.agent import ResumeAgent
from resume_agent.guardrails.guardrails import GuardrailViolation
from resume_agent.utils.ats_utils import ATSUtils
from resume_agent.utils.jd_utils import JDUtils

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger("web.app")

# Initialize FastAPI App
app = FastAPI(
    title="CampusOS ResumeIQ AI",
    description="Enterprise SaaS Platform for AI Resume Intelligence, ATS Scoring, Placement Eligibility & Career Advisory",
    version="2.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directories
STATIC_DIR = CURRENT_DIR / "static"
TEMPLATES_DIR = CURRENT_DIR / "templates"
UPLOADS_DIR = CURRENT_DIR / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
STATIC_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

# Mount static files & templates
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# User-scoped session storage to avoid cross-user resume/chat leakage.
USER_SESSION_AGENTS: dict[str, ResumeAgent] = {}
USER_SESSION_RESUME_META: dict[str, dict[str, dict]] = {}
USER_SESSION_INTERVIEWS: dict[str, dict] = {}
DEFAULT_SESSION_KEY = "career_agent:guest:user:guest"


def _normalize_session_fragment(value: Optional[str], fallback: str) -> str:
    cleaned = (value or fallback).strip()
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "_", cleaned)
    cleaned = cleaned.strip("_")
    return cleaned.lower() if cleaned else fallback.lower()


def build_session_key(
    role: Optional[str] = None,
    name: Optional[str] = None,
    user_id: Optional[str] = None,
    path: str = "career_agent",
) -> str:
    role_value = _normalize_session_fragment(role, "guest")
    name_value = _normalize_session_fragment(name, "user")
    user_value = _normalize_session_fragment(user_id, "guest")
    return f"{path}:{role_value}:{name_value}:{user_value}"


def resolve_session_key(request: Optional[Request] = None) -> str:
    if request is None:
        return DEFAULT_SESSION_KEY

    params = request.query_params
    role = params.get("role") or params.get("user_role") or "student"
    name = params.get("name") or params.get("username") or params.get("student_name") or "student"
    user_id = (
        params.get("user_id")
        or params.get("id")
        or params.get("student_id")
        or params.get("prn")
        or "guest"
    )
    return build_session_key(role=role, name=name, user_id=user_id, path="career_agent")


def get_session_storage(request: Optional[Request] = None):
    session_key = resolve_session_key(request)
    if session_key not in USER_SESSION_AGENTS:
        LOGGER.info("Initializing ResumeAgent instance for session %s", session_key)
        USER_SESSION_AGENTS[session_key] = ResumeAgent()
    if session_key not in USER_SESSION_RESUME_META:
        USER_SESSION_RESUME_META[session_key] = {}
    return session_key, USER_SESSION_AGENTS[session_key], USER_SESSION_RESUME_META[session_key]


def get_agent(request: Optional[Request] = None) -> ResumeAgent:
    _, agent, _ = get_session_storage(request)
    return agent


def get_loaded_resumes_meta(request: Optional[Request] = None) -> dict[str, dict]:
    _, _, meta = get_session_storage(request)
    return meta


# ---------------------------------------------------------
# Request / Response Schemas
# ---------------------------------------------------------
class ChatRequest(BaseModel):
    question: str
    job_description: Optional[str] = None
    mode: Optional[str] = None
    filename: Optional[str] = None


class ATSAuditRequest(BaseModel):
    filename: Optional[str] = None


class JDMatchRequest(BaseModel):
    job_description: str
    filename: Optional[str] = None


class CompareRequest(BaseModel):
    job_description: Optional[str] = None


class InterviewStartRequest(BaseModel):
    filename: Optional[str] = None
    role: Optional[str] = None
    interview_type: Optional[str] = "Mixed"
    difficulty: Optional[str] = "Intermediate"
    question_count: Optional[int] = 5
    job_description: Optional[str] = None


class InterviewAnswerRequest(BaseModel):
    session_id: str
    answer: str


class InterviewFinishRequest(BaseModel):
    session_id: str


# ---------------------------------------------------------
# UI Routes
# ---------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def serve_index(request: Request):
    """Serve the single-page SaaS dashboard."""
    return templates.TemplateResponse(
    request=request,
    name="index.html",
)


# ---------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------
@app.get("/api/status")
async def get_status(request: Request):
    """Get system status and catalog of loaded resumes."""
    _, agent, loaded_resumes_meta = get_session_storage(request)
    records = agent.tools_manager.loader.records()

    catalog = []
    for rid, rec in records.items():
        fn = rec.get("filename", "")
        catalog.append({
            "id": rid,
            "filename": fn,
            "candidate_name": rec.get("candidate_name", "Unknown Candidate"),
            "uploaded_at": loaded_resumes_meta.get(fn, {}).get("uploaded_at", "Active Session"),
            "size_bytes": loaded_resumes_meta.get(fn, {}).get("size_bytes", 0),
        })

    return {
        "status": "online",
        "total_resumes": len(catalog),
        "resumes": catalog,
        "modes": ResumeAgent.modes,
        "active_llm": "Groq Qwen-3.6-27B / Gemini Fallback"
    }


@app.post("/api/upload")
@app.post("/api/upload-resumes")
async def upload_resumes(request: Request, files: List[UploadFile] = File(...)):
    """Upload single or multiple resumes (PDF / DOCX) and index them."""
    _, agent, loaded_resumes_meta = get_session_storage(request)
    saved_paths = []

    for file in files:
        if not (file.filename.lower().endswith(".pdf") or file.filename.lower().endswith(".docx")):
            raise HTTPException(
                status_code=400,
                detail=f"File '{file.filename}' is not a supported format. Please upload PDF or DOCX."
            )
        
        dest_path = UPLOADS_DIR / file.filename
        with open(dest_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        saved_paths.append(str(dest_path))
        loaded_resumes_meta[file.filename] = {
            "uploaded_at": "Just now",
            "size_bytes": os.path.getsize(dest_path),
            "filepath": str(dest_path),
        }

    try:
        loaded, docs = agent.load_resume(saved_paths)
        records = agent.tools_manager.loader.records()
        catalog = []
        for rid, rec in records.items():
            fn = rec.get("filename", "")
            catalog.append({
                "id": rid,
                "filename": fn,
                "candidate_name": rec.get("candidate_name", "Unknown Candidate"),
                "uploaded_at": loaded_resumes_meta.get(fn, {}).get("uploaded_at", "Active Session"),
                "size_bytes": loaded_resumes_meta.get(fn, {}).get("size_bytes", 0),
            })

        return {
            "success": True,
            "message": f"Successfully indexed {len(loaded)} resume(s) into vector memory.",
            "loaded_files": loaded,
            "total_chunks": len(docs),
            "resumes": catalog,
        }
    except Exception as e:
        LOGGER.error(f"Error loading resumes: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/load-sample")
async def load_sample_resume(request: Request):
    """Load default workspace sample resume (e.g. omkar2.pdf) if available."""
    _, agent, loaded_resumes_meta = get_session_storage(request)
    sample_path = PROJECT_ROOT / "omkar2.pdf"
    
    if not sample_path.is_file():
        # Fallback to search any pdf in project root or data
        pdf_files = list(PROJECT_ROOT.glob("*.pdf")) + list((PROJECT_ROOT / "data").glob("*.pdf"))
        if pdf_files:
            sample_path = pdf_files[0]
        else:
            raise HTTPException(
                status_code=404, 
                detail="No sample PDF found in project root."
            )

    loaded_resumes_meta[sample_path.name] = {
        "uploaded_at": "Sample Demo",
        "size_bytes": sample_path.stat().st_size,
        "filepath": str(sample_path),
    }

    try:
        loaded, docs = agent.load_resume([str(sample_path)])
        return {
            "success": True,
            "message": f"Sample resume '{sample_path.name}' loaded successfully!",
            "loaded_files": loaded,
            "total_chunks": len(docs),
        }
    except Exception as e:
        LOGGER.error(f"Error loading sample resume: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat")
async def chat_with_agent(request: Request, payload: ChatRequest):
    """Interactive conversational agent with guardrails, memory, and tool integration."""
    _, agent, _ = get_session_storage(request)
    
    if not agent.tools_manager.loader.records():
        raise HTTPException(
            status_code=400,
            detail="Please upload or load at least one resume before querying the AI agent."
        )

    try:
        # Determine mode string
        mode = payload.mode
        if mode and mode.isdigit():
            mode = ResumeAgent.modes.get(mode, mode)

        # If specific filename is requested and multiple resumes are present, prepend context
        question = payload.question
        if payload.filename:
            question = f"[Focus on resume: {payload.filename}] {question}"

        answer = agent.ask(
            question=question,
            job_description=payload.job_description if payload.job_description and payload.job_description.strip() else None,
            mode=mode if mode else None,
        )

        inferred_mode_name = mode or agent.modes.get(agent._infer_mode(payload.question), "Resume Review Agent")

        return {
            "success": True,
            "answer": answer,
            "mode_used": inferred_mode_name,
            "guardrail_blocked": False,
        }

    except GuardrailViolation as e:
        LOGGER.warning(f"Guardrail violation: {e}")
        return {
            "success": False,
            "answer": f"**Guardrail Policy Notice**: {str(e)}",
            "mode_used": "Guardrail Filter",
            "guardrail_blocked": True,
        }
    except Exception as e:
        LOGGER.error(f"Chat processing error: {e}", exc_info=True)
        return {
            "success": False,
            "answer": f"An unexpected error occurred while analyzing the resume: {str(e)}",
            "mode_used": "System Error",
            "guardrail_blocked": False,
            "error_detail": str(e)
        }


@app.post("/api/ats-audit")
async def ats_audit(request: Request, payload: ATSAuditRequest):
    """Run comprehensive ATS structural & content scoring."""
    _, agent, _ = get_session_storage(request)
    
    if not agent.tools_manager.loader.records():
        raise HTTPException(
            status_code=400,
            detail="No resumes loaded. Please upload a resume first."
        )

    filename = payload.filename
    records = agent.tools_manager.loader.records()
    
    if not filename and records:
        filename = next(iter(records.values()))["filename"]

    try:
        ats_result = agent.tools_manager._ats_result(filename)
        
        # Calculate grade
        score = ats_result.get("ats_score", 0)
        if score >= 90:
            grade = "A+"
            grade_label = "Exceptional ATS Optimization"
            grade_color = "emerald"
        elif score >= 75:
            grade = "A"
            grade_label = "Strong ATS Compliance"
            grade_color = "teal"
        elif score >= 60:
            grade = "B"
            grade_label = "Acceptable — Minor Gaps"
            grade_color = "blue"
        elif score >= 45:
            grade = "C"
            grade_label = "Needs Structural Improvement"
            grade_color = "amber"
        else:
            grade = "D"
            grade_label = "Significant ATS Red Flags"
            grade_color = "rose"

        ats_result["grade"] = grade
        ats_result["grade_label"] = grade_label
        ats_result["grade_color"] = grade_color
        
        # Check contact details
        evidence = ats_result.get("evidence", "")
        ats_result["has_email"] = bool(agent.tools_manager.ats.has_email(evidence))
        ats_result["has_phone"] = bool(agent.tools_manager.ats.has_phone(evidence))
        ats_result["graduation_year"] = agent.tools_manager.ats.graduation_year(evidence)
        
        return {
            "success": True,
            "data": ats_result
        }

    except Exception as e:
        LOGGER.error(f"ATS audit error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/jd-match")
async def jd_match(request: Request, payload: JDMatchRequest):
    """Run instant Job Description matching, skill gap analysis, and placement eligibility."""
    _, agent, _ = get_session_storage(request)
    
    if not agent.tools_manager.loader.records():
        raise HTTPException(
            status_code=400,
            detail="No resumes loaded. Please upload a resume first."
        )

    if not payload.job_description or not payload.job_description.strip():
        raise HTTPException(
            status_code=400,
            detail="Job description cannot be empty."
        )

    filename = payload.filename
    records = agent.tools_manager.loader.records()
    if not filename and records:
        filename = next(iter(records.values()))["filename"]

    try:
        jd_result = agent.tools_manager.jd._jd_result(
            payload.job_description,
            filename=filename
        )
        
        score = jd_result["final_match"]
        if score >= 70:
            eligibility = "Eligible"
            eligibility_badge = "success"
            eligibility_desc = "Candidate demonstrates high competency match with the targeted job requirements."
        elif score >= 40:
            eligibility = "Borderline"
            eligibility_badge = "warning"
            eligibility_desc = "Candidate meets foundational criteria but exhibits notable skill gaps for key requirements."
        else:
            eligibility = "Not Eligible"
            eligibility_badge = "danger"
            eligibility_desc = "Candidate's current profile lacks several mandatory skills specified in the job description."

        jd_result["eligibility"] = eligibility
        jd_result["eligibility_badge"] = eligibility_badge
        jd_result["eligibility_desc"] = eligibility_desc

        return {
            "success": True,
            "data": jd_result
        }

    except Exception as e:
        LOGGER.error(f"JD Match error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/compare-resumes")
async def compare_resumes(request: Request, payload: CompareRequest):
    """Rank and compare all loaded candidate resumes against a JD or ATS benchmarks."""
    _, agent, _ = get_session_storage(request)
    records = agent.tools_manager.loader.records()
    
    if not records:
        raise HTTPException(
            status_code=400,
            detail="No resumes loaded. Please upload resumes to compare."
        )

    try:
        jd_text = payload.job_description.strip() if payload.job_description else ""
        ranked = []

        for record in records.values():
            fn = record["filename"]
            cname = record["candidate_name"]

            if jd_text:
                res = agent.tools_manager.jd._jd_result(jd_text, fn)
                score = res.get("final_match", 0)
                skills_match = res.get("skills_match", 0)
                matched_skills = res.get("matched_skills", [])
                missing_skills = res.get("missing_skills", [])
                verdict = res.get("verdict", "")
            else:
                res = agent.tools_manager._ats_result(fn)
                score = res.get("ats_score", 0)
                skills_match = score
                matched_skills = res.get("detected_sections", [])
                missing_skills = res.get("missing_sections", [])
                verdict = "ATS Baseline"

            ranked.append({
                "filename": fn,
                "candidate_name": cname,
                "score": score,
                "skills_match": skills_match,
                "matched_count": len(matched_skills),
                "matched_sample": matched_skills[:6],
                "missing_count": len(missing_skills),
                "missing_sample": missing_skills[:6],
                "verdict": verdict,
                "is_jd_match": bool(jd_text),
            })

        ranked.sort(key=lambda x: x["score"], reverse=True)
        
        # Assign leaderboard ranks
        for idx, item in enumerate(ranked):
            item["rank"] = idx + 1

        return {
            "success": True,
            "total_compared": len(ranked),
            "ranking": ranked,
            "has_jd": bool(jd_text)
        }

    except Exception as e:
        LOGGER.error(f"Compare error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/interview/start")
async def start_interview(request: Request, payload: InterviewStartRequest):
    """Create a resume-grounded interview session and generate its question set."""
    session_key, agent, _ = get_session_storage(request)
    records = agent.tools_manager.loader.records()
    if not records:
        raise HTTPException(status_code=400, detail="Upload or load a resume before starting an interview.")

    filename = payload.filename
    if filename:
        if not any(rec.get("filename") == filename for rec in records.values()):
            raise HTTPException(status_code=404, detail="Selected resume was not found.")
    else:
        filename = next(iter(records.values()))["filename"]

    count = max(3, min(int(payload.question_count or 5), 8))
    role = (payload.role or "the target role").strip()
    interview_type = (payload.interview_type or "Mixed").strip()
    difficulty = (payload.difficulty or "Intermediate").strip()

    selected = agent.tools_manager.loader.records()
    candidate_name = "Candidate"
    for rec in selected.values():
        if rec.get("filename") == filename:
            candidate_name = rec.get("candidate_name", "Candidate")
            break

    generation_prompt = (
        f"Create exactly {count} {difficulty.lower()} {interview_type.lower()} interview questions "
        f"for {candidate_name} applying for {role}. Use only facts from the selected resume. "
        "Return strict JSON with this shape: {\"questions\":[{\"question\":\"...\",\"category\":\"Technical|Behavioral|Project|Role\",\"focus\":\"...\",\"time_seconds\":60}]}. "
        "Ask about specific projects, technologies, achievements, or experiences visible in the resume. "
        "Do not add any text outside the JSON."
    )

    try:
        raw = agent.ask(
            question=generation_prompt,
            job_description=payload.job_description,
            mode="4",
        )
        match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        data = json.loads(match.group(0)) if match else {"questions": []}
        questions = data.get("questions", [])
    except Exception as exc:
        LOGGER.warning("Interview question generation fallback used: %s", exc)
        questions = []

    if not questions:
        questions = [
            {"question": "Walk me through the strongest project on your resume and explain your specific contribution.", "category": "Project", "focus": "Project depth", "time_seconds": 90},
            {"question": "Which technology from your resume has been most valuable to you, and why?", "category": "Technical", "focus": "Technical confidence", "time_seconds": 60},
            {"question": "Describe a challenge you faced in a project and how you solved it.", "category": "Behavioral", "focus": "Problem solving", "time_seconds": 75},
            {"question": "How would you explain your experience to someone who is not familiar with the domain?", "category": "Behavioral", "focus": "Communication", "time_seconds": 60},
            {"question": "Which skill would you prioritize improving for this role, and what is your plan?", "category": "Role", "focus": "Self-awareness", "time_seconds": 60},
        ]

    questions = questions[:count]
    session_id = uuid.uuid4().hex
    interview = {
        "session_id": session_id,
        "filename": filename,
        "candidate_name": candidate_name,
        "role": role,
        "interview_type": interview_type,
        "difficulty": difficulty,
        "questions": questions,
        "current_index": 0,
        "answers": [],
        "finished": False,
    }
    USER_SESSION_INTERVIEWS.setdefault(session_key, {})[session_id] = interview

    return {"success": True, "session_id": session_id, "candidate_name": candidate_name, "question": questions[0], "question_index": 0, "total_questions": len(questions)}


@app.post("/api/interview/answer")
async def submit_interview_answer(request: Request, payload: InterviewAnswerRequest):
    """Evaluate one spoken or written answer and advance the interview."""
    session_key, agent, _ = get_session_storage(request)
    interview = USER_SESSION_INTERVIEWS.get(session_key, {}).get(payload.session_id)
    if not interview:
        raise HTTPException(status_code=404, detail="Interview session not found.")
    if interview["finished"]:
        raise HTTPException(status_code=400, detail="This interview has already finished.")

    index = interview["current_index"]
    question = interview["questions"][index]
    answer = payload.answer.strip()
    if not answer:
        raise HTTPException(status_code=400, detail="Answer cannot be empty.")

    evaluation_prompt = (
        "Evaluate this mock interview answer. Be fair, interview-oriented, and grounded in the resume. "
        f"Question: {question.get('question')}\nCandidate answer: {answer}\n"
        "Return strict JSON: {\"score\":0-100,\"strengths\":[\"...\"],\"improvements\":[\"...\"],\"ideal_points\":[\"...\"],\"summary\":\"...\"}. "
        "Do not mention information not present in the resume. Do not add text outside JSON."
    )

    try:
        raw = agent.ask(evaluation_prompt, mode="4")
        match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        evaluation = json.loads(match.group(0)) if match else {}
        score = max(0, min(int(evaluation.get("score", 50)), 100))
    except Exception:
        score = 50
        evaluation = {
            "score": score,
            "strengths": ["The answer was presented clearly enough to assess."],
            "improvements": ["Add concrete evidence, examples, and measurable outcomes."],
            "ideal_points": ["Explain the situation, your action, and the result."],
            "summary": "Your answer has potential but needs more resume-grounded specifics.",
        }

    record = {"question": question, "answer": answer, "evaluation": evaluation | {"score": score}}
    interview["answers"].append(record)
    interview["current_index"] += 1

    has_next = interview["current_index"] < len(interview["questions"])
    next_question = interview["questions"][interview["current_index"]] if has_next else None

    return {
        "success": True,
        "evaluation": record["evaluation"],
        "has_next": has_next,
        "question": next_question,
        "question_index": interview["current_index"],
        "total_questions": len(interview["questions"]),
    }


@app.post("/api/interview/finish")
async def finish_interview(request: Request, payload: InterviewFinishRequest):
    """Calculate final interview performance and provide a hiring-style report."""
    session_key, _, _ = get_session_storage(request)
    interview = USER_SESSION_INTERVIEWS.get(session_key, {}).get(payload.session_id)
    if not interview:
        raise HTTPException(status_code=404, detail="Interview session not found.")

    interview["finished"] = True
    scores = [item["evaluation"].get("score", 0) for item in interview["answers"]]
    overall = round(sum(scores) / len(scores)) if scores else 0

    category_scores = {}
    for item in interview["answers"]:
        category = item["question"].get("category", "General")
        category_scores.setdefault(category, []).append(item["evaluation"].get("score", 0))
    category_scores = {key: round(sum(values) / len(values)) for key, values in category_scores.items()}

    return {
        "success": True,
        "candidate_name": interview["candidate_name"],
        "role": interview["role"],
        "overall_score": overall,
        "category_scores": category_scores,
        "answered": len(interview["answers"]),
        "total_questions": len(interview["questions"]),
        "responses": interview["answers"],
    }


@app.post("/api/reset-session")
async def reset_session(request: Request):
    """Reset conversational session memory."""
    _, agent, _ = get_session_storage(request)
    agent.tools_manager.session_memory = agent.tools_manager.session_memory.__class__()
    return {"success": True, "message": "Session conversation memory has been reset."}


@app.get("/api/resume-details")
async def resume_details(request: Request, filename: Optional[str] = Query(None)):
    """Retrieve extracted structured details, sections, and profile memory for a resume."""
    _, agent, _ = get_session_storage(request)
    records = agent.tools_manager.loader.records()
    if not records:
        raise HTTPException(status_code=400, detail="No resumes loaded.")

    selected_rec = None
    if filename:
        selected_rec = next((rec for rec in records.values() if rec.get("filename") == filename), None)
    if not selected_rec:
        selected_rec = next(iter(records.values()))

    fn = selected_rec.get("filename", "")
    cname = selected_rec.get("candidate_name", "Unknown")
    raw_text = selected_rec.get("text", "")
    profile = agent.tools_manager.profile_memory.get_profile(cname)
    sections = agent.tools_manager.ats.section_maker(raw_text)

    return {
        "success": True,
        "filename": fn,
        "candidate_name": cname,
        "profile_summary": profile or "No profile memory generated yet.",
        "word_count": len(raw_text.split()),
        "char_count": len(raw_text),
        "detected_sections": {k: len(v) for k, v in sections.items()},
        "raw_text_preview": raw_text[:2500] + ("..." if len(raw_text) > 2500 else ""),
    }


# ---------------------------------------------------------
# Application Entry Point      uv run uvicorn web.app:app --reload
# ---------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("web.app:app", host="0.0.0.0", port=8000, reload=True)
