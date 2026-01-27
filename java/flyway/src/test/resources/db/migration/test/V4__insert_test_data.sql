-- V4: Insert test data
-- Tests DML support in Aurora DSQL

INSERT INTO flyway_test_users (email, name, status) 
VALUES ('test@example.com', 'Test User', 'active');
