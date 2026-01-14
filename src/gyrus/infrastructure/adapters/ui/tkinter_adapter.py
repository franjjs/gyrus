import asyncio
import re
import tkinter as tk
from tkinter import font as tkfont
from typing import Any, Callable, List, Optional

from gyrus.application.services import UIService
from gyrus.domain.search_logic import hybrid_search


class TkinterAdapter(UIService):
    """UI with docked tooltip and hybrid search integration."""

    def __init__(self):
        self.selected_value: Optional[str] = None
        self.visible_nodes: List[Any] = []
        self.tip_window = None
        self.tip_label = None
        self.after_id = None
        self.last_tip_index = -1
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

    def select_from_list(
        self,
        nodes: List[Any],
        vectorizer: Optional[Callable] = None,
        vector_model_id: str = "unknown",
    ) -> Optional[str]:
        """Main orchestrator for the UI flow."""
        if not nodes:
            return None

        self.selected_value = None
        self.last_tip_index = -1
        self.vectorizer = vectorizer
        self.vector_model_id = vector_model_id
        self.nodes = nodes

        # Setup
        self.root = tk.Tk()
        self._setup_window()
        self._create_fonts()
        self._create_tooltip()
        self._create_container()
        self._create_search_bar()
        self._create_listbox()
        self._bind_events()
        self._update_ui()  # Load initial items

        # Run
        self.root.mainloop()
        return self.selected_value

    # Private methods

    def _truncate(self, text: str, max_chars: int) -> str:
        """Minimally clean and truncate text."""
        clean = text.replace("\n", " ").strip()
        clean = re.sub(r"\s+", " ", clean)
        return (clean[: max_chars - 3] + "...") if len(clean) > max_chars else clean

    def _setup_window(self) -> None:
        """Initialize main window properties."""
        self.root.title("🧠 Gyrus Recall")
        self.root.attributes("-topmost", True)
        self.root.configure(bg=self.colors["window_bg"])

        # Window positioning
        self.win_width = 450
        start_x = self.root.winfo_pointerx() - 50
        start_y = self.root.winfo_pointery() + 10
        self.root.geometry(f"{self.win_width}x150+{start_x}+{start_y}")

    def _create_fonts(self) -> None:
        """Create and store font objects."""
        self.font_mono_bold = tkfont.Font(family="Consolas", size=11, weight="bold")
        self.font_tip = tkfont.Font(family="Consolas", size=10)

    def _create_tooltip(self) -> None:
        """Initialize tooltip window with label."""
        self.tip_window = tk.Toplevel(self.root)
        self.tip_window.withdraw()
        self.tip_window.wm_overrideredirect(True)
        self.tip_window.wm_attributes("-topmost", True)

        card = tk.Frame(
            self.tip_window, bg=self.colors["tip_border"], padx=1, pady=1
        )
        card.pack()
        inner = tk.Frame(card, bg=self.colors["tip_bg"], padx=18, pady=16)
        inner.pack()
        self.tip_label = tk.Label(
            inner,
            text="",
            justify=tk.LEFT,
            fg=self.colors["tip_fg"],
            bg=self.colors["tip_bg"],
            font=self.font_tip,
            wraplength=400,
        )
        self.tip_label.pack()

    def _create_container(self) -> None:
        """Create main container frame."""
        self.container = tk.Frame(
            self.root, bg=self.colors["window_bg"], padx=15, pady=15
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
        search_frame.pack(fill=tk.X, pady=(0, 14))
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
        self.entry.pack(fill=tk.X, padx=10, ipady=10)

        # Placeholder
        placeholder_text = "🔍 Search or select..."
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
        self._cleanup_and_close()

    def _cleanup_and_close(self) -> None:
        """Clean up and close windows safely."""
        try:
            self._hide_tip()
            if self.tip_window and self.tip_window.winfo_exists():
                self.tip_window.destroy()
            if self.root.winfo_exists():
                self.root.destroy()
        except tk.TclError:
            pass
