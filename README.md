# TabBacklog v1 - Quick Reference Guide

## File Inventory

### Core Documentation
- **CLAUDE_CODE_SPEC.md** - Complete implementation specification
- **README.md** - This file, quick reference

### Database Files
- **01_core_tables.sql** - Main database schema with all tables
- **02_extensions_indexes.sql** - PostgreSQL extensions, indexes, and views
- **03_seed_data.sql** - Seed data for project tags and initialization

### Python Files
- **requirements.txt** - All Python dependencies
- **config.py** - Shared configuration module
- **parser_base.py** - Base parser class and registry system
- **.env.example** - Environment variables template

## Quick Start for Claude Code

### Step 1: Set Up Database
```sql
-- Run these in order
\i 01_core_tables.sql
\i 02_extensions_indexes.sql
\i 03_seed_data.sql

-- Initialize a user
SELECT initialize_user_data('YOUR_USER_ID'::uuid);
```

### Step 2: Set Up Python Environment
```bash
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env with your actual values
```

### Step 3: Build Services in Order

#### 3.1: Ingest Script (Python CLI)
**Location**: `ingest/`
**Files**: `cli.py`, `firefox_parser.py`, `db.py`
**Purpose**: Parse Firefox bookmarks HTML and insert into database

#### 3.2: Parser Service (FastAPI)
**Location**: `parser_service/`
**Files**: `main.py`, `parsers/*.py`, `models.py`
**Purpose**: HTTP service that fetches and parses URLs
**Endpoint**: `POST /fetch_parse`

Implement parsers:
- `GenericHtmlParser` - Extract title and text from any HTML
- `YouTubeParser` - Use yt-dlp to get video metadata
- `TwitterParser` - Extract tweet content from meta tags

#### 3.3: Enrichment Service (FastAPI + DSPy)
**Location**: `enrichment_service/`
**Files**: `main.py`, `dspy_setup.py`, `models.py`
**Purpose**: LLM enrichment with structured output
**Endpoint**: `POST /enrich_tab`

Use DSPy TypedPredictor with Pydantic model for:
- Summary
- Content type classification
- Tag generation
- Project assignment
- Reading time estimation

#### 3.4: n8n Workflow
**Location**: `n8n/workflows/`
**File**: `enrich_tabs.json`
**Purpose**: Orchestrate fetch → parse → enrich pipeline

Workflow steps:
1. Cron trigger (every 10 min)
2. Query new tabs from DB
3. Call parser service
4. Call enrichment service
5. Update database
6. Log events
7. Send error emails

#### 3.5: Web UI (FastAPI + HTMX)
**Location**: `web_ui/`
**Files**: `main.py`, `routes/*.py`, `templates/*.html`
**Purpose**: Browse, filter, and export tabs

Features:
- Filter by content type, project, status, processed
- Fuzzy search with trigram
- Toggle processed status
- Export to JSON/Markdown
- HTMX for dynamic updates

### Step 4: Containerize
Create Dockerfiles for each service and docker-compose.yml

## Implementation Checklist

### Phase 1: Database ✓
- [x] Core tables schema
- [x] Extensions and indexes
- [x] Seed data and functions
- [ ] Run migrations
- [ ] Initialize test user

### Phase 2: Ingest Script
- [ ] Parse Firefox bookmarks HTML
- [ ] Database insert logic
- [ ] Event logging
- [ ] CLI interface

### Phase 3: Parser Service
- [ ] Base parser class ✓
- [ ] Parser registry ✓
- [ ] GenericHtmlParser
- [ ] YouTubeParser
- [ ] TwitterParser
- [ ] FastAPI endpoints
- [ ] Error handling

### Phase 4: Enrichment Service
- [ ] DSPy configuration
- [ ] Pydantic models
- [ ] TypedPredictor setup
- [ ] FastAPI endpoints
- [ ] Retry logic

### Phase 5: n8n Workflow
- [ ] Workflow JSON
- [ ] Postgres nodes
- [ ] HTTP nodes
- [ ] Error handling
- [ ] Email notifications

