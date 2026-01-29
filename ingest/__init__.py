"""
TabBacklog v1 - Ingest Module

This module provides functionality to parse Firefox bookmarks exports
and ingest them into the database.
"""

from .firefox_parser import FirefoxParser, BookmarkItem
from .db import IngestDB

__all__ = ["FirefoxParser", "BookmarkItem", "IngestDB"]
