import os
import sys
import shutil
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

# Singleton ResumeAgent instance
agent_instance: Optional[ResumeAgent] = None
loaded_resumes_meta: dict[str, dict] = {}


def get_agent() -> ResumeAgent:
    global agent_instance
    if agent_instance is None:
        LOGGER.info("Initializing ResumeAgent instance...")
        agent_instance = ResumeAgent()
    return agent_instance


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
async def get_status():
    """Get system status and catalog of loaded resumes."""
    agent = get_agent()
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
async def upload_resumes(files: List[UploadFile] = File(...)):
    """Upload single or multiple resumes (PDF / DOCX) and index them."""
    agent = get_agent()
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
        return {
            "success": True,
            "message": f"Successfully indexed {len(loaded)} resume(s) into vector memory.",
            "loaded_files": loaded,
            "total_chunks": len(docs),
        }
    except Exception as e:
        LOGGER.error(f"Error loading resumes: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/load-sample")
async def load_sample_resume():
    """Load default workspace sample resume (e.g. omkar2.pdf) if available."""
    agent = get_agent()
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
async def chat_with_agent(payload: ChatRequest):
    """Interactive conversational agent with guardrails, memory, and tool integration."""
    agent = get_agent()
    
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
async def ats_audit(payload: ATSAuditRequest):
    """Run comprehensive ATS structural & content scoring."""
    agent = get_agent()
    
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
async def jd_match(payload: JDMatchRequest):
    """Run instant Job Description matching, skill gap analysis, and placement eligibility."""
    agent = get_agent()
    
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
async def compare_resumes(payload: CompareRequest):
    """Rank and compare all loaded candidate resumes against a JD or ATS benchmarks."""
    agent = get_agent()
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


@app.get("/api/resume-details")
async def resume_details(filename: Optional[str] = Query(None)):
    """Retrieve extracted structured details, sections, and profile memory for a resume."""
    agent = get_agent()
    records = agent.tools_manager.loader.records()
    
    if not records:
        raise HTTPException(status_code=400, detail="No resumes loaded.")

    selected_rec = None
    if filename:
        for rec in records.values():
            if rec.get("filename") == filename:
                selected_rec = rec
                break
    
    if not selected_rec and records:
        selected_rec = next(iter(records.values()))

    if not selected_rec:
        raise HTTPException(status_code=404, detail="Resume not found.")

    fn = selected_rec.get("filename", "")
    cname = selected_rec.get("candidate_name", "Unknown")
    raw_text = selected_rec.get("text", "")
    
    # Get Profile memory
    profile = agent.tools_manager.profile_memory.get_profile(cname)
    
    # Sections breakdown
    sections = agent.tools_manager.ats.section_maker(raw_text)
    
    return {
        "success": True,
        "filename": fn,
        "candidate_name": cname,
        "profile_summary": profile or "No profile memory generated yet.",
        "word_count": len(raw_text.split()),
        "char_count": len(raw_text),
        "detected_sections": {
            k: len(v) for k, v in sections.items()
        },
        "raw_text_preview": raw_text[:2500] + ("..." if len(raw_text) > 2500 else "")
    }


@app.post("/api/reset-session")
async def reset_session():
    """Reset conversational session memory."""
    agent = get_agent()
    agent.tools_manager.session_memory = agent.tools_manager.session_memory.__class__()
    return {"success": True, "message": "Session conversation memory has been reset."}


# ---------------------------------------------------------
# Application Entry Point      uv run uvicorn web.app:app --reload
# ---------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("web.app:app", host="0.0.0.0", port=8000, reload=True)
