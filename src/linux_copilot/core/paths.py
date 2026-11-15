"""Emplacements XDG et création des répertoires propres à l'application."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class AppPaths:
    """Chemins calculés une seule fois et partagés par les services."""

    config_dir: Path
    config_file: Path
    data_dir: Path
    snippets_dir: Path
    database_path: Path
    cache_dir: Path
    log_dir: Path

    def ensure_directories(self) -> AppPaths:
        """Créer les répertoires de l'application sans créer de fichier DB."""
        for directory in (
            self.config_dir,
            self.data_dir,
            self.snippets_dir,
            self.cache_dir,
            self.log_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)
        return self


def get_app_paths() -> AppPaths:
    """Calculer les chemins Linux en respectant les variables XDG absolues."""
    config_dir = _xdg_path("XDG_CONFIG_HOME", ".config") / "linux-copilot"
    data_dir = _xdg_path("XDG_DATA_HOME", ".local/share") / "linux-copilot"
    cache_dir = _xdg_path("XDG_CACHE_HOME", ".cache") / "linux-copilot"
    return AppPaths(
        config_dir=config_dir,
        config_file=config_dir / "config.toml",
        data_dir=data_dir,
        snippets_dir=data_dir / "snippets",
        database_path=data_dir / "linux-copilot.sqlite3",
        cache_dir=cache_dir,
        log_dir=cache_dir / "logs",
    )


def _xdg_path(variable: str, fallback: str) -> Path:
    configured = os.environ.get(variable)
    if configured:
        path = Path(configured).expanduser()
        if path.is_absolute():
            return path
    return Path.home() / fallback
