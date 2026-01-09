from abc import ABC, abstractmethod
from typing import List, Optional

class EmbeddingService(ABC):
    @abstractmethod
    async def encode(self, text: str) -> List[float]: pass

class ClipboardService(ABC):
    @abstractmethod
    def get_text(self) -> str: pass
    
    @abstractmethod
    def set_text(self, text: str) -> None: pass

class UIService(ABC):
    @abstractmethod
    def select_from_list(self, items: List[str]) -> Optional[str]: pass