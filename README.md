# TabBacklog v1

A Firefox tab management system that captures browser tabs into a structured database, enriches them with LLM-generated summaries and metadata, and provides a searchable web interface for processing and exporting.

## Features

- **Ingest**: Parse Firefox bookmarks HTML exports and import tabs from `Session-*` folders
- **Parse**: Fetch and extract content from URLs with site-specific parsers (YouTube, Twitter, generic HTML)
- **Enrich**: Generate summaries, classify content types, and assign tags using LLM (DSPy + Llama)
- **Search**: Fuzzy search with pg_trgm and semantic search with pgvector embeddings
- **Manage**: Web UI with filtering, bulk selection, and processing workflow
- **Export**: Export to JSON, Markdown, or Obsidian-compatible format
- **Observability**: LLM tracing and monitoring with Phoenix (Arize)

## Architecture

```
Firefox Bookmarks Export
    │
    ▼
┌─────────────────┐
│  Ingest CLI     │ ──► PostgreSQL/Supabase
└─────────────────┘
    │
    ▼
┌─────────────────┐
│ n8n Orchestrator│
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌───────┐ ┌────────┐
│Parser │ │Enricher│
│Service│ │Service │
└───────┘ └────────┘
    │         │
    └────┬────┘
         ▼
┌─────────────────┐
│    Web UI       │ ◄── Filter, Search, Export
└─────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 15+ with `pg_trgm` and `pgvector` extensions
- Docker/Podman (optional, for containerized deployment)
- n8n (for workflow orchestration)
- Local LLM server (LM Studio, Ollama) or OpenAI-compatible API

### 1. Database Setup

**Option A: Using Docker (Recommended)**

```bash
# Start PostgreSQL with automatic schema initialization
docker-compose up -d postgres

# Database is automatically initialized with all schema files
# Default user (00000000-0000-0000-0000-000000000000) is created
```

**Option B: Manual Setup (Local PostgreSQL)**

```bash
# Create database
createdb tabbacklog

# Run schema files in order (IMPORTANT: order matters!)
psql tabbacklog < database/schema/00_auth_setup.sql
psql tabbacklog < database/schema/01_extensions.sql
psql tabbacklog < database/schema/02_core_tables.sql
psql tabbacklog < database/schema/03_indexes_views.sql
psql tabbacklog < database/schema/04_seed_data.sql

# Initialize a user (if not using default)
psql tabbacklog -c "SELECT initialize_user_data('YOUR_USER_UUID'::uuid);"
```

**Note:** The database requires PostgreSQL 15+ with `pgvector` extension support. For Docker, we use the `pgvector/pgvector:pg15` image.

### 2. Environment Configuration

```bash
cp .env.example .env
# Edit .env with your values
```

Key environment variables:
```bash
DATABASE_URL=postgresql://user:pass@localhost/tabbacklog
DEFAULT_USER_ID=your-user-uuid
LLM_API_BASE=http://localhost:1234/v1
LLM_MODEL_NAME=llama-3.1-8b-instruct
```

### 3. Install Dependencies

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Run Services

```bash
# Ingest tabs from Firefox bookmarks
python -m ingest.cli ingest --file ~/bookmarks.html --user-id YOUR_UUID

# Start Parser Service (port 8001)
uvicorn parser_service.main:app --port 8001

# Start Enrichment Service (port 8002)
uvicorn enrichment_service.main:app --port 8002

# Start Web UI (port 8000)
uvicorn web_ui.main:app --port 8000
```

### 5. Docker Deployment

```bash
# Start all services
docker-compose up -d

