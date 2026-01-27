-- V8: Create a view
-- Tests CREATE VIEW support in DSQL

CREATE VIEW flyway_test_user_summary AS
SELECT
    u.id,
    u.email,
    u.name,
    u.status,
    c.name AS category_name,
    u.created_at
FROM flyway_test_users u
LEFT JOIN flyway_test_categories c ON u.category_id = c.id;
