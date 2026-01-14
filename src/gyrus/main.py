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
from gyrus.infrastructure.adapters.storage.sqlite_storage import SQLiteNodeRepository
from gyrus.infrastructure.adapters.system.clipboard_adapter import (
    CrossPlatformClipboardAdapter,
)
from gyrus.infrastructure.adapters.system.keyboard_adapter import KeyboardListenerAdapter
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
    clipboard = CrossPlatformClipboardAdapter()  # Cross-platform (Linux/Windows/macOS)

    if config.get('ui_adapter', 'tkinter') == 'rofi':
        ui = RofiAdapter()  # Linux-only (requires 'rofi' binary)
    else:
        ui = TkinterAdapter()  # Cross-platform (Linux/Windows/macOS)

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

def cli():
    """Entry point for the gyrus CLI command."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="""
╔═══════════════════════════════════════════════════════════════════╗
║                    🧠  GYRUS  🧠                                  ║
║          Semantic Collective Memory Infrastructure               ║
║                                                                   ║
║  "Nodes that fire together, wire together" — Hebb's Law          ║
╚═══════════════════════════════════════════════════════════════════╝
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 COMMANDS:

  🚀 gyrus start           Start in foreground (blocks terminal)
  📊 gyrus status          Check if daemon is running
  🔍 gyrus show            Show memory nodes (compact preview)
  📖 gyrus show --full     Show memory nodes (full details)
  🛑 gyrus stop            Stop running daemon

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 EXAMPLES:

  Run Gyrus in foreground (for testing):
    $ gyrus start

  Install as system daemon (Linux):
    $ ./scripts/install_gyrus_linux.sh
    $ systemctl --user status gyrus

  Check daemon status:
    $ gyrus status

  View your clipboard history:
    $ gyrus show

  See full node details (embeddings, metadata):
    $ gyrus show --full

  Stop the daemon (if running via PID):
    $ gyrus stop

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚙️  Configuration: config.yaml
📁  Database: data/gyrus.db
🔑  Default Hotkeys: Ctrl+Cmd+C (Capture) | Ctrl+Cmd+V (Recall)

🐧 Linux Daemon: Use scripts/install_gyrus_linux.sh (systemd)
🍎 macOS Daemon: Use launchd (plist needed)
🪟 Windows Daemon: Use Task Scheduler or NSSM

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        """
    )
    
    parser.add_argument(
        'command',
        nargs='?',
        default='start',
        choices=['start', 'status', 'show', 'stop'],
        help='Command to execute (default: start)'
    )
    
    parser.add_argument(
        '--full',
        action='store_true',
        help='Show full details (for show command)'
    )
    
    args = parser.parse_args()
    
    if args.command == 'start':
        try:
            logging.info("Starting Gyrus Daemon...")
            check_pid_file()
            asyncio.run(run_daemon())
        except KeyboardInterrupt:
            logging.info("Gyrus shutting down safely...")
        finally:
            cleanup_pid_file()
    
    elif args.command == 'status':
        if PIDFILE.exists():
            try:
                pid = int(PIDFILE.read_text().strip())
                os.kill(pid, 0)  # Check if process exists
                print(f"✅ Gyrus is running (PID {pid})")
                sys.exit(0)
            except (OSError, ValueError):
                print("❌ Gyrus is not running (stale PID file)")
                sys.exit(1)
        else:
            print("❌ Gyrus is not running")
            sys.exit(1)
    
    elif args.command == 'show':
        # Show memory nodes
        from gyrus.infrastructure.adapters.storage.sqlite_storage import SQLiteNodeRepository
        repo = SQLiteNodeRepository()
        nodes = asyncio.run(repo.find_last(limit=100))
        
        if not nodes:
            print("No memory nodes found.")
            sys.exit(0)
        
        if args.full:
            # Full details mode (like show_gyrus_memory.py script)
            print(f"\n--- Gyrus Local Memory (last {len(nodes)} nodes) ---\n")
            for node in nodes:
                print(
                    f"ID: {node.id}\n"
                    f"Content: {node.content}\n"
                    f"Created: {node.created_at}\n"
                    f"CircleId: {node.circle_id}\n"
                    f"Embeddings: {node.vector}\n"
                    f"Vector Model ID: {node.vector_model_id}\n"
                    f"Expires: {node.expires_at}\n"
                    f"{'-'*40}"
                )
        else:
            # Preview mode (compact)
            print(f"\n🧠 Gyrus Memory ({len(nodes)} nodes)\n")
            for i, node in enumerate(nodes, 1):
                content_preview = node.content[:60].replace('\n', ' ')
                print(f"{i:2d}. {content_preview}...")
                print(f"    Created: {node.created_at} | Model: {node.vector_model_id}")
            print()
    
    elif args.command == 'stop':
        if PIDFILE.exists():
            try:
                pid = int(PIDFILE.read_text().strip())
                os.kill(pid, 15)  # SIGTERM
                print(f"✅ Sent stop signal to Gyrus (PID {pid})")
                sys.exit(0)
            except (OSError, ValueError):
                print("❌ Could not stop Gyrus")
                sys.exit(1)
        else:
            print("❌ Gyrus is not running")
            sys.exit(1)

if __name__ == "__main__":
    cli()