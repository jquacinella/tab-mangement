"""
TabBacklog v1 - Web UI End-to-End Tests

Playwright-based e2e tests for the web interface.

Run with:
    pytest tests/e2e/ -m e2e --headed  # With browser visible
    pytest tests/e2e/ -m e2e           # Headless mode

Prerequisites:
    1. Install Playwright browsers: playwright install
    2. Start the web UI server: uvicorn web_ui.main:app --port 8000
    3. Ensure database has test data
"""

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.e2e
class TestPageLoad:
    """Tests for basic page loading and structure."""

    def test_homepage_loads(self, page: Page, base_url: str):
        """Test that the homepage loads successfully."""
        page.goto(base_url)

        # Check page title
        expect(page).to_have_title("TabBacklog - Your Tabs")

        # Check main elements are present
        expect(page.locator(".filters-section")).to_be_visible()
        expect(page.locator(".tabs-table")).to_be_visible()
        expect(page.locator(".actions-bar")).to_be_visible()

    def test_stats_page_loads(self, page: Page, base_url: str):
        """Test that the stats page loads successfully."""
        page.goto(f"{base_url}/stats")

        # Should have stats content
        expect(page.locator("body")).to_contain_text("Total")

    def test_health_endpoint(self, page: Page, base_url: str):
        """Test the health check endpoint."""
        response = page.request.get(f"{base_url}/health")
        assert response.ok
        data = response.json()
        assert data["status"] in ["healthy", "degraded"]
        assert "version" in data


@pytest.mark.e2e
class TestFilters:
    """Tests for filtering functionality."""

    def test_filter_elements_present(self, page: Page, base_url: str):
        """Test that all filter elements are present."""
        page.goto(base_url)

        expect(page.locator("#search-input")).to_be_visible()
        expect(page.locator("#status-filter")).to_be_visible()
        expect(page.locator("#content-type-filter")).to_be_visible()
        expect(page.locator("#processed-filter")).to_be_visible()
        expect(page.locator("#read-time-filter")).to_be_visible()

    def test_status_filter_options(self, page: Page, base_url: str):
        """Test that status filter has expected options."""
        page.goto(base_url)

        status_filter = page.locator("#status-filter")
        options = status_filter.locator("option").all_text_contents()

        # Should have "All Status" and various status options
        assert "All Status" in options

    def test_processed_filter_options(self, page: Page, base_url: str):
        """Test that processed filter has correct options."""
        page.goto(base_url)

        processed_filter = page.locator("#processed-filter")
        options = processed_filter.locator("option").all_text_contents()

        assert "All" in options
        assert "Unprocessed" in options
        assert "Processed" in options

    def test_filter_triggers_htmx_request(self, page: Page, base_url: str):
        """Test that changing a filter triggers an HTMX request."""
        page.goto(base_url)

        # Wait for initial load
        page.wait_for_load_state("networkidle")

        # Track network requests
        requests = []
        page.on("request", lambda r: requests.append(r.url) if "/tabs" in r.url else None)

        # Change status filter
        page.select_option("#status-filter", index=1)

        # Wait for HTMX request
        page.wait_for_timeout(500)

        # Should have made a request to /tabs
        assert any("/tabs" in r for r in requests)


@pytest.mark.e2e
class TestSearch:
    """Tests for search functionality."""

    def test_search_input_exists(self, page: Page, base_url: str):
        """Test that search input is present and functional."""
        page.goto(base_url)

        search_input = page.locator("#search-input")
        expect(search_input).to_be_visible()
        expect(search_input).to_have_attribute("placeholder", "Search tabs...")

    def test_semantic_search_toggle_exists(self, page: Page, base_url: str):
        """Test that semantic search toggle is present."""
        page.goto(base_url)

        toggle = page.locator("#semantic-search-toggle")
        expect(toggle).to_be_attached()

    def test_search_triggers_request(self, page: Page, base_url: str):
        """Test that typing in search triggers a request."""
        page.goto(base_url)
        page.wait_for_load_state("networkidle")

        requests = []
        page.on("request", lambda r: requests.append(r.url) if "/tabs" in r.url or "/search" in r.url else None)

        # Type in search
        page.fill("#search-input", "test query")

        # Wait for debounced request
        page.wait_for_timeout(500)

        # Should have made a search request
        assert len(requests) > 0

    def test_semantic_search_toggle_changes_endpoint(self, page: Page, base_url: str):
        """Test that toggling semantic search changes the search endpoint."""
        page.goto(base_url)
        page.wait_for_load_state("networkidle")

        # Enable semantic search
        page.check("#semantic-search-toggle")

        # Check that form action changed
        form = page.locator("#filter-form")
        expect(form).to_have_attribute("hx-get", "/search/semantic")

        # Disable semantic search
        page.uncheck("#semantic-search-toggle")

        # Should revert to /tabs
        expect(form).to_have_attribute("hx-get", "/tabs")


