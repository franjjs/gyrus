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

    @abstractmethod
    def capture_from_selection(self) -> str:
        """Copy current selection to clipboard and return the text."""
        pass

class UIService(ABC):
    @abstractmethod
    def select_from_list(
        self, 
        nodes: List[Any], 
        vectorizer: Optional[Callable] = None,
        vector_model_id: str = "unknown",
        circle_id: str = "local",
        mode: str = "recall"
    ) -> Optional[str]: 
        pass

class TrayService(ABC):
    @abstractmethod
    def update_status(self, circle_id: str, is_online: bool):
        pass

    @abstractmethod
    def set_available_circles(self, circles: list):
        pass