import logging
import subprocess
from subprocess import DEVNULL

from pynput import keyboard

from gyrus.application.services import ClipboardService


def _sanitize_log(text: str, max_chars: int = 60) -> str:
    """Sanitize text for logging: remove newlines, limit chars."""
    clean = text.replace("\n", " ").replace("\r", " ").strip()
    clean = " ".join(clean.split())
    return (clean[:max_chars] + "...") if len(clean) > max_chars else clean


class LinuxClipboardAdapter(ClipboardService):        
    def get_text(self) -> str:
        # Try to get selection first
        selection = self.get_selection()
        if selection:
            logging.info("get_text: using selection")
            return selection
        # Fallback to clipboard
        try:
            text = subprocess.check_output(
                ['wl-paste'], text=True, stderr=DEVNULL
            ).strip()
        except Exception:
            try:
                text = subprocess.check_output(
                    ['xclip', '-selection', 'clipboard', '-o'],
                    text=True,
                    stderr=DEVNULL
                ).strip()
            except Exception:
                text = ""
        logging.info(f"Clipboard get_text: '{_sanitize_log(text)}'")
        return text

    def set_text(self, text: str) -> None:
        logging.info(f"Clipboard set_text: '{_sanitize_log(text)}'")
        try:
            process = subprocess.Popen(['wl-copy'], stdin=subprocess.PIPE)
            process.communicate(input=text.encode())
        except Exception:
            process = subprocess.Popen(
                ['xclip', '-selection', 'clipboard'],
                stdin=subprocess.PIPE
            )
            process.communicate(input=text.encode())

    def get_selection(self) -> str:
        try:
            # Try to get X11 primary selection
            text = subprocess.check_output(
                ['xclip', '-selection', 'primary', '-o'],
                text=True,
                stderr=DEVNULL
            ).strip()
            logging.info(f"Selection get_selection: '{_sanitize_log(text)}'")
            return text
        except Exception:
            return ""

class KeyboardListenerAdapter:
    def __init__(self, hotkey_map):
        # hotkey_map: dict of key combo string -> callback
        self.hotkeys = [
            keyboard.HotKey(keyboard.HotKey.parse(combo), callback)
            for combo, callback in hotkey_map.items()
        ]
        self.listener = None

    def start(self):
        # Store listener for access in press/release
        with keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release
        ) as self.listener:
            self.listener.join()

    def _on_press(self, key):
        # Normalize key states
        canonical = self.listener.canonical(key)
        for hotkey in self.hotkeys:
            hotkey.press(canonical)

    def _on_release(self, key):
        canonical = self.listener.canonical(key)
        for hotkey in self.hotkeys:
            hotkey.release(canonical)