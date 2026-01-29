"""
TabBacklog v1 - Web UI Main Application

FastAPI application with HTMX-powered interface.
"""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import __version__
from .db import init_database, close_database, get_database
from .models import HealthResponse
from .routes import tabs_router, export_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Paths
BASE_DIR = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("Web UI starting...")

    # Initialize database
    await init_database()
    logger.info("Database connected")

    yield

    # Cleanup
    await close_database()
    logger.info("Web UI shutting down")


app = FastAPI(
    title="TabBacklog Web UI",
    description="Web interface for managing browser tabs",
    version=__version__,
    lifespan=lifespan,
)

# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Setup templates
templates = Jinja2Templates(directory=TEMPLATES_DIR)
app.state.templates = templates

# Include routers
app.include_router(tabs_router)
app.include_router(export_router)


def get_user_id() -> str:
    """Get the default user ID from environment"""
    return os.environ.get("DEFAULT_USER_ID", "")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Render the main page."""
    user_id = get_user_id()
    db = get_database()

    # Get filter options
    filter_options = await db.get_filter_options(user_id)

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "filter_options": filter_options,
        },
    )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    db = get_database()

    try:
        async with db.connection() as conn:
            await conn.fetchval("SELECT 1")
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    return HealthResponse(
        status="healthy" if db_status == "connected" else "degraded",
        version=__version__,
        database=db_status,
    )


@app.get("/stats", response_class=HTMLResponse)
async def stats_page(request: Request):
    """Render the stats page."""
    user_id = get_user_id()
    db = get_database()

    # Get stats
    filter_options = await db.get_filter_options(user_id)

    # Get status breakdown
    async with db.connection() as conn:
        status_counts = await conn.fetch("""
            SELECT status, COUNT(*) as count
            FROM tab_item
            WHERE user_id = $1 AND deleted_at IS NULL
            GROUP BY status
            ORDER BY count DESC
        """, user_id)

        content_type_counts = await conn.fetch("""
            SELECT e.content_type, COUNT(*) as count
            FROM tab_item t
            JOIN tab_enrichment e ON t.id = e.tab_id
            WHERE t.user_id = $1 AND t.deleted_at IS NULL AND e.content_type IS NOT NULL
            GROUP BY e.content_type
            ORDER BY count DESC
        """, user_id)

        recent_events = await conn.fetch("""
            SELECT event_type, entity_type, created_at
            FROM event_log
            WHERE user_id = $1
            ORDER BY created_at DESC
            LIMIT 10
        """, user_id)

    return templates.TemplateResponse(
        "stats.html",
        {
            "request": request,
            "filter_options": filter_options,
            "status_counts": [dict(r) for r in status_counts],
            "content_type_counts": [dict(r) for r in content_type_counts],
            "recent_events": [dict(r) for r in recent_events],
        },
    )


# Run with: uvicorn web_ui.main:app --host 0.0.0.0 --port 8000
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
