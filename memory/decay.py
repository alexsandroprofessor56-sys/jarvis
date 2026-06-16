import os
import sqlite3
from datetime import datetime, timedelta

MEMORY_DIR = os.path.expanduser("~/.jarvis/memory")


def decay_old_memories(days_threshold=30):
    conn = sqlite3.connect(os.path.join(MEMORY_DIR, "semantic.db"))
    threshold = (datetime.now() - timedelta(days=days_threshold)).isoformat()
    deleted = conn.execute(
        "DELETE FROM facts WHERE confidence < 0.3 AND accessed_at < ?",
        (threshold,)
    ).rowcount
    conn.commit()
    conn.close()
    return deleted
