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
                    circle_id TEXT
                )
            """)

    async def save(self, node: Node) -> None:
        logging.debug(
            f"Saving node: id={node.id}, content='{node.content[:40]}', "
            f"created_at={node.created_at}"
        )
        with sqlite3.connect(self.db_path) as conn:
            # Convert vector (list) to bytes for SQLite
            vector_bin = np.array(node.vector, dtype=np.float32).tobytes()
            circle_id_str = str(node.circle_id) if node.circle_id else None
            conn.execute(
                "INSERT INTO nodes VALUES (?, ?, ?, ?, ?, ?, ?)",
                (str(node.id), node.content, vector_bin,
                 json.dumps(node.metadata), node.created_at, node.expires_at, circle_id_str)
            )

    async def find_last(self, limit: int = 15) -> List[Node]:
        logging.debug(
            f"find_last: querying db_path={self.db_path} "
            f"for last {limit} nodes"
        )
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT id, content, vector, metadata, created_at, "
                "expires_at, circle_id FROM nodes ORDER BY created_at DESC LIMIT ?",
                (limit,)
            )
            rows = cursor.fetchall()
            logging.debug(f"find_last: found {len(rows)} rows")
            for row in rows:
                logging.debug(
                    f"find_last row: id={row[0]}, content='{row[1]}', "
                    f"created_at={row[4]}"
                )
            return [Node(
                id=row[0],
                content=row[1],
                vector=np.frombuffer(row[2], dtype=np.float32).tolist(),
                metadata=json.loads(row[3]),
                created_at=row[4],
                expires_at=row[5],
                circle_id=row[6]
            ) for row in rows]

    async def find_similar(
        self, vector: List[float], limit: int = 15
    ) -> List[Node]:
        logging.debug(
            f"find_similar: querying db_path={self.db_path} "
            f"for similar nodes"
        )
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT id, content, vector, metadata, "
                "created_at, expires_at, circle_id FROM nodes"
            )
            rows = cursor.fetchall()
            scored = []
            query_vec = np.array(vector, dtype=np.float32)
            for row in rows:
                node_vec = np.frombuffer(row[2], dtype=np.float32)
                sim = self._cosine_similarity(node_vec, query_vec)
                scored.append((sim, row))
            scored.sort(reverse=True, key=lambda x: x[0])
            result = []
            for sim, row in scored[:limit]:
                logging.debug(
                    f"find_similar row: sim={sim:.4f}, id={row[0]}, "
                    f"content='{row[1]}', created_at={row[4]}"
                )
                result.append(Node(
                    id=row[0],
                    content=row[1],
                    vector=np.frombuffer(row[2], dtype=np.float32).tolist(),
                    metadata=json.loads(row[3]),
                    created_at=row[4],
                    expires_at=row[5],
                    circle_id=row[6]
                ))
            logging.debug(
                f"find_similar: returning {len(result)} nodes "
                f"sorted by similarity"
            )
            return result

    async def delete_expired(self, ttl_seconds: int) -> int:
        logging.debug(
            f"delete_expired: checking for expired nodes "
            f"in db_path={self.db_path} with TTL={ttl_seconds}s"
        )
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT id, created_at FROM nodes"
            )
            now = datetime.now()
            expired_ids = []
            for row in cursor.fetchall():
                created_at = row[1]
                # Parse created_at if it's a string
                if isinstance(created_at, str):
                    try:
                        created_at_dt = datetime.fromisoformat(created_at)
                    except Exception:
                        continue
                else:
                    created_at_dt = created_at
                if (now - created_at_dt).total_seconds() > ttl_seconds:
                    expired_ids.append(row[0])
            for node_id in expired_ids:
                conn.execute("DELETE FROM nodes WHERE id = ?", (node_id,))
            logging.debug(f"delete_expired: deleted {len(expired_ids)} nodes")
            return len(expired_ids)

    def _cosine_similarity(self, vec1, vec2):
        if (
            vec1.shape != vec2.shape
            or np.linalg.norm(vec1) == 0
            or np.linalg.norm(vec2) == 0
        ):
            return -1.0
        return float(
            np.dot(vec1, vec2) /
            (np.linalg.norm(vec1) * np.linalg.norm(vec2))
        )

