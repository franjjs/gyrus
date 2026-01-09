from typing import List

from fastembed import TextEmbedding

from gyrus.application.services import EmbeddingService


class FastEmbedAdapter(EmbeddingService):
    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5"):
        # Downloads model (~80MB) on first run
        self.model = TextEmbedding(model_name=model_name)

    async def encode(self, text: str) -> List[float]:
        # fastembed returns generator, take first result
        embeddings = list(self.model.embed([text]))
        return embeddings[0].tolist()
