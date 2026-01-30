# TabBacklog API Documentation

**Version**: 1.0.0  
**Last Updated**: 2026-01-30  
**Base URLs**:
- Parser Service: `http://localhost:8001`
- Enrichment Service: `http://localhost:8002`
- Web UI: `http://localhost:8000`

## Table of Contents

1. [Parser Service API](#parser-service-api)
2. [Enrichment Service API](#enrichment-service-api)
3. [Web UI API](#web-ui-api)
4. [Data Models](#data-models)
5. [Error Handling](#error-handling)
6. [Rate Limiting](#rate-limiting)

---

## Parser Service API

**Base URL**: `http://localhost:8001`

### Health Check

Check if the parser service is running and which parsers are available.

**Endpoint**: `GET /health`

**Response** (200 OK):
```json
{
  "status": "healthy",
  "parsers": ["youtube", "twitter", "generic_html"],
  "version": "1.0.0"
}
```

**Example**:
```bash
curl http://localhost:8001/health
```

---

### Fetch and Parse URL

Fetch a URL and extract structured content using the appropriate parser.

**Endpoint**: `POST /fetch_parse`

**Request Body**:
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
  "text_full": "Full article text content...",
  "word_count": 1500,
  "video_seconds": null,
  "metadata": {
    "author": "John Doe",
    "published_date": "2024-01-15",
    "description": "Article description"
  }
}
```

**Response** (400 Bad Request):
```json
{
  "detail": "Invalid URL format"
}
```

**Response** (500 Internal Server Error):
```json
{
  "detail": "Failed to fetch URL: Connection timeout"
}
```

**Examples**:

```bash
# Parse a generic HTML page
curl -X POST http://localhost:8001/fetch_parse \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/article"}'

# Parse a YouTube video
curl -X POST http://localhost:8001/fetch_parse \
  -H "Content-Type: application/json" \
  -d '{"url": "https://youtube.com/watch?v=dQw4w9WgXcQ"}'

# Parse a Twitter/X post
curl -X POST http://localhost:8001/fetch_parse \
  -H "Content-Type: application/json" \
  -d '{"url": "https://twitter.com/user/status/123456789"}'
```

**Parser Selection**:
- **YouTube**: URLs matching `youtube.com/watch` or `youtu.be`
- **Twitter**: URLs matching `twitter.com` or `x.com`
- **Generic HTML**: Fallback for all other URLs

**Timeout**: 30 seconds (configurable via `FETCH_TIMEOUT`)

---

## Enrichment Service API

**Base URL**: `http://localhost:8002`

### Health Check

Check if the enrichment service is running and connected to the LLM.

**Endpoint**: `GET /health`

**Response** (200 OK):
```json
{
  "status": "healthy",
  "llm_connected": true,
  "model": "llama-3.1-8b-instruct",
  "phoenix_enabled": true,
  "version": "1.0.0"
}
```

**Response** (503 Service Unavailable):
```json
{
  "status": "unhealthy",
  "llm_connected": false,
  "error": "Cannot connect to LLM API"
}
```

**Example**:
```bash
curl http://localhost:8002/health
```

---

### Enrich Tab

Generate LLM-based metadata for a tab including summary, tags, and classification.

**Endpoint**: `POST /enrich_tab`

**Request Body**:
```json
{
  "url": "https://example.com/article",
  "title": "Understanding Machine Learning",
  "site_kind": "generic_html",
  "text": "Machine learning is a subset of artificial intelligence..."
}
```

**Response** (200 OK):
```json
{
  "summary": "This article provides an introduction to machine learning concepts, covering supervised and unsupervised learning approaches with practical examples.",
  "content_type": "article",
  "tags": ["#machinelearning", "#ai", "#tutorial"],
  "projects": ["machine_learning", "research"],
  "est_read_min": 7,
  "priority": "medium",
  "raw_output": {
    "model": "llama-3.1-8b-instruct",
    "tokens_used": 450,
    "completion_time": 2.3
  }
}
```

**Response** (400 Bad Request):
```json
{
  "detail": "Missing required field: text"
}
```

**Response** (500 Internal Server Error):
```json
{
  "detail": "LLM request failed: Timeout after 60s",
  "raw_output": "partial response if available"
}
```

**Examples**:

```bash
# Enrich an article
curl -X POST http://localhost:8002/enrich_tab \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/article",
    "title": "Understanding ML",
    "site_kind": "generic_html",
    "text": "Machine learning is..."
  }'

# Enrich a YouTube video
curl -X POST http://localhost:8002/enrich_tab \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://youtube.com/watch?v=abc",
    "title": "ML Tutorial",
    "site_kind": "youtube",
    "text": "Video description and transcript..."
  }'
```

**Content Types**:
- `article`: Blog posts, news articles, tutorials
- `video`: YouTube videos, video content
- `paper`: Academic papers, research documents
- `code_repo`: GitHub repositories, code documentation
- `reference`: API docs, reference materials
- `misc`: Other content types

**Priority Levels**:
- `high`: Important, time-sensitive content
- `medium`: Standard priority
- `low`: Nice-to-have, low priority

**Timeout**: 60 seconds (configurable via `LLM_TIMEOUT`)

**Retry Logic**: Up to 3 retries with exponential backoff

---

## Web UI API

**Base URL**: `http://localhost:8000`

### Get Tabs (HTMX Fragment)

Retrieve filtered and paginated tabs as HTML fragment.

**Endpoint**: `GET /tabs`

**Query Parameters**:
- `content_type` (optional): Filter by content type (article, video, paper, etc.)
- `status` (optional): Filter by pipeline status (new, parsed, enriched, etc.)
- `is_processed` (optional): Filter by processed flag (true, false)
- `search` (optional): Fuzzy text search query
- `read_time_max` (optional): Maximum read time in minutes
- `tag` (optional): Filter by tag name
- `limit` (optional): Number of results (default: 50)
- `offset` (optional): Pagination offset (default: 0)

**Response** (200 OK): HTML fragment with tab rows

**Examples**:

```bash
# Get all tabs
curl http://localhost:8000/tabs

# Get unprocessed articles
curl "http://localhost:8000/tabs?content_type=article&is_processed=false"

# Search for "machine learning"
curl "http://localhost:8000/tabs?search=machine+learning"

# Get tabs with read time under 10 minutes
curl "http://localhost:8000/tabs?read_time_max=10"
```

---

### Toggle Processed Status

Mark a tab as processed or unprocessed.

**Endpoint**: `POST /tabs/{tab_id}/toggle_processed`

**Path Parameters**:
- `tab_id`: Tab ID (integer)

**Response** (200 OK): Updated HTML row fragment

**Response** (404 Not Found):
```json
{
  "detail": "Tab not found"
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/tabs/123/toggle_processed
```

---

### Export Tabs (JSON)

Export selected tabs as JSON.

**Endpoint**: `POST /export/json`

**Request Body**:
```json
{
  "tab_ids": [1, 2, 3, 4, 5]
}
```

**Response** (200 OK): JSON file download
```json
[
  {
    "id": 1,
    "url": "https://example.com/article",
    "page_title": "Article Title",
    "content_type": "article",
    "summary": "Article summary...",
    "tags": ["#research", "#ai"],
    "est_read_min": 7,
    "collected_at": "2024-01-15T10:30:00Z"
  },
  ...
]
```

**Example**:
```bash
curl -X POST http://localhost:8000/export/json \
  -H "Content-Type: application/json" \
  -d '{"tab_ids": [1, 2, 3]}' \
  -o tabs.json
```

---

### Export Tabs (Markdown)

Export selected tabs as Markdown.

**Endpoint**: `POST /export/markdown`

**Request Body**:
```json
{
  "tab_ids": [1, 2, 3]
}
```

**Response** (200 OK): Markdown file download

**Example**:
```bash
curl -X POST http://localhost:8000/export/markdown \
  -H "Content-Type: application/json" \
  -d '{"tab_ids": [1, 2, 3]}' \
  -o tabs.md
```

---

### Export Tabs (Obsidian)

Export selected tabs in Obsidian-compatible format.

**Endpoint**: `POST /export/obsidian`

**Request Body**:
```json
{
  "tab_ids": [1, 2, 3]
}
```

**Response** (200 OK): ZIP file with Markdown files

**Example**:
```bash
curl -X POST http://localhost:8000/export/obsidian \
  -H "Content-Type: application/json" \
  -d '{"tab_ids": [1, 2, 3]}' \
  -o tabs.zip
```

---

### Semantic Search

Perform semantic search using vector embeddings.

**Endpoint**: `GET /search/semantic`

**Query Parameters**:
- `q` (required): Search query
- `limit` (optional): Number of results (default: 20)

**Response** (200 OK): HTML fragment with search results

**Example**:
```bash
curl "http://localhost:8000/search/semantic?q=machine+learning+tutorials"
```

**Note**: Requires embeddings to be generated first via `/search/generate-embeddings`

---

### Generate Embeddings

Generate vector embeddings for all tabs (background job).

**Endpoint**: `POST /search/generate-embeddings`

**Response** (202 Accepted):
```json
{
  "status": "started",
  "message": "Embedding generation started in background"
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/search/generate-embeddings
```

---

### Statistics

Get statistics about tabs in the system.

**Endpoint**: `GET /stats`

**Response** (200 OK): HTML page with statistics

**Example**:
```bash
curl http://localhost:8000/stats
```

---

## Data Models

### ParsedPage

Returned by Parser Service.

```typescript
{
  site_kind: "youtube" | "twitter" | "generic_html",
  title: string | null,
  text_full: string | null,
  word_count: number | null,
  video_seconds: number | null,
  metadata: {
    [key: string]: any
  }
}
```

### Enrichment

Returned by Enrichment Service.

```typescript
{
  summary: string,
  content_type: "article" | "video" | "paper" | "code_repo" | "reference" | "misc",
  tags: string[],
  projects: string[],
  est_read_min: number | null,
  priority: "high" | "medium" | "low" | null,
  raw_output: {
    model: string,
    tokens_used: number,
    completion_time: number
  }
}
```

### Tab (Web UI)

```typescript
{
  id: number,
  user_id: string,
  url: string,
  page_title: string | null,
  window_label: string | null,
  collected_at: string,
  status: "new" | "fetch_pending" | "parsed" | "llm_pending" | "enriched" | "fetch_error" | "llm_error",
  is_processed: boolean,
  processed_at: string | null,
  
  // From tab_parsed
  site_kind: string | null,
  word_count: number | null,
  
  // From tab_enrichment
  summary: string | null,
  content_type: string | null,
  est_read_min: number | null,
  priority: string | null,
  tags: string[] | null
}
```

---

## Error Handling

### Standard Error Response

All services return errors in this format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

### HTTP Status Codes

- **200 OK**: Request succeeded
- **202 Accepted**: Request accepted for background processing
- **400 Bad Request**: Invalid request parameters
- **404 Not Found**: Resource not found
- **500 Internal Server Error**: Server error
- **503 Service Unavailable**: Service temporarily unavailable
- **504 Gateway Timeout**: Request timeout

### Error Types

#### Parser Service Errors

- **Invalid URL**: Malformed URL provided
- **Fetch Failed**: Cannot retrieve URL content
- **Parse Failed**: Cannot extract content from HTML
- **Timeout**: Request exceeded timeout limit

#### Enrichment Service Errors

- **LLM Connection Failed**: Cannot connect to LLM API
- **LLM Timeout**: LLM request exceeded timeout
- **Validation Failed**: LLM output doesn't match expected schema
- **Rate Limited**: Too many requests to LLM API

#### Web UI Errors

- **Database Error**: Database query failed
- **Not Found**: Tab or resource not found
- **Invalid Filter**: Invalid filter parameters

---

## Rate Limiting

### Parser Service

- **Concurrent Requests**: 10 (configurable)
- **Timeout**: 30 seconds per request
- **Retry**: 3 attempts with exponential backoff

### Enrichment Service

- **Concurrent Requests**: 2 (configurable, limited by LLM API)
- **Timeout**: 60 seconds per request
- **Retry**: 3 attempts with exponential backoff
- **Rate Limit**: Depends on LLM provider

### Web UI

- **No explicit rate limiting**: Designed for single-user or small team use
- **Database Connection Pool**: 10 connections (configurable)

---

## Authentication

**Current Version**: Single-user mode with default user UUID

**Future**: Multi-user authentication with JWT tokens

**Configuration**: Set `DEFAULT_USER_ID` in `.env`

---

## CORS

**Current Version**: CORS not enabled (services on same network)

**Future**: Configurable CORS for external access

---

## Versioning

**Current Version**: 1.0.0

**API Versioning Strategy**: 
- Breaking changes will increment major version
- New endpoints will increment minor version
- Bug fixes will increment patch version

**Backward Compatibility**: 
- Current APIs are stable for v1.x.x
- Deprecated endpoints will be marked in documentation
- Breaking changes will be announced in advance

---

## Examples

### Complete Workflow Example

```bash
# 1. Check services are healthy
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8000/health

# 2. Parse a URL
PARSED=$(curl -s -X POST http://localhost:8001/fetch_parse \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/article"}')

echo $PARSED | jq

# 3. Enrich the content
ENRICHED=$(curl -s -X POST http://localhost:8002/enrich_tab \
  -H "Content-Type: application/json" \
  -d "{
    \"url\": \"https://example.com/article\",
    \"title\": $(echo $PARSED | jq -r .title),
    \"site_kind\": $(echo $PARSED | jq -r .site_kind),
    \"text\": $(echo $PARSED | jq -r .text_full)
  }")

echo $ENRICHED | jq

# 4. View tabs in Web UI
curl "http://localhost:8000/tabs?content_type=article"

# 5. Export tabs
curl -X POST http://localhost:8000/export/json \
  -H "Content-Type: application/json" \
  -d '{"tab_ids": [1, 2, 3]}' \
  -o tabs.json
```

---

## Testing APIs

### Using curl

```bash
# Pretty print JSON responses
curl http://localhost:8001/health | jq

# Save response to file
curl http://localhost:8000/tabs > tabs.html

# Follow redirects
curl -L http://localhost:8000/

# Include headers in output
curl -i http://localhost:8001/health

# Verbose output for debugging
curl -v http://localhost:8002/health
```

### Using httpie

```bash
# Install httpie
pip install httpie

# Make requests
http GET localhost:8001/health
http POST localhost:8001/fetch_parse url="https://example.com"
```

### Using Python

```python
import httpx

# Parser Service
async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8001/fetch_parse",
        json={"url": "https://example.com"}
    )
    parsed = response.json()
    print(parsed)

# Enrichment Service
async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8002/enrich_tab",
        json={
            "url": "https://example.com",
            "title": "Example",
            "site_kind": "generic_html",
            "text": "Content..."
        }
    )
    enriched = response.json()
    print(enriched)
```

---

## Additional Resources

- [Architecture Documentation](ARCHITECTURE.md)
- [Developer Guide](DEVELOPER_GUIDE.md)
- [Constitution](.specify/memory/constitution.md)
- [README](README.md)

---

**Last Updated**: 2026-01-30  
**API Version**: 1.0.0
