-- V5: Create a second table to test multi-table migrations
-- Tests CREATE TABLE with UNIQUE constraint

CREATE TABLE IF NOT EXISTS flyway_test_categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