@pytest.mark.e2e
class TestTabSelection:
    """Tests for tab selection functionality."""

    def test_select_all_checkbox_exists(self, page: Page, base_url: str):
        """Test that select all checkbox is present."""
        page.goto(base_url)

        select_all = page.locator("#select-all")
        expect(select_all).to_be_visible()

    def test_selected_count_display(self, page: Page, base_url: str):
        """Test that selected count is displayed."""
        page.goto(base_url)

        count_display = page.locator("#selected-count")
        expect(count_display).to_be_visible()
        expect(count_display).to_have_text("0")

    def test_export_buttons_disabled_when_none_selected(self, page: Page, base_url: str):
        """Test that export buttons are disabled when no tabs are selected."""
        page.goto(base_url)

        # Export buttons should be disabled
        json_btn = page.locator("button:has-text('Export JSON')")
        markdown_btn = page.locator("button:has-text('Export Markdown')")
        obsidian_btn = page.locator("button:has-text('Export to Obsidian')")

        expect(json_btn).to_be_disabled()
        expect(markdown_btn).to_be_disabled()
        expect(obsidian_btn).to_be_disabled()


@pytest.mark.e2e
class TestExport:
    """Tests for export functionality."""

    def test_export_buttons_present(self, page: Page, base_url: str):
        """Test that all export buttons are present."""
        page.goto(base_url)

        expect(page.locator("button:has-text('Export JSON')")).to_be_visible()
        expect(page.locator("button:has-text('Export Markdown')")).to_be_visible()
        expect(page.locator("button:has-text('Export to Obsidian')")).to_be_visible()


@pytest.mark.e2e
class TestModal:
    """Tests for tab detail modal."""

    def test_modal_hidden_by_default(self, page: Page, base_url: str):
        """Test that the modal is hidden by default."""
        page.goto(base_url)

        modal = page.locator("#tab-modal")
        expect(modal).to_have_css("display", "none")

    def test_escape_key_closes_modal(self, page: Page, base_url: str):
        """Test that pressing Escape would close the modal."""
        page.goto(base_url)

        # This tests that the event listener is set up
        # The actual modal closing requires a tab to be clicked first
        page.evaluate("""
            () => {
                const modal = document.getElementById('tab-modal');
                modal.style.display = 'flex';
            }
        """)

        modal = page.locator("#tab-modal")
        expect(modal).to_have_css("display", "flex")

        # Press Escape
        page.keyboard.press("Escape")

        expect(modal).to_have_css("display", "none")


@pytest.mark.e2e
class TestStatsPage:
    """Tests for the statistics page."""

    def test_stats_page_accessible(self, page: Page, base_url: str):
        """Test that stats page is accessible."""
        page.goto(f"{base_url}/stats")
        expect(page.locator("body")).not_to_be_empty()

    def test_stats_shows_totals(self, page: Page, base_url: str):
        """Test that stats page shows total counts."""
        page.goto(f"{base_url}/stats")

        # Should contain some stats information
        body_text = page.locator("body").text_content()
        # Stats page should have some numeric content or labels
        assert body_text is not None


@pytest.mark.e2e
class TestResponsiveness:
    """Tests for responsive design."""

    def test_mobile_viewport(self, browser, base_url: str):
        """Test that the page works on mobile viewport."""
        context = browser.new_context(viewport={"width": 375, "height": 667})
        page = context.new_page()

        page.goto(base_url)

        # Main elements should still be visible
        expect(page.locator(".container")).to_be_visible()
        expect(page.locator(".tabs-table")).to_be_visible()

        context.close()

    def test_tablet_viewport(self, browser, base_url: str):
        """Test that the page works on tablet viewport."""
        context = browser.new_context(viewport={"width": 768, "height": 1024})
        page = context.new_page()

        page.goto(base_url)

        expect(page.locator(".container")).to_be_visible()
        expect(page.locator(".filters-section")).to_be_visible()

        context.close()


@pytest.mark.e2e
class TestAccessibility:
    """Basic accessibility tests."""

    def test_form_labels_exist(self, page: Page, base_url: str):
        """Test that form inputs have labels."""
        page.goto(base_url)

        # Search input should have a label
        search_label = page.locator("label[for='search-input']")
        expect(search_label).to_be_visible()

        # Filter selects should have labels
        status_label = page.locator("label[for='status-filter']")
        expect(status_label).to_be_visible()

    def test_buttons_have_text(self, page: Page, base_url: str):
        """Test that buttons have descriptive text."""
        page.goto(base_url)

        # Export buttons should have text
        buttons = page.locator(".export-btn").all()
        for button in buttons:
            text = button.text_content()
            assert text and len(text.strip()) > 0


@pytest.mark.e2e
class TestHTMXIntegration:
    """Tests for HTMX integration."""

    def test_htmx_loaded(self, page: Page, base_url: str):
        """Test that HTMX library is loaded."""
        page.goto(base_url)

        htmx_loaded = page.evaluate("() => typeof htmx !== 'undefined'")
        assert htmx_loaded

    def test_tabs_body_has_htmx_attributes(self, page: Page, base_url: str):
        """Test that tabs body has HTMX attributes for loading."""
        page.goto(base_url)

        tabs_body = page.locator("#tabs-body")
        expect(tabs_body).to_have_attribute("hx-get", "/tabs")
        expect(tabs_body).to_have_attribute("hx-trigger", "load")

    def test_filter_form_has_htmx_attributes(self, page: Page, base_url: str):
        """Test that filter form has HTMX attributes."""
        page.goto(base_url)

        form = page.locator("#filter-form")
        expect(form).to_have_attribute("hx-target", "#tabs-body")
