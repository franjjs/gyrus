from typing import List

from fastembed import TextEmbedding

from gyrus.application.services import EmbeddingService


class FastEmbedAdapter(EmbeddingService):
    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5"):
        # Esto descarga el modelo (aprox 80MB) la primera vez
        self.model = TextEmbedding(model_name=model_name)

    async def encode(self, text: str) -> List[float]:
        # fastembed devuelve un generador, tomamos el primer resultado
        embeddings = list(self.model.embed([text]))
        return embeddings[0].tolist()
