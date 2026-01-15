import logging
from pathlib import Path

import pystray
from PIL import Image

from gyrus.application.services import TrayService


class PyStrayAdapter(TrayService):
    def __init__(self, current_circle_id, on_circle_change_callback):
        self.current_circle_id = current_circle_id
        self.on_change = on_circle_change_callback
        self.icon = None

    def _create_menu(self, circles):
        """Build dynamic menu from circle list."""
        menu_items = []
        for c_id in circles:
            menu_items.append(pystray.MenuItem(
                c_id, 
                self._handle_click(c_id),
                checked=lambda item, id=c_id: id == self.current_circle_id,
                radio=True
            ))
        
        # Separator alternative
        menu_items.append(pystray.MenuItem("-", None, enabled=False))
        menu_items.append(pystray.MenuItem("Exit", self._on_exit))
        
        return pystray.Menu(*menu_items)

    def _handle_click(self, c_id):
        """Handle circle selection click."""
        def _inner(icon, item):
            self.current_circle_id = c_id
            logging.info(f"Tray: Switched to {c_id}")
            self.on_change(c_id)
        return _inner

    def _on_exit(self, icon, item):
        """Shutdown tray icon."""
        logging.info("Tray: Stopping icon...")
        icon.stop()

    def _get_asset_path(self, filename):
        """Locate assets relative to project root."""
        try:
            # Navigate from: src/gyrus/infrastructure/adapters/ui/tray_adapter.py -> root
            root_path = Path(__file__).parent.parent.parent.parent.parent
            asset = root_path / "assets" / filename
            if asset.exists():
                return asset
        except Exception:
            pass
        
        # Fallback to current working directory
        fallback = Path.cwd() / "assets" / filename
        return fallback if fallback.exists() else None

    def render(self, initial_circles):
        """Initialize and run the system tray icon."""
        try:
            # 1. Load Image
            icon_path = self._get_asset_path("icon.png")
            if icon_path:
                image = Image.open(icon_path)
                logging.info(f"✅ Icon loaded: {icon_path}")
            else:
                logging.warning("⚠️ icon.png not found, using fallback")
                image = Image.new('RGB', (64, 64), color=(0, 255, 127))

            # 2. Setup Icon
            self.icon = pystray.Icon(
                "Gyrus", 
                image, 
                "Gyrus Synapse", 
                menu=self._create_menu(initial_circles)
            )

            # 3. Launch in detached mode (Non-blocking)
            self.icon.run_detached()
            logging.info("✅ Tray service active")

        except Exception as e:
            # Common on Linux if AppIndicator is missing
            logging.error(f"❌ Failed to start Tray: {e}")
            self.icon = None

    def set_available_circles(self, circles: list):
        """Refresh menu with new circles."""
        if self.icon:
            self.icon.menu = self._create_menu(circles)
            logging.info("Tray: Menu updated")

    def update_status(self, circle_id: str, is_online: bool):
        """Optional: show desktop notification."""
        if self.icon:
            status = "Online" if is_online else "Offline"
            self.icon.notify(f"{circle_id} is now {status}", title="Gyrus")