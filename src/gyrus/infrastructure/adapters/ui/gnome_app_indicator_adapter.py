import logging
import os
import signal
from pathlib import Path

import gi

from gyrus.application.services import TrayService


def load_appindicator():
    """Try to load AppIndicator3 and GTK bindings."""
    try:
        gi.require_version('Gtk', '3.0')
        gi.require_version('AppIndicator3', '0.1')
        from gi.repository import AppIndicator3, Gtk
        return True, AppIndicator3, Gtk
    except (ImportError, ValueError):
        return False, None, None


HAS_APPINDICATOR, AppIndicator3, Gtk = load_appindicator()

class GnomeAppIndicatorAdapter(TrayService):
    """AppIndicator adapter for GNOME (uses StatusNotifierItem via GI)."""

    def __init__(
        self,
        current_circle_id,
        on_circle_change_callback,
        on_purge_circle_callback=None,
        on_view_circle_callback=None,
        on_purge_all_callback=None,
        repo=None,
    ):
        if not HAS_APPINDICATOR:
            raise RuntimeError(
                "AppIndicator3 not found. Install: sudo apt install gir1.2-appindicator3-0.1"
            )
        
        self.current_circle_id = current_circle_id
        self.on_change = on_circle_change_callback
        self.on_purge = on_purge_circle_callback
        self.on_view = on_view_circle_callback
        self.on_purge_all = on_purge_all_callback
        self.repo = repo
        self.indicator = None
        self.available_circles = []

    def _get_icon_path(self):
        """Find icon file using absolute path."""
        # Adjusting path to reach /assets from infrastructure/adapters/ui/
        base_path = Path(__file__).parent.parent.parent.parent.parent
        
        candidates = [
            base_path / "assets" / "icon.png",
            base_path / "assets" / "icon.logo",
            Path.cwd() / "assets" / "icon.png",
        ]
        
        for icon in candidates:
            if icon.exists():
                return str(icon.absolute())
        
        return "system-run"  # GNOME generic fallback

    def _get_node_count_label(self, circle_id: str) -> str:
        """Get label with node count for view memory option."""
        if not self.repo:
            return "View memory"
        
        try:
            count = self.repo.count_nodes_by_circle_sync(circle_id)
            return f"View memory ({count})"
        except Exception as e:
            logging.warning(f"Could not count nodes: {e}")
            return "View memory"

    def _create_separator(self):
        """Create a visual separator with padding."""
        sep = Gtk.SeparatorMenuItem()
        return sep

    def _create_menu(self):
        """Create a native GTK menu."""
        menu = Gtk.Menu()
        group = None
        
        # Circles list (Radio-like behavior with RadioMenuItem)
        for circle_id in self.available_circles:
            # Create submenu for this circle
            submenu = Gtk.Menu()
            
            # Radio button for circle selection
            if circle_id == "local":
                label = f"<span foreground='green'><b>{circle_id}</b></span>"
                item = Gtk.RadioMenuItem(group, label=label)
                item.get_child().set_use_markup(True)
            else:
                item = Gtk.RadioMenuItem(group, label=circle_id)
            
            if group is None:
                group = item
            
            is_active = circle_id == self.current_circle_id
            item.set_active(is_active)
            item.connect("toggled", self._on_circle_selected, circle_id)
            
            # Add submenu with actions
            if self.on_view or self.on_purge:
                # View option with node count (refreshed each time)
                if self.on_view:
                    view_label = self._get_node_count_label(circle_id)
                    view_item = Gtk.MenuItem(label=view_label)
                    view_item.connect("activate", self._on_view_circle, circle_id)
                    submenu.append(view_item)
                
                # Purge option
                if self.on_purge:
                    purge_item = Gtk.MenuItem(label="Purge memory")
                    purge_item.connect("activate", self._on_purge_circle, circle_id)
                    submenu.append(purge_item)
                
                submenu.show_all()
                item.set_submenu(submenu)
            
            menu.append(item)
        
        menu.append(self._create_separator())
        
        # Purge all option - with icon
        if self.on_purge_all:
            purge_all_item = Gtk.MenuItem(label="⊗ Purge all")
            purge_all_item.connect("activate", self._on_purge_all)
            menu.append(purge_all_item)
        
        menu.append(self._create_separator())
        
        # Exit option - stops the daemon
        exit_item = Gtk.MenuItem(label="Stop Gyrus")
        exit_item.connect("activate", self._on_exit)
        menu.append(exit_item)
        
        menu.show_all()
        return menu

    def _on_circle_selected(self, widget, circle_id):
        """Handle circle selection - force radio-like behavior."""
        # Only react to activate (True), not deactivate (False)
        if widget.get_active():
            if circle_id != self.current_circle_id:
                self.current_circle_id = circle_id
                logging.info(f"🔄 Circle: {circle_id}")
                self.on_change(circle_id)
                # Rebuild menu to update checkboxes
                if self.indicator:
                    self.indicator.set_menu(self._create_menu())

    def _on_view_circle(self, widget, circle_id):
        """Handle view circle request."""
        logging.info(f"👁️ View circle requested from tray: {circle_id}")
        if self.on_view:
            self.on_view(circle_id)

    def _on_purge_circle(self, widget, circle_id):
        """Handle circle purge request."""
        logging.info(f"🧹 Purge circle requested from tray: {circle_id}")
        if self.on_purge:
            self.on_purge(circle_id)
        
        # Rebuild menu after purge
        if self.indicator:
            self.indicator.set_menu(self._create_menu())

    def _on_purge_all(self, widget):
        """Handle purge all memories request."""
        logging.info("🧹 Purge all memories requested from tray")
        if self.on_purge_all:
            self.on_purge_all()

    def _on_exit(self, widget):
        """Exit handler - stops the daemon process cleanly."""
        logging.info("🛑 Stop triggered from tray")
        os.kill(os.getpid(), signal.SIGTERM)

    def render(self, initial_circles):
        """Setup and display the GNOME Indicator."""
        self.available_circles = initial_circles
        icon_path = self._get_icon_path()
        
        # Initialize Indicator
        self.indicator = AppIndicator3.Indicator.new(
            "gyrus-app-indicator",
            icon_path,
            AppIndicator3.IndicatorCategory.APPLICATION_STATUS
        )
        
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        
        # Create initial menu
        initial_menu = self._create_menu()
        self.indicator.set_menu(initial_menu)
        
        logging.info(f"✅ GNOME AppIndicator active with icon: {icon_path}")

    def set_available_circles(self, circles: list):
        """Update the menu dynamically and refresh display."""
        self.available_circles = circles
        if self.indicator:
            # Rebuild menu to refresh node counts
            self.indicator.set_menu(self._create_menu())

    def update_status(self, circle_id: str, is_online: bool):
        """Visual feedback for connection status."""
        logging.info(f"Status update for {circle_id}: {'Online' if is_online else 'Offline'}")