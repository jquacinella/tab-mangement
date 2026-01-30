"""
TabBacklog v1 - Test Configuration and Fixtures

Shared fixtures for both unit and e2e tests.
"""

import asyncio
import os
import subprocess
import sys
import time
from typing import Generator

import pytest
from playwright.sync_api import Page, Browser, BrowserContext

# Default test configuration
TEST_BASE_URL = os.environ.get("TEST_BASE_URL", "http://localhost:8000")
TEST_DB_URL = os.environ.get("TEST_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/tabbacklog_test")


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def base_url() -> str:
    """Base URL for the web UI."""
    return TEST_BASE_URL


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """Configure browser context for tests."""
    return {
        **browser_context_args,
        "viewport": {"width": 1280, "height": 720},
        "ignore_https_errors": True,
    }


@pytest.fixture(scope="function")
def page_with_base_url(page: Page, base_url: str) -> Page:
    """Page fixture with base URL navigation helper."""
    page.base_url = base_url
    return page


class WebUITestHelper:
    """Helper class for common web UI test operations."""

    def __init__(self, page: Page, base_url: str):
        self.page = page
        self.base_url = base_url

    def goto(self, path: str = "/") -> None:
        """Navigate to a path on the web UI."""
        self.page.goto(f"{self.base_url}{path}")

    def wait_for_htmx(self, timeout: int = 5000) -> None:
        """Wait for HTMX requests to complete."""
        self.page.wait_for_function(
            "() => !document.body.classList.contains('htmx-request')",
            timeout=timeout
        )

    def wait_for_tabs_loaded(self, timeout: int = 10000) -> None:
        """Wait for tabs table to be populated."""
        self.page.wait_for_selector(
            "#tabs-body tr:not(.loading-cell)",
            timeout=timeout,
            state="attached"
        )

    def get_tab_count(self) -> int:
        """Get the number of tabs displayed in the table."""
        rows = self.page.query_selector_all("#tabs-body tr.tab-row")
        return len(rows)

    def search(self, query: str) -> None:
        """Perform a search."""
        search_input = self.page.locator("#search-input")
        search_input.fill(query)
        # Wait for debounced search to trigger
        self.page.wait_for_timeout(500)
        self.wait_for_htmx()

    def filter_by_status(self, status: str) -> None:
        """Filter tabs by status."""
        self.page.select_option("#status-filter", status)
        self.wait_for_htmx()

    def filter_by_content_type(self, content_type: str) -> None:
        """Filter tabs by content type."""
        self.page.select_option("#content-type-filter", content_type)
        self.wait_for_htmx()

    def filter_by_processed(self, processed: str) -> None:
        """Filter tabs by processed state."""
        self.page.select_option("#processed-filter", processed)
        self.wait_for_htmx()

    def select_tab(self, index: int) -> None:
        """Select a tab by its index in the table."""
        checkboxes = self.page.locator(".tab-checkbox")
        checkboxes.nth(index).check()

    def select_all_tabs(self) -> None:
        """Select all tabs."""
        self.page.locator("#select-all").check()

    def get_selected_count(self) -> int:
        """Get the number of selected tabs."""
        count_text = self.page.locator("#selected-count").text_content()
        return int(count_text) if count_text else 0

    def toggle_semantic_search(self, enabled: bool = True) -> None:
        """Toggle semantic search mode."""
        toggle = self.page.locator("#semantic-search-toggle")
        if enabled:
            toggle.check()
        else:
            toggle.uncheck()

    def open_tab_detail(self, index: int) -> None:
        """Open the detail modal for a tab."""
        titles = self.page.locator(".tab-title-link")
        titles.nth(index).click()
        self.page.wait_for_selector("#tab-modal[style*='flex']")


@pytest.fixture
def web_ui(page: Page, base_url: str) -> WebUITestHelper:
    """Fixture providing web UI test helper."""
    return WebUITestHelper(page, base_url)


# Server management fixtures for running tests against a live server

class ServerManager:
    """Manages the web UI server process for testing."""

    def __init__(self, port: int = 8000):
        self.port = port
        self.process = None

    def start(self) -> None:
        """Start the web UI server."""
        env = os.environ.copy()
        env["DATABASE_URL"] = TEST_DB_URL

        self.process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "web_ui.main:app",
             "--host", "127.0.0.1", "--port", str(self.port)],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Wait for server to be ready
        for _ in range(30):
            try:
                import httpx
                response = httpx.get(f"http://127.0.0.1:{self.port}/health")
                if response.status_code == 200:
                    return
            except Exception:
                pass
            time.sleep(0.5)

        raise RuntimeError("Server failed to start")

    def stop(self) -> None:
        """Stop the web UI server."""
        if self.process:
            self.process.terminate()
            self.process.wait(timeout=5)
            self.process = None


@pytest.fixture(scope="session")
def server_manager():
    """Fixture for managing the test server (manual control)."""
    return ServerManager()


# Optional: Auto-start server fixture
# Uncomment if you want tests to automatically start the server

# @pytest.fixture(scope="session", autouse=False)
# def live_server(server_manager):
#     """Start the server for the test session."""
#     server_manager.start()
#     yield
#     server_manager.stop()
