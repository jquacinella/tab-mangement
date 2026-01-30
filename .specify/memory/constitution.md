# TabBacklog Project Constitution

<!--
Sync Impact Report:
- Version: 1.0.0 (Initial Constitution)
- Created: 2026-01-30
- Principles Defined: 7 core principles
- Sections Added: Core Principles, Architecture Constraints, Development Workflow, Governance
- Templates Status: ✅ All templates reviewed and aligned
- Follow-up TODOs: None
-->

## Core Principles

### I. Microservices Architecture
Each service MUST be independently deployable, testable, and maintainable. Services communicate via well-defined HTTP APIs with clear contracts. No direct database access across service boundaries except through the shared database layer.

**Rationale**: Enables independent scaling, deployment, and development of components. Reduces coupling and allows technology flexibility per service.

### II. Database-First Design
The PostgreSQL schema is the source of truth. All services interact with a centralized database using explicit schemas defined in versioned SQL files. Schema changes MUST be applied in order (00_*, 01_*, 02_*, etc.) and are immutable once deployed.

**Rationale**: Ensures data consistency, enables complex queries, and provides a single source of truth. The numbered schema files enforce proper initialization order.

### III. Pipeline Status Tracking (NON-NEGOTIABLE)
Every tab item MUST progress through explicit status states: `new` → `fetch_pending` → `parsed` → `llm_pending` → `enriched`. Error states (`fetch_error`, `llm_error`) MUST be tracked with error messages and timestamps. All status transitions MUST be logged to `event_log`.

**Rationale**: Provides observability, enables retry logic, and allows debugging of pipeline failures. Critical for managing asynchronous processing of thousands of tabs.

### IV. Idempotency and Deduplication
All operations MUST be idempotent. Tab ingestion uses unique constraints on `(user_id, url)`. Enrichment operations can be safely retried. Database operations use `ON CONFLICT` clauses where appropriate.

**Rationale**: Enables safe retries, prevents duplicate data, and allows reprocessing without side effects.

### V. LLM Observability
All LLM interactions MUST be traced through Phoenix (Arize) using OpenTelemetry. This includes request/response logging, token usage tracking, latency metrics, and error monitoring. Services MUST gracefully handle Phoenix unavailability.

**Rationale**: LLM calls are expensive and opaque. Observability is essential for debugging, cost management, and quality assurance.

### VI. Parser Plugin System
Content parsers MUST implement the `BaseParser` interface and return `ParsedPage` objects. New parsers are registered in the parser registry. Each parser handles specific URL patterns (YouTube, Twitter, generic HTML). Parsers MUST be self-contained and testable.

**Rationale**: Enables extensibility for new content types without modifying core logic. Maintains separation of concerns and testability.

### VII. Configuration via Environment
All configuration MUST be provided via environment variables, loaded through the centralized `config.py` module using Pydantic settings. No hardcoded credentials, URLs, or environment-specific values in code. `.env.example` MUST be kept up-to-date.

**Rationale**: Enables deployment flexibility, security (no secrets in code), and easy configuration management across environments.

## Architecture Constraints

### Service Boundaries
- **Ingest CLI**: Standalone Python module for importing Firefox bookmarks. Direct database access allowed.
- **Parser Service** (port 8001): Fetches URLs and extracts content. No database access. Stateless HTTP API.
- **Enrichment Service** (port 8002): Generates LLM metadata. No database access. Stateless HTTP API.
- **Web UI** (port 8000): User interface with HTMX. Database access for queries and updates.
- **n8n Orchestrator** (port 5678): Workflow automation. Coordinates parser and enrichment services. Database access for status updates.

### Technology Stack Requirements
- **Python 3.11+**: All services use modern Python with type hints
- **FastAPI**: All HTTP services use FastAPI for consistency
- **PostgreSQL 15+**: With `pgvector` and `pg_trgm` extensions
- **DSPy**: LLM framework for structured outputs
- **HTMX**: Frontend interactivity without JavaScript frameworks
- **Docker/Podman**: Containerization for all services

