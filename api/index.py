import sys
import os

# Add backend directory to module search path for Vercel runtime execution
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

try:
    from backend.main import app  # Package style import (clears IDE static linter warnings)
except ImportError:
    from main import app          # Direct sys.path import fallback
