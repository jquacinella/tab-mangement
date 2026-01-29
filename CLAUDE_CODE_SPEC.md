# TabBacklog v1 - Implementation Specification for Claude Code

## Project Summary

Build a Firefox tab management system that captures ~1000 browser tabs into a structured database, enriches them with LLM-generated summaries and metadata, and provides a searchable web interface for processing and exporting.

## Tech Stack

- **Database**: PostgreSQL (Supabase)
- **Backend Services**: Python 3.11+, FastAPI
- **LLM Framework**: DSPy with Llama 3.1 8B Instruct
- **Orchestration**: n8n workflows
- **Frontend**: HTMX + server-side rendering
- **Deployment**: Podman containers
- **Key Libraries**: httpx, BeautifulSoup4, yt-dlp, asyncpg/psycopg

## Architecture Overview

```
Firefox Bookmarks Export
    ↓
Ingest Script (CLI) → Supabase/Postgres
    ↓
n8n Orchestrator
    ├→ Fetch+Parse Microservice (plugins for YouTube, Twitter, generic HTML)
    ├→ LLM Enrichment Service (DSPy + local Llama)
    └→ Update Database (parsed content, enrichments, tags)
    ↓
Web UI (HTMX) ← User filters, searches, marks processed, exports
```

## Project Structure

```
tabbacklog/
├── README.md
├── docker-compose.yml (or podman-compose)
├── .env.example
│
├── database/
│   ├── schema/
│   │   ├── 01_core_tables.sql
│   │   ├── 02_indexes.sql
│   │   ├── 03_extensions.sql
│   │   └── 04_seed_data.sql
│   └── migrations/
│
├── ingest/
│   ├── __init__.py
│   ├── cli.py              # Main ingest script
│   ├── firefox_parser.py   # Parse Firefox bookmarks HTML
│   └── db.py               # Database operations
│
├── parser_service/
│   ├── __init__.py
│   ├── main.py            # FastAPI app
│   ├── parsers/
│   │   ├── __init__.py
│   │   ├── base.py        # BaseParser, ParsedPage
│   │   ├── registry.py    # Parser registration
│   │   ├── generic.py     # GenericHtmlParser
│   │   ├── youtube.py     # YouTubeParser
│   │   └── twitter.py     # TwitterParser
│   ├── models.py          # Pydantic models
│   └── Dockerfile
│
├── enrichment_service/
│   ├── __init__.py
│   ├── main.py            # FastAPI app with DSPy
│   ├── dspy_setup.py      # DSPy configuration
│   ├── models.py          # Pydantic enrichment model
│   └── Dockerfile
│
├── web_ui/
│   ├── __init__.py
│   ├── main.py            # FastAPI app
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── tabs.py        # Tab listing/filtering
│   │   └── export.py      # Export endpoints
│   ├── templates/
│   │   ├── base.html
│   │   ├── index.html
│   │   └── fragments/
│   │       └── tab_rows.html
│   ├── static/
│   │   ├── css/
│   │   └── js/
│   └── Dockerfile
│
├── n8n/
│   └── workflows/
│       └── enrich_tabs.json
│
├── shared/
│   ├── __init__.py
│   ├── config.py         # Shared configuration
│   └── db.py             # Database connection utilities
│
└── tests/
    ├── test_parsers.py
    ├── test_enrichment.py
    └── test_ingest.py
```

## Implementation Phases

### PHASE 1: Database Setup

**Files to create:**
- `database/schema/01_core_tables.sql`
- `database/schema/02_indexes.sql`
- `database/schema/03_extensions.sql`
- `database/schema/04_seed_data.sql`

**Key tables:**
- `tab_item` - Main tab record with status tracking
- `tab_parsed` - Parsed content from fetch/parse
- `tab_enrichment` - LLM-generated metadata
- `tab_enrichment_history` - Enrichment run history
- `tag` - User-defined tags
- `tab_tag` - Many-to-many tag relationships
- `tab_embedding` - Vector embeddings for semantic search
- `event_log` - System events for debugging

**Requirements:**
- Enable `pg_trgm` extension for fuzzy search
- Enable `pgvector` extension for semantic search
- Create GIN indexes on text columns for trigram search
- Add unique constraint on `(user_id, url)` in `tab_item`
- All tables include: `user_id`, `created_at`, `updated_at`, `deleted_at`

