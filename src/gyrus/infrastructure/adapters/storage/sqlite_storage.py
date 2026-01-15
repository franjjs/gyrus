import json
import logging
import sqlite3
from datetime import datetime
from typing import List

import numpy as np

from gyrus.domain.models import Node
from gyrus.domain.repository import NodeRepository


class SQLiteNodeRepository(NodeRepository):
    def __init__(self, db_path: str = "data/gyrus.db"):
        self.db_path = db_path
        self._create_table()

    def _create_table(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS nodes (
                    id TEXT PRIMARY KEY,
                    content TEXT,
                    vector BLOB,
                    metadata TEXT,
                    created_at TIMESTAMP,
                    expires_at TIMESTAMP,
                    circle_id TEXT,
                    vector_model_id TEXT
                )
            """)

    async def save(self, node: Node) -> None:
        logging.debug(
            f"Saving node: id={node.id}, content='{node.content[:40]}', "
            f"model={node.vector_model_id}"
        )
        with sqlite3.connect(self.db_path) as conn:
            # Convert list to float32 binary for storage
            vector_bin = np.array(node.vector, dtype=np.float32).tobytes()
            circle_id_str = str(node.circle_id) if node.circle_id else None
            
            conn.execute(
                """INSERT INTO nodes VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    str(node.id), 
                    node.content, 
                    vector_bin,
                    json.dumps(node.metadata), 
                    node.created_at, 
                    node.expires_at, 
                    circle_id_str,
                    node.vector_model_id
                )
            )

    async def find_last(self, limit: int = 15) -> List[Node]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """SELECT id, content, vector, metadata, created_at, 
                   expires_at, circle_id, vector_model_id FROM nodes 
                   ORDER BY created_at DESC LIMIT ?""",
                (limit,)
            )
            rows = cursor.fetchall()
            return [Node(
                id=row[0],
                content=row[1],
                vector=np.frombuffer(row[2], dtype=np.float32).tolist(),
                metadata=json.loads(row[3]),
                created_at=row[4],
                expires_at=row[5],
                circle_id=row[6],
                vector_model_id=row[7]
            ) for row in rows]

    async def find_similar(self, vector: List[float], limit: int = 15) -> List[Node]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT id, content, vector, metadata, created_at, expires_at, circle_id, vector_model_id FROM nodes"
            )
            rows = cursor.fetchall()
            scored = []
            query_vec = np.array(vector, dtype=np.float32)
            
            for row in rows:
                node_vec = np.frombuffer(row[2], dtype=np.float32)
                sim = self._cosine_similarity(node_vec, query_vec)
                scored.append((sim, row))
            
            scored.sort(reverse=True, key=lambda x: x[0])
            
            return [Node(
                id=row[0],
                content=row[1],
                vector=np.frombuffer(row[2], dtype=np.float32).tolist(),
                metadata=json.loads(row[3]),
                created_at=row[4],
                expires_at=row[5],
                circle_id=row[6],
                vector_model_id=row[7]
            ) for sim, row in scored[:limit]]

    async def delete_expired(self, ttl_seconds: int) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT id, created_at FROM nodes")
            now = datetime.now()
            expired_ids = []
            for row in cursor.fetchall():
                created_at = row[1]
                if isinstance(created_at, str):
                    try:
                        created_at_dt = datetime.fromisoformat(created_at)
                    except ValueError:
                        continue
                else:
                    created_at_dt = created_at
                
                if (now - created_at_dt).total_seconds() > ttl_seconds:
                    expired_ids.append(row[0])
            
            for node_id in expired_ids:
                conn.execute("DELETE FROM nodes WHERE id = ?", (node_id,))
            return len(expired_ids)

    async def purge_circle_memory(self, circle_id: str) -> int:
        """Purge all nodes in a circle."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM nodes WHERE circle_id = ?", (circle_id,))
            deleted_count = cursor.rowcount
            logging.info(f"🧹 Purged {deleted_count} nodes from circle '{circle_id}'")
            return deleted_count

    async def purge_all_memory(self) -> int:
        """Purge all nodes from all circles."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM nodes")
            deleted_count = cursor.rowcount
            logging.info(f"Purged all {deleted_count} nodes from all circles")
            return deleted_count

    async def count_nodes_by_circle(self, circle_id: str) -> int:
        """Count nodes in a specific circle (async version)."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM nodes WHERE circle_id = ?", (circle_id,))
            count = cursor.fetchone()[0]
            return count

    def count_nodes_by_circle_sync(self, circle_id: str) -> int:
        """Count nodes in a specific circle (sync version for GTK menu)."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM nodes WHERE circle_id = ?", (circle_id,))
            count = cursor.fetchone()[0]
            return count

    def _cosine_similarity(self, vec1, vec2):
        if (vec1.shape != vec2.shape or np.linalg.norm(vec1) == 0 or np.linalg.norm(vec2) == 0):
            return -1.0
        return float(np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2)))