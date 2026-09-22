"""Top-level ASGI entry point for Render and standard ASGI runners."""
import os
import sys

# Ensure src/ is on sys.path
_src_dir = os.path.join(os.path.dirname(__file__), "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from backend.main import app  # noqa: E402

__all__ = ["app"]

if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
