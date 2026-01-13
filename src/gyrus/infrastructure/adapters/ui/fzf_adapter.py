import subprocess
from typing import List, Optional

from gyrus.application.services import UIService


class FzfAdapter(UIService):
    def select_from_list(self, items: List[str]) -> Optional[str]:
        input_str = "\n".join(items)
        fzf_cmd = [
            "fzf",
            "--prompt", "🧠 Gyrus Recall > ",
            "--border",
            "--color=bg+:#1a1a2f,fg+:#f8f8f2,hl:#ff79c6,hl+:#bd93f9,info:#8be9fd,pointer:#ffb86c,marker:#50fa7b,spinner:#ff5555,header:#bd93f9",
            "--pointer", "➤",
            "--marker", "✓",
            "--layout=reverse",
            "--height=40%",
            "--min-height=10",
            "--header", "Selecciona una memoria de Gyrus",
        ]
        try:
            process = subprocess.Popen(
                fzf_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                text=True
            )
            stdout, _ = process.communicate(input=input_str)
            return stdout.strip() if stdout else None
        except FileNotFoundError:
            print("Error: 'fzf' not found. Please install it.")
            return None
