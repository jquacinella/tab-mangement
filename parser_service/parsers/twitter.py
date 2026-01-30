"""
TabBacklog v1 - Twitter/X Parser

Parses Twitter (X) posts/tweets by extracting content from meta tags
and structured data.
"""

import re
from typing import Optional
from urllib.parse import urlparse
from bs4 import BeautifulSoup

from .base import BaseParser, ParsedPage


class TwitterParser(BaseParser):
    """
    Parser for Twitter/X posts.

    Extracts:
    - Tweet text from meta tags
    - Author information
    - Timestamp
    - Engagement metrics (if available)

    Note: Due to Twitter's heavy JavaScript usage, we rely on meta tags
    which are generally present for SEO/sharing purposes.
    """

    # Twitter/X domains
    TWITTER_DOMAINS = {"twitter.com", "www.twitter.com", "x.com", "www.x.com", "mobile.twitter.com"}

    # URL patterns for tweets/posts
    TWEET_PATTERNS = [
        r"(?:https?://)?(?:www\.|mobile\.)?(?:twitter|x)\.com/\w+/status/\d+",
    ]

    def match(self, url: str) -> bool:
        """Check if URL is a Twitter/X post."""
        domain = self.extract_domain(url)
        if domain not in self.TWITTER_DOMAINS:
            return False

        # Check if it's a status/post URL (not profile, search, etc.)
        for pattern in self.TWEET_PATTERNS:
            if re.match(pattern, url):
                return True

        # Also match if path contains /status/
        parsed = urlparse(url)
        return "/status/" in parsed.path

    def parse(self, url: str, html_content: str) -> ParsedPage:
        """Parse Twitter/X post from HTML content."""
        soup = BeautifulSoup(html_content, "html.parser")

        title = self._extract_title(soup)
        text_content = self._extract_tweet_text(soup)
        author = self._extract_author(soup, url)
        metadata = self._extract_metadata(soup, url, author)

        # Combine title and text for full content
        text_full = text_content or title

        return ParsedPage(
            site_kind="twitter",
            title=title,
            text_full=text_full,
            word_count=self.count_words(text_full),
            video_seconds=None,
            metadata=metadata,
        )

    def _extract_title(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract title from Twitter page."""
        # Try og:title first
        og_title = soup.find("meta", attrs={"property": "og:title"})
        if og_title and og_title.get("content"):
            return og_title["content"]

        # Try twitter:title
        tw_title = soup.find("meta", attrs={"name": "twitter:title"})
        if tw_title and tw_title.get("content"):
            return tw_title["content"]

        # Fall back to page title
        title_tag = soup.find("title")
        if title_tag:
            title = title_tag.get_text(strip=True)
            # Clean up Twitter title format
            if " / X" in title:
                title = title.replace(" / X", "")
            elif " / Twitter" in title:
                title = title.replace(" / Twitter", "")
            return title

        return None

    def _extract_tweet_text(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract the actual tweet text."""
        # Try og:description - usually contains the tweet
        og_desc = soup.find("meta", attrs={"property": "og:description"})
        if og_desc and og_desc.get("content"):
            text = og_desc["content"]
            # Twitter often wraps text in quotes for og:description
            if text.startswith('"') and text.endswith('"'):
                text = text[1:-1]
            return text

        # Try twitter:description
        tw_desc = soup.find("meta", attrs={"name": "twitter:description"})
        if tw_desc and tw_desc.get("content"):
            return tw_desc["content"]

        # Try standard description
        desc = soup.find("meta", attrs={"name": "description"})
        if desc and desc.get("content"):
            return desc["content"]

        return None

    def _extract_author(self, soup: BeautifulSoup, url: str) -> dict:
        """Extract author information."""
        author = {}

        # Extract username from URL
        parsed = urlparse(url)
        path_parts = parsed.path.strip("/").split("/")
        if path_parts:
            author["username"] = path_parts[0]

        # Try to get display name from title or meta
        # Title format is often: "Display Name on X: "tweet text""
        title_tag = soup.find("title")
        if title_tag:
            title_text = title_tag.get_text(strip=True)
            # Pattern: "Display Name on X: ..." or "Display Name (@username) / X"
            match = re.match(r'^([^(@]+?)(?:\s+on\s+(?:X|Twitter):|(?:\s*\(@\w+\)\s*/\s*(?:X|Twitter)))', title_text)
            if match:
                author["display_name"] = match.group(1).strip()

        # Try twitter:creator meta tag
        creator = soup.find("meta", attrs={"name": "twitter:creator"})
        if creator and creator.get("content"):
            author["twitter_handle"] = creator["content"]

        return author

    def _extract_metadata(self, soup: BeautifulSoup, url: str, author: dict) -> dict:
        """Extract metadata from the page."""
        metadata = {
            "url": url,
            "domain": self.extract_domain(url),
            "platform": "twitter" if "twitter.com" in url else "x",
        }

        # Add author info
        if author:
            metadata["author"] = author

        # Extract tweet ID from URL
        tweet_id = self._extract_tweet_id(url)
        if tweet_id:
            metadata["tweet_id"] = tweet_id

        # Try to get image
        og_image = soup.find("meta", attrs={"property": "og:image"})
        if og_image and og_image.get("content"):
            metadata["image"] = og_image["content"]

        # Try to get site name
        og_site = soup.find("meta", attrs={"property": "og:site_name"})
        if og_site and og_site.get("content"):
            metadata["site_name"] = og_site["content"]

        # Check for media type indicators
        og_type = soup.find("meta", attrs={"property": "og:type"})
        if og_type and og_type.get("content"):
            metadata["content_type"] = og_type["content"]

        # Check for video content
        og_video = soup.find("meta", attrs={"property": "og:video"})
        if og_video:
            metadata["has_video"] = True

        # Check for card type
        tw_card = soup.find("meta", attrs={"name": "twitter:card"})
        if tw_card and tw_card.get("content"):
            metadata["card_type"] = tw_card["content"]

        return metadata

    def _extract_tweet_id(self, url: str) -> Optional[str]:
        """Extract tweet ID from URL."""
        # Pattern: /status/1234567890
        match = re.search(r"/status/(\d+)", url)
        return match.group(1) if match else None
