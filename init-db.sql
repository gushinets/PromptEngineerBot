-- Database initialization script for Prompt Engineering Bot
-- This script sets up the initial database configuration

-- Create extensions if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Set timezone to UTC
SET timezone = 'UTC';

-- Create indexes for better performance (these will be created by Alembic migrations)
-- This file is mainly for any initial setup that needs to happen before migrations

-- Log the initialization
DO $$
BEGIN
    RAISE NOTICE 'Database initialized for Prompt Engineering Bot at %', NOW();
END $$;