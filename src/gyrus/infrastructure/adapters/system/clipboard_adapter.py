import logging
import time

import pyperclip
from pynput.keyboard import Controller, Key

from gyrus.application.services import ClipboardService


class CrossPlatformClipboardAdapter(ClipboardService):
    """
    Cross-platform clipboard adapter using pyperclip.
    Works on Linux, Windows, and macOS without external dependencies.
    """

    def __init__(self):
        self.kb_controller = Controller()

    def get_text(self) -> str:
        """Get text from clipboard."""
        try:
            text = pyperclip.paste().strip()
            logging.info(f"Clipboard get_text: '{text[:40]}'")
            return text
        except Exception as e:
            logging.error(f"Failed to get clipboard text: {e}")
            return ""

    def set_text(self, text: str) -> None:
        """Set text to clipboard."""
        try:
            pyperclip.copy(text)
            logging.info(f"Clipboard set_text: '{text[:40]}'")
        except Exception as e:
            logging.error(f"Failed to set clipboard text: {e}")

    def capture_from_selection(self) -> str:
        """
        Copy current selection to clipboard and return the text.
        Simulates Ctrl+C to capture the active selection.
        """
        try:
            # Simulate Ctrl+C to copy current selection
            with self.kb_controller.pressed(Key.ctrl):
                self.kb_controller.tap('c')
            # Small delay to ensure clipboard is updated
            time.sleep(0.1)
            # Get and return the text
            text = self.get_text()
            logging.info(f"Captured from selection: '{text[:40]}'")
            return text
        except Exception as e:
            logging.error(f"Failed to capture from selection: {e}")
            return ""
