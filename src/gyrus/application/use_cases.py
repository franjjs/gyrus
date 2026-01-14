import logging
import time
from datetime import datetime, timedelta
from typing import List

from pynput.keyboard import Controller, Key

from gyrus.application.services import ClipboardService, EmbeddingService, UIService
from gyrus.domain.models import Node
from gyrus.domain.repository import NodeRepository


class CaptureClipboard:
    def __init__(
        self,
        repo: NodeRepository,
        ai: EmbeddingService,
        cb: ClipboardService,
        ttl_seconds: int = 60,
        circle_id: str = "local"
    ):
        self.repo = repo
        self.ai = ai
        self.cb = cb
        self.ttl_seconds = ttl_seconds
        self.circle_id = circle_id

    async def execute(self):
        # Capture from current selection (infra handles Ctrl+C)
        text = self.cb.capture_from_selection()
        if not text:
            return

        # Get vector and current model metadata
        vector = await self.ai.encode(text)
        model_vector_id = self.ai.vector_model_id

        expires_at = datetime.now() + timedelta(seconds=self.ttl_seconds)
        
        node = Node(
            content=text,
            vector=vector,
            vector_model_id=model_vector_id,
            expires_at=expires_at,
            circle_id=self.circle_id
        )

        await self.repo.save(node)
        logging.info(f"Gyrus: Node {node.id} saved using model {model_vector_id}")

class RecallClipboard:
    def __init__(
        self,
        repo: NodeRepository,
        ui: UIService,
        cb: ClipboardService,
        ai: EmbeddingService
    ):
        self.repo = repo
        self.ui = ui
        self.cb = cb
        self.ai = ai
        self.kb_controller = Controller()

    async def execute(self):
        logging.info("RecallClipboard: Starting local hybrid search")
        
        # Fetch last 30 nodes for local buffer
        nodes = await self.repo.find_last(limit=30)
        if not nodes:
            logging.info("No nodes found in database")
            return

        # Get current model ID to ensure vector compatibility
        current_vmid = getattr(self.ai, "vector_model_id", "unknown")

        # Trigger UI selection with 3 synchronized arguments
        selected_content = self.ui.select_from_list(
            nodes=nodes,
            vectorizer=self.ai.encode,
            vector_model_id=current_vmid
        )

        if selected_content:
            self._handle_selection_and_paste(selected_content, nodes)

    def _handle_selection_and_paste(self, selected_content: str, nodes: List[Node]):
        # Match selection back to original node for full content
        target_node = next((n for n in nodes if n.content == selected_content), None)
        paste_text = target_node.content if target_node else selected_content
        
        # Update clipboard and trigger OS paste command
        self.cb.set_text(paste_text)
        logging.info("Clipboard text set, waiting for sync...")
        time.sleep(0.1) # OS clipboard sync buffer
        
        try:
            logging.info("Attempting to paste (Ctrl+V)...")
            with self.kb_controller.pressed(Key.ctrl):
                self.kb_controller.tap('v')
            logging.info(f"Gyrus: Pasted '{paste_text[:20]}...' successfully")
        except Exception as e:
            logging.error(f"Failed to paste: {e}")

class PurgeExpiredNodes:
    def __init__(self, repo: NodeRepository):
        self.repo = repo

    async def execute(self, ttl_seconds: int):
        deleted = await self.repo.delete_expired(ttl_seconds)
        if deleted > 0:
            logging.info(f"Purge: Deleted {deleted} expired nodes")