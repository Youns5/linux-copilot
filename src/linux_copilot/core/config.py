"""Configuration centrale, surchargeable par un fichier TOML utilisateur."""

from __future__ import annotations

import tomllib
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from linux_copilot import __version__
from linux_copilot.core.errors import (
    ConfigurationError,
    ResourceNotFoundError,
)
from linux_copilot.core.paths import AppPaths, get_app_paths
from linux_copilot.distros.base import SystemInfo


@dataclass(frozen=True, slots=True)
class AppConfig:
    """Etat de configuration partagé par les modules de l'application."""

    name: str
    version: str
    language: str
    distribution: SystemInfo
    paths: AppPaths
    ai_available: bool = False
    preferences: Mapping[str, object] = field(default_factory=dict)


def load_config(
    config_path: Path | str | None = None,
    *,
    paths: AppPaths | None = None,
    system_info: SystemInfo | None = None,
    ai_available: bool = False,
) -> AppConfig:
    """Charger les préférences TOML et compléter l'état détecté à l'exécution.

    Un fichier de configuration par défaut absent est normal; un chemin fourni
    explicitement doit, lui, exister.
    """
    app_paths = paths or get_app_paths()
    selected_path = Path(config_path) if config_path is not None else app_paths.config_file
    settings = _read_settings(selected_path, required=config_path is not None)

    app_settings = settings.get("app", {})
    preferences = settings.get("preferences", {})
    if not isinstance(app_settings, dict):
        raise ConfigurationError("La section [app] doit être une table TOML.")
    if not isinstance(preferences, dict):
        raise ConfigurationError("La section [preferences] doit être une table TOML.")

    name = _read_string(app_settings, "name", "Linux Copilot")
    version = _read_string(app_settings, "version", __version__)
    language = _read_string(app_settings, "language", "fr")
    from linux_copilot.core.preferences import preferences_from_settings

    user_preferences = preferences_from_settings(settings, fallback_language=language)

    detected_system = system_info
    if detected_system is None:
        from linux_copilot.distros import detect_system

        detected_system = detect_system()

    return AppConfig(
        name=name,
        version=version,
        language=user_preferences.resolved_language,
        distribution=detected_system,
        paths=app_paths,
        ai_available=ai_available,
        preferences=dict(preferences),
    )


def _read_settings(path: Path, *, required: bool) -> dict[str, object]:
    try:
        content = path.read_text(encoding="utf-8")
    except FileNotFoundError as error:
        if required:
            raise ResourceNotFoundError(f"Fichier de configuration introuvable : {path}") from error
        return {}
    except OSError as error:
        raise ConfigurationError("Impossible de lire le fichier de configuration.") from error

    try:
        settings = tomllib.loads(content)
    except tomllib.TOMLDecodeError as error:
        raise ConfigurationError(f"Syntaxe TOML invalide dans {path}.") from error
    return settings


def _read_string(settings: dict[str, object], key: str, default: str) -> str:
    value = settings.get(key, default)
    if not isinstance(value, str) or not value.strip():
        raise ConfigurationError(f"La valeur app.{key} doit être un texte non vide.")
    return value.strip()
