import asyncio

from gyrus.application.use_cases import CaptureClipboard
from gyrus.infrastructure.adapters.ai.fastembed_adapter import FastEmbedAdapter
from gyrus.infrastructure.adapters.storage.sqlite_adapter import SQLiteNodeRepository
from gyrus.infrastructure.adapters.system.linux_adapter import (
    LinuxClipboardAdapter,
)


async def main():
    # Output adaptors
    repo = SQLiteNodeRepository()
    ai = FastEmbedAdapter()
    clipboard = LinuxClipboardAdapter()

    # Define use case
    capture_use_case = CaptureClipboard(repo, ai, clipboard)

    # Daemon action
    loop = asyncio.get_event_loop()
    def trigger_capture():
        asyncio.run_coroutine_threadsafe(capture_use_case.execute(), loop)

    print("Gyrus Daemon up... (Ctrl+Super+C to memorize)")
    # 4. Iniciar Listener (este bloque depende de tu implementación de pynput)
    # Por simplicidad en el M1, puedes usar un loop infinito o el listener.start()