### Database Conventions
- All tables include: `created_at`, `updated_at` (with triggers)
- Soft deletes via `deleted_at` timestamp where applicable
- Foreign keys MUST use `ON DELETE CASCADE` for dependent data
- Indexes MUST be created for all foreign keys and common query patterns
- Use `bigserial` for primary keys, `uuid` for user references

### API Conventions
- All services expose `/health` endpoint for health checks
- Use Pydantic models for request/response validation
- Return appropriate HTTP status codes (200, 400, 404, 500)
- Include error details in response body for 4xx/5xx responses
- Use structured logging with correlation IDs where possible

## Development Workflow

### Schema Changes
1. Create new numbered SQL file in `database/schema/` (e.g., `05_new_feature.sql`)
2. Test locally with fresh database initialization
3. Document breaking changes in migration notes
4. Update `v_tabs_enriched` view if schema affects tab queries
5. Verify Docker initialization still works (`docker-compose up -d postgres`)

### Adding New Parsers
1. Create parser class in `parser_service/parsers/` inheriting from `BaseParser`
2. Implement `can_parse(url)` and `parse(url, html)` methods
3. Register in `parser_service/parsers/registry.py`
4. Add unit tests in `tests/unit/`
5. Update documentation with supported URL patterns

### Service Development
1. Changes to services require rebuilding containers: `docker-compose up -d --build [service-name]`
2. Local development: Run services directly with `uvicorn` for faster iteration
3. Environment variables: Always use `config.py` for configuration access
4. Health checks: Ensure `/health` endpoint reflects actual service status
5. Logging: Use structured logging with appropriate log levels

### Testing Requirements
- **Unit tests**: Required for parsers, enrichment logic, and utility functions
- **Integration tests**: Required for API endpoints (see `tests/e2e/`)
- **E2E tests**: Playwright tests for Web UI workflows
- **Database tests**: Use `conftest.py` fixtures for test database setup
- Run tests with: `pytest tests/`

### Code Quality Standards
- Type hints MUST be used for all function signatures
- Docstrings MUST be provided for all public functions and classes
- Follow PEP 8 style guidelines
- Use Pydantic for data validation
- Handle errors explicitly with try/except blocks
- Log errors with context (tab_id, url, error message)

## Governance

### Constitution Authority
This constitution supersedes all other documentation when conflicts arise. All code reviews, pull requests, and architectural decisions MUST verify compliance with these principles.

### Amendment Process
1. Propose amendment with clear rationale and impact analysis
2. Document affected services, schemas, and workflows
3. Require approval from project maintainer
4. Update version number according to semantic versioning:
   - **MAJOR**: Breaking changes to core principles or architecture
   - **MINOR**: New principles or significant expansions
   - **PATCH**: Clarifications, typo fixes, non-semantic changes
5. Update all dependent documentation and templates

### Compliance Review
- All new features MUST align with microservices architecture (Principle I)
- All database changes MUST follow schema versioning (Principle II)
- All status changes MUST be logged (Principle III)
- All LLM calls MUST be traced (Principle V)
- Configuration MUST use environment variables (Principle VII)

### Exception Handling
Exceptions to these principles require:
1. Written justification documenting why the principle cannot be followed
2. Approval from project maintainer
3. Documentation in code comments referencing this constitution
4. Plan for future compliance if temporary exception

### Runtime Development Guidance
For day-to-day development decisions not covered by this constitution, refer to:
- `README.md` for setup and usage instructions
- `CLAUDE_CODE_SPEC.md` for implementation details
- `tests/README.md` for testing guidelines
- Service-specific `Dockerfile` and `main.py` for service patterns

**Version**: 1.0.0 | **Ratified**: 2026-01-30 | **Last Amended**: 2026-01-30
