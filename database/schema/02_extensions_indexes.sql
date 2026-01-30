-- TabBacklog v1 - Extensions and Additional Indexes
-- Enable required PostgreSQL extensions

-- ============================================================================
-- Extensions
-- ============================================================================

-- Enable trigram fuzzy text search
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Enable vector similarity search (Supabase comes with pgvector)
CREATE EXTENSION IF NOT EXISTS vector;

-- Enable UUID generation (usually already enabled in Supabase)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- Trigram Indexes for Fuzzy Search
-- ============================================================================

-- Index on tab_item.page_title for fuzzy search
CREATE INDEX idx_tab_item_title_trgm
  ON tab_item USING gin (page_title gin_trgm_ops)
  WHERE deleted_at IS NULL;

-- Index on tab_item.url for fuzzy search
CREATE INDEX idx_tab_item_url_trgm
  ON tab_item USING gin (url gin_trgm_ops)
  WHERE deleted_at IS NULL;

-- Index on tab_enrichment.summary for fuzzy search
CREATE INDEX idx_tab_enrichment_summary_trgm
  ON tab_enrichment USING gin (summary gin_trgm_ops);

-- Index on tab_parsed.text_full for fuzzy search (optional - can be large)
-- Uncomment if you want to search full text
-- CREATE INDEX idx_tab_parsed_text_trgm
--   ON tab_parsed USING gin (text_full gin_trgm_ops);

-- ============================================================================
-- Additional Performance Indexes
-- ============================================================================

-- Index for date-based queries
CREATE INDEX idx_tab_item_collected_at ON tab_item(collected_at DESC) WHERE deleted_at IS NULL;

-- Composite index for common filter combinations
CREATE INDEX idx_tab_item_user_status_processed 
  ON tab_item(user_id, status, is_processed) 
  WHERE deleted_at IS NULL;

-- Index for tag-based filtering
CREATE INDEX idx_tag_kind ON tag(kind) WHERE deleted_at IS NULL;

-- Index for enrichment read time filtering
CREATE INDEX idx_tab_enrichment_read_time ON tab_enrichment(est_read_min) 
  WHERE est_read_min IS NOT NULL;

-- ============================================================================
-- Helper Functions for Search
-- ============================================================================

-- Function to get similarity score for fuzzy search
CREATE OR REPLACE FUNCTION tab_search_score(
  search_query text,
  title text,
  summary text
) RETURNS float AS $$
BEGIN
  RETURN GREATEST(
    COALESCE(similarity(search_query, title), 0),
    COALESCE(similarity(search_query, summary), 0)
  );
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- ============================================================================
-- Views for Common Queries
-- ============================================================================

-- View combining tab_item with enrichments and tags
CREATE OR REPLACE VIEW v_tabs_enriched AS
SELECT 
  ti.id,
  ti.user_id,
  ti.url,
  ti.page_title,
  ti.window_label,
  ti.collected_at,
  ti.status,
  ti.is_processed,
  ti.processed_at,
  ti.created_at,
  ti.updated_at,
  tp.site_kind,
  tp.word_count,
  tp.video_seconds AS parsed_video_seconds,
  te.summary,
  te.content_type,
  te.est_read_min,
  te.video_seconds AS enriched_video_seconds,
  te.priority,
  te.model_name,
  COALESCE(te.video_seconds, tp.video_seconds) AS video_seconds_combined,
  array_agg(DISTINCT t.name) FILTER (WHERE t.name IS NOT NULL) AS tags,
  array_agg(DISTINCT t.id) FILTER (WHERE t.id IS NOT NULL) AS tag_ids
FROM tab_item ti
LEFT JOIN tab_parsed tp ON ti.id = tp.tab_id
LEFT JOIN tab_enrichment te ON ti.id = te.tab_id
LEFT JOIN tab_tag tt ON ti.id = tt.tab_id
LEFT JOIN tag t ON tt.tag_id = t.id AND t.deleted_at IS NULL
WHERE ti.deleted_at IS NULL
GROUP BY 
  ti.id, ti.user_id, ti.url, ti.page_title, ti.window_label,
  ti.collected_at, ti.status, ti.is_processed, ti.processed_at,
  ti.created_at, ti.updated_at,
  tp.site_kind, tp.word_count, tp.video_seconds,
  te.summary, te.content_type, te.est_read_min, te.video_seconds,
  te.priority, te.model_name;

-- ============================================================================
-- Statistics and Monitoring Views
-- ============================================================================

-- View for pipeline status overview
CREATE OR REPLACE VIEW v_pipeline_stats AS
SELECT 
  user_id,
  status,
  COUNT(*) as count,
  MIN(created_at) as oldest,
  MAX(created_at) as newest
FROM tab_item
WHERE deleted_at IS NULL
GROUP BY user_id, status;

-- View for content type distribution
CREATE OR REPLACE VIEW v_content_type_stats AS
SELECT 
  ti.user_id,
  te.content_type,
  COUNT(*) as count,
  AVG(te.est_read_min) as avg_read_min,
  SUM(te.est_read_min) as total_read_min
FROM tab_item ti
JOIN tab_enrichment te ON ti.id = te.tab_id
WHERE ti.deleted_at IS NULL
GROUP BY ti.user_id, te.content_type;

-- View for error tracking
CREATE OR REPLACE VIEW v_error_summary AS
SELECT 
  user_id,
  status,
  COUNT(*) as error_count,
  MAX(error_at) as last_error_at,
  array_agg(DISTINCT COALESCE(SUBSTRING(last_error, 1, 100), 'No error message')) 
    FILTER (WHERE last_error IS NOT NULL) as error_samples
FROM tab_item
WHERE status IN ('fetch_error', 'parse_error', 'llm_error')
  AND deleted_at IS NULL
GROUP BY user_id, status;
