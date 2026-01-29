"""
TabBacklog v1 - Web UI Pydantic Models

Models for API requests/responses and data display.
"""

from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field


class TabFilters(BaseModel):
    """Query parameters for filtering tabs"""
    content_type: Optional[str] = Field(None, description="Filter by content type")
    project: Optional[str] = Field(None, description="Filter by project tag")
    status: Optional[str] = Field(None, description="Filter by pipeline status")
    is_processed: Optional[bool] = Field(None, description="Filter by processed flag")
    read_time_max: Optional[int] = Field(None, description="Max reading time in minutes")
    search: Optional[str] = Field(None, description="Search text (fuzzy)")
    page: int = Field(default=1, ge=1, description="Page number")
    per_page: int = Field(default=50, ge=1, le=200, description="Items per page")


class TabDisplay(BaseModel):
    """Tab data for display in the UI"""
    id: int
    url: str
    page_title: Optional[str]
    window_label: Optional[str]
    status: str
    is_processed: bool
    processed_at: Optional[datetime]
    created_at: datetime

    # Parsed data
    site_kind: Optional[str] = None
    word_count: Optional[int] = None
    video_seconds: Optional[int] = None

    # Enrichment data
    summary: Optional[str] = None
    content_type: Optional[str] = None
    est_read_min: Optional[int] = None
    priority: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)

    @property
    def display_title(self) -> str:
        """Get display title with fallback"""
        return self.page_title or self.url[:60] + "..." if len(self.url) > 60 else self.url

    @property
    def status_badge_class(self) -> str:
        """CSS class for status badge"""
        status_classes = {
            "new": "badge-new",
            "fetch_pending": "badge-pending",
            "parsed": "badge-parsed",
            "llm_pending": "badge-pending",
            "enriched": "badge-success",
            "fetch_error": "badge-error",
            "llm_error": "badge-error",
        }
        return status_classes.get(self.status, "badge-default")

    @property
    def content_type_badge_class(self) -> str:
        """CSS class for content type badge"""
        type_classes = {
            "article": "type-article",
            "video": "type-video",
            "paper": "type-paper",
            "code_repo": "type-code",
            "reference": "type-reference",
            "misc": "type-misc",
        }
        return type_classes.get(self.content_type or "", "type-default")

    @property
    def read_time_display(self) -> str:
        """Format read time for display"""
        if self.video_seconds:
            minutes = self.video_seconds // 60
            return f"{minutes}m video"
        if self.est_read_min:
            return f"{self.est_read_min}m read"
        if self.word_count:
            # Estimate ~200 words per minute
            est = max(1, self.word_count // 200)
            return f"~{est}m read"
        return "-"


class TabListResponse(BaseModel):
    """Response for tab list queries"""
    tabs: list[TabDisplay]
    total: int
    page: int
    per_page: int
    total_pages: int
    has_next: bool
    has_prev: bool


class ExportRequest(BaseModel):
    """Request for exporting tabs"""
    tab_ids: list[int] = Field(..., min_length=1, description="IDs of tabs to export")


class TabExport(BaseModel):
    """Tab data for export"""
    url: str
    title: Optional[str]
    summary: Optional[str]
    content_type: Optional[str]
    tags: list[str]
    projects: list[str]
    est_read_min: Optional[int]
    priority: Optional[str]
    window_label: Optional[str]
    created_at: str

    def to_markdown(self) -> str:
        """Convert to markdown format"""
        lines = []
        lines.append(f"## [{self.title or 'Untitled'}]({self.url})")
        lines.append("")

        if self.summary:
            lines.append(self.summary)
            lines.append("")

        metadata = []
        if self.content_type:
            metadata.append(f"**Type:** {self.content_type}")
        if self.est_read_min:
            metadata.append(f"**Read time:** {self.est_read_min} min")
        if self.priority:
            metadata.append(f"**Priority:** {self.priority}")
        if self.tags:
            metadata.append(f"**Tags:** {', '.join(self.tags)}")
        if self.projects:
            metadata.append(f"**Projects:** {', '.join(self.projects)}")

        if metadata:
            lines.append(" | ".join(metadata))
            lines.append("")

        lines.append("---")
        lines.append("")

        return "\n".join(lines)


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    database: str
