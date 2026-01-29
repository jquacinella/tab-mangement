"""
TabBacklog v1 - Tabs Routes

Routes for tab listing, filtering, and management.
"""

import os
from typing import Optional

from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import HTMLResponse

from ..db import get_database
from ..models import TabFilters

router = APIRouter(tags=["Tabs"])


def get_user_id() -> str:
    """Get the default user ID from environment"""
    user_id = os.environ.get("DEFAULT_USER_ID")
    if not user_id:
        raise HTTPException(500, "DEFAULT_USER_ID not configured")
    return user_id


@router.get("/tabs", response_class=HTMLResponse)
async def get_tabs(
    request: Request,
    content_type: Optional[str] = Query(None),
    project: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    is_processed: Optional[bool] = Query(None),
    read_time_max: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
):
    """
    Get filtered tabs list as HTMX fragment.

    Returns HTML tbody with tab rows for HTMX swap.
    """
    user_id = get_user_id()
    db = get_database()

    filters = TabFilters(
        content_type=content_type,
        project=project,
        status=status,
        is_processed=is_processed,
        read_time_max=read_time_max,
        search=search,
        page=page,
        per_page=per_page,
    )

    result = await db.get_tabs(user_id, filters)

    templates = request.app.state.templates
    return templates.TemplateResponse(
        "fragments/tab_rows.html",
        {
            "request": request,
            "tabs": result.tabs,
            "total": result.total,
            "page": result.page,
            "total_pages": result.total_pages,
            "has_next": result.has_next,
            "has_prev": result.has_prev,
            "filters": filters,
        },
    )


@router.post("/tabs/{tab_id}/toggle_processed", response_class=HTMLResponse)
async def toggle_processed(
    request: Request,
    tab_id: int,
):
    """
    Toggle the processed status of a tab.

    Returns updated row HTML for HTMX swap.
    """
    user_id = get_user_id()
    db = get_database()

    tab = await db.toggle_processed(user_id, tab_id)
    if not tab:
        raise HTTPException(404, "Tab not found")

    templates = request.app.state.templates
    return templates.TemplateResponse(
        "fragments/tab_row.html",
        {
            "request": request,
            "tab": tab,
        },
    )


@router.get("/tabs/{tab_id}", response_class=HTMLResponse)
async def get_tab_detail(
    request: Request,
    tab_id: int,
):
    """
    Get detailed view of a single tab.

    Returns HTML fragment with full tab details.
    """
    user_id = get_user_id()
    db = get_database()

    tab = await db.get_tab_by_id(user_id, tab_id)
    if not tab:
        raise HTTPException(404, "Tab not found")

    templates = request.app.state.templates
    return templates.TemplateResponse(
        "fragments/tab_detail.html",
        {
            "request": request,
            "tab": tab,
        },
    )


@router.get("/filters", response_class=HTMLResponse)
async def get_filter_options(request: Request):
    """
    Get available filter options.

    Returns JSON with filter option values.
    """
    user_id = get_user_id()
    db = get_database()

    options = await db.get_filter_options(user_id)
    return options
