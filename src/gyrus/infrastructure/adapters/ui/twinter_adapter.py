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
            "tip_border": "#334155"
        }

    def _truncate(self, text: str, max_chars: int) -> str:
        """Minimally clean and truncate text."""
        clean = text.replace("\n", " ").strip()
        clean = re.sub(r'\s+', ' ', clean)
        return (clean[:max_chars-3] + "...") if len(clean) > max_chars else clean

    def select_from_list(
        self,
        nodes: List[Any],
        vectorizer: Optional[Callable] = None,
        vector_model_id: str = "unknown"
    ) -> Optional[str]:
        if not nodes:
            return None

        self.selected_value = None
        self.last_tip_index = -1
        
        root = tk.Tk()
        root.title("🧠 Gyrus Recall")
        root.attributes('-topmost', True)
        root.configure(bg=self.colors["window_bg"])

        # Window positioning
        win_width = 450
        start_x = root.winfo_pointerx() - 50
        start_y = root.winfo_pointery() + 10
        root.geometry(f"{win_width}x150+{start_x}+{start_y}")
        
        font_mono_bold = tkfont.Font(family="Consolas", size=11, weight="bold")
        font_tip = tkfont.Font(family="Consolas", size=10)

        # Persistent Tooltip Window
        self.tip_window = tk.Toplevel(root)
        self.tip_window.withdraw()
        self.tip_window.wm_overrideredirect(True)
        self.tip_window.wm_attributes("-topmost", True)
        
        card = tk.Frame(self.tip_window, bg=self.colors["tip_border"], padx=1, pady=1)
        card.pack()
        inner = tk.Frame(card, bg=self.colors["tip_bg"], padx=18, pady=16)
        inner.pack()
        self.tip_label = tk.Label(inner, text="", justify=tk.LEFT, fg=self.colors["tip_fg"],
                                  bg=self.colors["tip_bg"], font=font_tip, wraplength=400)
        self.tip_label.pack()

        def hide_tip(*_):
            if self.after_id:
                root.after_cancel(self.after_id)
                self.after_id = None
            if self.tip_window:
                try:
                    self.tip_window.withdraw()
                except tk.TclError:
                    pass
            self.last_tip_index = -1

        def show_tip(text, idx):
            if idx == self.last_tip_index or not text:
                return
            hide_tip()
            self.last_tip_index = idx
            self.tip_label.config(text=text)
            root.update_idletasks()
            pos_x = root.winfo_x() + root.winfo_width() + 4
            pos_y = root.winfo_y()
            self.tip_window.wm_geometry(f"+{pos_x}+{pos_y}")
            self.tip_window.deiconify() 
            self.after_id = root.after(5000, hide_tip)

        container = tk.Frame(root, bg=self.colors["window_bg"], padx=15, pady=15)
        container.pack(fill=tk.BOTH, expand=True)

        # Search Bar UI
        search_frame = tk.Frame(container, bg=self.colors["search_bg"],
                                highlightthickness=1, highlightbackground=self.colors["search_border"])
        search_frame.pack(fill=tk.X, pady=(0, 14))

        search_var = tk.StringVar()
        entry = tk.Entry(search_frame, textvariable=search_var, borderwidth=0,
                         highlightthickness=0, bg=self.colors["search_bg"], 
                         fg=self.colors["text_main"], insertbackground=self.colors["accent"], 
                         font=font_mono_bold, insertwidth=1)
        entry.pack(fill=tk.X, padx=10, ipady=10)

        # Placeholder Label
        placeholder_text = "🔍 Search or select..."
        placeholder_lbl = tk.Label(entry, text=placeholder_text, 
                                  font=font_mono_bold, bg=self.colors["search_bg"], 
                                  fg=self.colors["placeholder"], cursor="xterm")
        placeholder_lbl.place(relx=0, rely=0.5, anchor="w")

        def activate_search(event=None):
            placeholder_lbl.place_forget()
            entry.focus_set()
            search_frame.configure(highlightbackground=self.colors["search_focus"])

        def deactivate_search():
            if not search_var.get():
                placeholder_lbl.place(relx=0, rely=0.5, anchor="w")
                search_frame.configure(highlightbackground=self.colors["search_border"])
                listbox.focus_set()

        placeholder_lbl.bind("<Button-1>", activate_search)
        entry.bind("<Button-1>", activate_search)
        
        listbox = tk.Listbox(container, bg=self.colors["window_bg"], fg=self.colors["text_dim"],
                             font=font_mono_bold, borderwidth=0, highlightthickness=0,
                             selectbackground=self.colors["item_highlight"],
                             selectforeground=self.colors["accent"], activestyle='none')
        listbox.pack(fill=tk.BOTH, expand=True)

        def update_ui(*_):
            hide_tip()
            query = search_var.get()
            if len(query) == 0:
                deactivate_search()
            else:
                placeholder_lbl.place_forget()

            listbox.delete(0, tk.END)
            query_vec = None
            if query.strip() and vectorizer:
                try:
                    query_vec = asyncio.run(vectorizer(query.strip()))
                except Exception:
                    pass

            # Call shared logic
            self.visible_nodes = hybrid_search(query.strip(), nodes, query_vec, vector_model_id)
            for n in self.visible_nodes[:15]:
                listbox.insert(tk.END, f" »  {self._truncate(n.content, 35)}")

            if listbox.size() > 0:
                listbox.selection_set(0)
                if query.strip():
                    show_tip(self.visible_nodes[0].content, 0)
            
            rows = min(listbox.size(), 8) if listbox.size() > 0 else 1
            new_h = 95 + (rows * 32) 
            root.geometry(f"{win_width}x{int(new_h)}")

        search_var.trace_add("write", update_ui)
        
        def on_confirm(e=None):
            if listbox.curselection():
                idx = listbox.curselection()[0]
                self.selected_value = self.visible_nodes[idx].content
                root.destroy()

        # Keyboard Bindings
        root.bind("<Return>", on_confirm)
        root.bind("<Escape>", lambda _: root.destroy())
        root.bind("<FocusOut>", lambda e: root.destroy() if e.widget == root else None)
        
        def move_sel(event):
            if not listbox.size():
                return "break"
            curr = listbox.curselection()
            idx = curr[0] if curr else 0
            
            if event.keysym == "Up":
                idx = max(0, idx - 1)
            else:
                idx = min(listbox.size() - 1, idx + 1)
                
            listbox.selection_clear(0, tk.END)
            listbox.selection_set(idx)
            listbox.see(idx)
            show_tip(self.visible_nodes[idx].content, idx)
            return "break"

        root.bind("<Up>", move_sel)
        root.bind("<Down>", move_sel)
        entry.bind("<Up>", move_sel)
        entry.bind("<Down>", move_sel)
        listbox.bind("<Up>", move_sel)
        listbox.bind("<Down>", move_sel)
        
        def on_key_press(event):
            if len(event.char) > 0 and ord(event.char) >= 32:
                activate_search()

        root.bind("<Key>", on_key_press)

        # Mouse Hover events
        listbox.bind("<Motion>", lambda e: [
            listbox.selection_clear(0, tk.END),
            listbox.selection_set(idx := listbox.nearest(e.y)),
            show_tip(self.visible_nodes[idx].content, idx)
            if listbox.bbox(idx) and listbox.bbox(idx)[1] <= e.y <= listbox.bbox(idx)[1] + listbox.bbox(idx)[3]
            else hide_tip()
        ])
        listbox.bind("<Leave>", hide_tip)
        listbox.bind("<Button-1>", on_confirm)

        update_ui()
        listbox.focus_set()
        
        root.mainloop()
        return self.selected_value