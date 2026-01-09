import asyncio
import threading
import logging
from gyrus.application.use_cases import CaptureClipboard, RecallClipboard # Importa el nuevo caso
from gyrus.infrastructure.adapters.ai.fastembed_adapter import FastEmbedAdapter
from gyrus.infrastructure.adapters.storage.sqlite_adapter import SQLiteNodeRepository
from gyrus.infrastructure.adapters.ui.rofi_adapter import RofiAdapter # Importa Rofi
from gyrus.infrastructure.adapters.system.linux_adapter import (
    LinuxClipboardAdapter,
    KeyboardListenerAdapter,
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
)

TTL_SECONDS = 10  # For testing, set to 10 seconds. Make configurable via config if needed.
CLEANUP_INTERVAL = 10  # Run cleanup every 10 seconds for testing

async def periodic_cleanup(repo, interval=CLEANUP_INTERVAL):
    while True:
        await repo.delete_expired()
        await asyncio.sleep(interval)

async def run_daemon():
    # Init adapters
    repo = SQLiteNodeRepository()
    ai = FastEmbedAdapter()
    clipboard = LinuxClipboardAdapter()
    ui = RofiAdapter()

    # Init use cases
    capture_use_case = CaptureClipboard(repo, ai, clipboard)
    recall_use_case = RecallClipboard(repo, ui, clipboard, ai)

    # Start periodic cleanup
    asyncio.create_task(periodic_cleanup(repo))

    loop = asyncio.get_running_loop()

    # Hotkey callbacks
    def on_capture():
        logging.info("💡 Capture triggered!")
        asyncio.run_coroutine_threadsafe(capture_use_case.execute(), loop)

    def on_recall():
        logging.info("🔍 Recall triggered!")
        asyncio.run_coroutine_threadsafe(recall_use_case.execute(), loop)

    # Start keyboard listener with hotkeys
    hotkeys = {
        '<ctrl>+<cmd>+c': on_capture,
        '<ctrl>+<cmd>+v': on_recall
    }
    
    listener = KeyboardListenerAdapter(hotkeys)
    listener_thread = threading.Thread(target=listener.start, daemon=True)
    listener_thread.start()

    logging.info("🧠 Gyrus Stage 1 (Synapse) Active")
    logging.info("⌨️  Ctrl+Super+C: Capture | Ctrl+Super+V: Recall")

    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    try:
        logging.info("Starting Gyrus Daemon...")
        asyncio.run(run_daemon())
    except KeyboardInterrupt:
        logging.info("Gyrus shutting down safely...")