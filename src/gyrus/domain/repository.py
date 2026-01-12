from abc import ABC, abstractmethod
from typing import List

from .models import Node


class NodeRepository(ABC):
    @abstractmethod
    async def save(self, node: Node) -> None: pass

    @abstractmethod
    async def find_similar(
        self, vector: List[float], limit: int = 15
    ) -> List[Node]:
        pass
    
    @abstractmethod
    async def delete_expired(self) -> int: pass
