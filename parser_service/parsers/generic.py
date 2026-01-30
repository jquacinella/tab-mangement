"""
TabBacklog v1 - Generic HTML Parser

Parses generic web pages to extract title, main content, and metadata.
Used as a fallback for URLs that don't match specific parsers.
"""

import re
from typing import Optional
from bs4 import BeautifulSoup, NavigableString

from .base import BaseParser, ParsedPage


class GenericHtmlParser(BaseParser):
    """
    Generic parser for HTML web pages.

    Extracts:
    - Page title from <title> tag
    - Main text content from <article>, <main>, or <p> tags
    - Word count
    - Basic metadata (description, author, etc.)
    """

    # Tags that typically contain main content
    CONTENT_TAGS = ["article", "main", "[role='main']"]

    # Tags to exclude from text extraction
    EXCLUDED_TAGS = {
        "script", "style", "nav", "header", "footer", "aside",
        "noscript", "iframe", "form", "button", "input", "select",
        "textarea", "svg", "canvas", "video", "audio"
    }

    def match(self, url: str) -> bool:
        """
        Generic parser matches all HTTP(S) URLs as a fallback.
        Should be registered last in the registry.
        """
        return url.startswith(("http://", "https://"))

    def parse(self, url: str, html_content: str) -> ParsedPage:
        """Parse HTML content and extract relevant information."""
        soup = BeautifulSoup(html_content, "html.parser")

        title = self._extract_title(soup)
        text_content = self._extract_text(soup)
        word_count = self.count_words(text_content)
        metadata = self._extract_metadata(soup, url)

        return ParsedPage(
            site_kind="generic_html",
            title=title,
            text_full=text_content,
            word_count=word_count,
            video_seconds=None,
            metadata=metadata,
        )

    def _extract_title(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract page title from <title> or <h1> tag."""
        # Try <title> first
        title_tag = soup.find("title")
        if title_tag:
            title = title_tag.get_text(strip=True)
            if title:
                return self._clean_title(title)

        # Fall back to first <h1>
        h1_tag = soup.find("h1")
        if h1_tag:
            return h1_tag.get_text(strip=True)

        return None

    def _clean_title(self, title: str) -> str:
        """Clean up title by removing common suffixes."""
        # Remove common site name suffixes like " | Site Name" or " - Site Name"
        separators = [" | ", " - ", " – ", " — ", " :: "]
        for sep in separators:
            if sep in title:
                parts = title.split(sep)
                # Keep the first part if it's substantial
                if len(parts[0]) > 10:
                    title = parts[0]
                    break
        return title.strip()

    def _extract_text(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract main text content from the page."""
        # Remove excluded tags
        for tag in soup.find_all(self.EXCLUDED_TAGS):
            tag.decompose()

        # Try to find main content container
        main_content = None
        for selector in self.CONTENT_TAGS:
            if selector.startswith("["):
                # Attribute selector
                main_content = soup.select_one(selector)
            else:
                main_content = soup.find(selector)
            if main_content:
                break

        # Fall back to body if no main content found
        if not main_content:
            main_content = soup.find("body")

        if not main_content:
            return None

        # Extract text from paragraphs
        paragraphs = []
        for p in main_content.find_all(["p", "li", "h1", "h2", "h3", "h4", "h5", "h6"]):
            text = p.get_text(strip=True)
            if text and len(text) > 20:  # Filter out very short fragments
                paragraphs.append(text)

        if not paragraphs:
            # Fall back to all text
            text = main_content.get_text(separator=" ", strip=True)
            return self._clean_text(text) if text else None

        return "\n\n".join(paragraphs)

    def _clean_text(self, text: str) -> str:
        """Clean up extracted text."""
        # Normalize whitespace
        text = re.sub(r"\s+", " ", text)
        # Remove excessive punctuation
        text = re.sub(r"[.]{3,}", "...", text)
        return text.strip()

    def _extract_metadata(self, soup: BeautifulSoup, url: str) -> dict:
        """Extract metadata from meta tags."""
        metadata = {
            "url": url,
            "domain": self.extract_domain(url),
        }

        # Extract common meta tags
        meta_mappings = {
            "description": ["description", "og:description", "twitter:description"],
            "author": ["author", "og:author", "article:author"],
            "published": ["article:published_time", "datePublished", "date"],
            "image": ["og:image", "twitter:image"],
            "site_name": ["og:site_name"],
            "type": ["og:type"],
        }

        for key, names in meta_mappings.items():
            for name in names:
                # Try name attribute
                meta = soup.find("meta", attrs={"name": name})
                if meta and meta.get("content"):
                    metadata[key] = meta["content"]
                    break
                # Try property attribute (for Open Graph)
                meta = soup.find("meta", attrs={"property": name})
                if meta and meta.get("content"):
                    metadata[key] = meta["content"]
                    break

        # Extract canonical URL
        canonical = soup.find("link", attrs={"rel": "canonical"})
        if canonical and canonical.get("href"):
            metadata["canonical_url"] = canonical["href"]

        # Extract language
        html_tag = soup.find("html")
        if html_tag and html_tag.get("lang"):
            metadata["language"] = html_tag["lang"]

        return metadata
