import logging
from pynput import keyboard
from gyrus.application.services import ClipboardService
import subprocess
from subprocess import DEVNULL

class LinuxClipboardAdapter(ClipboardService):        
    def get_text(self) -> str:
        # Try to get selection first
        selection = self.get_selection()
        if selection:
            logging.info("get_text: using selection")
            return selection
        # Fallback to clipboard
        try:
            text = subprocess.check_output(['wl-paste'], text=True, stderr=DEVNULL).strip()
        except:
            try:
                text = subprocess.check_output(['xclip', '-selection', 'clipboard', '-o'], text=True, stderr=DEVNULL).strip()
            except:
                text = ""
        logging.info(f"Clipboard get_text: '{text[:40]}'")
        return text

    def set_text(self, text: str) -> None:
        logging.info(f"Clipboard set_text: '{text[:40]}'")
        try:
            process = subprocess.Popen(['wl-copy'], stdin=subprocess.PIPE)
            process.communicate(input=text.encode())
        except:
            process = subprocess.Popen(['xclip', '-selection', 'clipboard'], stdin=subprocess.PIPE)
            process.communicate(input=text.encode())

    def get_selection(self) -> str:
        try:
            # Try to get X11 primary selection
            text = subprocess.check_output(['xclip', '-selection', 'primary', '-o'], text=True, stderr=DEVNULL).strip()
            logging.info(f"Selection get_selection: '{text[:40]}'")
            return text
        except:
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