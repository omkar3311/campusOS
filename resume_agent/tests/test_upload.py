import importlib.util
from pathlib import Path
from starlette.testclient import TestClient

APP_PATH = Path(__file__).resolve().parents[1] / "web" / "app.py"
SPEC = importlib.util.spec_from_file_location("resume_web_app_test", APP_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

CLIENT = TestClient(MODULE.app)


def test_upload_routes_exist():
    """Verify that both /api/upload and /api/upload-resumes routes are registered."""
    route_paths = [route.path for route in MODULE.app.routes]
    assert "/api/upload" in route_paths, "/api/upload route must be registered"
    assert "/api/upload-resumes" in route_paths, "/api/upload-resumes route must be registered"


def test_upload_rejects_invalid_file_extension():
    """Verify that uploading non-PDF/DOCX files returns 400 Bad Request."""
    resp = CLIENT.post(
        "/api/upload-resumes",
        files=[("files", ("bad_file.txt", b"plain text", "text/plain"))],
    )
    assert resp.status_code == 400
    assert "not a supported format" in resp.json().get("detail", "")
