from abc import ABC, abstractmethod
from typing import List


class EmbeddingService(ABC):
    @abstractmethod
    async def encode(self, text: str) -> List[float]: pass

class ClipboardService(ABC):
    @abstractmethod
    def get_text(self) -> str: pass
    
    @abstractmethod
    def set_text(self, text: str) -> None: pass
