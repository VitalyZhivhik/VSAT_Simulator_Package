import logging
import socket
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from pathlib import Path
from fastapi.responses import FileResponse, HTMLResponse

from server.config import load_config
from server.database import get_db, get_setting, close_db
from server.routes import auth, session, console, admin, websocket, simulator

logger = logging.getLogger("vsat")


def _get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initializing database...")
    try:
        await get_db()
        logger.info("Database ready")
    except Exception as e:
        logger.critical("Database init failed: %s", e, exc_info=True)
        raise

    config = load_config()
    local_ip = _get_local_ip()
    port = config["server"]["port"]
    banner = (
        "\n" + "=" * 60 +
        "\n  Comtech CEL-AC 3 Satellite Switch Simulator — Server" +
        "\n" + "=" * 60 +
        f"\n  Students connect to:  http://{local_ip}:{port}" +
        f"\n  Admin panel:          http://{local_ip}:{port}/admin" +
        f"\n  Local access:         http://localhost:{port}" +
        "\n" + "=" * 60
    )
    print(banner)
    logger.info("Server started — LAN IP: %s, port: %s", local_ip, port)

    yield

    # Shutdown
    logger.info("Shutting down server...")
    await close_db()
    logger.info("Database closed, shutdown complete")


app = FastAPI(
    title="Comtech CEL-AC 3 Simulator",
    version="2.0.0",
    lifespan=lifespan,
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled error on %s: %s", request.url.path, exc, exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# CORS — allow all origins for classroom LAN
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(session.router, prefix="/api/session", tags=["session"])
app.include_router(console.router, prefix="/api/session", tags=["console"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(websocket.router, tags=["websocket"])
app.include_router(simulator.router)


templates_dir = Path(__file__).parent / "static" / "templates"


@app.get("/", response_class=HTMLResponse)
async def login_page():
    return FileResponse(str(templates_dir / "login.html"))


@app.get("/terminal", response_class=HTMLResponse)
async def terminal_page():
    return FileResponse(str(templates_dir / "index.html"))


@app.get("/admin", response_class=HTMLResponse)
async def admin_page():
    admin_html = templates_dir / "admin.html"
    if admin_html.exists():
        return FileResponse(str(admin_html))
    return HTMLResponse("<h1>Admin panel — coming in Phase 3</h1>")

@app.get("/cb3")
async def profile_redirect():
    """Перенаправление для профилей (совместимость с оригинальным URL)"""
    return RedirectResponse(url="/terminal", status_code=302)

@app.get("/api/help-text")
async def public_help_text():
    """Public endpoint for help text (no auth required)."""
    text = await get_setting("help_text")
    return {"help_text": text or ""}

@app.get("/profiles/profile_config.html")
async def profile_config_page():
    """Страница настройки профиля (динамическая)"""
    profile_path = Path(__file__).parent / "static" / "templates" / "profiles" / "profile_config.html"
    if profile_path.exists():
        return FileResponse(str(profile_path))
    return HTMLResponse("<h1>Profile config not found</h1>", status_code=404)

if __name__ == "__main__":
    config = load_config()
    uvicorn.run(
        "server.main:app",
        host=config["server"]["host"],
        port=config["server"]["port"],
        reload=config["server"]["debug"],
    )
