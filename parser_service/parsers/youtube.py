"""
TabBacklog v1 - YouTube Parser

Parses YouTube video pages using yt-dlp to extract metadata.
"""

import json
import subprocess
import re
from typing import Optional
from urllib.parse import urlparse, parse_qs

from .base import BaseParser, ParsedPage


class YouTubeParser(BaseParser):
    """
    Parser for YouTube video pages.

    Uses yt-dlp to extract video metadata including:
    - Title
    - Description
    - Duration
    - Uploader/channel info
    - View count, likes
    - Upload date
    """

    # YouTube URL patterns
    YOUTUBE_PATTERNS = [
        r"(?:https?://)?(?:www\.)?youtube\.com/watch\?v=[\w-]+",
        r"(?:https?://)?(?:www\.)?youtube\.com/shorts/[\w-]+",
        r"(?:https?://)?youtu\.be/[\w-]+",
        r"(?:https?://)?(?:www\.)?youtube\.com/embed/[\w-]+",
        r"(?:https?://)?(?:www\.)?youtube\.com/v/[\w-]+",
    ]

    def __init__(self, timeout: int = 30):
        """
        Initialize YouTube parser.

        Args:
            timeout: Timeout in seconds for yt-dlp commands
        """
        self.timeout = timeout

    def match(self, url: str) -> bool:
        """Check if URL is a YouTube video."""
        for pattern in self.YOUTUBE_PATTERNS:
            if re.match(pattern, url):
                return True

        # Also check domain
        domain = self.extract_domain(url)
        return domain in ("youtube.com", "www.youtube.com", "youtu.be")

    def parse(self, url: str, html_content: str) -> ParsedPage:
        """
        Parse YouTube video using yt-dlp.

        Note: html_content is ignored - we use yt-dlp for reliable extraction.
        """
        try:
            video_info = self._fetch_video_info(url)
            return self._create_parsed_page(url, video_info)
        except Exception as e:
            # Fall back to basic HTML parsing if yt-dlp fails
            return self._fallback_parse(url, html_content, str(e))

    def _fetch_video_info(self, url: str) -> dict:
        """Fetch video metadata using yt-dlp."""
        cmd = [
            "yt-dlp",
            "--dump-json",
            "--no-download",
            "--no-playlist",
            "--no-warnings",
            url,
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=self.timeout,
        )

        if result.returncode != 0:
            raise RuntimeError(f"yt-dlp failed: {result.stderr}")

        return json.loads(result.stdout)

    def _create_parsed_page(self, url: str, info: dict) -> ParsedPage:
        """Create ParsedPage from yt-dlp JSON output."""
        title = info.get("title")
        description = info.get("description", "")
        duration = info.get("duration")  # in seconds

        # Build full text from title and description
        text_parts = []
        if title:
            text_parts.append(title)
        if description:
            text_parts.append(description)
        text_full = "\n\n".join(text_parts) if text_parts else None

        # Extract metadata
        metadata = {
            "url": url,
            "video_id": info.get("id"),
            "uploader": info.get("uploader"),
            "uploader_id": info.get("uploader_id"),
            "channel": info.get("channel"),
            "channel_id": info.get("channel_id"),
            "upload_date": info.get("upload_date"),
            "view_count": info.get("view_count"),
            "like_count": info.get("like_count"),
            "comment_count": info.get("comment_count"),
            "thumbnail": info.get("thumbnail"),
            "categories": info.get("categories", []),
            "tags": info.get("tags", []),
            "is_live": info.get("is_live", False),
            "was_live": info.get("was_live", False),
        }

        # Remove None values
        metadata = {k: v for k, v in metadata.items() if v is not None}

        return ParsedPage(
            site_kind="youtube",
            title=title,
            text_full=text_full,
            word_count=self.count_words(text_full),
            video_seconds=duration,
            metadata=metadata,
        )

    def _fallback_parse(self, url: str, html_content: str, error: str) -> ParsedPage:
        """Fallback parsing using HTML content if yt-dlp fails."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html_content, "html.parser")

        # Try to extract title
        title = None
        title_tag = soup.find("title")
        if title_tag:
            title = title_tag.get_text(strip=True)
            # Remove " - YouTube" suffix
            if title.endswith(" - YouTube"):
                title = title[:-10]

        # Try to extract description from meta
        description = None
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc:
            description = meta_desc.get("content")

        text_full = "\n\n".join(filter(None, [title, description]))

        # Try to extract video ID for metadata
        video_id = self._extract_video_id(url)

        metadata = {
            "url": url,
            "video_id": video_id,
            "parse_error": error,
            "fallback_used": True,
        }

        return ParsedPage(
            site_kind="youtube",
            title=title,
            text_full=text_full if text_full else None,
            word_count=self.count_words(text_full),
            video_seconds=None,  # Can't get duration from HTML easily
            metadata=metadata,
        )

    def _extract_video_id(self, url: str) -> Optional[str]:
        """Extract YouTube video ID from URL."""
        parsed = urlparse(url)

        # youtube.com/watch?v=VIDEO_ID
        if "youtube.com" in parsed.netloc:
            if parsed.path == "/watch":
                query = parse_qs(parsed.query)
                return query.get("v", [None])[0]
            # youtube.com/shorts/VIDEO_ID or /embed/VIDEO_ID
            match = re.match(r"^/(shorts|embed|v)/([^/?]+)", parsed.path)
            if match:
                return match.group(2)

        # youtu.be/VIDEO_ID
        if "youtu.be" in parsed.netloc:
            return parsed.path.lstrip("/").split("/")[0]

        return None
