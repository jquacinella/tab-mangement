"""
TabBacklog v1 - Parser Service Pydantic Models

API request/response models for the parser service.
"""

from typing import Optional
from pydantic import BaseModel, Field, HttpUrl


class FetchParseRequest(BaseModel):
    """Request model for /fetch_parse endpoint"""
    url: str = Field(..., description="URL to fetch and parse")
    timeout: float = Field(
        default=30.0,
        ge=1.0,
        le=120.0,
        description="Request timeout in seconds"
    )


class ParseHtmlRequest(BaseModel):
    """Request model for /parse_html endpoint (parse pre-fetched HTML)"""
    url: str = Field(..., description="Original URL (for parser selection)")
    html_content: str = Field(..., description="HTML content to parse")


class ParsedPageResponse(BaseModel):
    """Response model for parsed page content"""
    site_kind: str = Field(..., description="Type of site (youtube, twitter, generic_html)")
    title: Optional[str] = Field(None, description="Page/content title")
    text_full: Optional[str] = Field(None, description="Full extracted text content")
    word_count: Optional[int] = Field(None, description="Word count of text content")
    video_seconds: Optional[int] = Field(None, description="Video duration in seconds (if applicable)")
    metadata: dict = Field(default_factory=dict, description="Additional metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "site_kind": "youtube",
                "title": "Example Video Title",
                "text_full": "Example Video Title\n\nThis is the video description...",
                "word_count": 150,
                "video_seconds": 600,
                "metadata": {
                    "url": "https://youtube.com/watch?v=abc123",
                    "video_id": "abc123",
                    "uploader": "Example Channel",
                    "view_count": 10000
                }
            }
        }


class ErrorResponse(BaseModel):
    """Error response model"""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    url: Optional[str] = Field(None, description="URL that caused the error")


class HealthResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="Service version")
    parsers: list[str] = Field(..., description="Available parsers")
