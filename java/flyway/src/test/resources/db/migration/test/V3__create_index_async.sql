-- V3: Create async index
-- IMPORTANT: Aurora DSQL requires CREATE INDEX ASYNC
-- Standard CREATE INDEX will fail

CREATE INDEX ASYNC idx_flyway_test_users_email ON flyway_test_users(email);
