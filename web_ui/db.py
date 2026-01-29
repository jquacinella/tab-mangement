"""
TabBacklog v1 - Web UI Database Operations

Database queries for the web UI.
"""

import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import AsyncIterator, Optional

import asyncpg

from .models import TabDisplay, TabFilters, TabListResponse, TabExport

logger = logging.getLogger(__name__)


class Database:
    """Async database connection pool manager"""

    def __init__(self, database_url: str):
        self.database_url = database_url
        self._pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        """Create connection pool"""
        self._pool = await asyncpg.create_pool(
            self.database_url,
            min_size=2,
            max_size=10,
        )
        logger.info("Database pool created")

    async def disconnect(self):
        """Close connection pool"""
        if self._pool:
            await self._pool.close()
            logger.info("Database pool closed")

    @asynccontextmanager
    async def connection(self) -> AsyncIterator[asyncpg.Connection]:
        """Get a connection from the pool"""
        async with self._pool.acquire() as conn:
            yield conn

    async def get_tabs(
        self,
        user_id: str,
        filters: TabFilters,
    ) -> TabListResponse:
        """
        Get filtered list of tabs with pagination.
        """
        # Build WHERE clauses
        conditions = ["t.user_id = $1", "t.deleted_at IS NULL"]
        params = [user_id]
        param_idx = 2

        if filters.status:
            conditions.append(f"t.status = ${param_idx}")
            params.append(filters.status)
            param_idx += 1

        if filters.is_processed is not None:
            conditions.append(f"t.is_processed = ${param_idx}")
            params.append(filters.is_processed)
            param_idx += 1

        if filters.content_type:
            conditions.append(f"e.content_type = ${param_idx}")
            params.append(filters.content_type)
            param_idx += 1

        if filters.read_time_max:
            conditions.append(f"(e.est_read_min IS NULL OR e.est_read_min <= ${param_idx})")
            params.append(filters.read_time_max)
            param_idx += 1

        if filters.search:
            conditions.append(f"""
                (t.page_title ILIKE ${param_idx}
                 OR t.url ILIKE ${param_idx}
                 OR e.summary ILIKE ${param_idx})
            """)
            params.append(f"%{filters.search}%")
            param_idx += 1

        if filters.project:
            conditions.append(f"e.raw_meta->>'projects' ILIKE ${param_idx}")
            params.append(f"%{filters.project}%")
            param_idx += 1

        where_clause = " AND ".join(conditions)

        # Count query
        count_query = f"""
            SELECT COUNT(*) as total
            FROM tab_item t
            LEFT JOIN tab_enrichment e ON t.id = e.tab_id
            WHERE {where_clause}
        """

        # Main query with pagination
        offset = (filters.page - 1) * filters.per_page
        query = f"""
            SELECT
                t.id,
                t.url,
                t.page_title,
                t.window_label,
                t.status,
                t.is_processed,
                t.processed_at,
                t.created_at,
                p.site_kind,
                p.word_count,
                p.video_seconds,
                e.summary,
                e.content_type,
                e.est_read_min,
                e.priority,
                e.raw_meta
            FROM tab_item t
            LEFT JOIN tab_parsed p ON t.id = p.tab_id
            LEFT JOIN tab_enrichment e ON t.id = e.tab_id
            WHERE {where_clause}
            ORDER BY t.created_at DESC
            LIMIT ${param_idx} OFFSET ${param_idx + 1}
        """
        params.extend([filters.per_page, offset])

        async with self.connection() as conn:
            # Get total count
            total = await conn.fetchval(count_query, *params[:-2])

            # Get tabs
            rows = await conn.fetch(query, *params)

        tabs = []
        for row in rows:
            raw_meta = row["raw_meta"] or {}
            if isinstance(raw_meta, str):
                raw_meta = json.loads(raw_meta)

            tabs.append(TabDisplay(
                id=row["id"],
                url=row["url"],
                page_title=row["page_title"],
                window_label=row["window_label"],
                status=row["status"],
                is_processed=row["is_processed"],
                processed_at=row["processed_at"],
                created_at=row["created_at"],
                site_kind=row["site_kind"],
                word_count=row["word_count"],
                video_seconds=row["video_seconds"],
                summary=row["summary"],
                content_type=row["content_type"],
                est_read_min=row["est_read_min"],
                priority=row["priority"],
                tags=raw_meta.get("tags", []),
                projects=raw_meta.get("projects", []),
            ))

        total_pages = (total + filters.per_page - 1) // filters.per_page

        return TabListResponse(
            tabs=tabs,
            total=total,
            page=filters.page,
            per_page=filters.per_page,
            total_pages=total_pages,
            has_next=filters.page < total_pages,
            has_prev=filters.page > 1,
        )

    async def toggle_processed(self, user_id: str, tab_id: int) -> Optional[TabDisplay]:
        """Toggle the is_processed flag for a tab"""
        query = """
            UPDATE tab_item
            SET
                is_processed = NOT is_processed,
                processed_at = CASE WHEN is_processed THEN NULL ELSE now() END,
                updated_at = now()
            WHERE id = $1 AND user_id = $2 AND deleted_at IS NULL
            RETURNING id, is_processed, processed_at
        """

        log_query = """
            INSERT INTO event_log (user_id, event_type, entity_type, entity_id, details)
            VALUES ($1, $2, 'tab_item', $3, '{"source": "web_ui"}'::jsonb)
        """

        async with self.connection() as conn:
            row = await conn.fetchrow(query, tab_id, user_id)
            if row:
                event_type = "tab_processed" if row["is_processed"] else "tab_unprocessed"
                await conn.execute(log_query, user_id, event_type, tab_id)

                # Fetch full tab data
                return await self.get_tab_by_id(user_id, tab_id)

        return None

    async def get_tab_by_id(self, user_id: str, tab_id: int) -> Optional[TabDisplay]:
        """Get a single tab by ID"""
        query = """
            SELECT
                t.id,
                t.url,
                t.page_title,
                t.window_label,
                t.status,
                t.is_processed,
                t.processed_at,
                t.created_at,
                p.site_kind,
                p.word_count,
                p.video_seconds,
                e.summary,
                e.content_type,
                e.est_read_min,
                e.priority,
                e.raw_meta
            FROM tab_item t
            LEFT JOIN tab_parsed p ON t.id = p.tab_id
            LEFT JOIN tab_enrichment e ON t.id = e.tab_id
            WHERE t.id = $1 AND t.user_id = $2 AND t.deleted_at IS NULL
        """

        async with self.connection() as conn:
            row = await conn.fetchrow(query, tab_id, user_id)

        if not row:
            return None

        raw_meta = row["raw_meta"] or {}
        if isinstance(raw_meta, str):
            raw_meta = json.loads(raw_meta)

        return TabDisplay(
            id=row["id"],
            url=row["url"],
            page_title=row["page_title"],
            window_label=row["window_label"],
            status=row["status"],
            is_processed=row["is_processed"],
            processed_at=row["processed_at"],
            created_at=row["created_at"],
            site_kind=row["site_kind"],
            word_count=row["word_count"],
            video_seconds=row["video_seconds"],
            summary=row["summary"],
            content_type=row["content_type"],
            est_read_min=row["est_read_min"],
            priority=row["priority"],
            tags=raw_meta.get("tags", []),
            projects=raw_meta.get("projects", []),
        )

    async def get_tabs_for_export(self, user_id: str, tab_ids: list[int]) -> list[TabExport]:
        """Get tabs for export"""
        query = """
            SELECT
                t.url,
                t.page_title,
                t.window_label,
                t.created_at,
                e.summary,
                e.content_type,
                e.est_read_min,
                e.priority,
                e.raw_meta
            FROM tab_item t
            LEFT JOIN tab_enrichment e ON t.id = e.tab_id
            WHERE t.id = ANY($1) AND t.user_id = $2 AND t.deleted_at IS NULL
            ORDER BY t.created_at DESC
        """

        async with self.connection() as conn:
            rows = await conn.fetch(query, tab_ids, user_id)

        exports = []
        for row in rows:
            raw_meta = row["raw_meta"] or {}
            if isinstance(raw_meta, str):
                raw_meta = json.loads(raw_meta)

            exports.append(TabExport(
                url=row["url"],
                title=row["page_title"],
                summary=row["summary"],
                content_type=row["content_type"],
                tags=raw_meta.get("tags", []),
                projects=raw_meta.get("projects", []),
                est_read_min=row["est_read_min"],
                priority=row["priority"],
                window_label=row["window_label"],
                created_at=row["created_at"].isoformat() if row["created_at"] else "",
            ))

        return exports

    async def get_filter_options(self, user_id: str) -> dict:
        """Get available filter options"""
        async with self.connection() as conn:
            # Get distinct statuses
            statuses = await conn.fetch("""
                SELECT DISTINCT status FROM tab_item
                WHERE user_id = $1 AND deleted_at IS NULL
                ORDER BY status
            """, user_id)

            # Get distinct content types
            content_types = await conn.fetch("""
                SELECT DISTINCT e.content_type
                FROM tab_item t
                JOIN tab_enrichment e ON t.id = e.tab_id
                WHERE t.user_id = $1 AND t.deleted_at IS NULL AND e.content_type IS NOT NULL
                ORDER BY e.content_type
            """, user_id)

            # Get counts
            counts = await conn.fetchrow("""
                SELECT
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE is_processed) as processed,
                    COUNT(*) FILTER (WHERE NOT is_processed) as unprocessed
                FROM tab_item
                WHERE user_id = $1 AND deleted_at IS NULL
            """, user_id)

        return {
            "statuses": [r["status"] for r in statuses],
            "content_types": [r["content_type"] for r in content_types],
            "total": counts["total"],
            "processed": counts["processed"],
            "unprocessed": counts["unprocessed"],
        }


# Global database instance
_db: Optional[Database] = None


def get_database() -> Database:
    """Get the global database instance"""
    global _db
    if _db is None:
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            raise RuntimeError("DATABASE_URL environment variable not set")
        _db = Database(database_url)
    return _db


async def init_database():
    """Initialize the database connection"""
    db = get_database()
    await db.connect()


async def close_database():
    """Close the database connection"""
    global _db
    if _db:
        await _db.disconnect()
        _db = None
