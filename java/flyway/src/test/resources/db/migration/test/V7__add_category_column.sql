-- V7: Add category_id column to users table
-- Tests ALTER TABLE ADD COLUMN for relationship (without FK constraint)
-- Note: DSQL does not support foreign key constraints, so we add the column only

ALTER TABLE flyway_test_users ADD COLUMN category_id UUID;
