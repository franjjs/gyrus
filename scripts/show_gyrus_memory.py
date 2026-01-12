#!/usr/bin/env python3
import asyncio
from gyrus.infrastructure.adapters.storage.sqlite_adapter import SQLiteNodeRepository

async def show_memory():
    repo = SQLiteNodeRepository()
    nodes = await repo.find_last(limit=100)
    print(f"\n--- Gyrus Local Memory (last {len(nodes)} nodes) ---\n")
    for node in nodes:
        circle_id = node.metadata.get('circleId', 'N/A') if hasattr(node, 'metadata') else 'N/A'
        print(f"ID: {node.id}\nContent: {node.content}\nCreated: {node.created_at}\nCircleId: {circle_id}\nEmbeddings: {node.vector}\nExpires: {node.expires_at}\n{'-'*40}")

if __name__ == "__main__":
    asyncio.run(show_memory())
