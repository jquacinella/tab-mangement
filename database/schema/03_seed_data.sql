-- TabBacklog v1 - Seed Data
-- Initial project tags and sample data

-- ============================================================================
-- Project Tags
-- ============================================================================
-- Note: Replace 'YOUR_USER_ID_HERE' with actual user UUID when running

-- Function to seed project tags for a user
CREATE OR REPLACE FUNCTION seed_project_tags(p_user_id uuid)
RETURNS void AS $$
BEGIN
  -- Insert project tags if they don't already exist
  INSERT INTO tag (user_id, name, kind)
  VALUES 
    (p_user_id, 'argumentation_on_the_web', 'project'),
    (p_user_id, 'democratic_economic_planning', 'project'),
    (p_user_id, 'other_research', 'project')
  ON CONFLICT (user_id, name) WHERE deleted_at IS NULL
  DO NOTHING;
END;
$$ LANGUAGE plpgsql;

-- Example: Call this function after creating a user
-- SELECT seed_project_tags('YOUR_USER_ID_HERE'::uuid);

-- ============================================================================
-- Common Auto-Generated Tags
-- ============================================================================

CREATE OR REPLACE FUNCTION seed_common_tags(p_user_id uuid)
RETURNS void AS $$
BEGIN
  -- Insert common tags used for auto-tagging
  INSERT INTO tag (user_id, name, kind)
  VALUES 
    -- Content markers
    (p_user_id, '#video', 'auto'),
    (p_user_id, '#longread', 'auto'),
    (p_user_id, '#shortread', 'auto'),
    (p_user_id, '#paper', 'auto'),
    (p_user_id, '#code', 'auto'),
    (p_user_id, '#reference', 'auto'),
    
    -- Priority markers
    (p_user_id, '#priority_high', 'auto'),
    (p_user_id, '#priority_medium', 'auto'),
    (p_user_id, '#priority_low', 'auto'),
    
    -- Language markers
    (p_user_id, '#english', 'auto'),
    (p_user_id, '#non_english', 'auto')
  ON CONFLICT (user_id, name) WHERE deleted_at IS NULL
  DO NOTHING;
END;
$$ LANGUAGE plpgsql;

-- Example: Call this function after creating a user
-- SELECT seed_common_tags('YOUR_USER_ID_HERE'::uuid);

-- ============================================================================
-- Helper Function to Initialize a New User
-- ============================================================================

CREATE OR REPLACE FUNCTION initialize_user_data(p_user_id uuid)
RETURNS void AS $$
BEGIN
  -- Seed project tags
  PERFORM seed_project_tags(p_user_id);
  
  -- Seed common auto-generated tags
  PERFORM seed_common_tags(p_user_id);
  
  -- Log the initialization
  INSERT INTO event_log (user_id, event_type, entity_type, details)
  VALUES (
    p_user_id,
    'user_initialized',
    'user',
    jsonb_build_object(
      'project_tags_created', true,
      'common_tags_created', true,
      'initialized_at', now()
    )
  );
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Sample Data (for development/testing)
-- ============================================================================

-- Uncomment this section to insert sample data for testing
/*
-- Create a test user (if not using Supabase auth)
-- INSERT INTO auth.users (id, email) 
-- VALUES ('00000000-0000-0000-0000-000000000001', 'test@example.com')
-- ON CONFLICT (id) DO NOTHING;

-- Initialize the test user
SELECT initialize_user_data('00000000-0000-0000-0000-000000000001'::uuid);

-- Insert some sample tabs
INSERT INTO tab_item (user_id, url, page_title, window_label, status)
VALUES 
  (
    '00000000-0000-0000-0000-000000000001'::uuid,
    'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
    'Sample Video',
    'Research',
    'new'
  ),
  (
    '00000000-0000-0000-0000-000000000001'::uuid,
    'https://arxiv.org/abs/2301.00000',
    'Sample Research Paper',
    'Papers',
    'new'
  ),
  (
    '00000000-0000-0000-0000-000000000001'::uuid,
    'https://example.com/article',
    'Sample Article',
    'Reading',
    'new'
  )
ON CONFLICT (user_id, url) WHERE deleted_at IS NULL
DO NOTHING;
*/

-- ============================================================================
-- Data Validation Queries
-- ============================================================================

-- Check that all required tags exist for a user
CREATE OR REPLACE FUNCTION validate_user_tags(p_user_id uuid)
RETURNS TABLE(missing_tags text[]) AS $$
BEGIN
  RETURN QUERY
  SELECT ARRAY(
    SELECT required_tag
    FROM unnest(ARRAY[
      'argumentation_on_the_web',
      'democratic_economic_planning', 
      'other_research'
    ]) AS required_tag
    WHERE NOT EXISTS (
      SELECT 1 FROM tag
      WHERE user_id = p_user_id
        AND name = required_tag
        AND kind = 'project'
        AND deleted_at IS NULL
    )
  );
END;
$$ LANGUAGE plpgsql;

-- Usage: SELECT * FROM validate_user_tags('YOUR_USER_ID_HERE'::uuid);
