import json
import os
import sqlite3
from datetime import datetime

from config.settings import MEMORY_DIR


class MemoryStore:
    def __init__(self, db_path=None):
        if db_path is None:
            os.makedirs(MEMORY_DIR, exist_ok=True)
            db_path = os.path.join(MEMORY_DIR, "memory.db")
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE,
                value TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()

    def add_message(self, role, content):
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO conversations (role, content, created_at) VALUES (?, ?, ?)",
            (role, content, datetime.now().isoformat())
        )
        conn.commit()
        conn.close()

    def get_history(self, limit=50):
        conn = sqlite3.connect(self.db_path)
        rows = conn.execute(
            "SELECT role, content FROM conversations ORDER BY id DESC LIMIT ?",
            (limit,)
        ).fetchall()
        conn.close()
        rows.reverse()
        return [{"role": r[0], "content": r[1]} for r in rows]

    def clear_history(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("DELETE FROM conversations")
        conn.commit()
        conn.close()

    def remember(self, key, value):
        now = datetime.now().isoformat()
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """INSERT INTO memories (key, value, created_at, updated_at)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at""",
            (key, value, now, now)
        )
        conn.commit()
        conn.close()

    def recall(self, key):
        conn = sqlite3.connect(self.db_path)
        row = conn.execute(
            "SELECT value FROM memories WHERE key = ?", (key,)
        ).fetchone()
        conn.close()
        return row[0] if row else None

    def forget(self, key):
        conn = sqlite3.connect(self.db_path)
        conn.execute("DELETE FROM memories WHERE key = ?", (key,))
        conn.commit()
        conn.close()

    def get_all_memories(self):
        conn = sqlite3.connect(self.db_path)
        rows = conn.execute(
            "SELECT key, value, updated_at FROM memories ORDER BY updated_at DESC"
        ).fetchall()
        conn.close()
        return [{"key": r[0], "value": r[1], "updated_at": r[2]} for r in rows]
