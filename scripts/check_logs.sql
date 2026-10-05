-- SQLite CLI: .parameter init; .parameter set :user_id 1
SELECT u.id AS user_id, u.username, c.id AS chat_id, c.created_at, c.question, c.answer
FROM chats AS c
JOIN users AS u ON u.id = c.user_id
WHERE c.user_id = :user_id
ORDER BY c.id DESC
LIMIT 20;
