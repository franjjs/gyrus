#!/usr/bin/env python3
import asyncio

from gyrus.infrastructure.adapters.storage.sqlite_adapter import SQLiteNodeRepository


async def show_memory():
    repo = SQLiteNodeRepository()
    nodes = await repo.find_last(limit=100)
    print(f"\n--- Gyrus Local Memory (last {len(nodes)} nodes) ---\n")
    for node in nodes:
        circle_id = node.circle_id
        print(
            f"ID: {node.id}\n"
            f"Content: {node.content}\n"
            f"Created: {node.created_at}\n"
            f"CircleId: {circle_id}\n"
            f"Embeddings: {node.vector}\n"
            f"Expires: {node.expires_at}\n"
            f"{'-'*40}"
        )

if __name__ == "__main__":
    asyncio.run(show_memory())
