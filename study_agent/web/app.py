import os
import re
import sys
import json
import uuid
import shutil
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# Ensure 'src' is available in Python path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"

load_dotenv(PROJECT_ROOT / ".env")
load_dotenv()

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from study_agent.config import settings
from study_agent.logger import LOGGER
from study_agent.pipeline import RAGPipeline
from study_agent.ingestion.loader import PDFLoader
from study_agent.ingestion.splitter import DocumentSplitter
from langchain_core.documents import Document

# Directories
WEB_DIR = Path(__file__).resolve().parent
STATIC_DIR = WEB_DIR / "static"
TEMPLATES_DIR = WEB_DIR / "templates"
DATA_DIR = settings.data_dir
UPLOADS_DIR = DATA_DIR / "documents"
DOCS_REGISTRY_FILE = DATA_DIR / "documents_registry.json"

STATIC_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

# Global pipeline instance
rag_pipeline: Optional[RAGPipeline] = None


def get_pipeline() -> RAGPipeline:
    global rag_pipeline
    if rag_pipeline is None:
        LOGGER.info("Lazy initializing RAG Pipeline...")
        rag_pipeline = RAGPipeline()
        LOGGER.info("RAG Pipeline ready.")
    return rag_pipeline


# ============================================================================
# Response Sanitizer (Clean any thought / meta-reasoning preambles)
# ============================================================================

def clean_llm_response(text: str) -> str:
    """Clean out <think> tags, internal reasoning, and meta-commentary preambles."""
    if not text:
        return ""
    
    cleaned = text.strip()

    # 1. Remove closed <think>...</think> tags
    cleaned = re.sub(r'<think>.*?</think>', '', cleaned, flags=re.DOTALL).strip()

    # 2. If unclosed <think> tag remains, extract the actual answer
    if '<think>' in cleaned:
        parts = cleaned.split('<think>', 1)
        after_think = parts[1] if len(parts) > 1 else ""
        match = re.search(r'(\n\s*(?:#|\*\*|Based on|According to|Here is|The following|1\.|-)\s*.*)', after_think, flags=re.DOTALL)
        if match:
            cleaned = match.group(1).strip()
        else:
            cleaned = parts[0].strip()

    # 3. Strip raw reasoning preambles if any
    cleaned = re.sub(r"^(?:Here's a thinking process:[\s\S]*?(?=\n\s*(?:#|\*\*|Based on|According to|Here is|The |1\.)))", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"^(?:Thought Process:|Thinking Process:|Reasoning:)\s*", "", cleaned, flags=re.IGNORECASE).strip()

    # 4. Unwrap quotes if the whole text is enclosed in quotation marks
    if (cleaned.startswith('"') and cleaned.endswith('"')) or (cleaned.startswith('“') and cleaned.endswith('”')):
        cleaned = cleaned[1:-1].strip()

    # 5. Remove common meta-reasoning preambles
    unwanted_prefixes = [
        r"^I am thinking.*?\n\n",
        r"^Thinking Process:.*?\n\n",
        r"^Here is what I should do:.*?\n\n",
        r"^Let me determine the task.*?\n\n",
        r"^Task Classification:.*?\n\n",
        r"^\[Study Planning Request\]\s*",
        r"^\[Assignment Help Request\]\s*",
        r"^\[Quiz Generation Request\]\s*"
    ]
    for pattern in unwanted_prefixes:
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE | re.DOTALL).strip()

    return cleaned if cleaned else text.strip()



# ============================================================================
# Document Registry Helpers (Empty by default until user uploads or loads sample)
# ============================================================================

