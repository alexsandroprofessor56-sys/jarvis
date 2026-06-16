import os
import sqlite3
import json
from datetime import datetime, timedelta


MEMORY_DIR = os.path.expanduser("~/.jarvis/memory")


class EpisodicMemory:
    def __init__(self):
        os.makedirs(MEMORY_DIR, exist_ok=True)
        self.db_path = os.path.join(MEMORY_DIR, "episodic.db")
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS episodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                episode_type TEXT NOT NULL,
                summary TEXT NOT NULL,
                details TEXT DEFAULT '',
                importance REAL DEFAULT 0.5,
                context TEXT DEFAULT ''
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS daily_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT UNIQUE NOT NULL,
                summary TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()

    def add_episode(self, episode_type, summary, details="", importance=0.5, context=""):
        now = datetime.now().isoformat()
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """INSERT INTO episodes (timestamp, episode_type, summary, details, importance, context)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (now, episode_type, summary, details, importance, context)
        )
        conn.commit()
        conn.close()

    def get_episodes(self, hours=24, episode_type=None, min_importance=0):
        since = (datetime.now() - timedelta(hours=hours)).isoformat()
        conn = sqlite3.connect(self.db_path)
        if episode_type:
            rows = conn.execute(
                """SELECT timestamp, episode_type, summary, importance, context
                   FROM episodes WHERE timestamp > ? AND episode_type = ? AND importance >= ?
                   ORDER BY timestamp DESC LIMIT 50""",
                (since, episode_type, min_importance)
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT timestamp, episode_type, summary, importance, context
                   FROM episodes WHERE timestamp > ? AND importance >= ?
                   ORDER BY timestamp DESC LIMIT 50""",
                (since, min_importance)
            ).fetchall()
        conn.close()
        return [
            {"time": r[0], "type": r[1], "summary": r[2], "importance": r[3], "context": r[4]}
            for r in rows
        ]

    def search_episodes(self, query, limit=10):
        conn = sqlite3.connect(self.db_path)
        rows = conn.execute(
            """SELECT timestamp, episode_type, summary, importance, context
               FROM episodes WHERE summary LIKE ? OR details LIKE ?
               ORDER BY timestamp DESC LIMIT ?""",
            (f"%{query}%", f"%{query}%", limit)
        ).fetchall()
        conn.close()
        return [
            {"time": r[0], "type": r[1], "summary": r[2], "importance": r[3], "context": r[4]}
            for r in rows
        ]

    def get_today_summary(self):
        today = datetime.now().strftime("%Y-%m-%d")
        conn = sqlite3.connect(self.db_path)
        row = conn.execute(
            "SELECT summary FROM daily_summaries WHERE date = ?", (today,)
        ).fetchone()
        conn.close()
        return row[0] if row else None

    def save_daily_summary(self, summary):
        today = datetime.now().strftime("%Y-%m-%d")
        now = datetime.now().isoformat()
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """INSERT INTO daily_summaries (date, summary, created_at) VALUES (?, ?, ?)
               ON CONFLICT(date) DO UPDATE SET summary = excluded.summary""",
            (today, summary, now)
        )
        conn.commit()
        conn.close()
