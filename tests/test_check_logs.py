import sqlite3
import unittest
from pathlib import Path

CHECK_LOGS_SQL = (Path(__file__).resolve().parents[1] / "scripts" / "check_logs.sql").read_text(
    encoding="utf-8"
)


class CheckLogsScriptTests(unittest.TestCase):
    def test_script_returns_only_the_selected_users_latest_twenty_chats(self):
        connection = sqlite3.connect(":memory:")
        self.addCleanup(connection.close)
        connection.executescript(
            """
            CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT NOT NULL);
            CREATE TABLE chats (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL
            );
            INSERT INTO users VALUES (1, 'camus'), (2, 'other');
            """
        )
        connection.executemany(
            "INSERT INTO chats VALUES (?, ?, ?, ?, ?)",
            [
                (chat_id, 1, f"2026-10-08T00:00:{chat_id:02d}Z", f"q{chat_id}", f"a{chat_id}")
                for chat_id in range(1, 22)
            ]
            + [(100, 2, "2026-10-08T00:01:00Z", "other question", "other answer")],
        )

        rows = connection.execute(CHECK_LOGS_SQL, {"user_id": 1}).fetchall()

        self.assertEqual(len(rows), 20)
        self.assertEqual((rows[0][0], rows[0][1], rows[0][2]), (1, "camus", 21))
        self.assertEqual(rows[-1][2], 2)
        self.assertTrue(all(row[0] == 1 and row[1] == "camus" for row in rows))
