-- R__: Repeatable migration for view
-- Runs every time checksum changes
-- Note: Using CREATE OR REPLACE to avoid needing DROP (DSQL allows only 1 DDL per transaction)

CREATE OR REPLACE VIEW flyway_test_user_summary AS
SELECT
    u.id,
    u.email,
    u.name,
    u.status,
    c.name AS category_name,
    u.created_at
FROM flyway_test_users u
LEFT JOIN flyway_test_categories c ON u.category_id = c.id;
