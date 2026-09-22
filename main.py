"""Top-level ASGI entry point for Render and standard ASGI runners."""
import os
import sys

# Ensure backend/src is on sys.path
_backend_src = os.path.join(os.path.dirname(__file__), "backend", "src")
if _backend_src not in sys.path:
    sys.path.insert(0, _backend_src)

from backend.main import app  # noqa: E402

__all__ = ["app"]

if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
