"""
core.py - Moteur de surveillance des processus et de gestion de la
Rich Presence Discord.

Ce module ne contient aucune interface graphique : il expose une
classe RPCMonitor pilotable par l'application (fenêtre + icône de
zone de notification) et des fonctions de chargement/sauvegarde de
la configuration JSON.
"""

import json
import threading
import time
from pathlib import Path

import psutil
from pypresence import Presence

# Dossier de l'application (là où se trouve ce fichier), pour que la
# config reste à côté du script même si l'app est lancée depuis
# ailleurs (raccourci, démarrage Windows, etc.)
APP_DIR = Path(__file__).resolve().parent
CONFIG_DIR = APP_DIR / "config"
CONFIG_PATH = CONFIG_DIR / "games.json"

DEFAULT_CONFIG = {
    "check_interval": 5,
    "start_with_windows": False,
    "dark_mode": False,
    "presences": [
        {
            "process": "scrcpy.exe",
            "client_id": "1540806713572065280",
            "details": "\u2b50 Global Dokkan Campaign 2026 \u2b50",
            "state": "Farm & Chill",
            "large_image": "dokkan",
            "large_text": "Dragon Ball Z Dokkan Battle",
            "enabled": True,
        }
    ],
}


def load_config() -> dict:
    """Charge la configuration JSON. La crée avec des valeurs par
    défaut si elle n'existe pas encore (premier lancement)."""
    if not CONFIG_PATH.exists():
        save_config(DEFAULT_CONFIG)
        return json.loads(json.dumps(DEFAULT_CONFIG))  # copie profonde

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    data.setdefault("check_interval", 5)
    data.setdefault("start_with_windows", False)
    data.setdefault("dark_mode", False)
    data.setdefault("presences", [])
    for p in data["presences"]:
        p.setdefault("enabled", True)
    return data


def save_config(data: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _running_process_names() -> set:
    names = set()
    for proc in psutil.process_iter(attrs=["name"]):
        try:
            if proc.info["name"]:
                names.add(proc.info["name"].lower())
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return names


def _find_active_presence(names: set, presences: list):
    for entry in presences:
        if not entry.get("enabled", True):
            continue
        if entry["process"].lower() in names:
            return entry
    return None


class RPCMonitor:
    """Surveille les processus configurés et pilote la connexion
    Discord RPC en conséquence. Tourne dans un thread dédié."""

    def __init__(self, on_status_change=None):
        self._thread = None
        self._stop_event = threading.Event()
        self._rpc = None
        self.current_entry = None  # entrée active (dict) ou None
        self.last_error = None
        self.on_status_change = on_status_change  # callback(entry_or_None)
        self._config_lock = threading.Lock()
        self._config = load_config()

    def reload_config(self):
        with self._config_lock:
            self._config = load_config()

    def get_config(self) -> dict:
        with self._config_lock:
            return self._config

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        self._disconnect()

    def _disconnect(self):
        if self._rpc is not None:
            try:
                self._rpc.clear()
                self._rpc.close()
            except Exception:
                pass
            self._rpc = None

    def _connect(self, entry: dict) -> Presence:
        rpc = Presence(entry["client_id"])
        rpc.connect()
        rpc.update(
            details=entry.get("details") or None,
            state=entry.get("state") or None,
            large_image=entry.get("large_image") or None,
            large_text=entry.get("large_text") or None,
            start=int(time.time()),
        )
        return rpc

    def _run(self):
        while not self._stop_event.is_set():
            with self._config_lock:
                interval = self._config.get("check_interval", 5)
                presences = list(self._config.get("presences", []))

            names = _running_process_names()
            active = _find_active_presence(names, presences)

            if active != self.current_entry:
                self._disconnect()
                self.last_error = None
                if active is not None:
                    try:
                        self._rpc = self._connect(active)
                    except Exception as e:
                        self.last_error = str(e)
                        active = None
                self.current_entry = active
                if self.on_status_change:
                    try:
                        self.on_status_change(active)
                    except Exception:
                        pass

            self._stop_event.wait(interval)
