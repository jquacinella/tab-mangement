-- TabBacklog v1 - Core Database Schema
-- PostgreSQL with Supabase extensions

-- ============================================================================
-- Core Tables
-- ============================================================================

-- Main tab tracking table
CREATE TABLE tab_item (
  id             bigserial PRIMARY KEY,
  user_id        uuid NOT NULL REFERENCES auth.users(id),
  url            text NOT NULL,
  page_title     text,
  window_label   text,
  collected_at   timestamptz NOT NULL DEFAULT now(),

  -- Pipeline status tracking
  status         text NOT NULL DEFAULT 'new',
  -- Allowed values: 'new', 'fetch_pending', 'fetched', 'fetch_error',
  --                 'parse_pending', 'parsed', 'parse_error',
  --                 'llm_pending', 'enriched', 'llm_error'

  last_error     text,
  error_at       timestamptz,

  -- User workflow
  is_processed   boolean NOT NULL DEFAULT false,
  processed_at   timestamptz,

  -- Standard fields
  created_at     timestamptz NOT NULL DEFAULT now(),
  updated_at     timestamptz NOT NULL DEFAULT now(),
  deleted_at     timestamptz
);

-- Unique constraint on user_id + url (only active records)
CREATE UNIQUE INDEX idx_tab_item_user_url_unique
  ON tab_item(user_id, url)
  WHERE deleted_at IS NULL;

-- Index for common queries
CREATE INDEX idx_tab_item_user_status ON tab_item(user_id, status) WHERE deleted_at IS NULL;
CREATE INDEX idx_tab_item_user_processed ON tab_item(user_id, is_processed) WHERE deleted_at IS NULL;

-- ============================================================================

-- Parsed content from fetch/parse service
CREATE TABLE tab_parsed (
  tab_id          bigint PRIMARY KEY REFERENCES tab_item(id) ON DELETE CASCADE,
  site_kind       text NOT NULL,      -- youtube | twitter | generic_html | ...
  title_extracted text,
  text_full       text,
  word_count      integer,
  video_seconds   integer,
  metadata        jsonb NOT NULL DEFAULT '{}',
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now()
);

-- Index for searching by site kind
CREATE INDEX idx_tab_parsed_site_kind ON tab_parsed(site_kind);

-- ============================================================================

-- LLM-generated enrichments (current version)
CREATE TABLE tab_enrichment (
  tab_id         bigint PRIMARY KEY REFERENCES tab_item(id) ON DELETE CASCADE,
  summary        text,
  content_type   text,  -- article | video | paper | code_repo | reference | misc
  est_read_min   integer,
  video_seconds  integer,
  source_lang    text,
  priority       text,  -- high | medium | low
  raw_meta       jsonb NOT NULL DEFAULT '{}',
  model_name     text,
  created_at     timestamptz NOT NULL DEFAULT now(),
  updated_at     timestamptz NOT NULL DEFAULT now()
);

-- Index for filtering by content type
CREATE INDEX idx_tab_enrichment_content_type ON tab_enrichment(content_type);

-- ============================================================================

-- Historical record of all enrichment runs
CREATE TABLE tab_enrichment_history (
  id              bigserial PRIMARY KEY,
  tab_id          bigint NOT NULL REFERENCES tab_item(id) ON DELETE CASCADE,
  summary         text,
  content_type    text,
  est_read_min    integer,
  video_seconds   integer,
  source_lang     text,
  priority        text,
  raw_meta        jsonb NOT NULL DEFAULT '{}',
  model_name      text,
  run_started_at  timestamptz NOT NULL,
  run_finished_at timestamptz,
  created_at      timestamptz NOT NULL DEFAULT now()
);

-- Index for querying history by tab
CREATE INDEX idx_tab_enrichment_history_tab ON tab_enrichment_history(tab_id);

-- ============================================================================

-- Tag definitions
CREATE TABLE tag (
  id          bigserial PRIMARY KEY,
  user_id     uuid NOT NULL REFERENCES auth.users(id),
  name        text NOT NULL,
  kind        text NOT NULL DEFAULT 'generic',  -- generic | project | auto
  created_at  timestamptz NOT NULL DEFAULT now(),
  updated_at  timestamptz NOT NULL DEFAULT now(),
  deleted_at  timestamptz
);

-- Unique constraint on user_id + name
CREATE UNIQUE INDEX idx_tag_user_name_unique
  ON tag(user_id, name)
  WHERE deleted_at IS NULL;

-- ============================================================================

-- Many-to-many relationship between tabs and tags
CREATE TABLE tab_tag (
  tab_id      bigint NOT NULL REFERENCES tab_item(id) ON DELETE CASCADE,
  tag_id      bigint NOT NULL REFERENCES tag(id) ON DELETE CASCADE,
  created_at  timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (tab_id, tag_id)
);

-- Indexes for efficient querying
CREATE INDEX idx_tab_tag_tag ON tab_tag(tag_id);

-- ============================================================================

-- Vector embeddings for semantic search
CREATE TABLE tab_embedding (
  tab_id      bigint PRIMARY KEY REFERENCES tab_item(id) ON DELETE CASCADE,
  embedding   vector(768),  -- Adjust dimension based on embedding model
  model_name  text NOT NULL,
  created_at  timestamptz NOT NULL DEFAULT now(),
  updated_at  timestamptz NOT NULL DEFAULT now()
);

-- Vector similarity index (requires pgvector extension)
CREATE INDEX idx_tab_embedding_vector ON tab_embedding
  USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);

-- ============================================================================

-- Event log for debugging and audit trail
CREATE TABLE event_log (
  id           bigserial PRIMARY KEY,
  user_id      uuid REFERENCES auth.users(id),
  event_type   text NOT NULL,
  -- Examples: tab_created, tab_duplicate_skipped, fetch_started, fetch_success,
  --           fetch_error, llm_enrich_success, llm_enrich_error, tab_processed
  entity_type  text,  -- tab_item | tag | etc.
  entity_id    bigint,
  details      jsonb NOT NULL DEFAULT '{}',
  created_at   timestamptz NOT NULL DEFAULT now()
);

-- Indexes for common event queries
CREATE INDEX idx_event_log_user ON event_log(user_id, created_at DESC);
CREATE INDEX idx_event_log_type ON event_log(event_type, created_at DESC);
CREATE INDEX idx_event_log_entity ON event_log(entity_type, entity_id);

-- ============================================================================

-- Auto-update updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers for tables with updated_at
CREATE TRIGGER update_tab_item_updated_at
    BEFORE UPDATE ON tab_item
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_tab_parsed_updated_at
    BEFORE UPDATE ON tab_parsed
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_tab_enrichment_updated_at
    BEFORE UPDATE ON tab_enrichment
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_tag_updated_at
    BEFORE UPDATE ON tag
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_tab_embedding_updated_at
    BEFORE UPDATE ON tab_embedding
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
