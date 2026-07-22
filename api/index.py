import os
import sys

# Ensure backend directory is in Python path for Vercel & local execution
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from backend.main import app  # type: ignore # noqa: F401
except Exception:
    from main import app  # type: ignore # noqa: F401
