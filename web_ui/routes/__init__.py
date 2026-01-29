"""
TabBacklog v1 - Web UI Routes
"""

from .tabs import router as tabs_router
from .export import router as export_router
from .search import router as search_router

__all__ = ["tabs_router", "export_router", "search_router"]
