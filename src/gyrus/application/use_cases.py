from gyrus.application.services import ClipboardService, EmbeddingService
from gyrus.domain.models import Node
from gyrus.domain.repository import NodeRepository


class CaptureClipboard:
    def __init__(
        self,
        repo: NodeRepository,
        ai: EmbeddingService,
        cb: ClipboardService
    ):
        self.repo = repo
        self.ai = ai
        self.cb = cb

    async def execute(self):
        text = self.cb.get_text()
        if not text:
            return

        # Proceso asíncrono asumiendo que el AI service puede ser lento
        vector = await self.ai.encode(text)
        node = Node(content=text, vector=vector)

        await self.repo.save(node)
        print(f"Gyrus [M1]: Nodo {node.id} persisted.")
