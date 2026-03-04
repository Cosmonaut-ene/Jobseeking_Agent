"""FastAPI entry point for Jobseeking Agent v2."""
import logging
from dotenv import load_dotenv
from pathlib import Path

_env_path = Path(__file__).parents[2] / ".env"  # Jobseeking_Agent/.env
load_dotenv(_env_path, override=True)  # override=True so saved .env values always apply
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info("Loaded .env from %s", _env_path)

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.app.database import init_db
from backend.app.scheduler import start_scheduler, stop_scheduler
from backend.app.routers import jobs, profile, settings, notifications, scrapers, dashboard, files


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="Jobseeking Agent v2 API",
    description="Full-auto job hunting assistant",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:8000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs.router, prefix="/api")
app.include_router(profile.router, prefix="/api")
app.include_router(settings.router, prefix="/api")
app.include_router(notifications.router, prefix="/api")
app.include_router(scrapers.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(files.router, prefix="/api")

# Serve React build
frontend_dist = Path(__file__).parents[2] / "frontend" / "dist"
if frontend_dist.exists():
    assets_dir = frontend_dist / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        return FileResponse(str(frontend_dist / "index.html"))
