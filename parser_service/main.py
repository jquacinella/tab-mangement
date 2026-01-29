"""
TabBacklog v1 - Parser Service

FastAPI service for fetching and parsing web pages.
Provides endpoints for parsing URLs with site-specific handlers.
"""

import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .models import (
    FetchParseRequest,
    ParseHtmlRequest,
    ParsedPageResponse,
    ErrorResponse,
    HealthResponse,
)
from .parsers import get_default_registry, parse_url as do_parse_url
from .parsers.registry import parse_html, get_registry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Initialize the parser registry on startup
    registry = get_registry()
    logger.info(f"Parser service starting with parsers: {registry.list_parsers()}")
    yield
    logger.info("Parser service shutting down")


app = FastAPI(
    title="TabBacklog Parser Service",
    description="Fetches and parses web pages to extract structured content",
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


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Check service health and list available parsers."""
    registry = get_registry()
    return HealthResponse(
        status="healthy",
        version=__version__,
        parsers=registry.list_parsers(),
    )


@app.post(
    "/fetch_parse",
    response_model=ParsedPageResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        500: {"model": ErrorResponse, "description": "Parsing or fetch error"},
    },
    tags=["Parsing"],
)
async def fetch_and_parse(request: FetchParseRequest):
    """
    Fetch a URL and parse its content.

    The appropriate parser is automatically selected based on the URL:
    - YouTube URLs: Uses yt-dlp for metadata extraction
    - Twitter/X URLs: Extracts tweet content from meta tags
    - Other URLs: Generic HTML parsing

    Returns structured content including title, text, and metadata.
    """
    logger.info(f"Fetching and parsing URL: {request.url}")

    try:
        parsed = await do_parse_url(request.url, timeout=request.timeout)

        logger.info(
            f"Successfully parsed {request.url} as {parsed.site_kind}, "
            f"word_count={parsed.word_count}"
        )

        return ParsedPageResponse(
            site_kind=parsed.site_kind,
            title=parsed.title,
            text_full=parsed.text_full,
            word_count=parsed.word_count,
            video_seconds=parsed.video_seconds,
            metadata=parsed.metadata,
        )

    except httpx.TimeoutException:
        logger.warning(f"Timeout fetching URL: {request.url}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="Fetch timeout",
                detail=f"Request timed out after {request.timeout} seconds",
                url=request.url,
            ).model_dump(),
        )

    except httpx.HTTPStatusError as e:
        logger.warning(f"HTTP error fetching URL {request.url}: {e.response.status_code}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="HTTP error",
                detail=f"Received status {e.response.status_code}",
                url=request.url,
            ).model_dump(),
        )

    except httpx.RequestError as e:
        logger.warning(f"Request error fetching URL {request.url}: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="Request failed",
                detail=str(e),
                url=request.url,
            ).model_dump(),
        )

    except ValueError as e:
        logger.warning(f"Parse error for URL {request.url}: {e}")
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(
                error="Parse error",
                detail=str(e),
                url=request.url,
            ).model_dump(),
        )

    except Exception as e:
        logger.exception(f"Unexpected error parsing URL {request.url}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="Internal error",
                detail=str(e),
                url=request.url,
            ).model_dump(),
        )


@app.post(
    "/parse_html",
    response_model=ParsedPageResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        500: {"model": ErrorResponse, "description": "Parsing error"},
    },
    tags=["Parsing"],
)
async def parse_html_content(request: ParseHtmlRequest):
    """
    Parse pre-fetched HTML content.

    Use this endpoint when you already have the HTML content and don't
    need the service to fetch it. The URL is still required for
    parser selection.
    """
    logger.info(f"Parsing HTML for URL: {request.url}")

    try:
        parsed = parse_html(request.url, request.html_content)

        logger.info(
            f"Successfully parsed HTML for {request.url} as {parsed.site_kind}, "
            f"word_count={parsed.word_count}"
        )

        return ParsedPageResponse(
            site_kind=parsed.site_kind,
            title=parsed.title,
            text_full=parsed.text_full,
            word_count=parsed.word_count,
            video_seconds=parsed.video_seconds,
            metadata=parsed.metadata,
        )

    except ValueError as e:
        logger.warning(f"Parse error for URL {request.url}: {e}")
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(
                error="Parse error",
                detail=str(e),
                url=request.url,
            ).model_dump(),
        )

    except Exception as e:
        logger.exception(f"Unexpected error parsing HTML for {request.url}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="Internal error",
                detail=str(e),
                url=request.url,
            ).model_dump(),
        )


@app.get("/parsers", tags=["Info"])
async def list_parsers():
    """List all available parsers."""
    registry = get_registry()
    return {"parsers": registry.list_parsers()}


# Run with: uvicorn parser_service.main:app --host 0.0.0.0 --port 8001
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
