"""
TabBacklog v1 - Database Operations for Ingest

Provides database operations for ingesting parsed bookmarks into the database.
Handles upserts, deduplication, and event logging.
"""

import json
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Iterator
from uuid import UUID

import psycopg
from psycopg.rows import dict_row

from .firefox_parser import BookmarkItem


@dataclass
class IngestResult:
    """Result of an ingest operation"""
    total_processed: int = 0
    inserted: int = 0
    skipped_duplicates: int = 0
    errors: int = 0
    error_messages: list[str] | None = None

    def __post_init__(self):
        if self.error_messages is None:
            self.error_messages = []


class IngestDB:
    """
    Database operations for ingesting tab items.

    Handles connection management, upserts with deduplication,
    and event logging.
    """

    def __init__(self, database_url: str):
        """
        Initialize the database connection.

        Args:
            database_url: PostgreSQL connection string
        """
        self.database_url = database_url
        self._conn: psycopg.Connection | None = None

    @contextmanager
    def connection(self) -> Iterator[psycopg.Connection]:
        """Context manager for database connections"""
        conn = psycopg.connect(self.database_url, row_factory=dict_row)
        try:
            yield conn
        finally:
            conn.close()

    def ingest_bookmarks(
        self,
        bookmarks: list[BookmarkItem],
        user_id: str | UUID,
        batch_size: int = 100,
    ) -> IngestResult:
        """
        Ingest a list of bookmarks into the database.

        Performs upsert operations, deduplicating on (user_id, url).
        Logs events for each operation.

        Args:
            bookmarks: List of BookmarkItem objects to ingest
            user_id: UUID of the user owning these tabs
            batch_size: Number of records to process per transaction

        Returns:
            IngestResult with counts of processed, inserted, skipped records
        """
        user_id_str = str(user_id)
        result = IngestResult()

        with self.connection() as conn:
            # Process in batches
            for i in range(0, len(bookmarks), batch_size):
                batch = bookmarks[i : i + batch_size]
                batch_result = self._process_batch(conn, batch, user_id_str)

                result.total_processed += batch_result.total_processed
                result.inserted += batch_result.inserted
                result.skipped_duplicates += batch_result.skipped_duplicates
                result.errors += batch_result.errors
                if batch_result.error_messages:
                    result.error_messages.extend(batch_result.error_messages)

        return result

    def _process_batch(
        self,
        conn: psycopg.Connection,
        bookmarks: list[BookmarkItem],
        user_id: str,
    ) -> IngestResult:
        """Process a batch of bookmarks in a single transaction"""
        result = IngestResult()

        with conn.cursor() as cur:
            for bookmark in bookmarks:
                result.total_processed += 1

                try:
                    inserted = self._upsert_tab(cur, bookmark, user_id)
                    if inserted:
                        result.inserted += 1
                        self._log_event(
                            cur,
                            user_id=user_id,
                            event_type="tab_created",
                            entity_type="tab_item",
                            details={
                                "url": bookmark.url,
                                "source": "firefox_bookmarks_import",
                            },
                        )
                    else:
                        result.skipped_duplicates += 1
                        self._log_event(
                            cur,
                            user_id=user_id,
                            event_type="tab_duplicate_skipped",
                            entity_type="tab_item",
                            details={
                                "url": bookmark.url,
                                "source": "firefox_bookmarks_import",
                            },
                        )
                except Exception as e:
                    result.errors += 1
                    result.error_messages.append(f"Error processing {bookmark.url}: {e}")
                    # Continue processing other bookmarks
                    continue

            conn.commit()

        return result

    def _upsert_tab(
        self,
        cur: psycopg.Cursor,
        bookmark: BookmarkItem,
        user_id: str,
    ) -> bool:
        """
        Upsert a single tab item.

        Returns True if a new record was inserted, False if it was a duplicate.
        """
        # Use INSERT ... ON CONFLICT to handle duplicates
        # Only insert if no existing active record (deleted_at IS NULL)
        query = """
            INSERT INTO tab_item (
                user_id,
                url,
                page_title,
                window_label,
                collected_at,
                status,
                created_at,
                updated_at
            )
            VALUES (
                %(user_id)s,
                %(url)s,
                %(page_title)s,
                %(window_label)s,
                %(collected_at)s,
                'new',
                now(),
                now()
            )
            ON CONFLICT (user_id, url) WHERE deleted_at IS NULL
            DO UPDATE SET
                -- Only update if the existing record has less info
                page_title = COALESCE(tab_item.page_title, EXCLUDED.page_title),
                window_label = COALESCE(tab_item.window_label, EXCLUDED.window_label),
                updated_at = now()
            RETURNING (xmax = 0) AS inserted
        """

        cur.execute(
            query,
            {
                "user_id": user_id,
                "url": bookmark.url,
                "page_title": bookmark.page_title,
                "window_label": bookmark.window_label,
                "collected_at": bookmark.collected_at,
            },
        )

        row = cur.fetchone()
        # xmax = 0 means it was an INSERT, not an UPDATE
        return row["inserted"] if row else False

    def _log_event(
        self,
        cur: psycopg.Cursor,
        user_id: str,
        event_type: str,
        entity_type: str | None = None,
        entity_id: int | None = None,
        details: dict | None = None,
    ) -> None:
        """Log an event to the event_log table"""
        query = """
            INSERT INTO event_log (
                user_id,
                event_type,
                entity_type,
                entity_id,
                details,
                created_at
            )
            VALUES (
                %(user_id)s,
                %(event_type)s,
                %(entity_type)s,
                %(entity_id)s,
                %(details)s,
                now()
            )
        """

        cur.execute(
            query,
            {
                "user_id": user_id,
                "event_type": event_type,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "details": json.dumps(details or {}),
            },
        )

    def get_user_tab_count(self, user_id: str | UUID) -> int:
        """Get the total count of active tabs for a user"""
        with self.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT COUNT(*) as count
                    FROM tab_item
                    WHERE user_id = %s AND deleted_at IS NULL
                    """,
                    (str(user_id),),
                )
                row = cur.fetchone()
                return row["count"] if row else 0

    def get_ingest_summary(self, user_id: str | UUID) -> dict:
        """Get a summary of tabs for a user grouped by status"""
        with self.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT status, COUNT(*) as count
                    FROM tab_item
                    WHERE user_id = %s AND deleted_at IS NULL
                    GROUP BY status
                    ORDER BY status
                    """,
                    (str(user_id),),
                )
                rows = cur.fetchall()
                return {row["status"]: row["count"] for row in rows}
