import os
import sys

# Add backend and root paths to sys.path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from main import app  # type: ignore # Top-level ASGI application for Vercel
