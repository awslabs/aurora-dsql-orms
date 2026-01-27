-- V2: Migration to run after baseline
-- This should be the only migration executed when baselined at V1

ALTER TABLE baseline_test ADD COLUMN status VARCHAR(50);
