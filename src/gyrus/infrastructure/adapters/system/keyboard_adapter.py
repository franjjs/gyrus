from pynput import keyboard


class KeyboardListenerAdapter:
    """
    Cross-platform keyboard hotkey listener using pynput.
    Works on Linux, Windows, and macOS.
    """

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
