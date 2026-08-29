"""
app.pyw - Interface graphique + icône de zone de notification pour
Discord Rich Presence Manager.

Lancement portable :
    double-clic sur app.pyw (Windows associe .pyw à pythonw.exe)
    ou : pythonw.exe app.pyw
"""

import os
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

import core
import winstartup

APP_TITLE = "Discord Rich Presence Manager"
APP_DIR = Path(__file__).resolve().parent
SCRIPT_PATH = os.path.abspath(__file__)
ICON_PATH = APP_DIR / "discord_rpm.ico"

# File d'attente utilisée pour transmettre en toute sécurité des
# actions déclenchées depuis le thread de l'icône système ou le
# thread de surveillance, vers le thread principal (Tkinter).
ui_queue = queue.Queue()

tray_icon = None  # instance pystray, assignée dans main()


# ---------------------------------------------------------------
# Thèmes clair / sombre
# ---------------------------------------------------------------
THEMES = {
    "light": {
        "bg": "#f4f5f7",
        "surface": "#ffffff",
        "fg": "#1c1c1e",
        "muted": "#6b6f76",
        "entry_bg": "#ffffff",
        "border": "#dcdfe3",
        "accent": "#5865F2",
        "accent_hover": "#4752C4",
        "tree_bg": "#ffffff",
        "tree_fg": "#1c1c1e",
        "tree_heading_bg": "#e7e8ec",
        "tree_heading_fg": "#33353b",
        "tree_selected": "#5865F2",
        "status_ok": "#2b8a3e",
        "status_off": "#6b6f76",
    },
    "dark": {
        "bg": "#1e1f22",
        "surface": "#2b2d31",
        "fg": "#e7e7e8",
        "muted": "#9a9ca0",
        "entry_bg": "#232428",
        "border": "#3a3c41",
        "accent": "#5865F2",
        "accent_hover": "#707bf5",
        "tree_bg": "#2b2d31",
        "tree_fg": "#e7e7e8",
        "tree_heading_bg": "#3a3c41",
        "tree_heading_fg": "#e7e7e8",
        "tree_selected": "#5865F2",
        "status_ok": "#57d16b",
        "status_off": "#9a9ca0",
    },
}

FONT_FAMILY = "Segoe UI"


def _set_window_icon(window):
    if ICON_PATH.exists():
        try:
            window.iconbitmap(str(ICON_PATH))
        except Exception:
            pass


