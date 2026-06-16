import os
import json
import sqlite3
import numpy as np
from datetime import datetime, timedelta


MEMORY_DIR = os.path.expanduser("~/.jarvis/memory")


class SemanticMemory:
    def __init__(self):
        os.makedirs(MEMORY_DIR, exist_ok=True)
        self.db_path = os.path.join(MEMORY_DIR, "semantic.db")
        self._init_db()
        self._embedder = None

    @property
    def embedder(self):
        if self._embedder is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._embedder = SentenceTransformer("all-MiniLM-L6-v2")
            except ImportError:
                pass
        return self._embedder

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fact TEXT UNIQUE,
                category TEXT DEFAULT 'general',
                confidence REAL DEFAULT 1.0,
                source TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                accessed_at TEXT NOT NULL,
                access_count INTEGER DEFAULT 1
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS embeddings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fact_id INTEGER UNIQUE,
                vector BLOB,
                FOREIGN KEY (fact_id) REFERENCES facts(id)
            )
        """)
        conn.commit()
        conn.close()

    def remember_fact(self, fact, category="general", confidence=1.0, source=""):
        now = datetime.now().isoformat()
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """INSERT INTO facts (fact, category, confidence, source, created_at, accessed_at)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(fact) DO UPDATE SET
                       confidence = MAX(confidence, excluded.confidence),
                       accessed_at = excluded.accessed_at,
                       access_count = access_count + 1""",
                (fact, category, confidence, source, now, now)
            )
            conn.commit()
            row = conn.execute("SELECT id FROM facts WHERE fact = ?", (fact,)).fetchone()
            if row and self.embedder:
                self._store_embedding(conn, row[0], fact)
            conn.close()
            return True
        except Exception as e:
            conn.close()
            return False

    def _store_embedding(self, conn, fact_id, text):
        try:
            vec = self.embedder.encode(text)
            blob = np.array(vec, dtype=np.float32).tobytes()
            conn.execute(
                "INSERT OR REPLACE INTO embeddings (fact_id, vector) VALUES (?, ?)",
                (fact_id, blob)
            )
            conn.commit()
        except Exception:
            pass

    def recall_fact(self, text, top_k=5):
        if not self.embedder:
            return self._recall_keyword(text, top_k)
        try:
            query_vec = self.embedder.encode(text)
            conn = sqlite3.connect(self.db_path)
            rows = conn.execute(
                "SELECT f.id, f.fact, f.category, f.confidence, f.access_count, f.accessed_at, e.vector "
                "FROM facts f LEFT JOIN embeddings e ON f.id = e.fact_id"
            ).fetchall()
            conn.close()

            scored = []
            for row in rows:
                fid, fact, cat, conf, acc_count, acc_at, vec_blob = row
                if vec_blob:
                    stored = np.frombuffer(vec_blob, dtype=np.float32)
                    score = float(np.dot(query_vec, stored) / (np.linalg.norm(query_vec) * np.linalg.norm(stored) + 1e-8))
                else:
                    score = 0
                scored.append((score, fact, cat, conf, acc_count))

            scored.sort(key=lambda x: -x[0])
            self._update_access(scored[0][1] if scored else "")
            return [{"fact": s[1], "category": s[2], "confidence": s[3], "relevance": float(s[0])}
                    for s in scored[:top_k]]
        except Exception:
            return self._recall_keyword(text, top_k)

    def _recall_keyword(self, text, top_k=5):
        conn = sqlite3.connect(self.db_path)
        rows = conn.execute(
            "SELECT fact, category, confidence FROM facts WHERE fact LIKE ? ORDER BY access_count DESC LIMIT ?",
            (f"%{text}%", top_k)
        ).fetchall()
        conn.close()
        return [{"fact": r[0], "category": r[1], "confidence": r[2], "relevance": 0.5} for r in rows]

    def _update_access(self, fact):
        now = datetime.now().isoformat()
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "UPDATE facts SET accessed_at = ?, access_count = access_count + 1 WHERE fact = ?",
            (now, fact)
        )
        conn.commit()
        conn.close()

    def forget(self, fact):
        conn = sqlite3.connect(self.db_path)
        conn.execute("DELETE FROM embeddings WHERE fact_id IN (SELECT id FROM facts WHERE fact = ?)", (fact,))
        conn.execute("DELETE FROM facts WHERE fact = ?", (fact,))
        conn.commit()
        conn.close()

    def get_all_facts(self, category=None):
        conn = sqlite3.connect(self.db_path)
        if category:
            rows = conn.execute(
                "SELECT fact, category, confidence, access_count FROM facts WHERE category = ? ORDER BY access_count DESC",
                (category,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT fact, category, confidence, access_count FROM facts ORDER BY access_count DESC"
            ).fetchall()
        conn.close()
        return [{"fact": r[0], "category": r[1], "confidence": r[2], "access_count": r[3]} for r in rows]
