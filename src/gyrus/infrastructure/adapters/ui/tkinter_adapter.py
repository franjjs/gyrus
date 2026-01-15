import asyncio
import logging
import queue
import re
import threading
import tkinter as tk
from pathlib import Path
from tkinter import font as tkfont
from typing import Any, Callable, List, Optional

from gyrus.application.services import ClipboardService, UIService
from gyrus.domain.search_logic import hybrid_search


class TkinterAdapter(UIService):
    """UI with docked tooltip and hybrid search integration."""

    # Shared UI thread and root
    _ui_thread: Optional[threading.Thread] = None
    _root: Optional[tk.Tk] = None
    _command_queue: queue.Queue = queue.Queue()
    _ui_running: bool = False
    _active_windows: List[tk.Toplevel] = []

    def __init__(self, clipboard: ClipboardService):
        self.clipboard = clipboard
        self.selected_value: Optional[str] = None
        self.visible_nodes: List[Any] = []
        self.tip_window = None
        self.tip_label = None
        self.tip_inner = None
        self.after_id = None
        self.last_tip_index = -1
        self.mode: str = "recall"
        self.circle_id: str = "local"
        self.vectorizer: Optional[Callable] = None
        self.vector_model_id: str = "unknown"
        self.icon_image = None
        self.window: Optional[tk.Toplevel] = None
        self.colors = {
            "window_bg": "#ffffff",
            "search_bg": "#f8fafc",
            "search_border": "#cbd5e1",
            "search_focus": "#2563eb",
            "text_main": "#1e293b",
            "text_dim": "#475569",
            "placeholder": "#94a3b8",
            "item_highlight": "#eff6ff",
            "accent": "#2563eb",
            "tip_bg": "#0f172a",
            "tip_fg": "#f1f5f9",
            "tip_border": "#334155",
        }

    @classmethod
    def _start_ui_thread(cls):
        """Start the shared UI thread if not already running."""
        if not cls._ui_running:
            cls._ui_running = True
            cls._ui_thread = threading.Thread(target=cls._run_ui_loop, daemon=True)
            cls._ui_thread.start()
            # Wait for root to be ready
            import time
            while cls._root is None:
                time.sleep(0.01)

    @classmethod
    def _run_ui_loop(cls):
        """Main UI loop running in dedicated thread."""
        cls._root = tk.Tk(className="Gyrus")
        cls._root.withdraw()  # Keep root hidden
        
        def process_commands():
            """Process commands from main thread."""
            try:
                while not cls._command_queue.empty():
                    cmd, args = cls._command_queue.get_nowait()
                    cmd(*args)
            except queue.Empty:
                pass
            finally:
                cls._root.after(50, process_commands)
        
        process_commands()
        cls._root.mainloop()

    def select_from_list(
        self,
        nodes: List[Any],
        vectorizer: Optional[Callable] = None,
        vector_model_id: str = "unknown",
        circle_id: str = "local",
        mode: str = "recall",
    ) -> Optional[str]:
        """Main orchestrator for the UI flow.
        
        Args:
            mode: "recall" (select & paste) or "view" (select & copy)
        """
        if not nodes:
            return None

        # Ensure UI thread is running
        self._start_ui_thread()

        self.selected_value = None
        self.last_tip_index = -1
        self.vectorizer = vectorizer
        self.vector_model_id = vector_model_id
        self.circle_id = circle_id
        self.mode = mode
        self.nodes = nodes

        # Result queue for this window
        result_queue = queue.Queue()
        
        # Create isolated state for this window
        window_state = {
            'selected_value': None,
            'root': None,
            'tip_window': None,
            'closed': False
        }
        
        def create_window():
            """Create window in UI thread with isolated state."""
            # Close all existing windows first to ensure only one window at a time
            windows_to_close = list(TkinterAdapter._active_windows)
            for win in windows_to_close:
                try:
                    if win.winfo_exists():
                        win.destroy()
                except:
                    pass
            TkinterAdapter._active_windows.clear()
            
            # Create new instance to avoid state collision
            window = TkinterAdapter(self.clipboard)
            window.vectorizer = vectorizer
            window.vector_model_id = vector_model_id
            window.circle_id = circle_id
            window.mode = mode
            window.nodes = nodes
            window.selected_value = None
            window.last_tip_index = -1
            
            # Use Toplevel (not Tk) - there should only be one Tk() instance
            window.root = tk.Toplevel(TkinterAdapter._root, class_="Gyrus")
            window.root.withdraw()  # Hide root initially
            
            window._setup_window()
            window._create_fonts()
            window._create_tooltip()
            window._create_container()
            window._create_search_bar()
            window._create_listbox()
            window._bind_events()
            window._update_ui()
            
            window.root.deiconify()  # Show after setup
            
            # Store reference for cleanup
            window_state['root'] = window.root
            window_state['tip_window'] = window.tip_window
            
            # Track this window
            TkinterAdapter._active_windows.append(window.root)
            
            # Override cleanup to put result in queue
            original_cleanup = window._cleanup_and_close
            def cleanup_with_result():
                if not window_state['closed']:
                    window_state['closed'] = True
                    window_state['selected_value'] = window.selected_value
                    result_queue.put(window.selected_value)
                    # Untrack this window
                    if window.root in TkinterAdapter._active_windows:
                        TkinterAdapter._active_windows.remove(window.root)
                    original_cleanup()
            window._cleanup_and_close = cleanup_with_result
            
            # Handle window close button
            window.root.protocol("WM_DELETE_WINDOW", window._cleanup_and_close)

        # Send command to UI thread
        self._command_queue.put((create_window, ()))
        
        # Recall mode: wait for result
        # View mode: return immediately
        if mode == "recall":
            return result_queue.get()
        else:
            return None

    # Private methods

    def _set_wmctrl_name(self) -> None:
        """Try to set window name using wmctrl command for better window manager integration."""
        try:
            import subprocess
            import os
            
            wid = self.root.winfo_id()
            if self.mode == "recall":
                name = f"Gyrus Recall • {self.circle_id}"
            else:
                name = f"Gyrus View • {self.circle_id}"
            
            # Try to rename using wmctrl
            subprocess.run(
                ["wmctrl", "-i", "-r", str(wid), "-b", "remove,maximized_vert,maximized_horz"],
                capture_output=True,
                timeout=1
            )
            # Also try to set window class via xprop
            subprocess.run(
                ["xprop", "-id", str(wid), "-f", "WM_CLASS", "32s", "-set", "WM_CLASS", "gyrus\0Gyrus"],
                capture_output=True,
                timeout=1
            )
        except Exception:
            pass

    def _truncate(self, text: str, max_chars: int) -> str:
        """Minimally clean and truncate text."""
        clean = text.replace("\n", " ").strip()
        clean = re.sub(r"\s+", " ", clean)
        return (clean[: max_chars - 3] + "...") if len(clean) > max_chars else clean

    def _setup_window(self) -> None:
        """Initialize main window properties."""
        if self.mode == "recall":
            title = f"🧠 Gyrus Recall • {self.circle_id}"
        else:
            title = f"👁️ Gyrus View • {self.circle_id}"

        # Set title first
        self.root.title(title)
        
        # Try to set window class/name
        try:
            # For Toplevel windows, sometimes we need to set these attributes differently
            if self.mode == "recall":
                self.root.wm_class("gyrus-recall", "Gyrus")
            else:
                self.root.wm_class("gyrus-view", "Gyrus")
        except Exception:
            pass
        
        # Use wmctrl if available to set the window name in window manager
        try:
            import subprocess
            self.root.update_idletasks()
            self.root.after(100, self._set_wmctrl_name)
        except Exception:
            pass

        # Set window icon if available
        try:
            icon_path = Path(__file__).resolve().parents[5] / "assets" / "icon.png"
            if icon_path.exists():
                self.icon_image = tk.PhotoImage(file=str(icon_path))
                self.root.iconphoto(False, self.icon_image)
        except Exception as e:
            logging.debug(f"Could not set window icon: {e}")
        
        # Only set topmost for recall mode (view is normal window)
        if self.mode == "recall":
            self.root.attributes("-topmost", True)
        
        self.root.resizable(False, False)  # Not resizable but draggable
        self.root.configure(bg=self.colors["window_bg"])

        # Window positioning - different for recall vs view mode
        self.win_width = 450
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        if self.mode == "recall":
            # Recall mode: near cursor/destination app
            start_x = self.root.winfo_pointerx() - 50
            start_y = self.root.winfo_pointery() + 10
        else:
            # View mode: center horizontally, upper area
            start_x = int(screen_width * 0.5) - (self.win_width // 2)  # Center
            start_y = int(screen_height * 0.25)  # 25% from top
        
        self.root.geometry(f"{self.win_width}x150+{start_x}+{start_y}")

    def _create_fonts(self) -> None:
        """Create and store font objects."""
        self.font_mono_bold = tkfont.Font(size=11, weight="bold")
        self.font_tip = tkfont.Font(size=10)

    def _create_tooltip(self) -> None:
        """Initialize tooltip window with label."""
        self.tip_window = tk.Toplevel(self.root)
        self.tip_window.withdraw()
        self.tip_window.wm_overrideredirect(True)
        self.tip_window.wm_attributes("-topmost", True)
        
        # Set solid background color to prevent transparency issues
        self.tip_window.configure(bg=self.colors["tip_border"])
        
        card = tk.Frame(
            self.tip_window, bg=self.colors["tip_border"], padx=1, pady=1
        )
        card.pack(fill=tk.BOTH, expand=True)
        inner = tk.Frame(card, bg=self.colors["tip_bg"], padx=18, pady=16)
        inner.pack(fill=tk.BOTH, expand=True)
        self.tip_label = tk.Label(
            inner,
            text="",
            justify=tk.LEFT,
            fg=self.colors["tip_fg"],
            bg=self.colors["tip_bg"],
            font=self.font_tip,
            wraplength=400,
        )
        self.tip_label.pack(fill=tk.BOTH, expand=True)
        # Store reference to inner frame for minimum size enforcement in _show_copied_tooltip
        self.tip_inner = inner

    def _create_container(self) -> None:
        """Create main container frame."""
        self.container = tk.Frame(
            self.root, bg=self.colors["window_bg"], padx=18, pady=18
        )
        self.container.pack(fill=tk.BOTH, expand=True)

    def _create_search_bar(self) -> None:
        """Create search input and placeholder."""
        search_frame = tk.Frame(
            self.container,
            bg=self.colors["search_bg"],
            highlightthickness=1,
            highlightbackground=self.colors["search_border"],
        )
        search_frame.pack(fill=tk.X, pady=(0, 16))
        self.search_frame = search_frame

        self.search_var = tk.StringVar()
        self.entry = tk.Entry(
            search_frame,
            textvariable=self.search_var,
            borderwidth=0,
            highlightthickness=0,
            bg=self.colors["search_bg"],
            fg=self.colors["text_main"],
            insertbackground=self.colors["accent"],
            font=self.font_mono_bold,
            insertwidth=1,
        )
        self.entry.pack(fill=tk.X, padx=12, ipady=11)

        # Mode-specific placeholder
        if self.mode == "recall":
            placeholder_text = "🔍 Recall mode: search & paste"
        else:
            placeholder_text = "🔍 View mode: search & copy"
        
        self.placeholder_lbl = tk.Label(
            self.entry,
            text=placeholder_text,
            font=self.font_mono_bold,
            bg=self.colors["search_bg"],
            fg=self.colors["placeholder"],
            cursor="xterm",
        )
        self.placeholder_lbl.place(relx=0, rely=0.5, anchor="w")

        self.placeholder_lbl.bind("<Button-1>", self._activate_search)
        self.entry.bind("<Button-1>", self._activate_search)
        self.search_var.trace_add("write", self._update_ui)

    def _create_listbox(self) -> None:
        """Create results listbox."""
        self.listbox = tk.Listbox(
            self.container,
            bg=self.colors["window_bg"],
            fg=self.colors["text_dim"],
            font=self.font_mono_bold,
            borderwidth=0,
            highlightthickness=0,
            selectbackground=self.colors["item_highlight"],
            selectforeground=self.colors["accent"],
            activestyle="none",
        )
        self.listbox.pack(fill=tk.BOTH, expand=True)

    def _bind_events(self) -> None:
        """Bind all keyboard and mouse events."""
        self.root.bind("<Return>", lambda _: self._on_confirm())
        self.root.bind("<Escape>", lambda _: self._cleanup_and_close())
        
        # Only close on FocusOut in recall mode (view mode should stay open)
        if self.mode == "recall":
            self.root.bind(
                "<FocusOut>",
                lambda e: self._cleanup_and_close() if e.widget == self.root else None,
            )

        self.root.bind("<Up>", self._move_sel)
        self.root.bind("<Down>", self._move_sel)
        self.entry.bind("<Up>", self._move_sel)
        self.entry.bind("<Down>", self._move_sel)
        self.listbox.bind("<Up>", self._move_sel)
        self.listbox.bind("<Down>", self._move_sel)

        self.root.bind("<Key>", self._on_key_press)

        self.listbox.bind("<Motion>", self._on_motion)
        self.listbox.bind("<Leave>", lambda _: self._hide_tip())
        self.listbox.bind("<Button-1>", lambda _: self._on_confirm())

    def _activate_search(self, event=None) -> None:
        """Show search input."""
        self.placeholder_lbl.place_forget()
        self.entry.focus_set()
        self.search_frame.configure(highlightbackground=self.colors["search_focus"])

    def _deactivate_search(self) -> None:
        """Hide search input and show placeholder."""
        if not self.search_var.get():
            self.placeholder_lbl.place(relx=0, rely=0.5, anchor="w")
            self.search_frame.configure(
                highlightbackground=self.colors["search_border"]
            )
            self.listbox.focus_set()

    def _hide_tip(self, *_) -> None:
        """Hide tooltip and cancel scheduled callbacks."""
        try:
            if self.after_id and self.root.winfo_exists():
                self.root.after_cancel(self.after_id)
            self.after_id = None
        except tk.TclError:
            pass

        if self.tip_window:
            try:
                if self.tip_window.winfo_exists():
                    self.tip_window.withdraw()
            except tk.TclError:
                pass
        self.last_tip_index = -1

    def _show_tip(self, text: str, idx: int) -> None:
        """Display tooltip for item at index."""
        if idx == self.last_tip_index or not text:
            return
        try:
            if not self.root.winfo_exists() or not self.listbox.winfo_exists():
                return
        except tk.TclError:
            return

        self._hide_tip()
        self.last_tip_index = idx
        self.tip_label.config(text=text)
        self.root.update_idletasks()
        pos_x = self.root.winfo_x() + self.root.winfo_width() + 4
        pos_y = self.root.winfo_y()
        self.tip_window.wm_geometry(f"+{pos_x}+{pos_y}")
        self.tip_window.deiconify()
        self.after_id = self.root.after(5000, self._hide_tip)

    def _update_ui(self, *_) -> None:
        """Update listbox based on search query."""
        self._hide_tip()
        query = self.search_var.get()

        if len(query) == 0:
            self._deactivate_search()
        else:
            self.placeholder_lbl.place_forget()

        self.listbox.delete(0, tk.END)
        query_vec = None

        if query.strip() and self.vectorizer:
            try:
                query_vec = asyncio.run(self.vectorizer(query.strip()))
            except Exception:
                pass

        # Call shared search logic
        self.visible_nodes = hybrid_search(
            query.strip(), self.nodes, query_vec, self.vector_model_id
        )
        for n in self.visible_nodes[:15]:
            self.listbox.insert(tk.END, f" »  {self._truncate(n.content, 35)}")

        if self.listbox.size() > 0:
            self.listbox.selection_set(0)
            if query.strip():
                self._show_tip(self.visible_nodes[0].content, 0)

        # Resize window
        rows = min(self.listbox.size(), 8) if self.listbox.size() > 0 else 1
        new_h = 95 + (rows * 32)
        self.root.geometry(f"{self.win_width}x{int(new_h)}")

    def _move_sel(self, event) -> str:
        """Move selection up/down in listbox."""
        try:
            if not self.listbox.winfo_exists():
                return "break"
        except tk.TclError:
            return "break"

        if not self.listbox.size():
            return "break"

        curr = self.listbox.curselection()
        idx = curr[0] if curr else 0

        if event.keysym == "Up":
            idx = max(0, idx - 1)
        else:
            idx = min(self.listbox.size() - 1, idx + 1)

        self.listbox.selection_clear(0, tk.END)
        self.listbox.selection_set(idx)
        self.listbox.see(idx)
        self._show_tip(self.visible_nodes[idx].content, idx)
        return "break"

    def _on_key_press(self, event) -> None:
        """Activate search on any printable key press."""
        if len(event.char) > 0 and ord(event.char) >= 32:
            self._activate_search()

    def _on_motion(self, e) -> None:
        """Handle mouse hover over listbox."""
        try:
            if not self.listbox.winfo_exists():
                return
        except tk.TclError:
            return

        self.listbox.selection_clear(0, tk.END)
        idx = self.listbox.nearest(e.y)
        if idx >= 0:
            self.listbox.selection_set(idx)
            bbox = self.listbox.bbox(idx)
            if bbox and bbox[1] <= e.y <= bbox[1] + bbox[3]:
                self._show_tip(self.visible_nodes[idx].content, idx)
            else:
                self._hide_tip()

    def _on_confirm(self) -> None:
        """Handle selection confirmation."""
        if self.listbox.curselection():
            idx = self.listbox.curselection()[0]
            self.selected_value = self.visible_nodes[idx].content
            
            if self.mode == "recall":
                # Recall mode: hide window first to release focus, then close
                try:
                    self.root.withdraw()
                    self.root.update_idletasks()
                except:
                    pass
                self._cleanup_and_close()
            else:
                # View mode: copy to clipboard here, show feedback, don't close
                try:
                    self.clipboard.set_text(self.selected_value)
                    self._show_copied_tooltip(self.selected_value)
                except Exception as e:
                    logging.error(f"Failed to copy to clipboard: {e}")
                # Clear selection for next copy
                self.listbox.selection_clear(0, tk.END)
                # Clear selected_value so it won't be returned if window is closed
                self.selected_value = None

    def _show_copied_tooltip(self, content: str) -> None:
        """Show 'Copied to clipboard' banner above the tooltip."""
        try:
            # Check if tooltip is currently visible
            is_visible = self.tip_window.winfo_viewable()
            
            # If not visible, show it at normal position first
            if not is_visible and self.listbox.curselection():
                idx = self.listbox.curselection()[0]
                item_bbox = self.listbox.bbox(idx)
                if item_bbox:
                    list_x = self.listbox.winfo_rootx()
                    list_y = self.listbox.winfo_rooty()
                    tip_x = list_x + self.listbox.winfo_width() + 10
                    tip_y = list_y + item_bbox[1]
                    self.tip_window.geometry(f"+{tip_x}+{tip_y}")
                
                truncated = content[:200] + "..." if len(content) > 200 else content
                self.tip_label.config(text=truncated)
                self.tip_window.deiconify()
                self.root.update_idletasks()
            
            # Get tooltip position and size
            tip_x = self.tip_window.winfo_x()
            tip_y = self.tip_window.winfo_y()
            tip_width = self.tip_window.winfo_width()
            
            # Create banner window with transparency overlay on top line
            banner = tk.Toplevel(self.root)
            banner.withdraw()
            banner.overrideredirect(True)
            banner.attributes("-topmost", True)
            banner.attributes("-alpha", 0.9)  # 90% opaque
            
            # Banner frame spans tooltip width - darker blue
            banner_bg = "#1e40af"  # Darker blue
            banner_frame = tk.Frame(
                banner,
                bg=banner_bg,
                height=20
            )
            banner_frame.pack_propagate(False)
            banner_frame.pack(fill=tk.X)
            
            banner_label = tk.Label(
                banner_frame,
                text="Copied to clipboard",
                font=self.font_mono_bold,
                bg=banner_bg,
                fg="#ffffff",
                padx=5,
                pady=2
            )
            banner_label.pack(expand=True)
            
            # Position banner exactly on top line of tooltip
            banner.geometry(f"{tip_width}x20+{tip_x}+{tip_y}")
            banner.deiconify()
            
            # Flash tooltip border
            card = self.tip_window.winfo_children()[0]
            original_border = card.cget("bg")
            card.config(bg=self.colors["accent"])
            
            # Hide banner and reset border after 600ms
            def cleanup():
                banner.destroy()
                card.config(bg=original_border)
                if not is_visible:
                    self.tip_window.withdraw()
            
            self.tip_window.after(600, cleanup)
            
        except Exception as e:
            logging.warning(f"Could not show copied tooltip: {e}")

    def _cleanup_and_close(self) -> None:
        """Clean up and close windows safely."""
        try:
            # Unbind all events from root and children to prevent post-destruction handlers
            try:
                self.root.unbind_all("<Motion>")
                self.root.unbind_all("<Button-1>")
                self.root.unbind_all("<Return>")
                self.root.unbind_all("<Escape>")
                self.root.unbind_all("<FocusOut>")
                self.root.unbind_all("<Up>")
                self.root.unbind_all("<Down>")
                self.root.unbind_all("<Key>")
                self.root.unbind_all("<Leave>")
            except:
                pass
            
            # Cancel any pending after() callbacks
            try:
                if self.after_id:
                    self.root.after_cancel(self.after_id)
                    self.after_id = None
            except:
                pass
            
            # In recall mode, disable topmost on ALL windows to let target app get focus for paste
            if self.mode == "recall":
                for win in TkinterAdapter._active_windows:
                    try:
                        if win.winfo_exists():
                            win.attributes("-topmost", False)
                    except:
                        pass
                if self.root and self.root.winfo_exists():
                    self.root.update_idletasks()
            
            # In view mode on close, reset selected_value to None so nothing is returned
            if self.mode == "view":
                self.selected_value = None
            
            self._hide_tip()
            if self.tip_window and self.tip_window.winfo_exists():
                self.tip_window.destroy()
            if self.root and self.root.winfo_exists():
                self.root.destroy()
        except (tk.TclError, AttributeError):
            pass