# Access services:
# - Web UI: http://localhost:8000
# - n8n: http://localhost:5678
# - Parser API: http://localhost:8001
# - Enrichment API: http://localhost:8002
# - Phoenix (LLM Observability): http://localhost:6006
```

## Project Structure

```
tabbacklog/
├── .env.example                # Environment variables template
├── config.py                   # Shared configuration
├── requirements.txt            # Python dependencies
├── docker-compose.yml          # Container orchestration
├── pytest.ini                  # Pytest configuration
│
├── database/
│   └── schema/
│       ├── 00_auth_setup.sql       # Auth schema (for standalone PostgreSQL)
│       ├── 01_extensions.sql       # PostgreSQL extensions (pgvector, pg_trgm)
│       ├── 02_core_tables.sql      # Database schema
│       ├── 03_indexes_views.sql    # Indexes and views
│       └── 04_seed_data.sql        # Seed data functions
│
├── ingest/                     # Firefox bookmarks ingestion
│   ├── cli.py                  # CLI entry point
│   ├── firefox_parser.py       # Bookmarks HTML parser
│   └── db.py                   # Database operations
│
├── parser_service/             # URL fetch and parse service
│   ├── main.py                 # FastAPI app
│   ├── models.py               # Pydantic models
│   ├── Dockerfile
│   └── parsers/
│       ├── base.py             # BaseParser, ParsedPage
│       ├── registry.py         # Parser registry
│       ├── generic.py          # Generic HTML parser
│       ├── youtube.py          # YouTube parser (yt-dlp)
│       └── twitter.py          # Twitter/X parser
│
├── enrichment_service/         # LLM enrichment service
│   ├── main.py                 # FastAPI app
│   ├── dspy_setup.py           # DSPy configuration
│   ├── models.py               # Enrichment schema
│   └── Dockerfile
│
├── web_ui/                     # HTMX web interface
│   ├── main.py                 # FastAPI app
│   ├── db.py                   # Async database ops
│   ├── models.py               # Display models
│   ├── Dockerfile
│   ├── routes/
│   │   ├── tabs.py             # Tab listing/filtering
│   │   ├── export.py           # Export endpoints
│   │   └── search.py           # Semantic search
│   ├── templates/
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── stats.html
│   │   └── fragments/
│   │       ├── tab_row.html    # Single tab row
│   │       ├── tab_rows.html   # Tab rows container
│   │       └── tab_detail.html # Tab detail modal
│   └── static/
│       └── css/
│           └── style.css       # Application styles
│
├── shared/                     # Shared utilities
│   └── search.py               # Embedding generation
│
├── n8n/
│   ├── README.md               # Workflow documentation
│   └── workflows/
│       └── enrich_tabs.json    # Main enrichment workflow
│
└── tests/                      # Test suite
    ├── README.md               # Test documentation
    ├── conftest.py             # Shared fixtures
    ├── e2e/                    # Playwright browser tests
    │   ├── test_web_ui.py      # Web UI interaction tests
    │   └── test_api_endpoints.py # API endpoint tests
    └── unit/                   # Unit tests
```

## Services

### Ingest CLI

Parse Firefox bookmarks and insert tabs into the database.

```bash
# Import bookmarks
python -m ingest.cli ingest --file bookmarks.html --user-id UUID

# Preview without importing
python -m ingest.cli ingest --file bookmarks.html --user-id UUID --dry-run

# Show file statistics
python -m ingest.cli stats --file bookmarks.html

# Check database status
python -m ingest.cli status --user-id UUID
```

### Parser Service (Port 8001)

Fetch URLs and extract structured content.

```bash
# Fetch and parse a URL
curl -X POST http://localhost:8001/fetch_parse \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'

# Health check
curl http://localhost:8001/health
```

**Supported parsers:**
- `YouTubeParser`: Uses yt-dlp for video metadata
- `TwitterParser`: Extracts tweets from meta tags
- `GenericHtmlParser`: Fallback for all HTML pages

### Enrichment Service (Port 8002)

Generate LLM-based metadata using DSPy.

```bash
# Enrich a tab
curl -X POST http://localhost:8002/enrich_tab \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "title": "Example Article",
    "site_kind": "generic_html",
    "text": "Article content..."
  }'
