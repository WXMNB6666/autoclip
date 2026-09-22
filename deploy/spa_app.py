"""Single-origin web entrypoint: AutoClip API plus the built web UI.

The image builds the Vite frontend into /app/frontend/dist but only starts the
API, so nothing serves the web interface. Sealos publishes one port per app and
the SPA calls the API on same-origin relative paths (/api/v1), so both are
served from this one ASGI app instead of a second server on port 3000.
"""

import logging
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse

from backend.app_factory import create_app

DIST_DIR = Path(os.getenv("AUTOCLIP_FRONTEND_DIST", "/app/frontend/dist"))

app: FastAPI = create_app(mode="web")

logger = logging.getLogger(__name__)

if DIST_DIR.is_dir():
    assets_dir = DIST_DIR / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="spa-assets")

    index_file = DIST_DIR / "index.html"
    base_dir = DIST_DIR.resolve()

    # Registered after the API routers, so /api, /docs and /health keep winning.
    # The SPA uses HashRouter, so only real files need to resolve here and every
    # other path falls back to the app shell.
    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_files(full_path: str) -> FileResponse:
        # An unmatched API path is a missing endpoint, not a page: answering with
        # the HTML shell would hide it from API clients.
        if full_path == "api" or full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")
        candidate = (base_dir / full_path).resolve()
        if full_path and candidate.is_file() and candidate.is_relative_to(base_dir):
            return FileResponse(candidate)
        return FileResponse(index_file)

else:
    logger.warning("Frontend bundle not found at %s; serving the API only", DIST_DIR)