import sqlite3
import os
import uuid
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class ThreadStore:
    def __init__(self, db_path=None):
        self.db_path = db_path or os.getenv("THREAD_DB_PATH", "data/threads.sqlite3")
        # Ensure database directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initializes the SQLite database schema."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    thread_id TEXT,
                    role TEXT,
                    content TEXT,
                    timestamp TEXT,
                    citation_url TEXT
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_thread_id ON messages (thread_id)")
            conn.commit()

    def create_thread(self) -> str:
        """Creates a new unique thread_id."""
        return str(uuid.uuid4())

    def add_message(self, thread_id: str, role: str, content: str, citation_url: str = None) -> dict:
        """Inserts a new message into a thread."""
        msg_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO messages (id, thread_id, role, content, timestamp, citation_url)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (msg_id, thread_id, role, content, timestamp, citation_url))
            conn.commit()
            
        return {
            "id": msg_id,
            "thread_id": thread_id,
            "role": role,
            "content": content,
            "timestamp": timestamp,
            "citation_url": citation_url
        }

    def get_messages(self, thread_id: str, limit: int = None) -> list[dict]:
        """Retrieves messages for a thread, ordered by timestamp."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if limit:
                cursor.execute("""
                    SELECT id, thread_id, role, content, timestamp, citation_url 
                    FROM messages 
                    WHERE thread_id = ? 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                """, (thread_id, limit))
                # Reverse to get chronological order
                rows = reversed(cursor.fetchall())
            else:
                cursor.execute("""
                    SELECT id, thread_id, role, content, timestamp, citation_url 
                    FROM messages 
                    WHERE thread_id = ? 
                    ORDER BY timestamp ASC
                """, (thread_id,))
                rows = cursor.fetchall()
                
            return [dict(row) for row in rows]
            
    def delete_thread(self, thread_id: str):
        """Deletes all messages for a thread."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM messages WHERE thread_id = ?", (thread_id,))
            conn.commit()
            
    def get_all_threads(self) -> list[str]:
        """Returns a list of all unique thread_ids."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT thread_id FROM messages")
            return [row[0] for row in cursor.fetchall()]
