-- Initialize PDLS Database
-- This script runs when the PostgreSQL container starts for the first time

-- Create database if not exists (handled by POSTGRES_DB environment variable)
-- Create user if not exists (handled by POSTGRES_USER environment variable)

-- Set timezone to UTC
SET timezone = 'UTC';

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create audit function for updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Log database initialization
INSERT INTO pg_stat_activity_summary (datname, state, application_name) 
VALUES ('pdls', 'active', 'pdls-init') 
ON CONFLICT DO NOTHING;