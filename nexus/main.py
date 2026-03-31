"""
main.py — NEXUS FastAPI entry point (Fixed)

FIX: All imports now use the `nexus.` package prefix consistently.
FIX: Blackboard.load() is called in lifespan so L2 disk state is restored on startup.
"""
from __future__ import annotations

import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from dotenv import load_dotenv

# Load .env from this directory or one level up
_env_path = os.path.join(os.path.dirname(__file__), ".env")
if not os.path.exists(_env_path):
    _env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
load_dotenv(dotenv_path=_env_path)

from nexus.models.schemas import AGENT_REGISTRY
from nexus.routes import chat, memory, system
from nexus.agents.gemini_client import close_session
from nexus.config import get_demo_mode, get_port, get_allowed_origins, VERSION

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("nexus")

DEMO_MODE = get_demo_mode()
PORT = get_port()


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"\n{'=' * 56}")
    print("  NEXUS API — Multi-Agent Productivity OS")
    print(f"  Mode    : {'DEMO (fixtures)' if DEMO_MODE else 'LIVE (real APIs)'}")
    print(f"  Version : {VERSION}")
    print(f"  Agents  : {len(AGENT_REGISTRY)}")
    print(f"  Docs    : http://localhost:{PORT}/docs")
    print(f"{'=' * 56}\n")

    # FIX: Restore persisted Blackboard state from disk on startup
    try:
        from nexus.agents.blackboard import Blackboard
        _bb = Blackboard()
        await _bb.load()
    except Exception as e:
        logger.warning(f"Blackboard pre-load skipped: {e}")

    yield

    await close_session()
    print("\nNEXUS API shutting down.")


app = FastAPI(
    title="NEXUS API",
    description="Multi-Agent Productivity OS — Google Cloud Gen AI Academy APAC 2025",
    version=VERSION,
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────
_raw_origins = get_allowed_origins()
_allowed_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]
_use_wildcard = _allowed_origins == ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=not _use_wildcard,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key"],
)


# ── Exception handlers ────────────────────────────────────────

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(f"Validation error: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={"error": "Validation error", "detail": exc.errors()},
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail},
    )


# ── Routers ───────────────────────────────────────────────────
app.include_router(chat.router)
app.include_router(memory.router)
app.include_router(system.router)

# ── Static files & SPA routes ─────────────────────────────────
_base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
frontend_path = os.path.join(_base_dir, "frontend")
app.mount("/frontend", StaticFiles(directory=frontend_path), name="frontend")


@app.get("/")
async def read_index():
    return FileResponse(os.path.join(frontend_path, "index.html"))


@app.get("/studio")
@app.get("/app")
@app.get("/swarm")
async def read_studio():
    return FileResponse(os.path.join(frontend_path, "studio.html"))


@app.get("/memory")
async def read_memory_page():
    return FileResponse(os.path.join(frontend_path, "memory.html"))


@app.get("/mcp")
async def read_mcp():
    return FileResponse(os.path.join(frontend_path, "mcp.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
