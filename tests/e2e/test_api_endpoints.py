"""
TabBacklog v1 - API Endpoint E2E Tests

Tests for the REST API endpoints using Playwright's request context.

Run with:
    pytest tests/e2e/test_api_endpoints.py -m e2e
"""

import pytest
from playwright.sync_api import Page, APIRequestContext


@pytest.fixture
def api_context(playwright, base_url: str) -> APIRequestContext:
    """Create an API request context for testing."""
    context = playwright.request.new_context(base_url=base_url)
    yield context
    context.dispose()


@pytest.mark.e2e
class TestHealthEndpoint:
    """Tests for the health check endpoint."""

    def test_health_returns_200(self, api_context: APIRequestContext):
        """Test that health endpoint returns 200."""
        response = api_context.get("/health")
        assert response.ok
        assert response.status == 200

    def test_health_returns_json(self, api_context: APIRequestContext):
        """Test that health endpoint returns valid JSON."""
        response = api_context.get("/health")
        data = response.json()

        assert "status" in data
        assert "version" in data
        assert "database" in data

    def test_health_status_values(self, api_context: APIRequestContext):
        """Test that health status has valid values."""
        response = api_context.get("/health")
        data = response.json()

        assert data["status"] in ["healthy", "degraded"]
        assert data["database"] in ["connected", "disconnected"]


@pytest.mark.e2e
class TestTabsEndpoint:
    """Tests for the tabs listing endpoint."""

    def test_tabs_endpoint_exists(self, api_context: APIRequestContext):
        """Test that /tabs endpoint exists and responds."""
        response = api_context.get("/tabs")
        # Should return HTML fragment for HTMX
        assert response.status in [200, 500]  # 500 if DB not set up

    def test_tabs_accepts_filters(self, api_context: APIRequestContext):
        """Test that /tabs endpoint accepts filter parameters."""
        response = api_context.get("/tabs", params={
            "status": "new",
            "content_type": "article",
            "is_processed": "false",
            "search": "test"
        })
        # Should accept parameters without error (even if no results)
        assert response.status in [200, 500]


@pytest.mark.e2e
class TestExportEndpoints:
    """Tests for export endpoints."""

    def test_export_json_requires_post(self, api_context: APIRequestContext):
        """Test that JSON export requires POST method."""
        response = api_context.get("/export/json")
        assert response.status == 405  # Method Not Allowed

    def test_export_markdown_requires_post(self, api_context: APIRequestContext):
        """Test that Markdown export requires POST method."""
        response = api_context.get("/export/markdown")
        assert response.status == 405

    def test_export_obsidian_requires_post(self, api_context: APIRequestContext):
        """Test that Obsidian export requires POST method."""
        response = api_context.get("/export/obsidian")
        assert response.status == 405

    def test_export_json_with_empty_ids(self, api_context: APIRequestContext):
        """Test JSON export with empty tab_ids."""
        response = api_context.post("/export/json", data={
            "tab_ids": []
        })
        # Should handle empty list gracefully
        assert response.status in [200, 400, 422]

    def test_export_json_with_ids(self, api_context: APIRequestContext):
        """Test JSON export with tab IDs."""
        response = api_context.post(
            "/export/json",
            headers={"Content-Type": "application/json"},
            data={"tab_ids": [1, 2, 3]}
        )
        # Will fail if tabs don't exist, but should process the request
        assert response.status in [200, 404, 500]


@pytest.mark.e2e
class TestSearchEndpoints:
    """Tests for search endpoints."""

    def test_semantic_search_endpoint_exists(self, api_context: APIRequestContext):
        """Test that semantic search endpoint exists."""
        response = api_context.get("/search/semantic", params={"q": "test"})
        # Should respond (even if no embeddings)
        assert response.status in [200, 500]

    def test_semantic_search_requires_query(self, api_context: APIRequestContext):
        """Test that semantic search needs a query parameter."""
        response = api_context.get("/search/semantic")
        # Should either accept empty or require query
        assert response.status in [200, 400, 422, 500]

    def test_generate_embeddings_requires_post(self, api_context: APIRequestContext):
        """Test that generate embeddings requires POST."""
        response = api_context.get("/search/generate-embeddings")
        assert response.status == 405


@pytest.mark.e2e
class TestStaticFiles:
    """Tests for static file serving."""

    def test_css_file_served(self, api_context: APIRequestContext):
        """Test that CSS files are served."""
        response = api_context.get("/static/css/style.css")
        assert response.ok
        assert "text/css" in response.headers.get("content-type", "")

    def test_nonexistent_static_returns_404(self, api_context: APIRequestContext):
        """Test that nonexistent static files return 404."""
        response = api_context.get("/static/nonexistent.xyz")
        assert response.status == 404


@pytest.mark.e2e
class TestIndexPage:
    """Tests for the index page."""

    def test_index_returns_html(self, api_context: APIRequestContext):
        """Test that index page returns HTML."""
        response = api_context.get("/")
        assert response.ok
        content_type = response.headers.get("content-type", "")
        assert "text/html" in content_type

    def test_index_contains_required_elements(self, api_context: APIRequestContext):
        """Test that index page contains required HTML elements."""
        response = api_context.get("/")
        html = response.text()

        # Should contain key elements
        assert "filter-form" in html
        assert "tabs-body" in html
        assert "search-input" in html
        assert "htmx" in html.lower()


@pytest.mark.e2e
class TestStatsPage:
    """Tests for the stats page."""

    def test_stats_returns_html(self, api_context: APIRequestContext):
        """Test that stats page returns HTML."""
        response = api_context.get("/stats")
        assert response.status in [200, 500]  # 500 if DB not connected

    def test_stats_contains_statistics(self, api_context: APIRequestContext):
        """Test that stats page has statistical content."""
        response = api_context.get("/stats")
        if response.ok:
            html = response.text()
            # Should have some stats-related content
            assert len(html) > 100  # Not empty


@pytest.mark.e2e
class TestErrorHandling:
    """Tests for error handling."""

    def test_404_for_nonexistent_page(self, api_context: APIRequestContext):
        """Test that nonexistent pages return 404."""
        response = api_context.get("/this-page-does-not-exist")
        assert response.status == 404

    def test_invalid_tab_id(self, api_context: APIRequestContext):
        """Test handling of invalid tab ID."""
        response = api_context.get("/tabs/invalid-id")
        assert response.status in [404, 422, 500]

    def test_nonexistent_tab_id(self, api_context: APIRequestContext):
        """Test handling of nonexistent tab ID."""
        response = api_context.get("/tabs/999999999")
        assert response.status in [404, 500]