def load_docs_registry() -> List[Dict[str, Any]]:
    if not DOCS_REGISTRY_FILE.exists():
        return []
    try:
        data = json.loads(DOCS_REGISTRY_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        LOGGER.exception("Failed to load docs registry")
        return []


def save_docs_registry(registry: List[Dict[str, Any]]):
    try:
        DOCS_REGISTRY_FILE.write_text(json.dumps(registry, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        LOGGER.exception("Failed to save docs registry")


def clear_all_documents_and_memory():
    """Wipes all uploaded study documents, clears vector store, and clears chat session memory."""
    global rag_pipeline
    try:
        DOCS_REGISTRY_FILE.write_text("[]", encoding="utf-8")
        if UPLOADS_DIR.exists():
            for f in UPLOADS_DIR.glob("*"):
                if f.is_file():
                    try:
                        f.unlink()
                    except Exception:
                        pass
        chroma_dir = settings.db_dir
        if chroma_dir.exists():
            try:
                shutil.rmtree(chroma_dir, ignore_errors=True)
                chroma_dir.mkdir(parents=True, exist_ok=True)
            except Exception:
                LOGGER.exception("Failed to wipe chroma db directory")
        if rag_pipeline:
            try:
                rag_pipeline.clear_memory()
            except Exception:
                pass
            rag_pipeline = None
    except Exception:
        LOGGER.exception("Error in clear_all_documents_and_memory")


# In-memory sessions store (temporary per visit)
IN_MEMORY_SESSIONS: Dict[str, Any] = {}


# ============================================================================
# Lifespan
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    LOGGER.info("StudyAgent SaaS Web Server starting...")
    clear_all_documents_and_memory()
    asyncio.create_task(asyncio.to_thread(get_pipeline))
    yield
    LOGGER.info("StudyAgent SaaS Web Server shutting down.")


app = FastAPI(
    title="CampusOS StudyAgent SaaS",
    description="Modern AI-Powered Academic Assistant Grounded in Uploaded Study Materials",
    version="2.5.0",
    lifespan=lifespan
)

# Mount Static Files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
if (STATIC_DIR / "css").exists():
    app.mount("/css", StaticFiles(directory=str(STATIC_DIR / "css")), name="css")
if (STATIC_DIR / "js").exists():
    app.mount("/js", StaticFiles(directory=str(STATIC_DIR / "js")), name="js")


# ============================================================================
# Request / Response Models
# ============================================================================

class ChatRequest(BaseModel):
    session_id: Optional[str] = Field(None, description="Active session ID")
    message: str = Field(..., min_length=1, max_length=10000, description="User query")
    mode: Optional[str] = Field("auto", description="Mode: 'auto', 'concept', 'plan', 'assignment', 'quiz', 'cram'")
    topic: Optional[str] = Field(None, description="Optional focused chapter or topic")
    filename: Optional[str] = Field(None, description="Active document filename")
    user_id: Optional[str] = Field(None, description="Student/User identifier")


class PlannerRequest(BaseModel):
    topic: Optional[str] = None
    days: Optional[int] = 7
    hours_per_day: Optional[int] = 3
    filename: Optional[str] = None


class QuizRequest(BaseModel):
    topic: Optional[str] = None
    question_count: Optional[int] = 5
    difficulty: Optional[str] = "Medium"
    filename: Optional[str] = None


class FlashcardRequest(BaseModel):
    topic: Optional[str] = None
    count: Optional[int] = 6
    filename: Optional[str] = None


# ============================================================================
# UI Endpoint
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def serve_ui(request: Request):
    """Serve the single-page SaaS interface."""
    index_file = TEMPLATES_DIR / "index.html"
    return HTMLResponse(content=index_file.read_text(encoding="utf-8"))


# ============================================================================
# System Status & Catalog
# ============================================================================

@app.get("/api/status")
@app.get("/api/catalog")
async def get_catalog():
    """Returns platform metadata, registered documents, and indexing status."""
    registry = load_docs_registry()
    total_chunks = sum(doc.get("chunks", 0) for doc in registry)
    total_size_mb = round(sum(doc.get("size_mb", 0) for doc in registry), 2)
    
    return {
        "status": "online",
        "total_documents": len(registry),
        "total_chunks": total_chunks,
        "total_size_mb": total_size_mb,
        "documents": registry,
        "active_document": registry[0]["filename"] if registry else None,
        "modes": {
            "auto": "Auto-Infer Mode",
            "concept": "Concept Explainer",
            "plan": "Study Planner & Roadmap",
            "assignment": "Assignment Helper",
            "quiz": "Quiz & MCQ Generator",
            "cram": "Exam Crammer & Summary"
        }
    }


# ============================================================================
# Documents & Upload Management (Requires uploaded file before answering)
# ============================================================================

@app.get("/api/documents")
async def list_documents():
    """List all indexed study documents with chunk statistics."""
    registry = load_docs_registry()
    total_chunks = sum(doc.get("chunks", 0) for doc in registry)
    total_size_mb = round(sum(doc.get("size_mb", 0) for doc in registry), 2)

    return {
        "status": "success",
        "documents": registry,
        "stats": {
            "total_documents": len(registry),
            "total_chunks": total_chunks,
            "total_size_mb": total_size_mb
        }
    }


@app.post("/api/documents/upload")
@app.post("/api/upload")
async def upload_documents(files: List[UploadFile] = File(...)):
    """Upload study files (PDF, TXT, MD), index into Vector DB."""
    if not files:
        raise HTTPException(status_code=400, detail="No files provided for upload.")

    registry = load_docs_registry()
    pipeline = get_pipeline()
    splitter = DocumentSplitter()

    uploaded_results = []
    total_new_chunks = 0

    for upload in files:
        original_filename = upload.filename
        if not original_filename:
            continue
        
        file_ext = Path(original_filename).suffix.lower()
        if file_ext not in [".pdf", ".txt", ".text", ".md", ".markdown", ".json", ".csv", ".py", ".docx"]:
            continue

        file_id = f"doc_{int(datetime.now().timestamp()*1000)}_{uuid.uuid4().hex[:6]}"
        safe_filename = f"{Path(original_filename).stem}_{uuid.uuid4().hex[:4]}{file_ext}"
        save_path = UPLOADS_DIR / safe_filename
        
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(upload.file, buffer)

        size_mb = round(save_path.stat().st_size / (1024 * 1024), 2)

        raw_docs: List[Document] = []
        page_count = 1

        try:
            if file_ext == ".pdf":
                loader = PDFLoader()
                raw_docs = loader.load(save_path)
                page_count = len(raw_docs)
            else:
                content = ""
                for enc in ("utf-8", "latin-1", "cp1252"):
                    try:
                        content = save_path.read_text(encoding=enc)
                        break
                    except UnicodeDecodeError:
                        continue
                
                if content.strip():
                    raw_docs = [
                        Document(
                            page_content=content,
                            metadata={
                                "source": str(save_path),
                                "filename": original_filename,
                                "page": 1,
                                "total_pages": 1
                            }
                        )
                    ]

            if not raw_docs:
                LOGGER.warning("No extractable content from file %s", original_filename)
                continue

            chunks = splitter.split(raw_docs)
            if not chunks:
                continue

            for chunk in chunks:
                chunk.metadata["doc_id"] = file_id
                chunk.metadata["filename"] = original_filename
                chunk.metadata["source"] = str(save_path)

            pipeline.vectorstore.add_documents(chunks)

            total_new_chunks += len(chunks)

            doc_entry = {
                "id": file_id,
                "filename": original_filename,
                "saved_as": safe_filename,
                "path": str(save_path),
                "size_mb": size_mb,
                "chunks": len(chunks),
                "pages": page_count,
                "uploaded_at": datetime.now().strftime("%b %d, %Y %I:%M %p")
            }
            registry.append(doc_entry)
            uploaded_results.append(doc_entry)

        except Exception as exc:
            LOGGER.exception("Failed to process uploaded file: %s", original_filename)
            continue

    save_docs_registry(registry)

    return {
        "status": "success",
        "uploaded_count": len(uploaded_results),
        "total_new_chunks": total_new_chunks,
        "documents": uploaded_results
    }


@app.post("/api/load-sample")
async def load_sample_document():
    """1-Click loads demo study material for instant testing."""
    registry = load_docs_registry()
    sample_name = "Computer_Science_AI_Fundamentals.txt"
    
    # Check if already present
    existing = next((d for d in registry if d.get("filename") == sample_name), None)
    if existing:
        return {"status": "success", "success": True, "message": "Demo study material is already loaded.", "document": existing}

    sample_content = """# Computer Science & AI Systems Fundamentals

## Chapter 1: Data Structures and Algorithms
A Data Structure is a specialized format for organizing, processing, retrieving, and storing data.
- **Arrays**: Fixed-size sequential collection of elements with O(1) random access by index.
- **Linked Lists**: Sequence of nodes where each node contains data and a pointer to the next node. Insertion and deletion are O(1) at the head, O(n) traversal.
- **Hash Tables**: Key-value mapping utilizing a hash function. Average case lookup, insertion, and deletion are O(1); worst-case O(n) under high collision.
- **Binary Search Trees (BST)**: Tree data structure where left child < root < right child. Average lookup is O(log n); worst-case unbalanced is O(n).
- **Graph Algorithms**: BFS (Breadth-First Search) using queues for shortest unweighted path; DFS (Depth-First Search) using recursion/stacks for topological sort.
- **Time Complexity & Big-O**:
  - Binary Search: O(log n)
  - QuickSort / MergeSort: O(n log n)
  - Dijkstra's Algorithm: O((V + E) log V) with priority queues.

## Chapter 2: Database Systems & Normalization
Relational Database Management Systems (RDBMS) maintain structured data with ACID guarantees (Atomicity, Consistency, Isolation, Durability).
- **1NF (First Normal Form)**: Eliminate repeating groups; ensure all column values are atomic.
- **2NF (Second Normal Form)**: Satisfies 1NF and removes partial dependencies (non-prime attributes must depend on the whole candidate key).
- **3NF (Third Normal Form)**: Satisfies 2NF and eliminates transitive functional dependencies (A -> B, B -> C).
- **Indexing & B+ Trees**: Databases use B+ Trees on indexed columns to allow range queries and point lookups in O(log n) disk reads.
- **SQL Transactions & Isolation Levels**: Read Uncommitted, Read Committed, Repeatable Read, and Serializable.

## Chapter 3: Artificial Intelligence & Retrieval-Augmented Generation (RAG)
Modern Generative AI platforms integrate Large Language Models (LLMs) with external vector knowledge retrieval.
- **Dense Vector Embeddings**: Numerical representations of text semantics in high-dimensional vector spaces (e.g., 384-d MiniLM, 768-d BERT, 1536-d OpenAI).
- **Cosine Similarity**: Metric for measuring semantic similarity between vector query `q` and document vector `d`:
  `Similarity = (q · d) / (||q|| * ||d||)`
- **RAG Architecture Pipeline**:
  1. Document Ingestion & Chunking (Sliding window with overlap).
  2. Embedding Generation & Vector Storage (ChromaDB, FAISS).
  3. Hybrid Retrieval & Semantic Search (Top-k nearest neighbors).
  4. Cross-Encoder Re-Ranking (Precision filtering of top candidates).
  5. Grounded Prompt Synthesis with Guardrails & Source Citations.
- **Guardrails & Hallucination Prevention**: Strict validation ensures the LLM synthesizes answers solely from retrieved verified text chunks rather than unbounded parametric memory.
"""
    sample_path = UPLOADS_DIR / "sample_ai_study_guide.txt"
    sample_path.write_text(sample_content, encoding="utf-8")

    pipeline = get_pipeline()
    splitter = DocumentSplitter()
    raw_doc = Document(page_content=sample_content, metadata={"source": str(sample_path), "filename": sample_name, "page": 1})
    chunks = splitter.split([raw_doc])

    file_id = f"doc_{int(datetime.now().timestamp()*1000)}_sample"
    for chunk in chunks:
        chunk.metadata["doc_id"] = file_id
        chunk.metadata["filename"] = sample_name
        chunk.metadata["source"] = str(sample_path)

    pipeline.vectorstore.add_documents(chunks)


    doc_entry = {
        "id": file_id,
        "filename": sample_name,
        "saved_as": "sample_ai_study_guide.txt",
        "path": str(sample_path),
        "size_mb": 0.01,
        "chunks": len(chunks),
        "pages": 1,
        "uploaded_at": datetime.now().strftime("%b %d, %Y %I:%M %p")
    }
    registry.append(doc_entry)
    save_docs_registry(registry)

    return {
        "status": "success",
        "success": True,
        "message": "Demo study guide 'Computer Science & AI Systems Fundamentals' loaded and indexed successfully!",
        "document": doc_entry
    }


@app.delete("/api/documents/{doc_id}")
async def delete_document(doc_id: str):
    """Delete a document and clear its vector store chunks."""
    registry = load_docs_registry()
    doc_to_delete = next((d for d in registry if d.get("id") == doc_id), None)
    if not doc_to_delete:
        raise HTTPException(status_code=404, detail="Document not found.")

    file_path = Path(doc_to_delete.get("path", ""))
    if file_path.exists():
        try:
            file_path.unlink()
        except Exception:
            pass

    try:
        pipeline = get_pipeline()
        if pipeline.vectorstore.exists():
            db = pipeline.vectorstore.load()
            db._collection.delete(where={"filename": doc_to_delete.get("filename")})
    except Exception:
        pass

    registry = [d for d in registry if d.get("id") != doc_id]
    save_docs_registry(registry)

    return {"status": "success", "message": f"Document '{doc_to_delete.get('filename')}' deleted."}


# ============================================================================
# Chat API (Grounded strictly in uploaded files — blocks if no file uploaded)
# ============================================================================

@app.post("/api/chat")
async def chat_endpoint(payload: ChatRequest):
    """Process a query through RAG. Blocks with error if no files are uploaded."""
    user_message = payload.message.strip()
    if not user_message:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    registry = load_docs_registry()
    
    # REQUIREMENT GATE: If no files are uploaded, do NOT give answer
    if not registry:
        return {
            "status": "error",
            "session_id": payload.session_id or "new",
            "session_title": "Upload Study Material",
            "answer": "**Document Required**: Please upload your syllabus, textbook, or lecture notes (PDF, TXT, MD) using the **Upload Material** button or click **Load Demo Book** before asking questions.\n\n*StudyAgent requires verified course documents to provide grounded, hallucination-free explanations.*",
            "mode_used": "Document Required",
            "guardrail_blocked": True,
            "time": datetime.now().strftime("%I:%M %p").lstrip("0")
        }

    # If topic is attached, enhance prompt
    query_text = user_message
    if payload.topic and payload.topic.strip():
        query_text = f"[Focus Topic: {payload.topic.strip()}] {user_message}"

    session_id = payload.session_id or f"sess_{int(datetime.now().timestamp()*1000)}_{uuid.uuid4().hex[:6]}"

    try:
        pipeline = get_pipeline()
        raw_answer = await asyncio.to_thread(pipeline.ask, query_text, session_id)
        answer = clean_llm_response(raw_answer)

        return {
            "status": "success",
            "session_id": session_id,
            "session_title": "Study Session",
            "answer": answer,
            "mode_used": payload.mode or "auto",
            "guardrail_blocked": False,
            "time": datetime.now().strftime("%I:%M %p").lstrip("0")
        }
    except Exception as exc:
        LOGGER.exception("Error during chat processing")
        return {
            "status": "error",
            "session_id": session_id,
            "answer": f"An error occurred while analyzing the study material: {str(exc)}",
            "mode_used": "Error",
            "guardrail_blocked": True,
            "time": datetime.now().strftime("%I:%M %p").lstrip("0")
        }


# ============================================================================
# Advanced Academic Generators (Planner, Quiz, Flashcards)
# ============================================================================

@app.post("/api/planner")
async def generate_planner(payload: PlannerRequest = PlannerRequest()):
    """Generate structured day-by-day exam roadmap from uploaded document."""
    registry = load_docs_registry()
    if not registry:
        raise HTTPException(status_code=400, detail="Please upload a study document first.")

    pipeline = get_pipeline()
    topic = payload.topic or "all core topics in the document"
    prompt = f"Create a high-impact {payload.days}-day study and revision schedule for {topic}, allocating {payload.hours_per_day} hours/day. Include daily learning objectives, key chapters to review, and self-test checkpoints strictly based on the provided material."
    
    raw = await asyncio.to_thread(pipeline.ask, prompt, "planner_temp")
    return {"status": "success", "roadmap": clean_llm_response(raw)}


@app.post("/api/quiz")
async def generate_quiz(payload: QuizRequest = QuizRequest()):
    """Generate multiple-choice practice quiz strictly from uploaded material."""
    registry = load_docs_registry()
    if not registry:
        raise HTTPException(status_code=400, detail="Please upload a study document first.")

    pipeline = get_pipeline()
    topic = payload.topic or "key concepts across the document"
    prompt = f"""Generate {payload.question_count} high-quality Multiple Choice Questions (MCQs) on '{topic}' strictly based on the uploaded material.
For each question, provide:
1. Question text
2. 4 Options (A, B, C, D)
3. Correct Option
4. Detailed grounded explanation citing why it is correct.
Format cleanly with Markdown."""

    raw = await asyncio.to_thread(pipeline.ask, prompt, "quiz_temp")
    return {"status": "success", "quiz": clean_llm_response(raw)}


@app.post("/api/flashcards")
async def generate_flashcards(payload: FlashcardRequest = FlashcardRequest()):
    """Generate concept definitions and formulas deck from uploaded material."""
    registry = load_docs_registry()
    if not registry:
        raise HTTPException(status_code=400, detail="Please upload a study document first.")

    pipeline = get_pipeline()
    topic = payload.topic or "core definitions, theorems, and algorithms"
    prompt = f"""Extract {payload.count} essential key concept flashcards for '{topic}' from the study material.
For each flashcard:
- **Term / Concept**: [Name]
- **Definition / Principle**: [Precise 2-sentence summary]
- **Key Formula or Rule**: [If applicable]
- **Exam Tip**: [Common trap or core exam point]"""

    raw = await asyncio.to_thread(pipeline.ask, prompt, "flashcard_temp")
    return {"status": "success", "flashcards": clean_llm_response(raw)}


@app.post("/api/reset-session")
@app.post("/api/clear-all")
async def reset_session():
    """Clear temporary session memory and all uploaded documents for a fresh visit."""
    clear_all_documents_and_memory()
    return {"status": "success", "message": "Session memory and documents cleared."}


