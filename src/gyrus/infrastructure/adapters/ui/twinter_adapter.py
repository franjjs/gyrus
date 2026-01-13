import difflib
import re
import tkinter as tk
from tkinter import font as tkfont
from typing import List, Optional

from gyrus.application.services import UIService


class TkinterAdapter(UIService):
    def __init__(self):
        self.selected_value = None
        self.colors = {
            "bg": "#ffffff",
            "entry_bg": "#f8fafc",
            "placeholder": "#94a3b8",
            "fg": "#334155",
            "accent": "#3b82f6",
            "select_bg": "#eff6ff",
            "border": "#e2e8f0",
            "tooltip_bg": "#1e293b",
            "tooltip_fg": "#ffffff"
        }

    def _sanitize(self, text: str) -> str:
        clean = text.replace("\n", " ").strip()
        return re.sub(r'\s+', ' ', clean)[:60]

    def select_from_list(self, items: List[str]) -> Optional[str]:
        if not items:
            return None
        self.original_map = {self._sanitize(it): it for it in items}
        clean_items = list(self.original_map.keys())
        
        self.selected_value = None
        root = tk.Tk()
        root.withdraw()
        root.title("🧠 Gyrus Recall")
        root.attributes('-topmost', True)
        root.tk.call('wm', 'attributes', '.', '-type', 'dialog')
        root.configure(bg=self.colors["bg"])

        # Posición inicial basada en el puntero
        self.start_x = root.winfo_pointerx() - 50
        self.start_y = root.winfo_pointery() + 10

        family = "Sans Serif"
        families = set(tkfont.families())
        for f in ["Segoe UI", "Ubuntu", "Inter", "Helvetica"]:
            if f in families:
                family = f
                break
        
        font_items = tkfont.Font(family=family, size=11, weight="bold")
        font_entry = tkfont.Font(family=family, size=10)

        # --- TOOLTIP ---
        self.tip_window = None
        def hide_tip():
            if self.tip_window:
                try:
                    self.tip_window.destroy()
                except tk.TclError:
                    pass
                self.tip_window = None

        def show_tip(text):
            hide_tip()
            if not text:
                return
            try:
                self.tip_window = tk.Toplevel(root)
                self.tip_window.wm_overrideredirect(True)
                self.tip_window.wm_attributes("-topmost", True)
                self.tip_window.wm_geometry(f"+{root.winfo_pointerx()+25}+{root.winfo_pointery()+15}")
                tk.Label(self.tip_window, text=text, justify=tk.LEFT, background=self.colors["tooltip_bg"], 
                         foreground=self.colors["tooltip_fg"], relief=tk.FLAT, padx=15, pady=12, 
                         font=font_entry, wraplength=450).pack()
            except tk.TclError:
                pass

        # --- INTERFAZ ---
        container = tk.Frame(root, bg=self.colors["bg"], padx=20, pady=20)
        container.pack(fill=tk.BOTH, expand=True)

        # BUSCADOR
        search_var = tk.StringVar()
        search_frame = tk.Frame(container, bg=self.colors["entry_bg"], highlightthickness=1, 
                                highlightbackground=self.colors["border"], highlightcolor=self.colors["accent"])
        search_frame.pack(fill=tk.X, pady=(0, 15))

        placeholder_label = tk.Label(search_frame, text="Search in items...", bg=self.colors["entry_bg"], 
                                     fg=self.colors["placeholder"], font=font_entry)
        placeholder_label.place(x=10, y=8)

        entry = tk.Entry(search_frame, textvariable=search_var, bg=self.colors["entry_bg"], 
                         fg=self.colors["fg"], insertbackground=self.colors["accent"],
                         insertwidth=0, font=font_entry, borderwidth=0, relief="flat", highlightthickness=0)
        entry.pack(fill=tk.X, padx=10, ipady=8)

        # LISTA
        listbox = tk.Listbox(container, bg=self.colors["bg"], fg=self.colors["fg"],
                             font=font_items, borderwidth=0, highlightthickness=0,
                             selectbackground=self.colors["select_bg"],
                             selectforeground=self.colors["accent"],
                             activestyle='none', height=0)
        listbox.pack(fill=tk.BOTH, expand=True)

        def update_ui(*args):
            query = search_var.get().lower()
            if query:
                placeholder_label.place_forget()
            else:
                placeholder_label.place(x=10, y=8)
            
            listbox.delete(0, tk.END)
            matches = difflib.get_close_matches(query, clean_items, n=15, cutoff=0.1) if query else clean_items
            if query and not matches:
                matches = [it for it in clean_items if query in it.lower()]
            for it in matches:
                listbox.insert(tk.END, f" › {it}")
            
            if listbox.size() > 0:
                listbox.selection_clear(0, tk.END)
                listbox.selection_set(0)
                listbox.activate(0)
            
            visible_rows = min(listbox.size(), 8) if listbox.size() > 0 else 1
            new_h = 40 + 50 + 15 + (visible_rows * 28)
            root.geometry(f"500x{int(new_h)}+{self.start_x}+{self.start_y}")

        def move_selection(event):
            if listbox.size() == 0:
                return "break"
            current = listbox.curselection()
            idx = current[0] if current else 0
            
            if event.keysym == "Up":
                idx = max(0, idx - 1)
            else:
                idx = min(listbox.size() - 1, idx + 1)
            
            listbox.selection_clear(0, tk.END)
            listbox.selection_set(idx)
            listbox.activate(idx) 
            listbox.see(idx)
            
            try:
                clean_txt = listbox.get(idx).replace(" › ", "").strip()
                show_tip(self.original_map.get(clean_txt, clean_txt))
            except (tk.TclError, IndexError):
                pass
            return "break"

        def on_confirm(event=None):
            # Si es clic, obtener el ítem bajo el ratón
            if event and hasattr(event, 'y') and event.widget == listbox:
                idx = listbox.nearest(event.y)
                listbox.selection_clear(0, tk.END)
                listbox.selection_set(idx)

            selection = listbox.curselection()
            if selection:
                idx = selection[0]
                clean_txt = listbox.get(idx).replace(" › ", "").strip()
                self.selected_value = self.original_map.get(clean_txt)
            
            close_window()

        def on_cancel(event=None):
            """Cierra la ventana sin devolver ningún valor (cancelación)"""
            self.selected_value = None
            close_window()

        def close_window():
            hide_tip()
            if root.winfo_exists():
                root.grab_release()
                root.destroy()

        def on_mouse_move(event):
            idx = listbox.nearest(event.y)
            if idx >= 0:
                listbox.selection_clear(0, tk.END)
                listbox.selection_set(idx)
                listbox.activate(idx)
                try:
                    clean_txt = listbox.get(idx).replace(" › ", "").strip()
                    show_tip(self.original_map.get(clean_txt, clean_txt))
                except (tk.TclError, IndexError):
                    pass

        # Bindings
        search_var.trace_add("write", update_ui)
        listbox.bind("<Motion>", on_mouse_move)
        listbox.bind("<Button-1>", on_confirm)
        
        # ESCAPE y CLIC FUERA cancelan
        root.bind("<Escape>", on_cancel)
        root.bind("<FocusOut>", lambda e: on_cancel() if e.widget == root else None)
        
        root.bind("<Return>", on_confirm)
        entry.bind("<Up>", move_selection)
        entry.bind("<Down>", move_selection)
        entry.bind("<FocusIn>", lambda e: [placeholder_label.place_forget(), entry.config(insertwidth=2)])

        update_ui()
        root.deiconify()
        root.after(150, lambda: [root.focus_force(), entry.focus_set(), root.grab_set()])
        root.mainloop()
        
        return self.selected_value