"""
FastAPI entry point for Jobseeking Agent web app.
Run from the Jobseeking_Agent/ project root:
    uvicorn web.backend.main:app --reload
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Make `jobseeking_agent` importable (src layout)
sys.path.insert(0, str(Path(__file__).parents[2] / "src"))

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from jobseeking_agent.db import init_db
from web.backend.routers import dashboard, jobs, profile, scrapers, settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Jobseeking Agent API",
    description="API for the Jobseeking Agent web application",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow Vite dev server (port 5173) during development
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

# API routers
app.include_router(profile.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")
app.include_router(scrapers.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(settings.router, prefix="/api")

# Serve React build in production (frontend/dist must exist)
# Use explicit assets mount + catch-all so client-side routes (e.g. /jobs) serve index.html
frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    assets_dir = frontend_dist / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        return FileResponse(str(frontend_dist / "index.html"))
