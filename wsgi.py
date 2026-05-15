"""WSGI entry point for PythonAnywhere deployment."""
import os
import sys
import traceback
from pathlib import Path

USERNAME = "sleepwell"
PROJECT_DIR = "sleep-web"

project_home = Path(f"/home/{USERNAME}/{PROJECT_DIR}")
if not project_home.exists():
    if os.name == "nt":
        project_home = Path(__file__).resolve().parent
    else:
        # Keep the error explicit in PythonAnywhere's error log instead of
        # failing later with a less useful "No module named server".
        raise RuntimeError(f"Project directory does not exist: {project_home}")

project_home_str = str(project_home)
if project_home_str not in sys.path:
    sys.path.insert(0, project_home_str)

# PythonAnywhere workers may not have a writable home-backed matplotlib cache
# during import. Keep cache/temp files inside the project tree.
os.environ.setdefault("FLASK_ENV", "production")
os.environ.setdefault("MPLCONFIGDIR", str(project_home / ".matplotlib"))
os.makedirs(os.environ["MPLCONFIGDIR"], exist_ok=True)

try:
    from server import app as application
except Exception:
    print("=" * 60, file=sys.stderr)
    print("WSGI IMPORT ERROR:", file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    raise
