import logging
import subprocess
from typing import List, Optional

from gyrus.application.services import UIService


class RofiDmenuAdapter(UIService):
    """
    Adapter that uses Rofi in dmenu mode to provide a 
    graphical selection interface.
    """
    def select_from_list(self, items: List[str]) -> Optional[str]:
        if not items:
            logging.warning("RofiAdapter: No items to display.")
            return None

        # Join the memory items with newlines for Rofi's stdin
        input_str = "\n".join(items)

        # Inline theme to make it look modern and floating
        # Adjust width and lines as you prefer
        theme_str = (
            "window { width: 40%; border: 2px; border-color: #bd93f9; "
            "location: center; anchor: center; } "
            "listview { lines: 12; fixed-height: false; }"
        )

        cmd = [
            "rofi",
            "-dmenu",           # Act like dmenu (read from stdin, write to stdout)
            "-i",              # Case-insensitive matching
            "-p", "🧠 Gyrus",   # Prompt label
            "-sync",           # Force sync to avoid socket errors
            "-theme-str", theme_str
        ]

        try:
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,  # Capture stderr to avoid terminal noise
                text=True
            )
            
            stdout, stderr = process.communicate(input=input_str)

            if process.returncode != 0 and stderr:
                logging.debug(f"Rofi returned non-zero or stderr: {stderr.strip()}")

            selection = stdout.strip()
            return selection if selection else None

        except FileNotFoundError:
            logging.error("Rofi binary not found. Please install it: 'sudo apt install rofi'")
            return None
        except Exception as e:
            logging.error(f"Unexpected error in RofiAdapter: {e}")
            return None