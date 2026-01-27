-- V1: Create test table for Flyway integration test
-- This migration tests basic DDL support in Aurora DSQL

CREATE TABLE IF NOT EXISTS flyway_test_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
