-- TabBacklog v1 - Auth Schema Setup
-- Creates a minimal auth.users table for standalone PostgreSQL
-- (Supabase provides this automatically)

-- Create auth schema if it doesn't exist
CREATE SCHEMA IF NOT EXISTS auth;

-- Create a minimal users table for standalone mode
CREATE TABLE IF NOT EXISTS auth.users (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  email text UNIQUE,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- Create an index on email for lookups
CREATE INDEX IF NOT EXISTS idx_auth_users_email ON auth.users(email);

-- Insert a default user if none exists (for single-user mode)
-- This UUID should match your DEFAULT_USER_ID in .env
INSERT INTO auth.users (id, email)
VALUES ('00000000-0000-0000-0000-000000000000'::uuid, 'default@tabbacklog.local')
ON CONFLICT (id) DO NOTHING;
