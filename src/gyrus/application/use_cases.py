import logging
import time
from datetime import datetime, timedelta

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
        ttl_seconds: int = 10,  # Default TTL, configurable
        circle_id: str = "local"
    ):
        self.repo = repo
        self.ai = ai
        self.cb = cb
        self.ttl_seconds = ttl_seconds
        self.circle_id = circle_id

    async def execute(self):
        text = self.cb.get_text()
        if not text:
            return

        # Set clipboard to selection, mimicking Ctrl+C
        self.cb.set_text(text)

        # Async: AI service may be slow
        vector = await self.ai.encode(text)
        expires_at = datetime.now() + timedelta(seconds=self.ttl_seconds)
        node = Node(
            content=text,
            vector=vector,
            expires_at=expires_at,
            circle_id=self.circle_id
        )

        await self.repo.save(node)
        logging.info(
            f"Gyrus [M1]: Nodo {node.id} persisted. "
            f"Circle: {self.circle_id}, TTL={self.ttl_seconds}s expires_at={expires_at}"
        )


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
        logging.debug("Entered RecallClipboard.execute")
        ref_emb = await self._get_reference_embedding()
        if ref_emb is None:
            logging.warning("No reference text for similarity search.")
            return

        nodes = await self.repo.find_similar(ref_emb, limit=15)
        if not nodes:
            logging.info("No similar memories found.")
            return

        logging.debug(f"RecallClipboard: {len(nodes)} nodes obtained for selection.")

        selected, contents = self._show_ui_selection(nodes)

        self._handle_selection_and_paste(selected, nodes, contents)

    def _show_ui_selection(self, nodes):
        contents = [n.content for n in nodes]
        selected = self.ui.select_from_list(contents)
        return selected, contents

    async def _get_reference_embedding(self) -> list:
        try:
            ref_text = ''
            try:
                ref_text = (
                    self.cb.get_selection()
                    if hasattr(self.cb, 'get_selection')
                    else ''
                )
            except Exception as e:
                logging.warning(f"Error getting selection: {e}")
                ref_text = ''

            if not ref_text:
                try:
                    ref_text = self.cb.get_text()
                except Exception as e:
                    logging.warning(f"Error getting clipboard: {e}")
                    ref_text = ''

            logging.debug(f"RecallClipboard reference text: '{ref_text[:40]}'")
            return await self.ai.encode(ref_text)
        except Exception as e:
            logging.warning(f"Error getting reference embedding: {e}")
            return await self.ai.encode("")

    def _handle_selection_and_paste(self, selected, nodes, contents):
        if selected:
            try:
                idx = contents.index(selected)
                node = nodes[idx]
                paste_text = node.content
                logging.info(f"Selected node info: id={node.id}, content='{node.content}'")
                logging.info(f"  created_at={node.created_at}, metadata={node.metadata}")
            except ValueError:
                paste_text = selected
                logging.info(
                    f"Selected value not found in nodes, "
                    f"using raw selected: '{paste_text}'"
                )
            self.cb.set_text(paste_text)
            time.sleep(0.1)
            with self.kb_controller.pressed(Key.ctrl):
                self.kb_controller.tap('v')
            logging.info(f"Gyrus: '{paste_text[:20]}...' pasted (semantic match).")


class PurgeExpiredNodes:
    def __init__(self, repo: NodeRepository):
        self.repo = repo

    async def execute(self, ttl_seconds: int):
        deleted = await self.repo.delete_expired(ttl_seconds)
        logging.info(
            f"PurgeExpiredNodes: deleted {deleted} expired nodes "
            f"(TTL={ttl_seconds}s)."
        )

