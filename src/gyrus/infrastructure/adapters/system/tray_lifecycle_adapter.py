import logging
import os
import threading
from typing import Callable, Optional

# Safe import for AppIndicator - gracefully degrade if not available
try:
    from gyrus.infrastructure.adapters.ui.gnome_app_indicator_adapter import load_appindicator
    HAS_APPINDICATOR, AppIndicator3, Gtk = load_appindicator()
except ImportError:
    HAS_APPINDICATOR = False
    AppIndicator3 = None
    Gtk = None

from gyrus.infrastructure.adapters.ui.tray_adapter import PyStrayAdapter


class TrayLifecycleManager:
    """Manages tray adapter selection and GTK lifecycle."""

    @staticmethod
    def detect_desktop_env() -> str:
        """Detect desktop environment."""
        return os.getenv('XDG_CURRENT_DESKTOP', '').upper()

    @staticmethod
    def create_tray_adapter(on_circle_change: Callable, on_purge_circle: Callable = None, on_view_circle: Callable = None, on_purge_all: Callable = None, repo = None):
        """Factory: select best available tray adapter."""
        from gyrus.infrastructure.adapters.ui.gnome_app_indicator_adapter import (
            GnomeAppIndicatorAdapter,
        )

        desktop_env = TrayLifecycleManager.detect_desktop_env()

        try:
            if HAS_APPINDICATOR and "GNOME" in desktop_env:
                tray = GnomeAppIndicatorAdapter(
                    current_circle_id="local",
                    on_circle_change_callback=on_circle_change,
                    on_purge_circle_callback=on_purge_circle,
                    on_view_circle_callback=on_view_circle,
                    on_purge_all_callback=on_purge_all,
                    repo=repo,
                )
                logging.info("✅ Using GNOME AppIndicator adapter")
            elif "GNOME" in desktop_env:
                # GNOME without AppIndicator has no systray - skip gracefully
                logging.info("ℹ️ GNOME detected without AppIndicator - tray disabled")
                logging.info("   To enable, install: sudo apt install python3-gi gir1.2-appindicator3-0.1")
                return None
            else:
                # KDE, Xfce, Windows, macOS - use PyStray
                tray = PyStrayAdapter(
                    current_circle_id="local",
                    on_circle_change_callback=on_circle_change,
                )
                logging.info("✅ Using PyStray adapter")

            tray.render(["local", "cloud"])
            return tray
        except Exception as e:
            logging.warning(f"⚠️ Tray initialization failed (non-critical): {e}")
            return None

    @staticmethod
    def start_tray_thread(tray) -> Optional[threading.Thread]:
        """Start GTK event loop in a daemon thread if using AppIndicator."""
        if not tray or not HAS_APPINDICATOR:
            return None

        def gtk_loop():
            try:
                Gtk.main()
            except Exception as e:
                logging.warning(f"GTK loop error: {e}")

        thread = threading.Thread(target=gtk_loop, daemon=True)
        thread.start()
        return thread
