from typing import List

from fastembed import TextEmbedding

from gyrus.application.services import EmbeddingService

DEFAULT_MODEL_NAME = "BAAI/bge-small-en-v1.5"

class FastEmbedAdapter(EmbeddingService):
    def __init__(self, model_name: str = DEFAULT_MODEL_NAME):
        # Downloads model (~80MB) on first run
        self.model = TextEmbedding(model_name=model_name)

    async def encode(self, text: str) -> List[float]:
        # fastembed returns generator, take first result
        embeddings = list(self.model.embed([text]))
        return embeddings[0].tolist()
    
    @property
    def vector_model_id(self) -> str:
        return self.model.model_name
