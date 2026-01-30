"""
TabBacklog v1 - DSPy Configuration and Enrichment Module

Sets up DSPy with OpenAI-compatible API and defines the enrichment signature.
"""

import logging
import os
from typing import Literal, Optional

import dspy
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# Project categories that the LLM should classify into
PROJECT_CATEGORIES = [
    "argumentation_on_the_web",
    "democratic_economic_planning",
    "other_research",
    "personal",
    "work",
]

# Content type options
CONTENT_TYPES = ["article", "video", "paper", "code_repo", "reference", "misc"]


class EnrichmentOutput(BaseModel):
    """Structured output schema for the enrichment LLM call."""
    summary: str = Field(
        description="A brief 2-3 sentence summary of the content"
    )
    content_type: Literal["article", "video", "paper", "code_repo", "reference", "misc"] = Field(
        description="The type of content"
    )
    tags: list[str] = Field(
        description="3-5 relevant tags starting with # (e.g., #tutorial, #longread, #video)"
    )
    projects: list[str] = Field(
        description=f"Related project categories from: {', '.join(PROJECT_CATEGORIES)}"
    )
    est_read_min: Optional[int] = Field(
        description="Estimated reading/watching time in minutes"
    )
    priority: Optional[Literal["high", "medium", "low"]] = Field(
        description="Suggested priority based on content importance"
    )


class EnrichTabSignature(dspy.Signature):
    """
    Analyze web content and generate structured metadata for organization.

    Given information about a web page (URL, title, content), generate:
    - A concise summary
    - Content type classification
    - Relevant tags
    - Project categorization
    - Estimated reading time
    - Priority level
    """

    url: str = dspy.InputField(desc="The URL of the content")
    title: str = dspy.InputField(desc="The title of the content")
    site_kind: str = dspy.InputField(desc="Type of site (youtube, twitter, generic_html)")
    text: str = dspy.InputField(desc="The main text content (may be truncated)")
    word_count: int = dspy.InputField(desc="Word count of the full content")
    video_seconds: int = dspy.InputField(desc="Video duration in seconds (0 if not a video)")

    enrichment: EnrichmentOutput = dspy.OutputField(
        desc="Structured enrichment metadata"
    )


class TabEnricher(dspy.Module):
    """DSPy module for enriching tab content."""

    def __init__(self):
        super().__init__()
        self.enrich = dspy.Predict(EnrichTabSignature)

    def forward(
        self,
        url: str,
        title: str,
        site_kind: str,
        text: str,
        word_count: int = 0,
        video_seconds: int = 0,
    ) -> EnrichmentOutput:
        """
        Generate enrichment for a tab.

        Args:
            url: The URL of the content
            title: The title of the content
            site_kind: Type of site (youtube, twitter, generic_html)
            text: The main text content
            word_count: Word count of the content
            video_seconds: Video duration in seconds (0 if not video)

        Returns:
            EnrichmentOutput with structured metadata
        """
        # Truncate text if too long (keep under token limits)
        max_text_chars = 4000
        if len(text) > max_text_chars:
            text = text[:max_text_chars] + "... [truncated]"

        result = self.enrich(
            url=url,
            title=title or "Untitled",
            site_kind=site_kind,
            text=text or "No content available",
            word_count=word_count or 0,
            video_seconds=video_seconds or 0,
        )

        return result.enrichment


def configure_dspy(
    api_base: str,
    api_key: str,
    model_name: str,
    timeout: int = 60,
    temperature: float = 0.7,
) -> None:
    """
    Configure DSPy to use an OpenAI-compatible API.

    Args:
        api_base: Base URL for the API (e.g., http://localhost:1234/v1)
        api_key: API key (can be dummy for local models)
        model_name: Model name to use
        timeout: Request timeout in seconds
        temperature: Sampling temperature (0.0-1.0, higher = more creative)
    """
    logger.info(f"Configuring DSPy with model: {model_name} at {api_base}")

    lm = dspy.LM(
        model=f"openai/{model_name}",
        api_base=api_base,
        api_key=api_key,
        temperature=temperature,
        max_tokens=1024,
        timeout=timeout,
    )

    dspy.configure(lm=lm)
    logger.info("DSPy configured successfully")


def configure_dspy_from_env() -> str:
    """
    Configure DSPy from environment variables.

    Environment variables:
        LLM_API_BASE: Base URL for the API
        LLM_API_KEY: API key
        LLM_MODEL_NAME: Model name
        LLM_TIMEOUT: Request timeout in seconds
        LLM_TEMPERATURE: Sampling temperature (0.0-1.0)

    Returns:
        The model name that was configured
    """
    api_base = os.environ.get("LLM_API_BASE", "http://localhost:1234/v1")
    api_key = os.environ.get("LLM_API_KEY", "dummy_key")
    model_name = os.environ.get("LLM_MODEL_NAME", "llama-3.1-8b-instruct")
    timeout = int(os.environ.get("LLM_TIMEOUT", "60"))
    temperature = float(os.environ.get("LLM_TEMPERATURE", "0.7"))

    configure_dspy(api_base, api_key, model_name, timeout, temperature)
    return model_name


def get_enricher() -> TabEnricher:
    """Get a configured TabEnricher instance."""
    return TabEnricher()


async def test_llm_connection() -> bool:
    """
    Test if the LLM is reachable and responding.

    Performs a lightweight check by verifying DSPy configuration
    rather than making an actual LLM call.

    Returns:
        True if connection successful, False otherwise
    """
    try:
        # Check if DSPy is configured
        if dspy.settings.lm is None:
            logger.warning("DSPy LM not configured")
            return False
        
        # Verify we can create an enricher instance
        enricher = get_enricher()
        if enricher is None or enricher.enrich is None:
            logger.warning("Failed to create enricher instance")
            return False
        
        return True
    except Exception as e:
        logger.warning(f"LLM connection test failed: {e}")
        return False
