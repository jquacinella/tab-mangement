"""
TabBacklog v1 - Enrichment Service Pydantic Models

API request/response models and enrichment schema.
"""

from typing import Literal, Optional
from pydantic import BaseModel, Field


class EnrichmentRequest(BaseModel):
    """Request model for /enrich_tab endpoint"""
    url: str = Field(..., description="URL of the tab")
    title: Optional[str] = Field(None, description="Page title")
    site_kind: str = Field(..., description="Type of site (youtube, twitter, generic_html)")
    text: Optional[str] = Field(None, description="Extracted text content")
    word_count: Optional[int] = Field(None, description="Word count of content")
    video_seconds: Optional[int] = Field(None, description="Video duration in seconds")

    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://example.com/article",
                "title": "Understanding Machine Learning",
                "site_kind": "generic_html",
                "text": "This article explains the fundamentals of machine learning...",
                "word_count": 1500,
            }
        }


class Enrichment(BaseModel):
    """
    LLM-generated enrichment data for a tab.

    This is the structured output from the DSPy enrichment module.
    """
    summary: str = Field(
        ...,
        description="Brief summary of the content (2-3 sentences)",
        min_length=10,
        max_length=500,
    )
    content_type: Literal["article", "video", "paper", "code_repo", "reference", "misc"] = Field(
        ...,
        description="Type of content",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Relevant tags (e.g., #video, #longread, #tutorial)",
        max_length=10,
    )
    projects: list[str] = Field(
        default_factory=list,
        description="Related project categories",
        max_length=5,
    )
    est_read_min: Optional[int] = Field(
        None,
        description="Estimated reading/watch time in minutes",
        ge=1,
        le=600,
    )
    priority: Optional[Literal["high", "medium", "low"]] = Field(
        None,
        description="Suggested priority level",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "summary": "A comprehensive guide to machine learning fundamentals, covering supervised and unsupervised learning approaches with practical examples.",
                "content_type": "article",
                "tags": ["#tutorial", "#machinelearning", "#longread"],
                "projects": ["other_research"],
                "est_read_min": 15,
                "priority": "medium",
            }
        }


class EnrichmentResponse(BaseModel):
    """Response model for successful enrichment"""
    url: str = Field(..., description="URL that was enriched")
    enrichment: Enrichment = Field(..., description="Generated enrichment data")
    model_name: str = Field(..., description="LLM model used for enrichment")


class EnrichmentErrorResponse(BaseModel):
    """Response model for enrichment errors"""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    url: Optional[str] = Field(None, description="URL that failed enrichment")
    raw_output: Optional[str] = Field(None, description="Raw LLM output if parsing failed")
    attempts: int = Field(default=1, description="Number of attempts made")


class HealthResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="Service version")
    model_name: str = Field(..., description="Configured LLM model")
    llm_status: str = Field(..., description="LLM connection status")