### PHASE 2: Ingest Script

**Files to create:**
- `ingest/cli.py`
- `ingest/firefox_parser.py`
- `ingest/db.py`

**Functionality:**
- Parse Firefox bookmarks HTML export (BeautifulSoup)
- Look for "Session-" folders containing tab URLs
- Extract: URL, page title, window label
- Upsert into `tab_item` (dedupe on user_id + url)
- Log events to `event_log`
- CLI arguments: `--file`, `--user-id`

**Example usage:**
```bash
python -m ingest.cli --file ~/bookmarks.html --user-id UUID
```

### PHASE 3: Parser Service

**Files to create:**
- `parser_service/main.py`
- `parser_service/parsers/base.py`
- `parser_service/parsers/registry.py`
- `parser_service/parsers/generic.py`
- `parser_service/parsers/youtube.py`
- `parser_service/parsers/twitter.py`
- `parser_service/models.py`
- `parser_service/Dockerfile`

**Parser Plugin System:**

Create base class:
```python
@dataclass
class ParsedPage:
    site_kind: str
    title: str | None
    text_full: str | None
    word_count: int | None
    video_seconds: int | None
    metadata: dict
```

**GenericHtmlParser:**
- Extract `<title>` tag
- Extract all `<p>` text and article content
- Calculate word count
- site_kind = 'generic_html'

**YouTubeParser:**
- Match URLs: youtube.com/watch, youtu.be
- Use `yt-dlp -J URL` to fetch JSON metadata
- Extract: title, description, duration, uploader
- site_kind = 'youtube'

**TwitterParser:**
- Match URLs: twitter.com, x.com
- Parse meta tags for tweet text
- Extract author, timestamp
- site_kind = 'twitter'

**FastAPI Endpoints:**
```
POST /fetch_parse
{
  "url": "https://example.com"
}
→ Returns ParsedPage JSON
```

### PHASE 4: LLM Enrichment Service

**Files to create:**
- `enrichment_service/main.py`
- `enrichment_service/dspy_setup.py`
- `enrichment_service/models.py`
- `enrichment_service/Dockerfile`

**DSPy Configuration:**
- Initialize with JSONAdapter
- Connect to OpenAI-compatible API (LM Studio, Ollama, or custom)
- Use Llama 3.1 8B Instruct model

**Pydantic Model:**
```python
class Enrichment(BaseModel):
    summary: str
    content_type: Literal["article", "video", "paper", "code_repo", "reference", "misc"]
    tags: List[str]  # e.g., ["#video", "#longread"]
    projects: List[str]  # argumentation_on_the_web, democratic_economic_planning, other_research
    est_read_min: int | None
    priority: Literal["high", "medium", "low"] | None
```

**FastAPI Endpoints:**
```
POST /enrich_tab
{
  "url": "...",
  "title": "...",
  "site_kind": "...",
  "text": "..."
}
→ Returns Enrichment JSON
```

**Error Handling:**
- Retry on validation failure (max 3 attempts)
- Return 500 with `raw_output` if persistent failure

### PHASE 5: n8n Orchestration Workflow

**File to create:**
- `n8n/workflows/enrich_tabs.json`

**Workflow Steps:**

1. **Cron Trigger** (every 10 minutes)
2. **Postgres: Get New Tabs**
   - Query: `SELECT * FROM tab_item WHERE status = 'new' AND deleted_at IS NULL LIMIT 10`
3. **Split in Batches** (process 2 at a time)
4. **For each tab:**
   - **Update status to 'fetch_pending'**
   - **HTTP: POST to parser service** `/fetch_parse`
   - **On success:**
     - Insert/update `tab_parsed`
     - Update status to 'parsed'
     - Log event
   - **On error:**
     - Update status to 'fetch_error'
     - Log error
5. **For parsed tabs:**
   - **Update status to 'llm_pending'**
   - **HTTP: POST to enrichment service** `/enrich_tab`
   - **On success:**
     - Upsert `tab_enrichment`
     - Insert `tab_enrichment_history`
     - Upsert tags and `tab_tag` relationships
     - Update status to 'enriched'
     - Log event
   - **On error:**
     - Update status to 'llm_error'
     - Log error
6. **Aggregate Errors**
   - If any errors, send email summary

### PHASE 6: Web UI (HTMX)

