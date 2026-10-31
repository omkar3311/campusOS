from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_SOURCE_APP = Path(__file__).resolve().parents[3] / "web" / "app.py"

if not _SOURCE_APP.exists():
    raise FileNotFoundError(f"Cannot find Helpdesk web app at {_SOURCE_APP}")

_spec = importlib.util.spec_from_file_location("helpdesk_agent_web_runtime", _SOURCE_APP)
if _spec is None or _spec.loader is None:
    raise ImportError(f"Could not load Helpdesk app from {_SOURCE_APP}")

_runtime_module = importlib.util.module_from_spec(_spec)
sys.modules["helpdesk_agent_web_runtime"] = _runtime_module
_spec.loader.exec_module(_runtime_module)

app = _runtime_module.app

__all__ = ["app"]
