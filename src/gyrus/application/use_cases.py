import logging
import time
from datetime import datetime, timedelta
from typing import List

from pynput.keyboard import Controller, Key

from gyrus.application.services import ClipboardService, EmbeddingService, UIService
from gyrus.application.circle_service import CircleService
from gyrus.domain.models import Node


def _sanitize_log(text: str, max_chars: int = 60) -> str:
    """Sanitize text for logging: remove newlines, limit chars."""
    clean = text.replace("\n", " ").replace("\r", " ").strip()
    clean = " ".join(clean.split())  # Normalize whitespace
    return (clean[:max_chars] + "...") if len(clean) > max_chars else clean
from gyrus.domain.repository import NodeRepository


class CaptureClipboard:
    def __init__(
        self,
        repo: NodeRepository,
        ai: EmbeddingService,
        cb: ClipboardService,
        circle_service: CircleService,
        ttl_seconds: int = 60
    ):
        self.repo = repo
        self.ai = ai
        self.cb = cb
        self.circle_service = circle_service
        self.ttl_seconds = ttl_seconds

    async def execute(self):
        # Capture from current selection (infra handles Ctrl+C)
        text = self.cb.capture_from_selection()
        if not text:
            return

        # Get vector and current model metadata
        vector = await self.ai.encode(text)
        model_vector_id = self.ai.vector_model_id

        expires_at = datetime.now() + timedelta(seconds=self.ttl_seconds)
        
        # Use current circle from service
        circle_id = self.circle_service.get_circle()
        
        node = Node(
            content=text,
            vector=vector,
            vector_model_id=model_vector_id,
            expires_at=expires_at,
            circle_id=circle_id
        )

        await self.repo.save(node)
        logging.info(f"💾 Captured in '{circle_id}': {node.id}")

class RecallClipboard:
    def __init__(
        self,
        repo: NodeRepository,
        ui: UIService,
        cb: ClipboardService,
        ai: EmbeddingService,
        circle_service: CircleService
    ):
        self.repo = repo
        self.ui = ui
        self.cb = cb
        self.ai = ai
        self.circle_service = circle_service
        self.kb_controller = Controller()

    async def execute(self, mode: str = "recall"):
        """Execute recall/view.
        
        Args:
            mode: "recall" (select & paste) or "view" (select & copy to clipboard)
        """
        # Get current circle
        circle_id = self.circle_service.get_circle()
        logging.info(f"🔍 Recalling from circle: {circle_id}")
        
        # Fetch last 30 nodes for current circle
        nodes = await self.repo.find_last(limit=30)
        
        # Filter by circle_id
        circle_nodes = [n for n in nodes if n.circle_id == circle_id]
        
        if not circle_nodes:
            logging.info(f"No nodes found in circle '{circle_id}'")
            return

        # Get current model ID to ensure vector compatibility
        current_vmid = getattr(self.ai, "vector_model_id", "unknown")

        # Trigger UI selection with circle_id in context
        selected_content = self.ui.select_from_list(
            nodes=circle_nodes,
            vectorizer=self.ai.encode,
            vector_model_id=current_vmid,
            circle_id=circle_id,
            mode=mode
        )

        if selected_content:
            if mode == "recall":
                self._handle_selection_and_paste(selected_content, circle_nodes)
            elif mode == "view":
                self._handle_selection_and_copy(selected_content, circle_nodes)

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
            logging.info(f"✅ Pasted from '{self.circle_service.get_circle()}': {_sanitize_log(paste_text)}")
        except Exception as e:
            logging.error(f"Failed to paste: {e}")

    def _handle_selection_and_copy(self, selected_content: str, nodes: List[Node]):
        """Copy selected content to clipboard (view mode)."""
        # Match selection back to original node for full content
        target_node = next((n for n in nodes if n.content == selected_content), None)
        copy_text = target_node.content if target_node else selected_content
        
        # Copy to clipboard
        self.cb.set_text(copy_text)
        logging.info(f"✅ Copied to clipboard from '{self.circle_service.get_circle()}': {_sanitize_log(copy_text)}")


class PurgeExpiredNodes:
    def __init__(self, repo: NodeRepository):
        self.repo = repo

    async def execute(self, ttl_seconds: int):
        deleted = await self.repo.delete_expired(ttl_seconds)
        if deleted > 0:
            logging.info(f"Purge: Deleted {deleted} expired nodes")


class PurgeCircleMemory:
    """Purge all nodes in a circle."""
    
    def __init__(self, repo: NodeRepository):
        self.repo = repo

    async def execute(self, circle_id: str):
        deleted = await self.repo.purge_circle_memory(circle_id)
        logging.info(f"🧹 Purged circle '{circle_id}': {deleted} nodes removed")
        return deleted


class PurgeAllMemory:
    """Purge all nodes from all circles."""
    
    def __init__(self, repo: NodeRepository):
        self.repo = repo

    async def execute(self):
        deleted = await self.repo.purge_all_memory()
        logging.info(f"Purged all memories: {deleted} nodes removed")
        return deleted
