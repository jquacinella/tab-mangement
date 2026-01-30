# Implementation Plan: [FEATURE]

**Branch**: `[###-feature-name]` | **Date**: [DATE] | **Spec**: [link]
**Input**: Feature specification from `/specs/[###-feature-name]/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

[Extract from feature spec: primary requirement + technical approach from research]

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: [e.g., Python 3.11, Swift 5.9, Rust 1.75 or NEEDS CLARIFICATION]  
**Primary Dependencies**: [e.g., FastAPI, UIKit, LLVM or NEEDS CLARIFICATION]  
**Storage**: [if applicable, e.g., PostgreSQL, CoreData, files or N/A]  
**Testing**: [e.g., pytest, XCTest, cargo test or NEEDS CLARIFICATION]  
**Target Platform**: [e.g., Linux server, iOS 15+, WASM or NEEDS CLARIFICATION]
**Project Type**: [single/web/mobile - determines source structure]  
**Performance Goals**: [domain-specific, e.g., 1000 req/s, 10k lines/sec, 60 fps or NEEDS CLARIFICATION]  
**Constraints**: [domain-specific, e.g., <200ms p95, <100MB memory, offline-capable or NEEDS CLARIFICATION]  
**Scale/Scope**: [domain-specific, e.g., 10k users, 1M LOC, 50 screens or NEEDS CLARIFICATION]

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Reference**: [`.specify/memory/constitution.md`](../.specify/memory/constitution.md)

### Core Principles Compliance

- [ ] **Microservices Architecture**: Does this feature maintain service boundaries?
- [ ] **Database-First Design**: Are schema changes versioned and ordered?
- [ ] **Pipeline Status Tracking**: Are status transitions logged to event_log?
- [ ] **Idempotency**: Can operations be safely retried?
- [ ] **LLM Observability**: Are LLM calls traced through Phoenix?
- [ ] **Parser Plugin System**: Do new parsers implement BaseParser?
- [ ] **Configuration via Environment**: No hardcoded values?

### Service Boundary Check

Which services does this feature affect?
- [ ] Ingest CLI
- [ ] Parser Service (port 8001)
- [ ] Enrichment Service (port 8002)
- [ ] Web UI (port 8000)
- [ ] n8n Orchestrator (port 5678)
- [ ] Database Schema

### Breaking Changes

Does this feature introduce breaking changes?
- [ ] Database schema changes (requires migration)
- [ ] API contract changes (requires version bump)
- [ ] Configuration changes (requires .env update)
- [ ] None (backward compatible)

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
# TabBacklog Project Structure (Microservices)

# Ingest CLI
ingest/
├── cli.py                  # Click CLI commands
├── firefox_parser.py       # HTML parsing
└── db.py                   # Database operations

# Parser Service (Port 8001)
parser_service/
├── main.py                 # FastAPI app
├── models.py               # Pydantic models
├── Dockerfile
└── parsers/
    ├── base.py             # BaseParser interface
    ├── registry.py         # Parser registration
    ├── generic.py          # Generic HTML parser
    ├── youtube.py          # YouTube parser
    └── twitter.py          # Twitter parser

# Enrichment Service (Port 8002)
enrichment_service/
├── main.py                 # FastAPI app
├── dspy_setup.py           # DSPy configuration
├── models.py               # Enrichment schema
└── Dockerfile

# Web UI (Port 8000)
web_ui/
├── main.py                 # FastAPI app
├── db.py                   # Async database ops
├── models.py               # Display models
├── Dockerfile
├── routes/
│   ├── tabs.py             # Tab listing/filtering
│   ├── export.py           # Export endpoints
│   └── search.py           # Semantic search
├── templates/              # Jinja2 templates
│   ├── base.html
│   ├── index.html
│   └── fragments/          # HTMX fragments
└── static/
    └── css/
        └── style.css

# Shared Utilities
shared/
└── search.py               # Embedding generation

# Database Schema
database/
└── schema/
    ├── 00_auth_setup.sql
    ├── 01_extensions.sql
    ├── 02_core_tables.sql
    ├── 03_indexes_views.sql
    └── 04_seed_data.sql

# n8n Workflows
n8n/
├── README.md
└── workflows/
    └── enrich_tabs.json

# Tests
tests/
├── conftest.py             # Pytest fixtures
├── e2e/                    # End-to-end tests
│   ├── test_api_endpoints.py
│   └── test_web_ui.py
└── unit/                   # Unit tests

# Configuration
config.py                   # Centralized configuration
.env.example                # Environment template
docker-compose.yml          # Container orchestration
requirements.txt            # Python dependencies
```

**Structure Decision**: [Document the selected structure and reference the real
directories captured above]

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