```

**Enrichment output:**
- `summary`: 2-3 sentence summary
- `content_type`: article, video, paper, code_repo, reference, misc
- `tags`: Relevant hashtags
- `projects`: Category classification
- `est_read_min`: Estimated reading time
- `priority`: high, medium, low

### Web UI (Port 8000)

HTMX-powered interface for managing tabs.

**Features:**
- Filter by status, content type, processed state, read time
- Fuzzy search with pg_trgm
- Semantic search with embeddings (toggle AI mode)
- Bulk selection and export
- Mark tabs as processed
- Statistics dashboard

**Routes:**
- `GET /` - Main tab listing
- `GET /tabs` - HTMX fragment for filtered tabs
- `POST /tabs/{id}/toggle_processed` - Toggle processed flag
- `GET /stats` - Statistics page
- `POST /export/json` - Export as JSON
- `POST /export/markdown` - Export as Markdown
- `POST /export/obsidian` - Export for Obsidian
- `GET /search/semantic?q=query` - Semantic search
- `POST /search/generate-embeddings` - Generate embeddings

### n8n Workflow

Automated pipeline that runs every 10 minutes:

1. Query new tabs (`status = 'new'`)
2. Update status to `fetch_pending`
3. Call Parser Service
4. Insert parsed content
5. Update status to `llm_pending`
6. Call Enrichment Service
7. Store enrichment and tags
8. Update status to `enriched`
9. Log all events

**Status flow:**
```
new → fetch_pending → parsed → llm_pending → enriched
              ↘                     ↘
           fetch_error           llm_error
```

## Database Schema

### Core Tables

| Table | Purpose |
|-------|---------|
| `tab_item` | Main tab record with URL, title, status |
| `tab_parsed` | Extracted content from parser |
| `tab_enrichment` | LLM-generated metadata |
| `tab_enrichment_history` | Enrichment run history |
| `tag` | User-defined and auto-generated tags |
| `tab_tag` | Tab-tag relationships |
| `tab_embedding` | Vector embeddings for semantic search |
| `event_log` | Audit trail for all operations |

### Key Indexes

- Trigram indexes on `page_title`, `summary` for fuzzy search
- Vector index on `embedding` for semantic search
- Composite indexes for common query patterns

## Configuration

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:pass@host/db

# User (single-user mode)
DEFAULT_USER_ID=uuid

# LLM Service
LLM_API_BASE=http://localhost:1234/v1
LLM_API_KEY=dummy_key
LLM_MODEL_NAME=llama-3.1-8b-instruct
LLM_TIMEOUT=60
LLM_TEMPERATURE=0.7
MAX_RETRIES=3

# Phoenix Observability
OTEL_EXPORTER_OTLP_ENDPOINT=http://phoenix:4317
PHOENIX_COLLECTOR_ENDPOINT=http://localhost:6006
PHOENIX_PROJECT_NAME=tabbacklog

# Embeddings (for semantic search)
EMBEDDING_API_BASE=http://localhost:1234/v1
EMBEDDING_MODEL_NAME=text-embedding-nomic-embed-text-v1.5

# Services
PARSER_SERVICE_URL=http://localhost:8001
ENRICHMENT_SERVICE_URL=http://localhost:8002
```

## LLM Integration Setup

TabBacklog uses an OpenAI-compatible API for two purposes:
1. **Enrichment** - Generate summaries, classify content, assign tags (chat completions)
2. **Embeddings** - Create vectors for semantic search (embeddings endpoint)

Any provider that supports the OpenAI API format will work.

### LM Studio (Local)

