"""
TabBacklog v1 - Search Routes

Routes for fuzzy and semantic search functionality.
"""

import os
import logging
from typing import Optional

from fastapi import APIRouter, Request, HTTPException, Query, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse

from ..db import get_database
from ..models import TabFilters

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search", tags=["Search"])


def get_user_id() -> str:
    """Get the default user ID from environment"""
    user_id = os.environ.get("DEFAULT_USER_ID")
    if not user_id:
        raise HTTPException(500, "DEFAULT_USER_ID not configured")
    return user_id


@router.get("/semantic", response_class=HTMLResponse)
async def semantic_search(
    request: Request,
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(50, ge=1, le=200),
):
    """
    Perform semantic search using vector embeddings.

    Returns tabs sorted by semantic similarity to the query.
    """
    user_id = get_user_id()
    db = get_database()

    try:
        # Import here to avoid circular imports
        from shared.search import EmbeddingGenerator, SearchService

        # Generate query embedding
        generator = EmbeddingGenerator()
        search_service = SearchService(generator)

        query_embedding = await search_service.generate_query_embedding(q)
        await generator.close()

        # Search using vector similarity
        tabs = await db.semantic_search(user_id, query_embedding, limit)

        templates = request.app.state.templates
        return templates.TemplateResponse(
            "fragments/tab_rows.html",
            {
                "request": request,
                "tabs": tabs,
                "total": len(tabs),
                "page": 1,
                "total_pages": 1,
                "has_next": False,
                "has_prev": False,
                "filters": TabFilters(search=q),
                "search_mode": "semantic",
            },
        )

    except ImportError:
        raise HTTPException(500, "Semantic search not configured - embedding service unavailable")
    except Exception as e:
        logger.exception(f"Semantic search error: {e}")
        raise HTTPException(500, f"Search error: {str(e)}")


@router.post("/generate-embeddings")
async def generate_embeddings(
    background_tasks: BackgroundTasks,
    batch_size: int = Query(10, ge=1, le=100),
):
    """
    Trigger embedding generation for tabs without embeddings.

    Runs in background and returns immediately.
    """
    user_id = get_user_id()

    background_tasks.add_task(generate_embeddings_task, user_id, batch_size)

    return JSONResponse({
        "status": "started",
        "message": f"Generating embeddings for up to {batch_size} tabs",
    })


async def generate_embeddings_task(user_id: str, batch_size: int):
    """Background task to generate embeddings"""
    try:
        from shared.search import EmbeddingGenerator, SearchService

        db = get_database()
        generator = EmbeddingGenerator()
        search_service = SearchService(generator)

        # Get tabs without embeddings
        tabs = await db.get_tabs_without_embeddings(user_id, batch_size)

        if not tabs:
            logger.info("No tabs need embeddings")
            return

        logger.info(f"Generating embeddings for {len(tabs)} tabs")

        for tab in tabs:
            try:
                embedding = await search_service.generate_document_embedding(
                    title=tab.get("page_title"),
                    summary=tab.get("summary"),
                    text=tab.get("text_full"),
                )

                await db.save_embedding(
                    tab_id=tab["id"],
                    embedding=embedding,
                    model_name=generator.model_name,
                )

                logger.info(f"Generated embedding for tab {tab['id']}")

            except Exception as e:
                logger.warning(f"Failed to generate embedding for tab {tab['id']}: {e}")
                continue

        await generator.close()
        logger.info(f"Embedding generation complete for {len(tabs)} tabs")

    except Exception as e:
        logger.exception(f"Embedding generation task failed: {e}")


@router.get("/embedding-status")
async def embedding_status():
    """Get status of embedding coverage"""
    user_id = get_user_id()
    db = get_database()

    async with db.connection() as conn:
        stats = await conn.fetchrow("""
            SELECT
                COUNT(*) as total_enriched,
                COUNT(emb.tab_id) as with_embeddings,
                COUNT(*) - COUNT(emb.tab_id) as without_embeddings
            FROM tab_item t
            LEFT JOIN tab_embedding emb ON t.id = emb.tab_id
            WHERE t.user_id = $1
              AND t.deleted_at IS NULL
              AND t.status = 'enriched'
        """, user_id)

    return {
        "total_enriched": stats["total_enriched"],
        "with_embeddings": stats["with_embeddings"],
        "without_embeddings": stats["without_embeddings"],
        "coverage_percent": round(
            (stats["with_embeddings"] / stats["total_enriched"] * 100)
            if stats["total_enriched"] > 0 else 0,
            1
        ),
    }
