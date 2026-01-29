"""
TabBacklog v1 - Parser Base Class and Registry

This module defines the base parser interface and registry system
for site-specific content parsers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Type, Dict, List
import re
from urllib.parse import urlparse


@dataclass
class ParsedPage:
    """Structured representation of parsed page content"""
    
    site_kind: str  # youtube | twitter | generic_html | etc.
    title: Optional[str] = None
    text_full: Optional[str] = None
    word_count: Optional[int] = None
    video_seconds: Optional[int] = None
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "site_kind": self.site_kind,
            "title": self.title,
            "text_full": self.text_full,
            "word_count": self.word_count,
            "video_seconds": self.video_seconds,
            "metadata": self.metadata,
        }


class BaseParser(ABC):
    """
    Abstract base class for site-specific parsers.
    
    Each parser must implement:
    - match(url): Return True if this parser can handle the URL
    - parse(url, html_content): Return ParsedPage with extracted content
    """
    
    @abstractmethod
    def match(self, url: str) -> bool:
        """
        Determine if this parser can handle the given URL.
        
        Args:
            url: The URL to check
            
        Returns:
            True if this parser should be used for this URL
        """
        pass
    
    @abstractmethod
    def parse(self, url: str, html_content: str) -> ParsedPage:
        """
        Parse the page content and extract relevant information.
        
        Args:
            url: The original URL
            html_content: The raw HTML content
            
        Returns:
            ParsedPage with extracted content
        """
        pass
    
    def extract_domain(self, url: str) -> str:
        """Helper to extract domain from URL"""
        parsed = urlparse(url)
        return parsed.netloc.lower()
    
    def count_words(self, text: Optional[str]) -> int:
        """Helper to count words in text"""
        if not text:
            return 0
        # Simple word count - split on whitespace
        return len(text.split())


class ParserRegistry:
    """
    Registry for managing parser instances.
    
    Parsers are checked in registration order, so register more specific
    parsers before generic ones.
    """
    
    def __init__(self):
        self._parsers: List[BaseParser] = []
    
    def register(self, parser: BaseParser) -> None:
        """
        Register a parser instance.
        
        Args:
            parser: Instance of a BaseParser subclass
        """
        self._parsers.append(parser)
    
    def get_parser(self, url: str) -> Optional[BaseParser]:
        """
        Find the first parser that matches the given URL.
        
        Args:
            url: The URL to find a parser for
            
        Returns:
            A parser instance if found, None otherwise
        """
        for parser in self._parsers:
            if parser.match(url):
                return parser
        return None
    
    def parse_page(self, url: str, html_content: str) -> ParsedPage:
        """
        Parse a page using the appropriate parser.
        
        Args:
            url: The URL of the page
            html_content: The raw HTML content
            
        Returns:
            ParsedPage with extracted content
            
        Raises:
            ValueError: If no parser matches the URL
        """
        parser = self.get_parser(url)
        if parser is None:
            raise ValueError(f"No parser found for URL: {url}")
        
        return parser.parse(url, html_content)
    
    def list_parsers(self) -> List[str]:
        """Get list of registered parser class names"""
        return [parser.__class__.__name__ for parser in self._parsers]


# Global registry instance
_global_registry = ParserRegistry()


def register_parser(parser: BaseParser) -> None:
    """
    Register a parser with the global registry.
    
    Args:
        parser: Instance of a BaseParser subclass
    """
    _global_registry.register(parser)


def get_parser(url: str) -> Optional[BaseParser]:
    """
    Get a parser for the given URL from the global registry.
    
    Args:
        url: The URL to find a parser for
        
    Returns:
        A parser instance if found, None otherwise
    """
    return _global_registry.get_parser(url)


def parse_page(url: str, html_content: str) -> ParsedPage:
    """
    Parse a page using the global registry.
    
    Args:
        url: The URL of the page
        html_content: The raw HTML content
        
    Returns:
        ParsedPage with extracted content
        
    Raises:
        ValueError: If no parser matches the URL
    """
    return _global_registry.parse_page(url, html_content)


def list_parsers() -> List[str]:
    """Get list of registered parsers from global registry"""
    return _global_registry.list_parsers()


# Example usage and testing
if __name__ == "__main__":
    # Example: Create a simple test parser
    class TestParser(BaseParser):
        def match(self, url: str) -> bool:
            return "example.com" in url
        
        def parse(self, url: str, html_content: str) -> ParsedPage:
            return ParsedPage(
                site_kind="test",
                title="Test Page",
                text_full="This is test content",
                word_count=4,
                metadata={"test": True}
            )
    
    # Register the test parser
    register_parser(TestParser())
    
    # Test
    test_url = "https://example.com/test"
    parser = get_parser(test_url)
    print(f"Parser for {test_url}: {parser.__class__.__name__ if parser else 'None'}")
    
    # List all parsers
    print(f"Registered parsers: {list_parsers()}")
