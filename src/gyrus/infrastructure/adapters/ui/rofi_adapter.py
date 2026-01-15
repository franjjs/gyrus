import subprocess
from typing import Any, Callable, List, Optional

from gyrus.application.services import UIService


class RofiAdapter(UIService):
    """
    Linux-only text-based picker using rofi dmenu.
    Requires 'rofi' binary to be installed on the system.
    """

    def select_from_list(
        self, 
        nodes: List[Any], 
        vectorizer: Optional[Callable] = None, 
        vector_model_id: str = "unknown",
        circle_id: str = "local",
        mode: str = "recall"
    ) -> Optional[str]:
        if not nodes:
            return None

        # Format lines for Rofi
        items = [f"{n.content.replace('\n', ' ')}" for n in nodes]
        input_str = "\n".join(items)

        try:
            if mode == "recall":
                prompt = f"🧠 Gyrus Recall • {circle_id}"
            else:
                prompt = f"👁️ Gyrus View • {circle_id}"
            
            process = subprocess.Popen(
                ['rofi', '-dmenu', '-p', prompt, '-i', '-theme-str', 'window {width: 40%;}'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                text=True
            )
            stdout, _ = process.communicate(input=input_str)
            
            if not stdout:
                return None

            # Map selection back to node
            clean_sel = stdout.strip().replace(" »  ", "")
            for n in nodes:
                if n.content.replace('\n', ' ').strip() == clean_sel:
                    return n.content
            return clean_sel
            
        except FileNotFoundError:
            return None