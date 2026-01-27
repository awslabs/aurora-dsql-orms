-- V1: Table that represents "already existing" schema for baseline test

CREATE TABLE IF NOT EXISTS baseline_test (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
