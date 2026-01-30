# TabBacklog Architecture Documentation

**Version**: 1.0.0  
**Last Updated**: 2026-01-30  
**Constitution**: See [`.specify/memory/constitution.md`](.specify/memory/constitution.md)

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Principles](#architecture-principles)
3. [Service Architecture](#service-architecture)
4. [Data Architecture](#data-architecture)
5. [Pipeline Architecture](#pipeline-architecture)
6. [API Contracts](#api-contracts)
7. [Deployment Architecture](#deployment-architecture)
8. [Security Architecture](#security-architecture)
9. [Observability Architecture](#observability-architecture)
10. [Extension Points](#extension-points)

---

## System Overview

TabBacklog is a microservices-based tab management system that processes browser tabs through a multi-stage pipeline: ingestion → parsing → enrichment → presentation.

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Interactions                         │
├─────────────────────────────────────────────────────────────────┤
│  Firefox Export  │  Web UI (HTMX)  │  CLI Commands  │  n8n UI   │
└────────┬─────────┴────────┬─────────┴────────┬──────┴───────┬───┘
         │                  │                  │              │
         ▼                  ▼                  ▼              ▼
┌─────────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────┐
│  Ingest CLI     │  │   Web UI     │  │  Parser Svc  │  │  n8n   │
│  (Port: N/A)    │  │  (Port 8000) │  │ (Port 8001)  │  │ (5678) │
└────────┬────────┘  └──────┬───────┘  └──────┬───────┘  └───┬────┘
         │                  │                  │              │
         │                  │                  │              │
         └──────────────────┼──────────────────┼──────────────┘
                            │                  │
                            ▼                  ▼
                    ┌────────────────────────────────┐
                    │   PostgreSQL + pgvector        │
                    │   (Port 5432)                  │
                    └────────────────────────────────┘
                            ▲
                            │
                    ┌───────┴────────┐
                    │  Enrichment    │
                    │  Service       │
                    │  (Port 8002)   │
                    └───────┬────────┘
                            │
                            ▼
                    ┌────────────────┐
                    │  Phoenix       │
                    │  Observability │
                    │  (Port 6006)   │
                    └────────────────┘
```

### Design Philosophy

1. **Microservices**: Each service has a single responsibility and can be deployed independently
2. **Database-Centric**: PostgreSQL is the source of truth; services coordinate through database state
3. **Asynchronous Processing**: n8n orchestrates long-running pipelines
4. **Extensibility**: Plugin architecture for parsers and enrichment strategies
5. **Observability-First**: All LLM interactions are traced and monitored

---

## Architecture Principles

These principles are defined in [`.specify/memory/constitution.md`](.specify/memory/constitution.md):

1. **Microservices Architecture** - Independent deployment and scaling
2. **Database-First Design** - PostgreSQL schema as source of truth
3. **Pipeline Status Tracking** - Explicit state machine for tab processing
4. **Idempotency and Deduplication** - Safe retries and no duplicate data
5. **LLM Observability** - All AI interactions traced via Phoenix
6. **Parser Plugin System** - Extensible content extraction
7. **Configuration via Environment** - No hardcoded values

---

## Service Architecture

### Service Catalog

| Service | Port | Language | Framework | Purpose | Database Access |
|---------|------|----------|-----------|---------|-----------------|
| **Ingest CLI** | N/A | Python 3.11 | Click | Import Firefox bookmarks | Direct (psycopg) |
| **Parser Service** | 8001 | Python 3.11 | FastAPI | Fetch and parse URLs | None (stateless) |
| **Enrichment Service** | 8002 | Python 3.11 | FastAPI + DSPy | Generate LLM metadata | None (stateless) |
| **Web UI** | 8000 | Python 3.11 | FastAPI + HTMX | User interface | Direct (asyncpg) |
| **n8n Orchestrator** | 5678 | Node.js | n8n | Workflow automation | Direct (PostgreSQL node) |
| **Phoenix** | 6006 | Python | Arize Phoenix | LLM observability | Own storage |
| **PostgreSQL** | 5432 | SQL | PostgreSQL 15 | Data persistence | N/A |

### Service Boundaries

#### Ingest CLI
- **Responsibility**: Parse Firefox bookmarks HTML and insert tabs into database
- **Input**: Firefox bookmarks HTML file, user UUID
- **Output**: Tab records in `tab_item` table with status `new`
- **Dependencies**: PostgreSQL
- **Deployment**: Run manually or via cron

#### Parser Service
- **Responsibility**: Fetch URLs and extract structured content
- **Input**: HTTP POST with URL
- **Output**: JSON with `ParsedPage` (title, text, metadata)
- **Dependencies**: None (stateless HTTP service)
- **Deployment**: Docker container, horizontally scalable

#### Enrichment Service
- **Responsibility**: Generate LLM-based summaries and metadata
- **Input**: HTTP POST with URL, title, text
- **Output**: JSON with `Enrichment` (summary, tags, content_type, priority)
- **Dependencies**: LLM API (LM Studio, Ollama, OpenAI-compatible), Phoenix
- **Deployment**: Docker container, horizontally scalable

#### Web UI
- **Responsibility**: User interface for browsing, filtering, and exporting tabs
- **Input**: HTTP requests from browser
- **Output**: HTML (server-rendered with HTMX)
- **Dependencies**: PostgreSQL
- **Deployment**: Docker container, can run multiple instances behind load balancer

#### n8n Orchestrator
- **Responsibility**: Coordinate parser and enrichment services, update database
- **Input**: Cron trigger (every 10 minutes)
- **Output**: Updated tab records with parsed content and enrichments
- **Dependencies**: PostgreSQL, Parser Service, Enrichment Service
- **Deployment**: Docker container, single instance (workflow state)

---

## Data Architecture

### Database Schema Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Core Tables                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐         ┌──────────────┐                     │
│  │  auth.users  │◄────────│  tab_item    │                     │
│  │  (id, email) │         │  (main tab)  │                     │
│  └──────────────┘         └──────┬───────┘                     │
│                                   │                              │
│                    ┌──────────────┼──────────────┐              │
│                    │              │              │              │
│            ┌───────▼──────┐  ┌───▼────────┐  ┌─▼──────────┐   │
│            │ tab_parsed   │  │tab_enrichmt│  │tab_embedding│   │
│            │ (content)    │  │ (LLM meta) │  │  (vectors)  │   │
│            └──────────────┘  └────┬───────┘  └─────────────┘   │
│                                   │                              │
│                          ┌────────▼────────┐                    │
│                          │tab_enrichment_  │                    │
│                          │    history      │                    │
│                          └─────────────────┘                    │
│                                                                  │
│  ┌──────────────┐         ┌──────────────┐                     │
│  │     tag      │◄────────│   tab_tag    │                     │
│  │  (user tags) │         │  (many-many) │                     │
│  └──────────────┘         └──────────────┘                     │
│                                                                  │
│  ┌──────────────────────────────────────┐                      │
│  │          event_log                   │                      │
│  │  (audit trail for all operations)    │                      │
│  └──────────────────────────────────────┘                      │
└─────────────────────────────────────────────────────────────────┘
```

### Key Tables

#### `tab_item` (Main Tab Record)
- **Purpose**: Central record for each browser tab
- **Key Fields**: `id`, `user_id`, `url`, `page_title`, `status`, `is_processed`
- **Status Values**: `new`, `fetch_pending`, `parsed`, `llm_pending`, `enriched`, `fetch_error`, `llm_error`
- **Constraints**: Unique on `(user_id, url)` where `deleted_at IS NULL`

#### `tab_parsed` (Extracted Content)
- **Purpose**: Store parsed content from Parser Service
- **Key Fields**: `tab_id`, `site_kind`, `text_full`, `word_count`, `video_seconds`
- **Site Kinds**: `youtube`, `twitter`, `generic_html`

#### `tab_enrichment` (LLM Metadata)
- **Purpose**: Store current enrichment from Enrichment Service
- **Key Fields**: `tab_id`, `summary`, `content_type`, `priority`, `est_read_min`
- **Content Types**: `article`, `video`, `paper`, `code_repo`, `reference`, `misc`

#### `tab_enrichment_history` (Enrichment Audit)
- **Purpose**: Track all enrichment runs for debugging and comparison
- **Key Fields**: `id`, `tab_id`, `model_name`, `run_started_at`, `run_finished_at`

#### `tag` (User Tags)
- **Purpose**: User-defined and auto-generated tags
- **Key Fields**: `id`, `user_id`, `name`, `kind`
- **Tag Kinds**: `generic`, `project`, `auto`

#### `tab_embedding` (Semantic Search)
- **Purpose**: Vector embeddings for semantic search
- **Key Fields**: `tab_id`, `embedding` (vector(768)), `model_name`
- **Index**: IVFFlat index for cosine similarity search

#### `event_log` (Audit Trail)
- **Purpose**: Log all system events for debugging
- **Key Fields**: `id`, `user_id`, `event_type`, `entity_type`, `entity_id`, `details`

### Views

#### `v_tabs_enriched`
- **Purpose**: Denormalized view joining tabs with parsed content, enrichments, and tags
- **Usage**: Primary query interface for Web UI
- **Performance**: Indexed on common filter columns

---

## Pipeline Architecture

### Tab Processing State Machine

```
┌─────────┐
│   new   │ ◄─── Ingest CLI creates tabs
└────┬────┘
     │
     │ n8n: Query new tabs
     ▼
┌──────────────┐
│fetch_pending │
└──────┬───────┘
       │
       │ n8n: Call Parser Service
       ▼
┌──────────┐         ┌─────────────┐
│  parsed  │         │ fetch_error │ ◄─── Parser failed
└────┬─────┘         └─────────────┘
     │
     │ n8n: Call Enrichment Service
     ▼
┌─────────────┐
│ llm_pending │
└──────┬──────┘
       │
       │ n8n: Store enrichment
       ▼
┌──────────┐         ┌────────────┐
│ enriched │         │ llm_error  │ ◄─── Enrichment failed
└──────────┘         └────────────┘
```

### n8n Workflow Steps

1. **Cron Trigger** (every 10 minutes)
2. **Query New Tabs**: `SELECT * FROM tab_item WHERE status = 'new' LIMIT 10`
3. **Update Status**: Set `status = 'fetch_pending'`
4. **Call Parser Service**: `POST /fetch_parse` with URL
5. **On Parser Success**:
   - Insert/update `tab_parsed`
   - Set `status = 'parsed'`
   - Log event
6. **On Parser Error**:
   - Set `status = 'fetch_error'`
   - Store error in `last_error`
   - Log event
7. **Update Status**: Set `status = 'llm_pending'`
8. **Call Enrichment Service**: `POST /enrich_tab` with parsed content
9. **On Enrichment Success**:
   - Upsert `tab_enrichment`
   - Insert `tab_enrichment_history`
   - Upsert tags and `tab_tag` relationships
   - Set `status = 'enriched'`
   - Log event
10. **On Enrichment Error**:
    - Set `status = 'llm_error'`
    - Store error in `last_error`
    - Log event

### Error Handling Strategy

- **Transient Errors**: Retry up to 3 times with exponential backoff
- **Permanent Errors**: Mark as error state, log details, continue with next tab
- **Partial Success**: Store what succeeded, mark remaining as error
- **Dead Letter Queue**: Error tabs can be manually retried via Web UI

---

## API Contracts

### Parser Service API

#### `POST /fetch_parse`

**Request**:
```json
{
  "url": "https://example.com/article"
}
```

**Response** (200 OK):
```json
{
  "site_kind": "generic_html",
  "title": "Article Title",
  "text_full": "Full article text...",
  "word_count": 1500,
  "video_seconds": null,
  "metadata": {
    "author": "John Doe",
    "published_date": "2024-01-15"
  }
}
```

**Response** (500 Error):
```json
{
  "detail": "Failed to fetch URL: Connection timeout"
}
```

#### `GET /health`

**Response** (200 OK):
```json
{
  "status": "healthy",
  "parsers": ["youtube", "twitter", "generic_html"]
}
```

### Enrichment Service API

#### `POST /enrich_tab`

**Request**:
```json
{
  "url": "https://example.com/article",
  "title": "Article Title",
  "site_kind": "generic_html",
  "text": "Article content..."
}
```

**Response** (200 OK):
```json
{
  "summary": "This article discusses...",
  "content_type": "article",
  "tags": ["#research", "#ai"],
  "projects": ["machine_learning"],
  "est_read_min": 7,
  "priority": "medium",
  "raw_output": {...}
}
```

**Response** (500 Error):
```json
{
  "detail": "LLM request failed: Timeout after 60s",
  "raw_output": "partial response..."
}
```

#### `GET /health`

**Response** (200 OK):
```json
{
  "status": "healthy",
  "llm_connected": true,
  "model": "llama-3.1-8b-instruct"
}
```

### Web UI API

#### `GET /tabs`

**Query Parameters**:
- `content_type`: Filter by content type
- `status`: Filter by pipeline status
- `is_processed`: Filter by processed flag
- `search`: Fuzzy text search
- `read_time_max`: Maximum read time in minutes

**Response**: HTML fragment (HTMX)

#### `POST /tabs/{id}/toggle_processed`

**Response**: Updated HTML row (HTMX)

#### `POST /export/json`

**Request**:
```json
{
  "tab_ids": [1, 2, 3]
}
```

**Response**: JSON file download

---

## Deployment Architecture

### Docker Compose Stack

```yaml
services:
  postgres:       # PostgreSQL with pgvector
  parser-service: # Parser microservice
  enrichment-service: # Enrichment microservice
  web-ui:         # Web interface
  n8n:            # Workflow orchestrator
  phoenix:        # LLM observability
  pgadmin:        # Database admin (dev profile)
```

### Network Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    tabbacklog-network (bridge)               │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Parser   │  │Enrichment│  │  Web UI  │  │   n8n    │   │
│  │  :8001   │  │  :8002   │  │  :8000   │  │  :5678   │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
│       │             │              │             │          │
│       └─────────────┴──────────────┴─────────────┘          │
│                          │                                   │
│                    ┌─────▼──────┐                           │
│                    │ PostgreSQL │                           │
│                    │   :5432    │                           │
│                    └────────────┘                           │
│                                                              │
│                    ┌────────────┐                           │
│                    │  Phoenix   │                           │
│                    │   :6006    │                           │
│                    └────────────┘                           │
└─────────────────────────────────────────────────────────────┘
         │              │              │              │
         ▼              ▼              ▼              ▼
    localhost:8001  localhost:8002  localhost:8000  localhost:5678
```

### Volume Management

- `postgres_data`: PostgreSQL data persistence
- `n8n_data`: n8n workflow state and credentials
- `phoenix_data`: Phoenix traces and analytics

### Health Checks

All services implement health checks:
- **Interval**: 30 seconds
- **Timeout**: 10 seconds
- **Retries**: 3
- **Start Period**: 40 seconds

### Scaling Considerations

- **Parser Service**: Stateless, can scale horizontally
- **Enrichment Service**: Stateless, can scale horizontally (limited by LLM API rate limits)
- **Web UI**: Can scale horizontally behind load balancer
- **n8n**: Single instance (maintains workflow state)
- **PostgreSQL**: Single instance (can use read replicas for queries)

---

## Security Architecture

### Authentication & Authorization

- **Single-User Mode**: Default user UUID in environment variable
- **Multi-User Ready**: `auth.users` table supports multiple users
- **Row-Level Security**: All queries filtered by `user_id`

### Secrets Management

- **Environment Variables**: All secrets in `.env` file
- **Docker Secrets**: Can use Docker secrets for production
- **No Hardcoded Credentials**: Constitution Principle VII enforced

### Network Security

- **Internal Network**: Services communicate via Docker bridge network
- **Exposed Ports**: Only necessary ports exposed to host
- **API Keys**: LLM API keys stored in environment variables

### Data Security

- **Soft Deletes**: `deleted_at` timestamp preserves data
- **Audit Trail**: All operations logged to `event_log`
- **Backup Strategy**: PostgreSQL volume backups recommended

---

## Observability Architecture

### LLM Tracing with Phoenix

```
┌──────────────────┐
│ Enrichment Svc   │
│                  │
│  DSPy + OpenAI   │
│  Instrumentation │
└────────┬─────────┘
         │
         │ OpenTelemetry (OTLP)
         ▼
┌──────────────────┐
│     Phoenix      │
│   (Port 6006)    │
│                  │
│  - Traces        │
│  - Token Usage   │
│  - Latency       │
│  - Errors        │
└──────────────────┘
```

### Logging Strategy

- **Structured Logging**: JSON format for production
- **Log Levels**: DEBUG, INFO, WARNING, ERROR
- **Correlation IDs**: Track requests across services
- **Event Log**: Database table for business events

### Metrics

- **Pipeline Metrics**: Tabs by status, processing time
- **LLM Metrics**: Token usage, cost estimation, latency
- **Error Metrics**: Error rates by type, retry counts
- **Performance Metrics**: Response times, throughput

### Monitoring Endpoints

- `/health`: Service health status
- `/metrics`: Prometheus metrics (future)
- Phoenix UI: LLM observability dashboard

---

## Extension Points

### Adding New Parsers

1. Create parser class in `parser_service/parsers/`
2. Inherit from `BaseParser`
3. Implement `can_parse(url)` and `parse(url, html)`
4. Register in `parser_service/parsers/registry.py`
5. Add tests

**Example**:
```python
class RedditParser(BaseParser):
    def can_parse(self, url: str) -> bool:
        return "reddit.com" in url
    
    def parse(self, url: str, html: str) -> ParsedPage:
        # Extract Reddit post content
        return ParsedPage(...)
```

### Adding New Enrichment Fields

1. Add column to `tab_enrichment` table
2. Update `Enrichment` Pydantic model in `enrichment_service/models.py`
3. Update DSPy signature in `enrichment_service/dspy_setup.py`
4. Update `v_tabs_enriched` view
5. Update Web UI to display new field

### Adding New Export Formats

1. Create new route in `web_ui/routes/export.py`
2. Implement format conversion logic
3. Add button to Web UI template
4. Update documentation

### Adding Semantic Search

1. Generate embeddings using `shared/search.py`
2. Store in `tab_embedding` table
3. Query using vector similarity
4. Add search UI in Web UI

---

## Future Architecture Considerations

### Potential Enhancements

1. **Real-Time Processing**: WebSocket updates for pipeline progress
2. **Batch Processing**: Process multiple tabs in parallel
3. **Caching Layer**: Redis for frequently accessed data
4. **Message Queue**: RabbitMQ/Kafka for event-driven architecture
5. **API Gateway**: Centralized authentication and routing
6. **Read Replicas**: Scale read-heavy queries
7. **Multi-Tenancy**: Full multi-user support with isolation

### Migration Path

- Current: Single-user, Docker Compose deployment
- Next: Multi-user with authentication
- Future: Kubernetes deployment with auto-scaling

---

## References

- [Constitution](.specify/memory/constitution.md) - Core principles and constraints
- [README.md](README.md) - Setup and usage instructions
- [CLAUDE_CODE_SPEC.md](CLAUDE_CODE_SPEC.md) - Implementation specification
- [Database Schema](database/schema/) - SQL schema files
- [n8n Workflow](n8n/workflows/enrich_tabs.json) - Orchestration workflow
