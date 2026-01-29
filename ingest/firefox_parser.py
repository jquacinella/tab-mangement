"""
TabBacklog v1 - Firefox Bookmarks Parser

Parses Firefox bookmarks HTML export files to extract tab information.
Specifically looks for "Session-" prefixed folders which contain saved browser tabs.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterator
from bs4 import BeautifulSoup, Tag


@dataclass
class BookmarkItem:
    """Represents a single bookmark/tab extracted from Firefox export"""
    url: str
    page_title: str | None
    window_label: str | None
    collected_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        # Normalize URL by stripping whitespace
        self.url = self.url.strip()
        # Normalize title
        if self.page_title:
            self.page_title = self.page_title.strip() or None


class FirefoxParser:
    """
    Parser for Firefox bookmarks HTML export files.

    Looks for folders with "Session-" prefix and extracts all bookmarks
    within them. The folder name after "Session-" is used as the window_label.

    Example folder structure:
        Session-Research
            - bookmark1
            - bookmark2
        Session-Work
            - bookmark3
    """

    SESSION_PREFIX = "Session-"

    def __init__(self, file_path: str | Path):
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise FileNotFoundError(f"Bookmarks file not found: {self.file_path}")

    def parse(self) -> list[BookmarkItem]:
        """
        Parse the bookmarks file and return all tab items from Session- folders.

        Returns:
            List of BookmarkItem objects
        """
        return list(self._iter_bookmarks())

    def _iter_bookmarks(self) -> Iterator[BookmarkItem]:
        """
        Iterate over all bookmarks in Session- folders.

        Yields:
            BookmarkItem objects for each bookmark found
        """
        html_content = self.file_path.read_text(encoding="utf-8")
        soup = BeautifulSoup(html_content, "html.parser")

        # Find all H3 tags (folder headers)
        for h3 in soup.find_all("h3"):
            folder_name = h3.get_text(strip=True)

            # Check if this is a Session- folder
            if not folder_name.startswith(self.SESSION_PREFIX):
                continue

            # Extract window label (everything after "Session-")
            window_label = folder_name[len(self.SESSION_PREFIX):]
            if not window_label:
                window_label = "default"

            # Find the DL element that follows this H3 (contains bookmarks)
            dl = self._find_folder_contents(h3)
            if dl is None:
                continue

            # Extract all bookmarks from this folder
            yield from self._extract_bookmarks_from_dl(dl, window_label)

    def _find_folder_contents(self, h3_tag: Tag) -> Tag | None:
        """
        Find the DL element containing bookmarks for a folder.

        In Firefox bookmark HTML format:
        <DT>
            <H3>Folder Name</H3>
            <DL><p>
                ... bookmarks ...
            </DL>
        </DT>
        """
        # The H3 is inside a DT, and the DL follows it
        dt_parent = h3_tag.find_parent("dt")
        if dt_parent is None:
            return None

        # Find the DL that is a sibling after the H3
        for sibling in h3_tag.find_next_siblings():
            if sibling.name == "dl":
                return sibling

        return None

    def _extract_bookmarks_from_dl(
        self,
        dl: Tag,
        window_label: str
    ) -> Iterator[BookmarkItem]:
        """
        Extract all bookmark links from a DL element.

        Args:
            dl: The DL tag containing bookmarks
            window_label: The window/session label for these bookmarks

        Yields:
            BookmarkItem objects
        """
        # Find all anchor tags with href
        for a_tag in dl.find_all("a", href=True):
            url = a_tag.get("href", "").strip()

            # Skip empty URLs and non-http(s) URLs
            if not url or not url.startswith(("http://", "https://")):
                continue

            title = a_tag.get_text(strip=True) or None

            # Try to get add_date attribute if present
            add_date_str = a_tag.get("add_date")
            if add_date_str:
                try:
                    # Firefox stores timestamps in seconds since epoch
                    timestamp = int(add_date_str)
                    collected_at = datetime.utcfromtimestamp(timestamp)
                except (ValueError, OSError):
                    collected_at = datetime.utcnow()
            else:
                collected_at = datetime.utcnow()

            yield BookmarkItem(
                url=url,
                page_title=title,
                window_label=window_label,
                collected_at=collected_at,
            )

    def get_stats(self) -> dict:
        """
        Get statistics about the bookmarks file without fully parsing.

        Returns:
            Dictionary with stats like total_bookmarks, session_folders, etc.
        """
        html_content = self.file_path.read_text(encoding="utf-8")
        soup = BeautifulSoup(html_content, "html.parser")

        session_folders = []
        total_bookmarks = 0

        for h3 in soup.find_all("h3"):
            folder_name = h3.get_text(strip=True)
            if folder_name.startswith(self.SESSION_PREFIX):
                window_label = folder_name[len(self.SESSION_PREFIX):] or "default"
                dl = self._find_folder_contents(h3)
                if dl:
                    count = len([
                        a for a in dl.find_all("a", href=True)
                        if a.get("href", "").startswith(("http://", "https://"))
                    ])
                    session_folders.append({"label": window_label, "count": count})
                    total_bookmarks += count

        return {
            "file_path": str(self.file_path),
            "session_folders": session_folders,
            "total_session_folders": len(session_folders),
            "total_bookmarks": total_bookmarks,
        }


def parse_bookmarks_file(file_path: str | Path) -> list[BookmarkItem]:
    """
    Convenience function to parse a Firefox bookmarks file.

    Args:
        file_path: Path to the Firefox bookmarks HTML file

    Returns:
        List of BookmarkItem objects from Session- folders
    """
    parser = FirefoxParser(file_path)
    return parser.parse()
