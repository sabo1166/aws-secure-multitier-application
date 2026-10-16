"""Filesystem locations shared by the application factory and the engineering pages."""
from pathlib import Path

# The frontend (Jinja2 templates and static files) lives in frontend/, a sibling of backend/.
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
DATA_DIR = FRONTEND_DIR / "static" / "data"
