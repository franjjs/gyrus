import json
import sqlite3
from typing import List

import numpy as np

from gyrus.domain.models import Node
from gyrus.domain.repository import NodeRepository


class SQLiteNodeRepository(NodeRepository):
    def __init__(self, db_path: str = "gyrus.db"):
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
                    expires_at TIMESTAMP
                )
            """)

    async def save(self, node: Node) -> None:
        with sqlite3.connect(self.db_path) as conn:
            # Convertimos el vector (list) a bytes para SQLite
            vector_bin = np.array(node.vector, dtype=np.float32).tobytes()
            conn.execute(
                "INSERT INTO nodes VALUES (?, ?, ?, ?, ?, ?)",
                (str(node.id), node.content, vector_bin, 
                 json.dumps(node.metadata), node.created_at, node.expires_at)
            )

    async def find_similar(self, vector: List[float], limit: int = 10) -> List[Node]:
        # En el M1 hacemos un select simple. 
        # La búsqueda vectorial real (coseno) la haremos en memoria o con extensión VSS.
        return []

    async def delete_expired(self) -> int:
        # Stub implementation for abstract method
        return 0
