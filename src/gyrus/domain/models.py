from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID, uuid4

DEFAULT_CIRCLE_NAME = "local"


@dataclass
class Circle:
    """
    A trust circle represents a shared context for memory.
    If is_local is True, it is only available on this machine.
    """
    id: UUID = field(default_factory=uuid4)
    name: str = DEFAULT_CIRCLE_NAME
    is_local: bool = True
    # Future Stage 3: Encryption keys will be stored in metadata/dedicated fields
    metadata: Dict = field(default_factory=dict)


@dataclass
class Node:
    content: str
    vector: List[float]
    vector_model_id: str = "bge-small-en-v1.5"
    circle_id: Optional[UUID] = None  # None represents the 'local' circle
    id: UUID = field(default_factory=uuid4)
    metadata: Dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None

    def is_expired(self) -> bool:
        if not self.expires_at:
            return False
        return datetime.now() > self.expires_at
