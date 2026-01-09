import subprocess
from gyrus.application.services import UIService
from typing import List, Optional

class RofiAdapter(UIService):
    def select_from_list(self, items: List[str]) -> Optional[str]:
        input_str = "\n".join(items)
        try:
            process = subprocess.Popen(
                ['rofi', '-dmenu', '-p', '🧠 Gyrus Recall', '-i', '-theme-str', 'window {width: 40%;}'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                text=True
            )
            stdout, _ = process.communicate(input=input_str)
            return stdout.strip() if stdout else None
        except FileNotFoundError:
            print("Error: 'rofi' not found. Please install it.")
            return None