[LM Studio](https://lmstudio.ai/) provides a local OpenAI-compatible server.

1. Download and install LM Studio
2. Download a model (e.g., `llama-3.1-8b-instruct`, `mistral-7b-instruct`)
3. Start the local server (default port 1234)
4. For embeddings, also load an embedding model (e.g., `nomic-embed-text-v1.5`)

```bash
# .env configuration for LM Studio
LLM_API_BASE=http://localhost:1234/v1
LLM_API_KEY=lm-studio
LLM_MODEL_NAME=llama-3.1-8b-instruct

EMBEDDING_API_BASE=http://localhost:1234/v1
EMBEDDING_API_KEY=lm-studio
EMBEDDING_MODEL_NAME=text-embedding-nomic-embed-text-v1.5
```

### Ollama (Local)

[Ollama](https://ollama.ai/) is another popular local LLM runner.

1. Install Ollama
2. Pull models: `ollama pull llama3.1` and `ollama pull nomic-embed-text`
3. Ollama runs on port 11434 by default

```bash
# .env configuration for Ollama
LLM_API_BASE=http://localhost:11434/v1
LLM_API_KEY=ollama
LLM_MODEL_NAME=llama3.1

EMBEDDING_API_BASE=http://localhost:11434/v1
EMBEDDING_API_KEY=ollama
EMBEDDING_MODEL_NAME=nomic-embed-text
```

### OpenRouter (Cloud)

[OpenRouter](https://openrouter.ai/) provides access to many models via a unified API.

1. Create an account at openrouter.ai
2. Generate an API key
3. Choose your preferred models

```bash
# .env configuration for OpenRouter
LLM_API_BASE=https://openrouter.ai/api/v1
LLM_API_KEY=sk-or-v1-your-api-key-here
LLM_MODEL_NAME=anthropic/claude-3-haiku

# OpenRouter supports some embedding models, or use a different provider
EMBEDDING_API_BASE=https://openrouter.ai/api/v1
EMBEDDING_API_KEY=sk-or-v1-your-api-key-here
EMBEDDING_MODEL_NAME=openai/text-embedding-3-small
```

**Note:** OpenRouter charges per token. Check pricing at openrouter.ai/models.

### Mixed Configuration

You can use different providers for enrichment and embeddings:

```bash
# Use OpenRouter for chat (better models)
LLM_API_BASE=https://openrouter.ai/api/v1
LLM_API_KEY=sk-or-v1-your-key
LLM_MODEL_NAME=anthropic/claude-3-haiku

# Use local Ollama for embeddings (free, fast)
EMBEDDING_API_BASE=http://localhost:11434/v1
EMBEDDING_API_KEY=ollama
EMBEDDING_MODEL_NAME=nomic-embed-text
```

### Recommended Models

| Use Case | Model | Notes |
|----------|-------|-------|
| Enrichment (local) | `llama-3.1-8b-instruct` | Good balance of speed and quality |
| Enrichment (cloud) | `anthropic/claude-3-haiku` | Fast, affordable, high quality |
| Embeddings (local) | `nomic-embed-text-v1.5` | Open source, good quality |
| Embeddings (cloud) | `text-embedding-3-small` | OpenAI's efficient embedding model |

### Testing the Connection

After configuration, test that the LLM is reachable:

```bash
# Start the enrichment service
uvicorn enrichment_service.main:app --port 8002

# Check health (includes LLM status)
curl http://localhost:8002/health
```

## LLM Observability with Phoenix

TabBacklog includes integrated LLM observability using [Phoenix by Arize](https://phoenix.arize.com/). Phoenix automatically traces all LLM calls, providing insights into:

- **Request/Response Tracking**: See all LLM inputs and outputs
- **Token Usage**: Monitor token consumption per request
- **Latency Metrics**: Track response times and identify bottlenecks
- **Error Monitoring**: Catch and debug LLM failures
- **Cost Analysis**: Estimate API costs based on token usage

### Accessing Phoenix

When running with Docker Compose, Phoenix is automatically started and accessible at:

```
http://localhost:6006
```

The enrichment service automatically sends traces to Phoenix. No additional configuration needed.

### Features

**Trace Explorer**
- View all LLM calls in real-time
- Inspect prompts, completions, and metadata
- Filter by status, latency, or token count

**Analytics Dashboard**
- Token usage over time
- Average latency trends
- Error rates and types
- Request volume metrics

**Prompt Engineering**
- Compare different prompt versions
- A/B test prompt changes
- Track prompt performance

### Configuration

Phoenix is enabled by default. To disable it:

```bash
# In .env or docker-compose environment
OTEL_EXPORTER_OTLP_ENDPOINT=disabled
```

To use a different Phoenix instance:

```bash
# Point to external Phoenix server
OTEL_EXPORTER_OTLP_ENDPOINT=http://your-phoenix-host:4317
PHOENIX_COLLECTOR_ENDPOINT=http://your-phoenix-host:6006
```

### Data Persistence

Phoenix data is stored in a Docker volume (`tabbacklog-phoenix-data`) and persists across container restarts. To reset Phoenix data:

```bash
docker-compose down
docker volume rm tabbacklog-phoenix-data
docker-compose up -d
```

### Using Phoenix for Development

1. **Start services**: `docker-compose up -d`
2. **Open Phoenix**: Navigate to http://localhost:6006
3. **Trigger enrichment**: Process some tabs through the enrichment service
4. **View traces**: See LLM calls appear in Phoenix in real-time
5. **Analyze**: Use Phoenix dashboards to optimize prompts and performance

## Development

### Running Tests

```bash
# Install test dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install

# Run all tests
pytest

# Run E2E tests only
pytest tests/e2e/ -m e2e

# Run with browser visible
pytest tests/e2e/ -m e2e --headed

# Run specific test file
pytest tests/e2e/test_web_ui.py -v

# Run with coverage
pytest --cov=web_ui --cov-report=html
```

**Note:** E2E tests require the web server running on `http://localhost:8000`.
Set `TEST_BASE_URL` environment variable to use a different URL.

### Code Style

```bash
black .
ruff check .
mypy .
```

## Troubleshooting

### Docker Services Not Starting

**Check service status:**
```bash
docker compose ps
```

**View logs for specific service:**
```bash
docker compose logs postgres
docker compose logs enrichment
docker compose logs web-ui
docker compose logs phoenix
```

**Restart all services:**
```bash
docker compose down
docker compose up -d
```

### Database Connection Issues

**Error: "Connection refused" or "could not connect to server"**

- Ensure DATABASE_URL uses Docker service name `postgres` not `localhost`
- Correct: `postgresql://postgres:postgres@postgres:5432/tabbacklog`
- Wrong: `postgresql://postgres:postgres@localhost:5432/tabbacklog`
- Check postgres is healthy: `docker compose ps postgres`

**Error: "database does not exist"**

The database is automatically created by Docker. If using manual setup:
```bash
createdb tabbacklog
```

**Error: "schema 'auth' does not exist" or "type 'vector' does not exist"**

Schema files must run in order. With Docker, this is automatic. For manual setup:
```bash
psql tabbacklog < database/schema/00_auth_setup.sql
psql tabbacklog < database/schema/01_extensions.sql
psql tabbacklog < database/schema/02_core_tables.sql
psql tabbacklog < database/schema/03_indexes_views.sql
psql tabbacklog < database/schema/04_seed_data.sql
```

### Port Conflicts

**Error: "port is already allocated"**

Check what's using the port:
```bash
# Check port 8000 (web-ui)
sudo netstat -tulpn | grep 8000

# Stop conflicting service
docker stop <container-name>
```

Common conflicts:
- Port 8000: Portainer, other web apps
- Port 5432: Local PostgreSQL
- Port 6006: Other Phoenix instances

### Health Check Failures

**Services showing as "unhealthy":**

1. Check logs: `docker compose logs <service-name>`
2. Verify dependencies are healthy (e.g., postgres must be healthy before web-ui)
3. Wait for startup period (some services take 30-40 seconds)
4. Check health endpoint manually:
   ```bash
   curl http://localhost:8001/health  # parser
   curl http://localhost:8002/health  # enrichment
   curl http://localhost:8000/health  # web-ui
   curl http://localhost:6006/healthz # phoenix
   ```

### LLM Connection Issues

**Error: "LLM connection test failed"**

1. Verify LLM service is running (LM Studio, Ollama, etc.)
2. Check LLM_API_BASE is correct in `.env`
3. Test connection manually:
   ```bash
   curl http://localhost:1234/v1/models
   ```
4. Check enrichment service logs: `docker compose logs enrichment`

### Phoenix Not Showing Traces

1. Verify Phoenix is healthy: `docker compose ps phoenix`
2. Check OTEL_EXPORTER_OTLP_ENDPOINT is not "disabled"
3. Make a test enrichment request to generate traces
4. Check enrichment logs for "Phoenix tracing configured successfully"
5. Access Phoenix UI at http://localhost:6006

### Resetting the Environment

**Complete reset (deletes all data):**
```bash
docker compose down -v
docker compose up -d
```

**Reset only database:**
```bash
docker compose down postgres
docker volume rm tabbacklog-postgres-data
docker compose up -d postgres
```

**Reset only Phoenix data:**
```bash
docker compose down phoenix
docker volume rm tabbacklog-phoenix-data
docker compose up -d phoenix
```

### Adding a New Parser

1. Create `parser_service/parsers/mysite.py`
2. Extend `BaseParser` with `match()` and `parse()` methods
3. Register in `parser_service/parsers/registry.py`

```python
class MySiteParser(BaseParser):
    def match(self, url: str) -> bool:
        return "mysite.com" in url

    def parse(self, url: str, html_content: str) -> ParsedPage:
        # Extract content
        return ParsedPage(
            site_kind="mysite",
            title=title,
            text_full=text,
            word_count=len(text.split()),
            metadata={"custom": "data"},
        )
```

## License

MIT
