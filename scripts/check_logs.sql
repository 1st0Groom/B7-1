-- SQLite CLI: .parameter init; .parameter set :user_id 1
SELECT c.user_id, t.id AS turn_id, t.conversation_id, t.created_at,
       t.question, t.answer, t.status, t.error_code
FROM chat_turns AS t
JOIN conversations AS c ON c.id = t.conversation_id
WHERE c.user_id = :user_id
ORDER BY t.id DESC
LIMIT 20;
