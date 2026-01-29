"""
TabBacklog v1 - Enrichment Service

FastAPI service for LLM-based content enrichment using DSPy.
Generates summaries, classifications, and metadata for tabs.
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from . import __version__
from .models import (
    EnrichmentRequest,
    Enrichment,
    EnrichmentResponse,
    EnrichmentErrorResponse,
    HealthResponse,
)
from .dspy_setup import (
    configure_dspy_from_env,
    get_enricher,
    test_llm_connection,
    TabEnricher,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Global state
_model_name: str = ""
_enricher: Optional[TabEnricher] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    global _model_name, _enricher

    # Configure DSPy on startup
    logger.info("Enrichment service starting...")
    try:
        _model_name = configure_dspy_from_env()
        _enricher = get_enricher()
        logger.info(f"Enrichment service ready with model: {_model_name}")
    except Exception as e:
        logger.error(f"Failed to configure DSPy: {e}")
        raise

    yield

    logger.info("Enrichment service shutting down")


app = FastAPI(
    title="TabBacklog Enrichment Service",
    description="LLM-based content enrichment for tab metadata generation",
    version=__version__,
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_max_retries() -> int:
    """Get max retries from environment."""
    return int(os.environ.get("MAX_RETRIES", "3"))


class EnrichmentError(Exception):
    """Custom exception for enrichment failures."""
    def __init__(self, message: str, raw_output: Optional[str] = None):
        super().__init__(message)
        self.raw_output = raw_output


def enrich_with_retry(request: EnrichmentRequest) -> Enrichment:
    """
    Attempt enrichment with retries on validation failure.

    Args:
        request: The enrichment request

    Returns:
        Enrichment object on success

    Raises:
        EnrichmentError: If all retries fail
    """
    max_retries = get_max_retries()
    last_error = None
    raw_output = None

    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Enrichment attempt {attempt}/{max_retries} for {request.url}")

            result = _enricher(
                url=request.url,
                title=request.title or "Untitled",
                site_kind=request.site_kind,
                text=request.text or "",
                word_count=request.word_count or 0,
                video_seconds=request.video_seconds or 0,
            )

            # Convert DSPy output to our Pydantic model
            enrichment = Enrichment(
                summary=result.summary,
                content_type=result.content_type,
                tags=result.tags[:10] if result.tags else [],  # Limit tags
                projects=result.projects[:5] if result.projects else [],  # Limit projects
                est_read_min=result.est_read_min,
                priority=result.priority,
            )

            logger.info(f"Successfully enriched {request.url} on attempt {attempt}")
            return enrichment

        except Exception as e:
            last_error = str(e)
            # Try to capture raw output if available
            if hasattr(e, 'raw_output'):
                raw_output = e.raw_output
            logger.warning(f"Enrichment attempt {attempt} failed: {e}")

    raise EnrichmentError(
        f"Enrichment failed after {max_retries} attempts: {last_error}",
        raw_output=raw_output,
    )


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Check service health and LLM connection status."""
    llm_ok = await test_llm_connection()

    return HealthResponse(
        status="healthy" if llm_ok else "degraded",
        version=__version__,
        model_name=_model_name,
        llm_status="connected" if llm_ok else "disconnected",
    )


@app.post(
    "/enrich_tab",
    response_model=EnrichmentResponse,
    responses={
        400: {"model": EnrichmentErrorResponse, "description": "Invalid request"},
        500: {"model": EnrichmentErrorResponse, "description": "Enrichment failed"},
    },
    tags=["Enrichment"],
)
async def enrich_tab(request: EnrichmentRequest):
    """
    Generate LLM-based enrichment for a tab.

    Takes parsed content (URL, title, text) and generates:
    - Summary: Brief 2-3 sentence description
    - Content type: article, video, paper, code_repo, reference, or misc
    - Tags: Relevant hashtags for organization
    - Projects: Related project categories
    - Estimated read time: In minutes
    - Priority: high, medium, or low

    Automatically retries on validation failures (up to 3 attempts).
    """
    logger.info(f"Enrichment request for: {request.url}")

    if _enricher is None:
        raise HTTPException(
            status_code=500,
            detail=EnrichmentErrorResponse(
                error="Service not initialized",
                detail="DSPy enricher not configured",
                url=request.url,
            ).model_dump(),
        )

    try:
        enrichment = enrich_with_retry(request)

        return EnrichmentResponse(
            url=request.url,
            enrichment=enrichment,
            model_name=_model_name,
        )

    except EnrichmentError as e:
        logger.error(f"Enrichment failed for {request.url}: {e}")
        raise HTTPException(
            status_code=500,
            detail=EnrichmentErrorResponse(
                error="Enrichment failed",
                detail=str(e),
                url=request.url,
                raw_output=e.raw_output,
                attempts=get_max_retries(),
            ).model_dump(),
        )

    except Exception as e:
        logger.exception(f"Unexpected error enriching {request.url}")
        raise HTTPException(
            status_code=500,
            detail=EnrichmentErrorResponse(
                error="Internal error",
                detail=str(e),
                url=request.url,
            ).model_dump(),
        )


@app.post(
    "/enrich_batch",
    response_model=list[EnrichmentResponse],
    tags=["Enrichment"],
)
async def enrich_batch(requests: list[EnrichmentRequest]):
    """
    Enrich multiple tabs in a single request.

    Processes each tab sequentially. Failed enrichments are skipped
    and not included in the response (check response length vs input).
    """
    results = []

    for request in requests:
        try:
            enrichment = enrich_with_retry(request)
            results.append(EnrichmentResponse(
                url=request.url,
                enrichment=enrichment,
                model_name=_model_name,
            ))
        except Exception as e:
            logger.warning(f"Skipping failed enrichment for {request.url}: {e}")
            continue

    return results


@app.get("/model", tags=["Info"])
async def get_model_info():
    """Get information about the configured LLM model."""
    return {
        "model_name": _model_name,
        "max_retries": get_max_retries(),
    }


# Run with: uvicorn enrichment_service.main:app --host 0.0.0.0 --port 8002
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
