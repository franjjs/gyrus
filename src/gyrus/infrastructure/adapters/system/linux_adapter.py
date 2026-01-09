import subprocess

from application.services import ClipboardService
from pynput import keyboard


class LinuxClipboardAdapter(ClipboardService):
    def get_text(self) -> str:
        try:
            return subprocess.check_output(['wl-paste'], text=True).strip()
        except Exception:
            return subprocess.check_output(
                ['xclip', '-selection', 'clipboard', '-o'], text=True
            ).strip()

    def set_text(self, text: str) -> None:
        # Para el M1, inyectamos el texto de vuelta al portapapeles
        process = subprocess.Popen(['wl-copy'], stdin=subprocess.PIPE)
        process.communicate(input=text.encode())

class KeyboardListenerAdapter:
    def __init__(self, on_hotkey_triggered):
        self.on_hotkey = on_hotkey_triggered
        self.hotkey = keyboard.HotKey(
            keyboard.HotKey.parse('<ctrl>+<cmd>+c'),
            self.on_hotkey
        )

    def start(self):
        with keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release
        ) as listener:
            listener.join()

    def _on_press(self, key):
        self.hotkey.press(self.listener.canonical(key))
    def _on_release(self, key):
        self.hotkey.release(self.listener.canonical(key))
