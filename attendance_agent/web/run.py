#!/usr/bin/env python3
"""
Launcher for CampusOS Attendance AI Web UI.
Run with:
    python web/run.py
or
    uv run python web/run.py
"""
import sys
from pathlib import Path
import uvicorn

web_dir = Path(__file__).resolve().parent
project_root = web_dir.parent
src_dir = project_root / "src"

if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))
if str(web_dir) not in sys.path:
    sys.path.insert(0, str(web_dir))

if __name__ == "__main__":
    print("==================================================")
    print("  CampusOS Attendance AI Web Application")
    print("  URL: http://localhost:8000")
    print("  Powered by FastAPI & LangChain Attendance Agent")
    print("==================================================")
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True, app_dir=str(web_dir))