### Phase 6: Web UI
- [ ] FastAPI app skeleton
- [ ] Base templates
- [ ] Tab listing endpoint
- [ ] Filter implementation
- [ ] Search implementation
- [ ] Toggle processed
- [ ] Export JSON
- [ ] Export Markdown

### Phase 7: Search
- [ ] Fuzzy search queries
- [ ] Semantic search endpoint
- [ ] Embedding generation job

### Phase 8: Deployment
- [ ] Dockerfiles
- [ ] docker-compose.yml
- [ ] Health checks
- [ ] Logging
- [ ] Documentation

## Key Design Patterns

### Parser Plugin Pattern
```python
# Register parsers in order of specificity
register_parser(YouTubeParser())
register_parser(TwitterParser())
register_parser(GenericHtmlParser())  # Fallback

# Parse automatically selects the right parser
result = parse_page(url, html_content)
```

### DSPy Structured Output
```python
# Define schema with Pydantic
class Enrichment(BaseModel):
    summary: str
    content_type: Literal["article", "video", ...]
    # ...

# Use TypedPredictor
predictor = TypedPredictor(EnrichSignature)
result = predictor(url=url, title=title, text=text)
```

### Event Logging
```python
# Log everything to event_log table
INSERT INTO event_log (user_id, event_type, entity_type, entity_id, details)
VALUES (:user_id, 'tab_created', 'tab_item', :tab_id, :details_json)
```

### Status State Machine
```
new → fetch_pending → parsed → llm_pending → enriched
   ↓                     ↓                       ↓
fetch_error        parse_error            llm_error
```

## Testing Strategy

### Unit Tests
- Parser plugins with sample HTML
- DSPy enrichment with mock LLM
- Database operations

### Integration Tests
- Full pipeline: ingest → parse → enrich
- n8n workflow execution
- Web UI endpoints

### Manual Testing
1. Export Firefox bookmarks
2. Run ingest script
3. Trigger n8n workflow
4. Check Web UI
5. Export to Markdown

## Common Issues & Solutions

### Database Connection
- Check DATABASE_URL format
- Verify pg_trgm and vector extensions installed
- Test connection: `psql $DATABASE_URL`

### LLM Service
- Ensure LM Studio/Ollama running
- Test API: `curl $LLM_API_BASE/models`
- Check model name matches

### Parser Failures
- Add logging to see which parser matched
- Check HTML structure for site changes
- Add more specific parsers as needed

### n8n Workflow
- Test each node individually
- Check error nodes configured
- Verify database credentials

## Environment Variable Priority

1. **DATABASE_URL** - Must be set first
2. **LLM_API_BASE** & **LLM_MODEL_NAME** - Required for enrichment
3. **DEFAULT_USER_ID** - Needed for single-user setup
4. **Service URLs** - For n8n orchestration

## File Structure to Create

```
tabbacklog/
├── database/
│   └── schema/
│       ├── 01_core_tables.sql ✓
│       ├── 02_extensions_indexes.sql ✓
│       └── 03_seed_data.sql ✓
├── ingest/
│   ├── cli.py
│   ├── firefox_parser.py
│   └── db.py
├── parser_service/
│   ├── main.py
│   ├── parsers/
│   │   ├── base.py ✓
│   │   ├── registry.py ✓
│   │   ├── generic.py
│   │   ├── youtube.py
│   │   └── twitter.py
│   └── Dockerfile
├── enrichment_service/
│   ├── main.py
│   ├── dspy_setup.py
│   └── Dockerfile
├── web_ui/
│   ├── main.py
│   ├── routes/
│   ├── templates/
│   └── Dockerfile
├── n8n/
│   └── workflows/
│       └── enrich_tabs.json
├── shared/
│   ├── config.py ✓
│   └── db.py
├── requirements.txt ✓
├── .env.example ✓
└── docker-compose.yml
```

## Next Steps

Start with **Phase 2: Ingest Script** since database schema is complete.

1. Create `ingest/firefox_parser.py` to parse bookmarks HTML
2. Create `ingest/db.py` with database insert operations
3. Create `ingest/cli.py` with Click CLI interface
4. Test with actual Firefox export

Then move to **Phase 3: Parser Service** for the core parsing logic.
