"""
TabBacklog v1 - Export Routes

Routes for exporting tabs to various formats.
"""

import os
from datetime import datetime

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, Response

from ..db import get_database
from ..models import ExportRequest

router = APIRouter(prefix="/export", tags=["Export"])


def get_user_id() -> str:
    """Get the default user ID from environment"""
    user_id = os.environ.get("DEFAULT_USER_ID")
    if not user_id:
        raise HTTPException(500, "DEFAULT_USER_ID not configured")
    return user_id


@router.post("/json")
async def export_json(request: ExportRequest):
    """
    Export selected tabs as JSON.

    Returns JSON array of tab data.
    """
    user_id = get_user_id()
    db = get_database()

    tabs = await db.get_tabs_for_export(user_id, request.tab_ids)

    if not tabs:
        raise HTTPException(404, "No tabs found")

    # Convert to JSON-serializable format
    data = [tab.model_dump() for tab in tabs]

    return JSONResponse(
        content=data,
        headers={
            "Content-Disposition": f'attachment; filename="tabs_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json"'
        },
    )


@router.post("/markdown")
async def export_markdown(request: ExportRequest):
    """
    Export selected tabs as Markdown.

    Returns Markdown file with tab summaries and metadata.
    """
    user_id = get_user_id()
    db = get_database()

    tabs = await db.get_tabs_for_export(user_id, request.tab_ids)

    if not tabs:
        raise HTTPException(404, "No tabs found")

    # Build markdown content
    lines = [
        "# TabBacklog Export",
        "",
        f"*Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
        f"*Total: {len(tabs)} tabs*",
        "",
        "---",
        "",
    ]

    for tab in tabs:
        lines.append(tab.to_markdown())

    content = "\n".join(lines)

    return Response(
        content=content,
        media_type="text/markdown",
        headers={
            "Content-Disposition": f'attachment; filename="tabs_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.md"'
        },
    )


@router.post("/obsidian")
async def export_obsidian(request: ExportRequest):
    """
    Export selected tabs in Obsidian-compatible format.

    Returns Markdown with YAML frontmatter for Obsidian.
    """
    user_id = get_user_id()
    db = get_database()

    tabs = await db.get_tabs_for_export(user_id, request.tab_ids)

    if not tabs:
        raise HTTPException(404, "No tabs found")

    # Build Obsidian-style markdown with frontmatter
    lines = [
        "---",
        "type: reading-list",
        f"exported: {datetime.now().isoformat()}",
        f"count: {len(tabs)}",
        "---",
        "",
        "# Reading List Export",
        "",
    ]

    for tab in tabs:
        # Create individual note format
        lines.append(f"## [{tab.title or 'Untitled'}]({tab.url})")
        lines.append("")

        if tab.summary:
            lines.append(f"> {tab.summary}")
            lines.append("")

        # Metadata as inline tags
        metadata_parts = []
        if tab.content_type:
            metadata_parts.append(f"#type/{tab.content_type}")
        if tab.priority:
            metadata_parts.append(f"#priority/{tab.priority}")
        for tag in tab.tags[:5]:  # Limit tags
            clean_tag = tag.lstrip("#").replace(" ", "-")
            metadata_parts.append(f"#{clean_tag}")

        if metadata_parts:
            lines.append(" ".join(metadata_parts))
            lines.append("")

        if tab.est_read_min:
            lines.append(f"⏱️ {tab.est_read_min} min")
            lines.append("")

        lines.append("---")
        lines.append("")

    content = "\n".join(lines)

    return Response(
        content=content,
        media_type="text/markdown",
        headers={
            "Content-Disposition": f'attachment; filename="obsidian_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.md"'
        },
    )
