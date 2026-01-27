-- V2: Add column to test table
-- Tests ALTER TABLE support in Aurora DSQL
-- Note: DSQL requires one DDL per transaction (handled by plugin)

ALTER TABLE flyway_test_users ADD COLUMN status VARCHAR(50);
