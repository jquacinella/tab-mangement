"""
TabBacklog v1 - Parser Plugins

Site-specific parsers for extracting content from web pages.
"""

from .base import BaseParser, ParsedPage, ParserRegistry
from .generic import GenericHtmlParser
from .youtube import YouTubeParser
from .twitter import TwitterParser
from .registry import get_default_registry, parse_url

__all__ = [
    "BaseParser",
    "ParsedPage",
    "ParserRegistry",
    "GenericHtmlParser",
    "YouTubeParser",
    "TwitterParser",
    "get_default_registry",
    "parse_url",
]
