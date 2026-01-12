import asyncio
import threading
import logging
import yaml
from gyrus.application.use_cases import CaptureClipboard, RecallClipboard, PurgeExpiredNodes # Importa el nuevo caso
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

with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)
    
TTL_SECONDS = config.get('ttl_seconds', 60)
CLEANUP_INTERVAL = config.get('cleanup_interval', 60)

async def periodic_cleanup(purge_use_case, ttl_seconds, interval=CLEANUP_INTERVAL):
    while True:
        await purge_use_case.execute(ttl_seconds)
        await asyncio.sleep(interval)

async def run_daemon():
    # Init adapters
    repo = SQLiteNodeRepository()
    ai = FastEmbedAdapter()
    clipboard = LinuxClipboardAdapter()
    ui = RofiAdapter()

    # Init use cases
    capture_use_case = CaptureClipboard(repo, ai, clipboard, ttl_seconds=TTL_SECONDS)
    recall_use_case = RecallClipboard(repo, ui, clipboard, ai)
    purge_use_case = PurgeExpiredNodes(repo)

    # Start periodic cleanup
    asyncio.create_task(periodic_cleanup(purge_use_case, TTL_SECONDS, interval=CLEANUP_INTERVAL))

    loop = asyncio.get_running_loop()

    # Hotkey callbacks
    def on_capture():
        logging.info("💡 Capture triggered!")
        asyncio.run_coroutine_threadsafe(capture_use_case.execute(), loop)

    def on_recall():
        logging.info("🔍 Recall triggered!")
        asyncio.run_coroutine_threadsafe(recall_use_case.execute(), loop)

    # Start keyboard listener with hotkeys from config
    hotkey_cfg = config.get('hotkeys', {})
    capture_hotkey = hotkey_cfg.get('capture', '<ctrl>+<cmd>+c')
    recall_hotkey = hotkey_cfg.get('recall', '<ctrl>+<cmd>+v')

    hotkeys = {
        capture_hotkey: on_capture,
        recall_hotkey: on_recall
    }

    listener = KeyboardListenerAdapter(hotkeys)
    listener_thread = threading.Thread(target=listener.start, daemon=True)
    listener_thread.start()

    logging.info(f"🧠 Gyrus Stage 1 (Synapse) Active")
    logging.info(f"⌨️  Capture: {capture_hotkey} | Recall: {recall_hotkey}")

    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    try:
        logging.info("Starting Gyrus Daemon...")
        asyncio.run(run_daemon())
    except KeyboardInterrupt:
        logging.info("Gyrus shutting down safely...")