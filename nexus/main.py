"""
main.py — NEXUS FastAPI entry point (Cloud Run / AlloyDB edition)

Cloud Run injects PORT=8080 automatically; the server binds to it.
AlloyDB connection pool is initialised at startup and closed cleanly.
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

# Load .env (dev only — Cloud Run uses env vars injected at deploy time)
_env_path = os.path.join(os.path.dirname(__file__), ".env")
if not os.path.exists(_env_path):
    _env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
if os.path.exists(_env_path):
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
PORT = get_port()   # defaults to 8080 — matches Cloud Run


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────
    print(f"\n{'=' * 56}")
    print("  NEXUS API — Multi-Agent Productivity OS")
    print(f"  Mode     : {'DEMO (fixtures)' if DEMO_MODE else 'LIVE'}")
    print(f"  Version  : {VERSION}")
    print(f"  Agents   : {len(AGENT_REGISTRY)}")
    print(f"  Port     : {PORT}")
    print(f"{'=' * 56}\n")

    # Warm up AlloyDB connection pool
    try:
        from nexus.memory.alloydb_client import get_db_client
        db = get_db_client()
        if db.is_active():
            logger.info("AlloyDB: connection pool ready.")
        else:
            logger.warning("AlloyDB: pool not active — running without DB persistence.")
    except Exception as exc:
        logger.warning(f"AlloyDB warm-up skipped: {exc}")

    # Restore Blackboard from disk (L2)
    try:
        from nexus.agents.blackboard import Blackboard
        await Blackboard().load()
    except Exception as exc:
        logger.warning(f"Blackboard pre-load skipped: {exc}")

    yield

    # ── Shutdown ─────────────────────────────────────────────
    await close_session()
    try:
        from nexus.memory.alloydb_client import get_db_client
        get_db_client().close()
    except Exception:
        pass
    print("\nNEXUS API shutting down.")


app = FastAPI(
    title="NEXUS API",
    description="Multi-Agent Productivity OS — Google Cloud Gen AI Academy APAC 2025",
    version=VERSION,
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────
_raw = get_allowed_origins()
_origins = [o.strip() for o in _raw.split(",") if o.strip()]
_wildcard = _origins == ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=not _wildcard,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key"],
)

# ── Exception handlers ────────────────────────────────────────

@app.exception_handler(RequestValidationError)
async def _validation(request: Request, exc: RequestValidationError):
    logger.warning(f"Validation error: {exc.errors()}")
    return JSONResponse(422, content={"error": "Validation error", "detail": exc.errors()})

@app.exception_handler(StarletteHTTPException)
async def _http(request: Request, exc: StarletteHTTPException):
    return JSONResponse(exc.status_code, content={"error": exc.detail})

# ── Routers ───────────────────────────────────────────────────
app.include_router(chat.router)
app.include_router(memory.router)
app.include_router(system.router)

# ── Static files & SPA routes ─────────────────────────────────
_base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_frontend = os.path.join(_base, "frontend")

if os.path.isdir(_frontend):
    app.mount("/frontend", StaticFiles(directory=_frontend), name="frontend")

    @app.get("/")
    async def root():          return FileResponse(os.path.join(_frontend, "index.html"))

    @app.get("/studio")
    @app.get("/app")
    @app.get("/swarm")
    async def studio():        return FileResponse(os.path.join(_frontend, "studio.html"))

    @app.get("/memory")
    async def memory_page():   return FileResponse(os.path.join(_frontend, "memory.html"))

    @app.get("/mcp")
    async def mcp_page():      return FileResponse(os.path.join(_frontend, "mcp.html"))
else:
    @app.get("/")
    async def root():
        return {"status": "ok", "version": VERSION, "docs": "/docs"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("nexus.main:app", host="0.0.0.0", port=PORT, reload=True)