**Files to create:**
- `web_ui/main.py`
- `web_ui/routes/tabs.py`
- `web_ui/routes/export.py`
- `web_ui/templates/base.html`
- `web_ui/templates/index.html`
- `web_ui/templates/fragments/tab_rows.html`
- `web_ui/static/css/style.css`
- `web_ui/Dockerfile`

**Routes:**

**GET /**
- Render main page with filters
- Auto-load tabs via HTMX

**GET /tabs** (HTMX fragment)
- Query parameters:
  - `content_type`: filter by type
  - `project`: filter by project tag
  - `read_time_max`: filter by estimated read time
  - `status`: filter by pipeline status
  - `is_processed`: filter by processed flag
  - `search`: fuzzy text search
  - `semantic_search`: semantic search mode
- Return `<tbody>` with tab rows
- Each row includes:
  - Checkbox for selection
  - Title (link to URL)
  - Content type badge
  - Tags
  - Estimated read time
  - Processed toggle button

**POST /tabs/{id}/toggle_processed**
- Toggle `is_processed` flag
- Set/clear `processed_at`
- Log event
- Return updated row HTML

**POST /export/json**
- Accept list of tab IDs
- Return JSON array

**POST /export/markdown**
- Accept list of tab IDs
- Generate Markdown for each tab
- Return as downloadable file

**UI Features:**
- Filter dropdowns for content_type, project, status
- Search box with debounce
- Select all/none checkboxes
- Bulk export buttons
- Responsive table
- HTMX for dynamic updates without page reload

### PHASE 7: Search Implementation

**Fuzzy Search (pg_trgm):**
- Already enabled in schema
- Use in `/tabs` query:
  ```sql
  WHERE (tab_item.page_title % :search 
      OR tab_enrichment.summary % :search)
  ```

**Semantic Search (optional):**
- Create embedding generation job
- Use same model for query and document embeddings
- Query with vector similarity:
  ```sql
  SELECT ... FROM tab_embedding
  ORDER BY embedding <-> :query_embedding
  LIMIT 50
  ```

### PHASE 8: Containerization

**Files to create:**
- `docker-compose.yml` (or `podman-compose.yml`)
- `.env.example`
- Individual Dockerfiles for each service

**Containers:**
- `tabbacklog-parser` - Parser microservice
- `tabbacklog-llm` - Enrichment service
- `tabbacklog-ui` - Web UI
- `tabbacklog-n8n` - n8n orchestrator

**Environment Variables:**
```bash
DATABASE_URL=postgresql://user:pass@host/db
SUPABASE_SERVICE_ROLE_KEY=...
LLM_API_BASE=http://localhost:1234/v1
LLM_API_KEY=...
LLM_MODEL_NAME=llama-3.1-8b-instruct
N8N_SMTP_HOST=...
N8N_SMTP_USER=...
N8N_SMTP_PASS=...
APP_SECRET_KEY=...
```

## Implementation Order

1. Set up database schema and extensions
2. Build and test ingest script
3. Build parser service with all plugins
4. Build enrichment service with DSPy
5. Create n8n workflow
6. Build web UI
7. Add search functionality
8. Containerize everything
9. Write documentation

## Testing Checklist

- [ ] Ingest script correctly parses Firefox bookmarks HTML
- [ ] Parser service handles generic HTML, YouTube, Twitter
- [ ] Enrichment service returns valid structured JSON
- [ ] n8n workflow processes tabs through full pipeline
- [ ] Web UI filters and search work correctly
- [ ] Export generates valid JSON and Markdown
- [ ] Containers start and communicate properly
- [ ] Error handling logs to event_log

## Key Design Principles

1. **Modularity**: Each service is independent and replaceable
2. **Idempotency**: Rerunning operations is safe
3. **Observability**: All operations logged to event_log
4. **Extensibility**: Easy to add new parsers or enrichment features
5. **Offline-first**: No real-time browser integration (batch processing)

## Non-Goals for v1

- Real-time tab syncing
- Multi-user authentication
- Firefox extension
- Advanced semantic features beyond basic scaffolding
- WebDriver/Selenium automation

## Success Criteria

- Successfully ingest 1000+ tabs from Firefox export
- Automatically enrich tabs with summaries and metadata
- Searchable, filterable web interface
- Export capabilities for Obsidian integration
- All services containerized and documented