class ThemeManager:
    """Centralise l'application d'une palette clair/sombre sur le
    style ttk global et sur les widgets qui ne suivent pas ttk
    (fenêtres tk brutes, Treeview)."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.style = ttk.Style(root)
        self.style.theme_use("clam")
        self.mode = "light"
        self._status_widgets = []  # (widget, dict d'états -> couleur) enregistrés pour maj

    def apply(self, mode: str):
        self.mode = mode
        p = THEMES[mode]
        s = self.style

        self.root.configure(bg=p["bg"])

        s.configure("TFrame", background=p["bg"])
        s.configure("Surface.TFrame", background=p["surface"])
        s.configure("TLabelframe", background=p["bg"], foreground=p["fg"], bordercolor=p["border"])
        s.configure("TLabelframe.Label", background=p["bg"], foreground=p["fg"], font=(FONT_FAMILY, 10, "bold"))
        s.configure("TLabel", background=p["bg"], foreground=p["fg"], font=(FONT_FAMILY, 10))
        s.configure("Muted.TLabel", background=p["bg"], foreground=p["muted"], font=(FONT_FAMILY, 9))
        s.configure("Title.TLabel", background=p["bg"], foreground=p["fg"], font=(FONT_FAMILY, 15, "bold"))
        s.configure(
            "TButton",
            background=p["accent"],
            foreground="#ffffff",
            font=(FONT_FAMILY, 9, "bold"),
            padding=(10, 6),
            borderwidth=0,
            focuscolor=p["accent"],
        )
        s.map(
            "TButton",
            background=[("active", p["accent_hover"]), ("disabled", p["border"])],
            foreground=[("disabled", p["muted"])],
        )
        s.configure(
            "Secondary.TButton",
            background=p["surface"],
            foreground=p["fg"],
            bordercolor=p["border"],
            padding=(10, 6),
        )
        s.map("Secondary.TButton", background=[("active", p["border"])])
        s.configure("TCheckbutton", background=p["bg"], foreground=p["fg"], font=(FONT_FAMILY, 10))
        s.map("TCheckbutton", background=[("active", p["bg"])])
        s.configure(
            "TEntry",
            fieldbackground=p["entry_bg"],
            foreground=p["fg"],
            insertcolor=p["fg"],
            bordercolor=p["border"],
        )
        s.configure(
            "TSpinbox",
            fieldbackground=p["entry_bg"],
            foreground=p["fg"],
            arrowsize=14,
            bordercolor=p["border"],
        )
        s.configure(
            "Treeview",
            background=p["tree_bg"],
            foreground=p["tree_fg"],
            fieldbackground=p["tree_bg"],
            rowheight=28,
            font=(FONT_FAMILY, 9),
            borderwidth=0,
        )
        s.configure(
            "Treeview.Heading",
            background=p["tree_heading_bg"],
            foreground=p["tree_heading_fg"],
            font=(FONT_FAMILY, 9, "bold"),
            relief="flat",
        )
        s.map("Treeview.Heading", background=[("active", p["border"])])
        s.map(
            "Treeview",
            background=[("selected", p["tree_selected"])],
            foreground=[("selected", "#ffffff")],
        )

        for widget, kind in self._status_widgets:
            self._apply_to_extra(widget, kind, p)

    def register_toplevel(self, window: tk.Toplevel):
        """Applique le fond de thème à une fenêtre secondaire (les
        Toplevel ne suivent pas ttk pour leur propre fond)."""
        window.configure(bg=THEMES[self.mode]["bg"])

    def register_status_label(self, widget: ttk.Label):
        self._status_widgets.append((widget, "status"))

    def _apply_to_extra(self, widget, kind, palette):
        pass  # emplacement réservé si d'autres widgets custom sont ajoutés


# ---------------------------------------------------------------
# Boîte de dialogue d'ajout / édition d'une entrée
# ---------------------------------------------------------------
class PresenceEditorDialog(tk.Toplevel):
    FIELDS = [
        ("process", "Exécutable (ex : jeu.exe)"),
        ("client_id", "Client ID Discord"),
        ("details", "Ligne 1 (details)"),
        ("state", "Ligne 2 (state)"),
        ("large_image", "Clé image (large_image)"),
        ("large_text", "Texte au survol de l'image"),
    ]

    def __init__(self, parent, theme: ThemeManager, entry=None):
        super().__init__(parent)
        self.title("Modifier la présence" if entry else "Nouvelle présence")
        self.resizable(False, False)
        self.result = None
        self.transient(parent)
        self.grab_set()
        theme.register_toplevel(self)
        _set_window_icon(self)

        container = ttk.Frame(self, padding=16)
        container.pack(fill="both", expand=True)

        entry = entry or {}
        self.vars = {}

        for row, (key, label) in enumerate(self.FIELDS):
            ttk.Label(container, text=label).grid(row=row, column=0, sticky="w", padx=(0, 10), pady=6)
            var = tk.StringVar(value=str(entry.get(key, "")))
            ttk.Entry(container, textvariable=var, width=42).grid(row=row, column=1, pady=6)
            self.vars[key] = var

        self.enabled_var = tk.BooleanVar(value=entry.get("enabled", True))
        ttk.Checkbutton(container, text="Présence activée", variable=self.enabled_var).grid(
            row=len(self.FIELDS), column=0, columnspan=2, sticky="w", pady=(6, 0)
        )

        btn_frame = ttk.Frame(container)
        btn_frame.grid(row=len(self.FIELDS) + 1, column=0, columnspan=2, pady=(18, 0), sticky="e")
        ttk.Button(btn_frame, text="Annuler", style="Secondary.TButton", command=self.destroy).pack(
            side="left", padx=5
        )
        ttk.Button(btn_frame, text="Enregistrer", command=self._on_save).pack(side="left")

        self.bind("<Return>", lambda e: self._on_save())
        self.bind("<Escape>", lambda e: self.destroy())

        self._center_on_parent(parent)

    def _center_on_parent(self, parent):
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        try:
            px, py = parent.winfo_rootx(), parent.winfo_rooty()
            pw, ph = parent.winfo_width(), parent.winfo_height()
        except tk.TclError:
            px, py, pw, ph = 0, 0, self.winfo_screenwidth(), self.winfo_screenheight()

        x = px + (pw - w) // 2
        y = py + (ph - h) // 2

        # Garde la fenêtre visible même si la fenêtre principale est
        # proche d'un bord de l'écran.
        x = max(0, min(x, self.winfo_screenwidth() - w))
        y = max(0, min(y, self.winfo_screenheight() - h))

        self.geometry(f"+{x}+{y}")

    def _on_save(self):
        process = self.vars["process"].get().strip()
        client_id = self.vars["client_id"].get().strip()

        if not process:
            messagebox.showerror(APP_TITLE, "Le nom de l'exécutable est obligatoire.", parent=self)
            return
        if not process.lower().endswith(".exe"):
            if not messagebox.askyesno(
                APP_TITLE,
                f"'{process}' ne se termine pas par .exe, continuer quand même ?",
                parent=self,
            ):
                return
        if not client_id.isdigit():
            messagebox.showerror(
                APP_TITLE, "Le Client ID Discord doit être uniquement composé de chiffres.", parent=self
            )
            return

        self.result = {key: var.get().strip() for key, var in self.vars.items()}
        self.result["enabled"] = self.enabled_var.get()
        self.destroy()


# ---------------------------------------------------------------
# Fenêtre principale
# ---------------------------------------------------------------
class MainWindow:
    def __init__(self, root: tk.Tk, monitor: core.RPCMonitor):
        self.root = root
        self.monitor = monitor
        self.config_data = monitor.get_config()

        root.title(APP_TITLE)
        root.geometry("1000x650")
        root.minsize(780, 565)
        root.protocol("WM_DELETE_WINDOW", self.hide)
        root.bind("<Control-p>", lambda e: print(f"Taille actuelle : {root.winfo_width()}x{root.winfo_height()}"))
        _set_window_icon(root)

        self.theme = ThemeManager(root)
        self.theme.apply("dark" if self.config_data.get("dark_mode") else "light")

        self._build_widgets()
        self._refresh_list()
        self._poll_queue()

    # --- construction de l'UI -----------------------------------
    def _build_widgets(self):
        outer = ttk.Frame(self.root, padding=18)
        outer.pack(fill="both", expand=True)

        header = ttk.Frame(outer)
        header.pack(fill="x", pady=(0, 14))
        ttk.Label(header, text=APP_TITLE, style="Title.TLabel").pack(side="left")

        self.dark_var = tk.BooleanVar(value=self.config_data.get("dark_mode", False))
        ttk.Checkbutton(
            header,
            text="Mode sombre",
            variable=self.dark_var,
            command=self._toggle_theme,
        ).pack(side="right")

        presences_box = ttk.Labelframe(outer, text="Présences surveillées", padding=12)
        presences_box.pack(fill="both", expand=True)

        list_row = ttk.Frame(presences_box)
        list_row.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(list_row, columns=("process", "name", "state"), show="headings", height=10)
        self.tree.heading("process", text="Exécutable")
        self.tree.heading("name", text="Nom affiché")
        self.tree.heading("state", text="Statut")
        self.tree.column("process", width=160)
        self.tree.column("name", width=300)
        self.tree.column("state", width=90, anchor="center")
        self.tree.pack(fill="both", expand=True, side="left")
        self.tree.bind("<Double-1>", lambda e: self._edit_selected())

        btns = ttk.Frame(list_row)
        btns.pack(side="left", fill="y", padx=(12, 0))
        ttk.Button(btns, text="Ajouter", command=self._add).pack(fill="x", pady=2)
        ttk.Button(btns, text="Modifier", style="Secondary.TButton", command=self._edit_selected).pack(
            fill="x", pady=2
        )
        ttk.Button(btns, text="Supprimer", style="Secondary.TButton", command=self._delete_selected).pack(
            fill="x", pady=2
        )
        ttk.Button(btns, text="▲ Monter", style="Secondary.TButton", command=lambda: self._move(-1)).pack(
            fill="x", pady=(20, 2)
        )
        ttk.Button(btns, text="▼ Descendre", style="Secondary.TButton", command=lambda: self._move(1)).pack(
            fill="x", pady=2
        )

        ttk.Label(
            presences_box,
            text="L'ordre compte : si plusieurs applications surveillées tournent en même temps, la première de la liste l'emporte.",
            style="Muted.TLabel",
            wraplength=640,
        ).pack(fill="x", pady=(10, 0))

        settings_box = ttk.Labelframe(outer, text="Paramètres", padding=12)
        settings_box.pack(fill="x", pady=(14, 0))

        ttk.Label(settings_box, text="Intervalle de vérification (secondes)").grid(row=0, column=0, sticky="w")
        self.interval_var = tk.IntVar(value=self.config_data.get("check_interval", 5))
        ttk.Spinbox(settings_box, from_=2, to=60, textvariable=self.interval_var, width=5).grid(
            row=0, column=1, sticky="w", padx=(10, 30)
        )

        self.startup_var = tk.BooleanVar(value=winstartup.is_enabled())
        ttk.Checkbutton(
            settings_box,
            text="Démarrer automatiquement avec Windows",
            variable=self.startup_var,
            command=self._toggle_startup,
        ).grid(row=0, column=2, sticky="w")

        ttk.Button(settings_box, text="Enregistrer", command=self._save_all).grid(
            row=0, column=3, sticky="e", padx=(30, 0)
        )
        settings_box.columnconfigure(3, weight=1)

        status_box = ttk.Frame(outer, padding=(0, 14, 0, 0))
        status_box.pack(fill="x")
        self.status_var = tk.StringVar(value="Aucune présence active")
        self.status_label = ttk.Label(status_box, textvariable=self.status_var, style="Muted.TLabel")
        self.status_label.pack(anchor="w")

    # --- utilitaires liste ---------------------------------------
    def _refresh_list(self):
        self.tree.delete(*self.tree.get_children())
        for i, entry in enumerate(self.config_data["presences"]):
            state = "Activée" if entry.get("enabled", True) else "Désactivée"
            self.tree.insert("", "end", iid=str(i), values=(entry["process"], entry.get("large_text", ""), state))

    def _selected_index(self):
        sel = self.tree.selection()
        if not sel:
            return None
        return int(sel[0])

    def _add(self):
        dlg = PresenceEditorDialog(self.root, self.theme)
        self.root.wait_window(dlg)
        if dlg.result:
            self.config_data["presences"].append(dlg.result)
            self._refresh_list()

    def _edit_selected(self):
        idx = self._selected_index()
        if idx is None:
            return
        dlg = PresenceEditorDialog(self.root, self.theme, entry=self.config_data["presences"][idx])
        self.root.wait_window(dlg)
        if dlg.result:
            self.config_data["presences"][idx] = dlg.result
            self._refresh_list()

    def _delete_selected(self):
        idx = self._selected_index()
        if idx is None:
            return
        entry = self.config_data["presences"][idx]
        if messagebox.askyesno(APP_TITLE, f"Supprimer '{entry['process']}' ?"):
            del self.config_data["presences"][idx]
            self._refresh_list()

    def _move(self, direction):
        idx = self._selected_index()
        if idx is None:
            return
        new_idx = idx + direction
        presences = self.config_data["presences"]
        if 0 <= new_idx < len(presences):
            presences[idx], presences[new_idx] = presences[new_idx], presences[idx]
            self._refresh_list()
            self.tree.selection_set(str(new_idx))

    def _toggle_startup(self):
        try:
            winstartup.set_enabled(self.startup_var.get(), SCRIPT_PATH)
        except Exception as e:
            messagebox.showerror(APP_TITLE, f"Impossible de modifier le démarrage automatique :\n{e}")
            self.startup_var.set(not self.startup_var.get())

    def _toggle_theme(self):
        mode = "dark" if self.dark_var.get() else "light"
        self.theme.apply(mode)
        self.config_data["dark_mode"] = self.dark_var.get()
        core.save_config(self.config_data)

    def _save_all(self):
        self.config_data["check_interval"] = int(self.interval_var.get())
        self.config_data["start_with_windows"] = self.startup_var.get()
        self.config_data["dark_mode"] = self.dark_var.get()
        core.save_config(self.config_data)
        self.monitor.reload_config()
        messagebox.showinfo(APP_TITLE, "Configuration enregistrée.")

    # --- affichage / statut ---------------------------------------
    def show(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def hide(self):
        self.root.withdraw()

    def _poll_queue(self):
        try:
            while True:
                action, payload = ui_queue.get_nowait()
                if action == "show":
                    self.show()
                elif action == "status":
                    palette = THEMES[self.theme.mode]
                    if payload:
                        self.status_var.set(
                            f"● Présence active pour {payload['process']} ({payload.get('large_text', '')})"
                        )
                        self.status_label.configure(foreground=palette["status_ok"])
                    else:
                        self.status_var.set("Aucune présence active")
                        self.status_label.configure(foreground=palette["status_off"])
                elif action == "quit":
                    self._quit()
        except queue.Empty:
            pass
        self.root.after(200, self._poll_queue)

    def _quit(self):
        self.monitor.stop()
        if tray_icon is not None:
            try:
                tray_icon.stop()
            except Exception:
                pass
        self.root.destroy()
        os._exit(0)


# ---------------------------------------------------------------
# Icône de la zone de notification (pystray)
# ---------------------------------------------------------------
def _load_tray_image():
    from PIL import Image, ImageDraw

    if ICON_PATH.exists():
        try:
            return Image.open(str(ICON_PATH))
        except Exception:
            pass

    # Repli si discord_rpm.ico est absent : icône générée à la volée.
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse((4, 4, 60, 60), fill=(88, 101, 242, 255))
    draw.ellipse((20, 24, 30, 34), fill=(255, 255, 255, 255))
    draw.ellipse((34, 24, 44, 34), fill=(255, 255, 255, 255))
    draw.arc((18, 30, 46, 50), start=20, end=160, fill=(255, 255, 255, 255), width=3)
    return img


def _build_tray_icon():
    import pystray

    def on_open(icon, item):
        ui_queue.put(("show", None))

    def on_quit(icon, item):
        ui_queue.put(("quit", None))

    menu = pystray.Menu(
        pystray.MenuItem("Ouvrir", on_open, default=True),
        pystray.MenuItem("Quitter", on_quit),
    )
    return pystray.Icon(APP_TITLE, _load_tray_image(), APP_TITLE, menu)


def _on_status_change(entry):
    ui_queue.put(("status", entry))


def main():
    global tray_icon

    monitor = core.RPCMonitor(on_status_change=_on_status_change)
    monitor.start()

    root = tk.Tk()
    MainWindow(root, monitor)
    root.withdraw()  # démarre réduit dans la zone de notification

    tray_icon = _build_tray_icon()
    threading.Thread(target=tray_icon.run, daemon=True).start()

    root.mainloop()


if __name__ == "__main__":
    main()
