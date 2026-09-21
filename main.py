"""
CampusOS Root Entry Point
Starts the unified CampusOS Platform (FastAPI web platform + mounted sub-agents).

Usage:
    python main.py
    # or
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload
"""

import sys
import os
from pathlib import Path

# Setup paths so website and all agents are importable
ROOT_DIR = Path(__file__).resolve().parent
WEBSITE_DIR = ROOT_DIR / "website"

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(WEBSITE_DIR) not in sys.path:
    sys.path.insert(0, str(WEBSITE_DIR))

# Expose the FastAPI application instance for ASGI servers (e.g., uvicorn main:app)
try:
    from website.main import app  # noqa: F401
except ImportError as err:
    print(f"❌ Failed to import CampusOS website application: {err}")
    print("💡 Ensure dependencies are installed: pip install -r website/requirements.txt")
    raise err


if __name__ == "__main__":
    try:
        import uvicorn
    except ImportError:
        print("❌ 'uvicorn' is not installed in the current Python environment.")
        print("💡 Activate your virtual environment first:")
        print("     source website/.venv/bin/activate  # On Linux/macOS")
        print("     website\\.venv\\Scripts\\activate    # On Windows")
        print("   Or run using the virtual environment directly:")
        print("     ./website/.venv/bin/python main.py")
        sys.exit(1)

    print("=" * 60)
    print("🎓 Starting CampusOS Platform from Root")
    print("   🌐 Dashboard: http://localhost:8000")
    print("   📚 Study Agent: http://localhost:8000/agent/study")
    print("   💼 Resume Agent: http://localhost:8000/agent/career")
    print("   📊 Attendance Agent: http://localhost:8000/agent/attendance")
    print("   💬 Campus Helpdesk: http://localhost:8000/agent/campus")
    print("=" * 60)

    uvicorn.run(
        "website.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=[str(ROOT_DIR)]
    )
