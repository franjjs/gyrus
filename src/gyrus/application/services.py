from abc import ABC, abstractmethod
from typing import Any, Callable, List, Optional


class EmbeddingService(ABC):
    @abstractmethod
    async def encode(self, text: str) -> List[float]: pass

    @property
    @abstractmethod
    def vector_model_id(self) -> str:
        pass

class ClipboardService(ABC):
    @abstractmethod
    def get_text(self) -> str: pass
    
    @abstractmethod
    def set_text(self, text: str) -> None: pass

class UIService(ABC):
    @abstractmethod
    def select_from_list(
        self, 
        nodes: List[Any], 
        vectorizer: Optional[Callable] = None,
        vector_model_id: str = "unknown" # Updated name
    ) -> Optional[str]: 
        pass