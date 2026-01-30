-- TabBacklog v1 - PostgreSQL Extensions
-- Enable required PostgreSQL extensions

-- ============================================================================
-- Extensions
-- ============================================================================

-- Enable trigram fuzzy text search
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Enable vector similarity search (requires pgvector)
CREATE EXTENSION IF NOT EXISTS vector;

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
