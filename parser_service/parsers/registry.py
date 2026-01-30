"""
TabBacklog v1 - Parser Registry

Pre-configured parser registry with all available parsers.
Parsers are registered in order of specificity (most specific first).
"""

from typing import Optional
import httpx

from .base import ParsedPage, ParserRegistry
from .youtube import YouTubeParser
from .twitter import TwitterParser
from .generic import GenericHtmlParser


def get_default_registry() -> ParserRegistry:
    """
    Create and return a parser registry with all default parsers.

    Parsers are registered in order of specificity:
    1. YouTube (most specific)
    2. Twitter/X
    3. Generic HTML (fallback, matches everything)
    """
    registry = ParserRegistry()

    # Register specific parsers first
    registry.register(YouTubeParser())
    registry.register(TwitterParser())

    # Register generic parser last (fallback)
    registry.register(GenericHtmlParser())

    return registry


# Global default registry
_default_registry: Optional[ParserRegistry] = None


def get_registry() -> ParserRegistry:
    """Get the global default registry, creating it if necessary."""
    global _default_registry
    if _default_registry is None:
        _default_registry = get_default_registry()
    return _default_registry


async def fetch_url(url: str, timeout: float = 30.0) -> str:
    """
    Fetch HTML content from a URL.

    Args:
        url: The URL to fetch
        timeout: Request timeout in seconds

    Returns:
        HTML content as string

    Raises:
        httpx.HTTPError: If the request fails
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        return response.text


async def parse_url(url: str, timeout: float = 30.0) -> ParsedPage:
    """
    Fetch and parse a URL using the appropriate parser.

    Args:
        url: The URL to fetch and parse
        timeout: Request timeout in seconds

    Returns:
        ParsedPage with extracted content

    Raises:
        ValueError: If no parser matches the URL
        httpx.HTTPError: If the request fails
    """
    registry = get_registry()

    # Fetch the HTML content
    html_content = await fetch_url(url, timeout)

    # Parse with the appropriate parser
    return registry.parse_page(url, html_content)


def parse_html(url: str, html_content: str) -> ParsedPage:
    """
    Parse HTML content using the appropriate parser.

    Args:
        url: The original URL (used for parser selection)
        html_content: The HTML content to parse

    Returns:
        ParsedPage with extracted content

    Raises:
        ValueError: If no parser matches the URL
    """
    registry = get_registry()
    return registry.parse_page(url, html_content)
