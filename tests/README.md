# TabBacklog v1 - Test Suite

This directory contains tests for the TabBacklog application.

## Structure

```
tests/
├── conftest.py          # Shared fixtures and configuration
├── e2e/                 # End-to-end browser tests (Playwright)
│   ├── test_web_ui.py   # Web UI interaction tests
│   └── test_api_endpoints.py  # API endpoint tests
└── unit/                # Unit tests (future)
```

## Prerequisites

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Install Playwright Browsers

```bash
playwright install
# Or install specific browsers:
playwright install chromium
```

### 3. Start the Server

The e2e tests require a running web server:

```bash
# Start the web UI (default port 8000)
uvicorn web_ui.main:app --port 8000

# Or use Docker
docker-compose up web-ui
```

### 4. Database Setup

Ensure the database is running and has the schema:

```bash
# Using local PostgreSQL
psql -d tabbacklog < database/schema/01_core_tables.sql
psql -d tabbacklog < database/schema/02_extensions_indexes.sql
psql -d tabbacklog < database/schema/03_seed_data.sql

# Initialize test user
psql -d tabbacklog -c "SELECT initialize_user_data('00000000-0000-0000-0000-000000000000'::uuid);"
```

## Running Tests

### Run All Tests

```bash
pytest
```

### Run E2E Tests Only

```bash
pytest tests/e2e/ -m e2e
```

### Run with Browser Visible

```bash
pytest tests/e2e/ -m e2e --headed
```

### Run Specific Test File

```bash
pytest tests/e2e/test_web_ui.py -v
```

### Run Specific Test Class

```bash
pytest tests/e2e/test_web_ui.py::TestPageLoad -v
```

### Run with Coverage

```bash
pytest --cov=web_ui --cov-report=html
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TEST_BASE_URL` | `http://localhost:8000` | Base URL for the web UI |
| `TEST_DATABASE_URL` | `postgresql://...` | Test database URL |

### Pytest Options

```bash
# Slow mode (watch tests run)
pytest --headed --slowmo 500

# Debug mode (pause on failure)
pytest --headed -x --pdb

# Parallel execution
pytest -n auto

# Generate JUnit XML report
pytest --junitxml=report.xml
```

## Test Categories

### E2E Tests (`tests/e2e/`)

Browser-based tests using Playwright:

- **test_web_ui.py**: Tests for the web interface
  - Page loading
  - Filter functionality
  - Search (fuzzy and semantic)
  - Tab selection
  - Export buttons
  - Modal interactions
  - Responsive design
  - Accessibility basics

- **test_api_endpoints.py**: Tests for REST API
  - Health endpoint
  - Tabs listing
  - Export endpoints
  - Search endpoints
  - Error handling

### Unit Tests (`tests/unit/`)

Fast, isolated tests for individual components (to be added):

- Parser functions
- Database queries
- Model validation
- Utility functions

## Writing New Tests

### E2E Test Example

```python
import pytest
from playwright.sync_api import Page, expect

@pytest.mark.e2e
class TestMyFeature:
    def test_feature_works(self, page: Page, base_url: str):
        page.goto(base_url)

        # Use Playwright's expect for assertions
        expect(page.locator("#my-element")).to_be_visible()

        # Interact with the page
        page.click("#my-button")

        # Verify result
        expect(page.locator("#result")).to_have_text("Success")
```

### Using the WebUI Helper

```python
def test_with_helper(self, web_ui):
    web_ui.goto("/")
    web_ui.search("my query")
    web_ui.wait_for_htmx()

    count = web_ui.get_tab_count()
    assert count > 0
```

## Troubleshooting

### Tests Fail with Connection Error

Ensure the web server is running:
```bash
curl http://localhost:8000/health
```

### Tests Fail with Database Error

Check database connection:
```bash
psql $DATABASE_URL -c "SELECT 1"
```

### Playwright Browser Issues

Reinstall browsers:
```bash
playwright install --force
```

### Slow Tests

Run headless (default) for faster execution:
```bash
pytest tests/e2e/  # No --headed flag
```

## CI/CD Integration

Example GitHub Actions workflow:

```yaml
name: E2E Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        ports:
          - 5432:5432

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          playwright install chromium

      - name: Set up database
        run: |
          psql -h localhost -U postgres -d postgres -c "CREATE DATABASE tabbacklog"
          psql -h localhost -U postgres -d tabbacklog < database/schema/01_core_tables.sql
        env:
          PGPASSWORD: postgres

      - name: Start server
        run: |
          uvicorn web_ui.main:app --port 8000 &
          sleep 5
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost/tabbacklog

      - name: Run tests
        run: pytest tests/e2e/ -m e2e -v
        env:
          TEST_BASE_URL: http://localhost:8000
```
