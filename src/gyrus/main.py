import asyncio
import atexit
import logging
import os
import sys
import threading
from pathlib import Path

import yaml

from gyrus.application.use_cases import (  # Importa el nuevo caso
    CaptureClipboard,
    PurgeExpiredNodes,
    RecallClipboard,
)
from gyrus.infrastructure.adapters.ai.fastembed_adapter import FastEmbedAdapter
from gyrus.infrastructure.adapters.storage.sqlite_adapter import SQLiteNodeRepository
from gyrus.infrastructure.adapters.system.linux_adapter import (
    KeyboardListenerAdapter,
    LinuxClipboardAdapter,
)
from gyrus.infrastructure.adapters.ui.rofi_adapter import RofiAdapter
from gyrus.infrastructure.adapters.ui.twinter_adapter import TkinterAdapter  # Importa RofiDmenuAdapter

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
)

with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)
    
TTL_SECONDS = config.get('ttl_seconds', 60)
CLEANUP_INTERVAL = config.get('cleanup_interval', 60)

PIDFILE = Path.home() / '.gyrus.pid'

def check_pid_file():
    """Check if another instance is running via PID file."""
    if PIDFILE.exists():
        try:
            pid = int(PIDFILE.read_text().strip())
            # Check if process is still running
            os.kill(pid, 0)
            logging.error(
                f"Gyrus is already running (PID {pid}). "
                f"Use 'kill {pid}' to stop it."
            )
            sys.exit(1)
        except (OSError, ValueError):
            # Process doesn't exist or invalid PID, remove stale file
            logging.warning("Removing stale PID file")
            PIDFILE.unlink()
    
    # Write current PID
    PIDFILE.write_text(str(os.getpid()))
    logging.info(f"PID file created: {PIDFILE}")
    
    # Ensure cleanup on exit
    atexit.register(cleanup_pid_file)

def cleanup_pid_file():
    """Remove PID file on clean exit."""
    if PIDFILE.exists():
        PIDFILE.unlink()
        logging.info("PID file removed")

async def periodic_cleanup(purge_use_case, ttl_seconds, interval=CLEANUP_INTERVAL):
    while True:
        await purge_use_case.execute(ttl_seconds)
        await asyncio.sleep(interval)

async def run_daemon():
    # Init adapters
    repo = SQLiteNodeRepository()
    ai = FastEmbedAdapter()
    clipboard = LinuxClipboardAdapter()

    if config.get('ui_adapter', 'tkinter') == 'rofi':
        ui = RofiAdapter()
    else:
        ui = TkinterAdapter()

    # Init use cases
    capture_use_case = CaptureClipboard(repo, ai, clipboard, ttl_seconds=TTL_SECONDS)
    recall_use_case = RecallClipboard(repo, ui, clipboard, ai)
    purge_use_case = PurgeExpiredNodes(repo)

    # Start periodic cleanup
    asyncio.create_task(
        periodic_cleanup(purge_use_case, TTL_SECONDS, interval=CLEANUP_INTERVAL)
    )

    loop = asyncio.get_running_loop()

    # Hotkey callbacks
    _capture_count = 0
    _recall_count = 0
    
    def on_capture():
        nonlocal _capture_count
        _capture_count += 1
        logging.info(f"💡 Capture triggered! (call #{_capture_count})")
        asyncio.run_coroutine_threadsafe(capture_use_case.execute(), loop)

    def on_recall():
        nonlocal _recall_count
        _recall_count += 1
        logging.info(f"🔍 Recall triggered! (call #{_recall_count})")
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

    logging.info("🧠 Gyrus Stage 1 (Synapse) Active")
    logging.info(f"⌨️  Capture: {capture_hotkey} | Recall: {recall_hotkey}")

    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    try:
        logging.info("Starting Gyrus Daemon...")
        check_pid_file()
        asyncio.run(run_daemon())
    except KeyboardInterrupt:
        logging.info("Gyrus shutting down safely...")
    finally:
        cleanup_pid_file()