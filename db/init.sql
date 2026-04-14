-- NewsLens database initialization
-- This script runs when the PostgreSQL container starts for the first time.
-- Tables and seed data are managed by the FastAPI backend on startup.

-- Enable UUID generation (used by gen_random_uuid() in table definitions)
-- Note: gen_random_uuid() is built-in since PostgreSQL 13, but this ensures
-- compatibility if the extension is referenced elsewhere.
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
