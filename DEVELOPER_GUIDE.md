# TabBacklog Developer Guide

**Version**: 1.0.0  
**Last Updated**: 2026-01-30  
**For**: Developers working on TabBacklog features and maintenance

## Table of Contents

1. [Getting Started](#getting-started)
2. [Development Workflow](#development-workflow)
3. [Project Structure](#project-structure)
4. [Adding Features](#adding-features)
5. [Testing Guide](#testing-guide)
6. [Debugging Guide](#debugging-guide)
7. [Common Tasks](#common-tasks)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)

---

## Getting Started

### Prerequisites

- Python 3.11+
- Docker/Podman
- PostgreSQL 15+ (or use Docker)
- Git
- Code editor (VS Code recommended)

### Initial Setup

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd tab-mangement
   ```

2. **Set up environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start database**:
   ```bash
   docker-compose up -d postgres
   ```

4. **Install dependencies**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

5. **Verify setup**:
   ```bash
   # Check database connection
   python -c "from config import get_config; print(get_config().database.url)"
   
   # Run tests
   pytest tests/
   ```

### Development Environment Options

#### Option 1: Full Docker Stack (Recommended for Testing)
```bash
docker-compose up -d
# All services running in containers
```

#### Option 2: Hybrid (Recommended for Development)
```bash
# Run database and Phoenix in Docker
docker-compose up -d postgres phoenix

# Run services locally for faster iteration
uvicorn parser_service.main:app --reload --port 8001
uvicorn enrichment_service.main:app --reload --port 8002
uvicorn web_ui.main:app --reload --port 8000
```

#### Option 3: Local Only
```bash
# Start local PostgreSQL
# Configure DATABASE_URL in .env
# Run services as in Option 2
```

---

## Development Workflow

### Branch Strategy

```
main
  ├── feature/001-new-parser
  ├── feature/002-export-format
  └── bugfix/003-enrichment-error
```

### Feature Development Process

1. **Create feature branch**:
   ```bash
   git checkout -b feature/NNN-feature-name
   ```

2. **Review constitution**:
   - Read [`.specify/memory/constitution.md`](.specify/memory/constitution.md)
   - Ensure feature aligns with core principles

3. **Implement feature**:
   - Follow service boundaries
   - Add tests
   - Update documentation

4. **Test locally**:
   ```bash
   pytest tests/
   docker-compose up -d --build
   ```

5. **Commit and push**:
   ```bash
   git add .
   git commit -m "feat: add new parser for Reddit"
   git push origin feature/NNN-feature-name
   ```

6. **Create pull request**:
   - Reference constitution compliance
   - Include test results
   - Update CHANGELOG.md

### Commit Message Convention

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples**:
```
feat(parser): add Reddit parser with comment extraction

Implements BaseParser interface for Reddit posts and comments.
Extracts post title, body, top comments, and metadata.

Closes #42
```

```
fix(enrichment): handle timeout errors gracefully

Adds retry logic with exponential backoff for LLM timeouts.
Logs errors to event_log for debugging.

Fixes #56
```

---

## Project Structure

### Service Organization

```
tab-mangement/
├── .specify/                    # Project governance
│   ├── memory/
│   │   └── constitution.md      # Core principles (READ THIS FIRST)
│   └── templates/               # Documentation templates
│
├── database/
│   └── schema/                  # SQL schema files (numbered order)
│       ├── 00_auth_setup.sql
│       ├── 01_extensions.sql
│       ├── 02_core_tables.sql
│       ├── 03_indexes_views.sql
│       └── 04_seed_data.sql
│
├── ingest/                      # CLI for importing tabs
│   ├── cli.py                   # Click CLI commands
│   ├── firefox_parser.py        # HTML parsing logic
│   └── db.py                    # Database operations
│
├── parser_service/              # URL fetch and parse
│   ├── main.py                  # FastAPI app
│   ├── models.py                # Pydantic models
│   ├── Dockerfile
│   └── parsers/
│       ├── base.py              # BaseParser interface
│       ├── registry.py          # Parser registration
│       ├── generic.py           # Generic HTML parser
│       ├── youtube.py           # YouTube parser
│       └── twitter.py           # Twitter parser
│
├── enrichment_service/          # LLM enrichment
│   ├── main.py                  # FastAPI app
│   ├── dspy_setup.py            # DSPy configuration
│   ├── models.py                # Enrichment schema
│   └── Dockerfile
│
├── web_ui/                      # User interface
│   ├── main.py                  # FastAPI app
│   ├── db.py                    # Async database ops
│   ├── models.py                # Display models
│   ├── Dockerfile
│   ├── routes/
│   │   ├── tabs.py              # Tab listing/filtering
│   │   ├── export.py            # Export endpoints
│   │   └── search.py            # Semantic search
│   ├── templates/               # Jinja2 templates
│   │   ├── base.html
│   │   ├── index.html
│   │   └── fragments/           # HTMX fragments
│   └── static/
│       └── css/
│           └── style.css
│
├── shared/                      # Shared utilities
│   └── search.py                # Embedding generation
│
├── n8n/
│   ├── README.md
│   └── workflows/
│       └── enrich_tabs.json     # Main workflow
│
├── tests/
│   ├── conftest.py              # Pytest fixtures
│   ├── e2e/                     # End-to-end tests
│   └── unit/                    # Unit tests
│
├── config.py                    # Centralized configuration
├── requirements.txt             # Python dependencies
├── docker-compose.yml           # Container orchestration
├── .env.example                 # Environment template
├── README.md                    # User documentation
├── ARCHITECTURE.md              # Architecture documentation
├── DEVELOPER_GUIDE.md           # This file
└── CLAUDE_CODE_SPEC.md          # Implementation spec
```

### Configuration Management

All configuration is centralized in [`config.py`](config.py):

```python
from config import get_config

config = get_config()

# Access configuration
db_url = config.database.url
llm_model = config.llm.model_name
parser_url = config.services.parser_url
```

**Never hardcode**:
- Database URLs
- API keys
- Service endpoints
- Environment-specific values

---

## Adding Features

### Adding a New Parser

**Example**: Add a Reddit parser

1. **Create parser file**: `parser_service/parsers/reddit.py`

```python
from .base import BaseParser, ParsedPage
import re

class RedditParser(BaseParser):
    """Parser for Reddit posts and comments"""
    
    def can_parse(self, url: str) -> bool:
        return bool(re.search(r'reddit\.com/r/\w+/comments/', url))
    
    def parse(self, url: str, html: str) -> ParsedPage:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract post title
        title_elem = soup.find('h1')
        title = title_elem.text.strip() if title_elem else None
        
        # Extract post body
        post_body = soup.find('div', {'data-test-id': 'post-content'})
        text = post_body.text.strip() if post_body else ""
        
        # Extract metadata
        metadata = {
            'subreddit': self._extract_subreddit(url),
            'author': self._extract_author(soup),
            'score': self._extract_score(soup)
        }
        
        return ParsedPage(
            site_kind='reddit',
            title=title,
            text_full=text,
            word_count=len(text.split()) if text else 0,
            video_seconds=None,
            metadata=metadata
        )
    
    def _extract_subreddit(self, url: str) -> str:
        match = re.search(r'/r/(\w+)/', url)
        return match.group(1) if match else None
    
    def _extract_author(self, soup) -> str:
        # Implementation details...
        pass
    
    def _extract_score(self, soup) -> int:
        # Implementation details...
        pass
```

2. **Register parser**: `parser_service/parsers/registry.py`

```python
from .reddit import RedditParser

def get_parser_registry() -> List[BaseParser]:
    return [
        YouTubeParser(),
        TwitterParser(),
        RedditParser(),  # Add new parser
        GenericHtmlParser()  # Keep generic last (fallback)
    ]
```

3. **Add tests**: `tests/unit/test_reddit_parser.py`

```python
import pytest
from parser_service.parsers.reddit import RedditParser

def test_reddit_parser_can_parse():
    parser = RedditParser()
    assert parser.can_parse('https://reddit.com/r/python/comments/abc123/')
    assert not parser.can_parse('https://youtube.com/watch?v=123')

def test_reddit_parser_extracts_content():
    parser = RedditParser()
    html = """<html>...</html>"""  # Sample HTML
    result = parser.parse('https://reddit.com/r/python/comments/abc123/', html)
    
    assert result.site_kind == 'reddit'
    assert result.title is not None
    assert result.metadata['subreddit'] == 'python'
```

4. **Test locally**:
```bash
# Run unit tests
pytest tests/unit/test_reddit_parser.py

# Test with real URL
curl -X POST http://localhost:8001/fetch_parse \
  -H "Content-Type: application/json" \
  -d '{"url": "https://reddit.com/r/python/comments/..."}'
```

5. **Update documentation**:
   - Add to README.md supported parsers list
   - Update ARCHITECTURE.md with new parser

### Adding a New Export Format

**Example**: Add CSV export

1. **Create export function**: `web_ui/routes/export.py`

```python
import csv
from io import StringIO
from fastapi.responses import StreamingResponse

@router.post("/export/csv")
async def export_csv(request: ExportRequest):
    """Export selected tabs as CSV"""
    tabs = await get_tabs_by_ids(request.tab_ids)
    
    # Create CSV in memory
    output = StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['URL', 'Title', 'Content Type', 'Summary', 'Tags'])
    
    # Write rows
    for tab in tabs:
        writer.writerow([
            tab.url,
            tab.page_title,
            tab.content_type,
            tab.summary,
            ','.join(tab.tags) if tab.tags else ''
        ])
    
    # Return as download
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=tabs.csv"}
    )
```

2. **Add button to UI**: `web_ui/templates/index.html`

```html
<button hx-post="/export/csv" 
        hx-include="[name='tab_ids']:checked"
        class="btn btn-secondary">
    Export CSV
</button>
```

3. **Test**:
```bash
# Start web UI
uvicorn web_ui.main:app --reload --port 8000

# Test in browser
# Select tabs and click "Export CSV"
```

### Adding a New Enrichment Field

**Example**: Add "difficulty_level" field

1. **Update database schema**: Create `database/schema/05_add_difficulty.sql`

```sql
-- Add difficulty_level to tab_enrichment
ALTER TABLE tab_enrichment 
ADD COLUMN difficulty_level text;

-- Add to history table too
ALTER TABLE tab_enrichment_history 
ADD COLUMN difficulty_level text;

-- Update view
CREATE OR REPLACE VIEW v_tabs_enriched AS
SELECT 
  ti.*,
  te.difficulty_level,  -- Add new field
  -- ... other fields
FROM tab_item ti
LEFT JOIN tab_enrichment te ON ti.id = te.tab_id
-- ... rest of view
```

2. **Update Pydantic model**: `enrichment_service/models.py`

```python
from typing import Literal

class Enrichment(BaseModel):
    summary: str
    content_type: str
    difficulty_level: Literal["beginner", "intermediate", "advanced"] | None
    # ... other fields
```

3. **Update DSPy signature**: `enrichment_service/dspy_setup.py`

```python
class EnrichmentSignature(dspy.Signature):
    """Generate metadata for a web page"""
    url: str = dspy.InputField()
    title: str = dspy.InputField()
    text: str = dspy.InputField()
    
    summary: str = dspy.OutputField()
    difficulty_level: str = dspy.OutputField(desc="beginner, intermediate, or advanced")
    # ... other fields
```

4. **Update Web UI**: `web_ui/templates/fragments/tab_row.html`

```html
<td>
    {% if tab.difficulty_level %}
    <span class="badge badge-{{ tab.difficulty_level }}">
        {{ tab.difficulty_level }}
    </span>
    {% endif %}
</td>
```

5. **Apply schema change**:
```bash
psql $DATABASE_URL < database/schema/05_add_difficulty.sql
```

---

## Testing Guide

### Test Structure

```
tests/
├── conftest.py              # Shared fixtures
├── unit/                    # Fast, isolated tests
│   ├── test_parsers.py
│   └── test_enrichment.py
└── e2e/                     # End-to-end tests
    ├── test_api_endpoints.py
    └── test_web_ui.py
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/test_parsers.py

# Run specific test
pytest tests/unit/test_parsers.py::test_youtube_parser

# Run with coverage
pytest --cov=parser_service --cov-report=html

# Run only unit tests
pytest tests/unit/

# Run only e2e tests
pytest tests/e2e/
```

### Writing Unit Tests

```python
import pytest
from parser_service.parsers.youtube import YouTubeParser

@pytest.fixture
def youtube_parser():
    return YouTubeParser()

def test_can_parse_youtube_url(youtube_parser):
    assert youtube_parser.can_parse('https://youtube.com/watch?v=abc123')
    assert youtube_parser.can_parse('https://youtu.be/abc123')
    assert not youtube_parser.can_parse('https://twitter.com/user/status/123')

def test_parse_youtube_video(youtube_parser):
    url = 'https://youtube.com/watch?v=dQw4w9WgXcQ'
    html = '<html>...</html>'  # Mock HTML
    
    result = youtube_parser.parse(url, html)
    
    assert result.site_kind == 'youtube'
    assert result.title is not None
    assert result.video_seconds is not None
```

### Writing Integration Tests

```python
import pytest
from httpx import AsyncClient
from web_ui.main import app

@pytest.mark.asyncio
async def test_get_tabs_endpoint():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/tabs")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

@pytest.mark.asyncio
async def test_toggle_processed():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/tabs/1/toggle_processed")
        assert response.status_code == 200
```

### Test Database Setup

Use `conftest.py` for test database fixtures:

```python
import pytest
import asyncpg

@pytest.fixture
async def test_db():
    """Create test database connection"""
    conn = await asyncpg.connect(
        host='localhost',
        database='tabbacklog_test',
        user='postgres',
        password='postgres'
    )
    
    # Setup: Create tables
    await conn.execute(open('database/schema/02_core_tables.sql').read())
    
    yield conn
    
    # Teardown: Clean up
    await conn.execute('DROP SCHEMA public CASCADE; CREATE SCHEMA public;')
    await conn.close()
```

---

## Debugging Guide

### Debugging Services

#### Parser Service

```bash
# Run with debug logging
LOG_LEVEL=DEBUG uvicorn parser_service.main:app --reload --port 8001

# Test specific URL
curl -X POST http://localhost:8001/fetch_parse \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}' | jq
```

#### Enrichment Service

```bash
# Check LLM connection
curl http://localhost:8002/health | jq

# Test enrichment
curl -X POST http://localhost:8002/enrich_tab \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "title": "Test",
    "site_kind": "generic_html",
    "text": "Test content"
  }' | jq
```

#### Web UI

```bash
# Run with auto-reload
uvicorn web_ui.main:app --reload --port 8000

# Check database queries
LOG_LEVEL=DEBUG uvicorn web_ui.main:app --reload --port 8000
# Watch for SQL queries in logs
```

### Debugging Database

```bash
# Connect to database
psql $DATABASE_URL

# Check tab statuses
SELECT status, COUNT(*) FROM tab_item GROUP BY status;

# View recent events
SELECT * FROM event_log ORDER BY created_at DESC LIMIT 10;

# Check enrichment errors
SELECT id, url, last_error 
FROM tab_item 
WHERE status IN ('fetch_error', 'llm_error')
ORDER BY error_at DESC;
```

### Debugging n8n Workflow

1. Access n8n UI: `http://localhost:5678`
2. Open workflow: `enrich_tabs.json`
3. Click "Execute Workflow" to run manually
4. View execution logs for each node
5. Check database for status updates

### Using Phoenix for LLM Debugging

1. Access Phoenix UI: `http://localhost:6006`
2. View traces for all LLM calls
3. Check token usage and costs
4. Analyze failed requests
5. Compare different model outputs

---

## Common Tasks

### Reset Database

```bash
# Stop services
docker-compose down

# Remove volume
docker volume rm tabbacklog-postgres-data

# Restart with fresh database
docker-compose up -d postgres

# Database will auto-initialize from schema files
```

### Reprocess Failed Tabs

```sql
-- Reset fetch errors
UPDATE tab_item 
SET status = 'new', last_error = NULL, error_at = NULL
WHERE status = 'fetch_error';

-- Reset LLM errors
UPDATE tab_item 
SET status = 'parsed', last_error = NULL, error_at = NULL
WHERE status = 'llm_error';
```

### Generate Embeddings for Semantic Search

```bash
# Run embedding generation
python -c "
from shared.search import generate_embeddings_for_all_tabs
generate_embeddings_for_all_tabs()
"
```

### Export All Tabs

```bash
# Via Web UI
curl -X POST http://localhost:8000/export/json \
  -H "Content-Type: application/json" \
  -d '{"tab_ids": []}' > all_tabs.json

# Via SQL
psql $DATABASE_URL -c "COPY (
  SELECT * FROM v_tabs_enriched
) TO STDOUT CSV HEADER" > all_tabs.csv
```

### Update LLM Model

```bash
# Update .env
LLM_MODEL_NAME=llama-3.2-8b-instruct

# Restart enrichment service
docker-compose restart enrichment-service
```

---

## Best Practices

### Code Style

- **Type Hints**: Always use type hints
- **Docstrings**: Document all public functions
- **PEP 8**: Follow Python style guide
- **Imports**: Group stdlib, third-party, local
- **Line Length**: Max 100 characters

### Error Handling

```python
# Good: Specific exceptions with context
try:
    result = await fetch_url(url)
except httpx.TimeoutException as e:
    logger.error(f"Timeout fetching {url}: {e}")
    raise HTTPException(status_code=504, detail=f"Timeout: {url}")
except httpx.HTTPError as e:
    logger.error(f"HTTP error fetching {url}: {e}")
    raise HTTPException(status_code=500, detail=f"Fetch failed: {url}")

# Bad: Bare except
try:
    result = await fetch_url(url)
except:
    pass
```

### Logging

```python
import logging

logger = logging.getLogger(__name__)

# Good: Structured logging with context
logger.info(f"Processing tab {tab_id}", extra={
    'tab_id': tab_id,
    'url': url,
    'status': status
})

# Bad: Unstructured logging
print(f"Processing {tab_id}")
```

### Database Queries

```python
# Good: Parameterized queries
await conn.execute(
    "UPDATE tab_item SET status = $1 WHERE id = $2",
    'enriched', tab_id
)

# Bad: String interpolation (SQL injection risk)
await conn.execute(
    f"UPDATE tab_item SET status = '{status}' WHERE id = {tab_id}"
)
```

### Configuration

```python
# Good: Use config module
from config import get_config
config = get_config()
llm_url = config.llm.api_base

# Bad: Environment variables directly
import os
llm_url = os.getenv('LLM_API_BASE')
```

---

## Troubleshooting

### Service Won't Start

**Problem**: `docker-compose up` fails

**Solutions**:
```bash
# Check logs
docker-compose logs [service-name]

# Rebuild containers
docker-compose up -d --build

# Check port conflicts
lsof -i :8000  # Check if port is in use

# Reset everything
docker-compose down -v
docker-compose up -d
```

### Database Connection Errors

**Problem**: `psycopg.OperationalError: could not connect`

**Solutions**:
```bash
# Check database is running
docker-compose ps postgres

# Check DATABASE_URL in .env
echo $DATABASE_URL

# Test connection
psql $DATABASE_URL -c "SELECT 1"

# Check network
docker network ls
docker network inspect tabbacklog-network
```

### LLM Enrichment Fails

**Problem**: Enrichment service returns 500 errors

**Solutions**:
```bash
# Check LLM service is running
curl $LLM_API_BASE/models

# Check Phoenix connection
curl http://localhost:6006/healthz

# View enrichment logs
docker-compose logs enrichment-service

# Test with simple request
curl -X POST http://localhost:8002/enrich_tab \
  -H "Content-Type: application/json" \
  -d '{"url":"test","title":"test","site_kind":"generic_html","text":"test"}'
```

### Parser Service Timeouts

**Problem**: Parser service times out on some URLs

**Solutions**:
```bash
# Increase timeout in .env
FETCH_TIMEOUT=60

# Restart parser service
docker-compose restart parser-service

# Test URL directly
curl -I https://problem-url.com

# Check if site blocks bots
curl -A "Mozilla/5.0" https://problem-url.com
```

### n8n Workflow Not Running

**Problem**: Tabs stay in `new` status

**Solutions**:
1. Access n8n UI: `http://localhost:5678`
2. Check workflow is activated (toggle in top right)
3. Manually execute workflow to test
4. Check workflow logs for errors
5. Verify service URLs in workflow nodes

---

## Additional Resources

- [Constitution](.specify/memory/constitution.md) - Core principles
- [Architecture](ARCHITECTURE.md) - System architecture
- [README](README.md) - User documentation
- [Implementation Spec](CLAUDE_CODE_SPEC.md) - Original specification
- [Tests README](tests/README.md) - Testing documentation
- [n8n README](n8n/README.md) - Workflow documentation

---

## Getting Help

1. **Check logs**: `docker-compose logs [service-name]`
2. **Review constitution**: Ensure compliance with principles
3. **Search issues**: Check if problem is known
4. **Ask for help**: Provide logs and steps to reproduce

---

**Happy coding! 🚀**
