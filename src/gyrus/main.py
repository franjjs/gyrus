import asyncio
import atexit
import logging
import os
import sys
import threading
from pathlib import Path

import yaml

from gyrus.application.circle_service import CircleService
from gyrus.application.use_cases import (
    CaptureClipboard,
    PurgeAllMemory,
    PurgeCircleMemory,
    PurgeExpiredNodes,
    RecallClipboard,
)
from gyrus.infrastructure.adapters.ai.fastembed_adapter import FastEmbedAdapter
from gyrus.infrastructure.adapters.storage.sqlite_storage import SQLiteNodeRepository
from gyrus.infrastructure.adapters.system.clipboard_adapter import (
    CrossPlatformClipboardAdapter,
)
from gyrus.infrastructure.adapters.system.keyboard_adapter import KeyboardListenerAdapter
from gyrus.infrastructure.adapters.system.tray_lifecycle_adapter import (
    TrayLifecycleManager,
)
from gyrus.infrastructure.adapters.ui.rofi_adapter import RofiAdapter
from gyrus.infrastructure.adapters.ui.tkinter_adapter import TkinterAdapter

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
            os.kill(pid, 0)
            logging.error(f"Gyrus is already running (PID {pid}).")
            sys.exit(1)
        except (OSError, ValueError):
            logging.warning("Removing stale PID file")
            PIDFILE.unlink()
    
    PIDFILE.write_text(str(os.getpid()))
    atexit.register(cleanup_pid_file)

def cleanup_pid_file():
    """Remove PID file on clean exit."""
    if PIDFILE.exists():
        PIDFILE.unlink()

async def periodic_cleanup(purge_use_case, ttl_seconds, interval=CLEANUP_INTERVAL):
    while True:
        await purge_use_case.execute(ttl_seconds)
        await asyncio.sleep(interval)

async def run_daemon():
    # Init CircleService (centralized circle state)
    circle_service = CircleService(initial_circle="local")
    
    # Init adapters
    repo = SQLiteNodeRepository()
    ai = FastEmbedAdapter()
    clipboard = CrossPlatformClipboardAdapter()

    if config.get('ui_adapter', 'tkinter') == 'rofi':
        ui = RofiAdapter()
    else:
        ui = TkinterAdapter(clipboard)

    # Init use cases with circle service
    capture_use_case = CaptureClipboard(repo, ai, clipboard, circle_service, ttl_seconds=TTL_SECONDS)
    recall_use_case = RecallClipboard(repo, ui, clipboard, ai, circle_service)
    purge_use_case = PurgeExpiredNodes(repo)
    purge_circle_use_case = PurgeCircleMemory(repo)
    purge_all_use_case = PurgeAllMemory(repo)

    loop = asyncio.get_running_loop()

    # Callbacks
    def on_capture():
        logging.info("💡 Capture triggered!")
        loop.call_soon_threadsafe(lambda: asyncio.create_task(capture_use_case.execute()))

    def on_recall():
        logging.info("🔍 Recall triggered!")
        loop.call_soon_threadsafe(lambda: asyncio.create_task(recall_use_case.execute(mode="recall")))

    def on_purge():
        logging.info("🗑️ Purge triggered!")
        loop.call_soon_threadsafe(lambda: asyncio.create_task(purge_use_case.execute(TTL_SECONDS)))

    def on_purge_circle(circle_id: str):
        logging.info(f"🧹 Purge circle requested: {circle_id}")
        loop.call_soon_threadsafe(lambda: asyncio.create_task(purge_circle_use_case.execute(circle_id)))

    def on_view_circle(circle_id: str):
        logging.info(f"👁️ View circle requested: {circle_id}")
        # Use recall_use_case with mode="view" (copy to clipboard, not paste)
        loop.call_soon_threadsafe(lambda: asyncio.create_task(recall_use_case.execute(mode="view")))

    def on_purge_all():
        logging.info("Purge all memories requested")
        loop.call_soon_threadsafe(lambda: asyncio.create_task(purge_all_use_case.execute()))

    def on_circle_change(new_id):
        circle_service.set_circle(new_id)

    # Initialize tray adapter
    tray = TrayLifecycleManager.create_tray_adapter(
        on_circle_change, on_purge_circle, on_view_circle, on_purge_all, repo
    )
    if tray:
        TrayLifecycleManager.start_tray_thread(tray)

    # Hotkeys
    hotkey_cfg = config.get('hotkeys', {})
    hotkeys = {
        hotkey_cfg.get('capture', '<ctrl>+<cmd>+c'): on_capture,
        hotkey_cfg.get('recall', '<ctrl>+<cmd>+v'): on_recall,
        hotkey_cfg.get('purge', '<ctrl>+<cmd>+p'): on_purge,
    }

    listener = KeyboardListenerAdapter(hotkeys)
    threading.Thread(target=listener.start, daemon=True).start()

    logging.info("🧠 Gyrus Stage 2 Active")
    
    while True:
        await asyncio.sleep(3600)

def cli():
    import argparse
    parser = argparse.ArgumentParser(
        description="🧠 GYRUS - Semantic Collective Memory",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('command', nargs='?', default='start', choices=['start', 'status', 'show', 'stop'])
    parser.add_argument('--full', action='store_true')
    args = parser.parse_args()
    
    if args.command == 'start':
        try:
            check_pid_file()
            asyncio.run(run_daemon())
        except KeyboardInterrupt:
            logging.info("Gyrus shutting down...")
        finally:
            cleanup_pid_file()
    
    elif args.command == 'status':
        if PIDFILE.exists():
            print("✅ Gyrus is running")
        else:
            print("❌ Gyrus is not running")
            
    elif args.command == 'show':
        from gyrus.infrastructure.adapters.storage.sqlite_storage import SQLiteNodeRepository
        repo = SQLiteNodeRepository()
        nodes = asyncio.run(repo.find_last(limit=100))
        for i, node in enumerate(nodes, 1):
            print(f"{i:2d}. {node.content[:60]}...")

    elif args.command == 'stop':
        if PIDFILE.exists():
            pid = int(PIDFILE.read_text().strip())
            os.kill(pid, 15)
            print(f"✅ Stop signal sent to PID {pid}")

if __name__ == "__main__":
    cli()