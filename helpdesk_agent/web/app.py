from __future__ import annotations

import os
import time
import json
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Setup paths
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
STATIC_DIR = BASE_DIR / "static"

# Load environment variables
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv()
TEMPLATES_DIR = BASE_DIR / "templates"
DOCS_DIR = PROJECT_ROOT / "data" / "documents"

# Logger
logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger("campusos.ai")

# Import helpdesk agent internals
from helpdesk_agent.agent import HelpdeskGraph
from helpdesk_agent.guardrails import GuardrailViolation
from helpdesk_agent.retrieval import VectorStore
from helpdesk_agent.config import get_settings

# Initialize FastAPI App
app = FastAPI(
    title="CampusOS AI Helpdesk",
    description="Enterprise Campus Intelligence & Virtual Assistant Platform",
    version="2.4.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Static Files and Templates
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Singleton instances cache
_graph_instance: Optional[HelpdeskGraph] = None
_vector_store_instance: Optional[VectorStore] = None


def get_graph() -> HelpdeskGraph:
    global _graph_instance
    if _graph_instance is None:
        LOGGER.info("Initializing CampusOS LangGraph Engine...")
        _graph_instance = HelpdeskGraph()
    return _graph_instance


def get_vector_store() -> VectorStore:
    global _vector_store_instance
    if _vector_store_instance is None:
        _vector_store_instance = VectorStore()
    return _vector_store_instance


# ---------------------------------------------------------------------------
# Request/Response Models
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    question: str
    session_id: Optional[str] = "default"


class ChatResponse(BaseModel):
    answer: str
    sources: List[str] = []
    session_id: str
    latency_ms: float
    status: str
    error: Optional[str] = None
    timestamp: str


# ---------------------------------------------------------------------------
# Core Web Application Route
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def serve_app(request: Request):
    """Renders the single SaaS application interface."""
    return templates.TemplateResponse(request=request, name="index.html")


# ---------------------------------------------------------------------------
# Chat API Endpoint
# ---------------------------------------------------------------------------

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(payload: ChatRequest):
    """Processes user queries through LangGraph RAG with guardrails and citations."""
    start_time = time.time()
    session_id = (payload.session_id or "default").strip()
    question = payload.question.strip()

    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    try:
        graph = get_graph()
        result = graph.invoke(question=question, session_id=session_id)
        
        answer = result.get("answer", "I could not locate specific details in the college knowledge base.")
        
        # Clean unique source references
        raw_sources = result.get("sources", [])
        clean_sources = []
        for s in raw_sources:
            # Clean path to basename
            s_clean = s.replace(str(DOCS_DIR) + "/", "").replace(str(PROJECT_ROOT) + "/", "")
            if s_clean not in clean_sources:
                clean_sources.append(s_clean)

        latency_ms = round((time.time() - start_time) * 1000, 2)

        return ChatResponse(
            answer=answer,
            sources=clean_sources,
            session_id=session_id,
            latency_ms=latency_ms,
            status="success",
            timestamp=datetime.now().isoformat()
        )

    except GuardrailViolation as exc:
        latency_ms = round((time.time() - start_time) * 1000, 2)
        LOGGER.warning("Guardrail blocked request: %s", exc)
        return ChatResponse(
            answer=str(exc),
            sources=[],
            session_id=session_id,
            latency_ms=latency_ms,
            status="guardrail_blocked",
            error=str(exc),
            timestamp=datetime.now().isoformat()
        )

    except Exception as exc:
        LOGGER.exception("Error processing chat: %s", exc)
        latency_ms = round((time.time() - start_time) * 1000, 2)
        return ChatResponse(
            answer="I encountered an unexpected issue while processing your question. Please rephrase or try again in a moment.",
            sources=[],
            session_id=session_id,
            latency_ms=latency_ms,
            status="error",
            error=str(exc),
            timestamp=datetime.now().isoformat()
        )


# ---------------------------------------------------------------------------
# Info & Health
# ---------------------------------------------------------------------------

@app.get("/api/info")
async def get_info():
    """Returns platform metadata and status."""
    settings = get_settings()
    vs = get_vector_store()
    return {
        "name": "CampusOS AI Helpdesk",
        "version": "2.4.0",
        "model": "Qwen 3.6 27B (Groq Enterprise) • Gemini 2.5 Backup",
        "collection": settings.chroma_collection,
        "indexed_chunks": vs.count(),
        "status": "operational"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("web.app:app", host="0.0.0.0", port=8000, reload=True)
