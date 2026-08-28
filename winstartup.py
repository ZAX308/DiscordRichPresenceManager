"""
winstartup.py - Gestion du démarrage automatique avec Windows via la
clé de registre "Run" de l'utilisateur courant (HKEY_CURRENT_USER),
donc sans avoir besoin de droits administrateur ni de tâche
planifiée.
"""

import os
import sys

try:
    import winreg
except ImportError:  # pragma: no cover - environnement non-Windows
    winreg = None

RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "AutoRichPresenceDiscord"


def _pythonw_command(script_path: str) -> str:
    """Construit la commande pythonw.exe "app.pyw" à écrire dans le
    registre, à partir de l'interpréteur qui exécute ce code."""
    exe = sys.executable
    if exe.lower().endswith("python.exe"):
        candidate = exe[: -len("python.exe")] + "pythonw.exe"
        if os.path.exists(candidate):
            exe = candidate
    return f'"{exe}" "{script_path}"'


def is_enabled() -> bool:
    if winreg is None:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_READ) as key:
            winreg.QueryValueEx(key, APP_NAME)
            return True
    except FileNotFoundError:
        return False


def set_enabled(enabled: bool, script_path: str) -> None:
    if winreg is None:
        raise RuntimeError("Le démarrage automatique n'est disponible que sous Windows.")
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_SET_VALUE) as key:
        if enabled:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, _pythonw_command(script_path))
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass
