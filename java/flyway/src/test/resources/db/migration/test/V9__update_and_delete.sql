-- V9: Test UPDATE and DELETE operations

-- Update existing record
UPDATE flyway_test_users
SET status = 'verified'
WHERE email = 'test@example.com';

-- Insert another record then delete it
INSERT INTO flyway_test_users (email, name, status)
VALUES ('delete_me@example.com', 'To Delete', 'pending');

DELETE FROM flyway_test_users
WHERE email = 'delete_me@example.com';
