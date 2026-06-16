import os
import sqlite3
from datetime import datetime


MEMORY_DIR = os.path.expanduser("~/.jarvis/memory")


class ProceduralMemory:
    def __init__(self):
        os.makedirs(MEMORY_DIR, exist_ok=True)
        self.db_path = os.path.join(MEMORY_DIR, "procedural.db")
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS procedures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT DEFAULT '',
                steps TEXT NOT NULL,
                category TEXT DEFAULT 'general',
                success_count INTEGER DEFAULT 0,
                fail_count INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()

    def learn_procedure(self, name, steps, description="", category="general"):
        now = datetime.now().isoformat()
        steps_json = "\n".join(steps) if isinstance(steps, list) else steps
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """INSERT INTO procedures (name, description, steps, category, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(name) DO UPDATE SET
                   steps = excluded.steps,
                   description = excluded.description,
                   updated_at = excluded.updated_at""",
            (name, description, steps_json, category, now, now)
        )
        conn.commit()
        conn.close()

    def recall_procedure(self, name=None, category=None):
        conn = sqlite3.connect(self.db_path)
        if name:
            row = conn.execute(
                "SELECT name, description, steps, category, success_count, fail_count FROM procedures WHERE name = ?",
                (name,)
            ).fetchone()
            conn.close()
            if row:
                return {
                    "name": row[0], "description": row[1],
                    "steps": row[2].split("\n"), "category": row[3],
                    "success_count": row[4], "fail_count": row[5]
                }
            return None
        elif category:
            rows = conn.execute(
                "SELECT name, description, category FROM procedures WHERE category = ? ORDER BY success_count DESC",
                (category,)
            ).fetchall()
            conn.close()
            return [{"name": r[0], "description": r[1], "category": r[2]} for r in rows]
        else:
            rows = conn.execute(
                "SELECT name, description, category FROM procedures ORDER BY success_count DESC"
            ).fetchall()
            conn.close()
            return [{"name": r[0], "description": r[1], "category": r[2]} for r in rows]

    def record_success(self, name):
        conn = sqlite3.connect(self.db_path)
        conn.execute("UPDATE procedures SET success_count = success_count + 1 WHERE name = ?", (name,))
        conn.commit()
        conn.close()

    def record_failure(self, name):
        conn = sqlite3.connect(self.db_path)
        conn.execute("UPDATE procedures SET fail_count = fail_count + 1 WHERE name = ?", (name,))
        conn.commit()
        conn.close()
