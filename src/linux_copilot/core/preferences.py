"""Préférences utilisateur validées et persistées dans le fichier TOML XDG."""

from __future__ import annotations

import json
import locale
import math
import os
import re
import tempfile
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, time
from pathlib import Path

from linux_copilot.core.config import _read_settings
from linux_copilot.core.errors import ConfigurationError
from linux_copilot.core.paths import get_app_paths

_LANGUAGES = {"fr", "en", "auto"}
_LAYOUTS = {"compact", "detailed"}
_DETAIL_LEVELS = {"brief", "normal", "detailed"}
_AI_MODES = {"local", "ollama", "auto"}
_PRUDENCE_LEVELS = {"low", "standard", "high"}
_PREFERENCE_FIELDS = {
    "language": None,
    "display.colors": ("display", "colors"),
    "display.layout": ("display", "layout"),
    "display.show_explanations": ("display", "show_explanations"),
    "display.show_sources": ("display", "show_sources"),
    "display.detail_level": ("display", "detail_level"),
    "ai.enabled": ("ai", "enabled"),
    "ai.provider": ("ai", "provider"),
    "ai.mode": ("ai", "mode"),
    "ai.model": ("ai", "model"),
    "ai.max_tokens": ("ai", "max_tokens"),
    "ai.temperature": ("ai", "temperature"),
    "security.confirmation_required": ("security", "confirmation_required"),
    "security.prudence": ("security", "prudence"),
    "security.show_warnings": ("security", "show_warnings"),
    "security.allow_command_execution": ("security", "allow_command_execution"),
}


@dataclass(frozen=True, slots=True)
class DisplayPreferences:
    colors: bool = True
    layout: str = "detailed"
    show_explanations: bool = True
    show_sources: bool = True
    detail_level: str = "normal"


@dataclass(frozen=True, slots=True)
class AIPreferences:
    """Préférences IA locale; le fournisseur n'est pas activé par défaut."""

    enabled: bool = False
    provider: str = "ollama"
    mode: str = "local"
    model: str = ""
    max_tokens: int = 2048
    temperature: float = 0.2


@dataclass(frozen=True, slots=True)
class SecurityPreferences:
    """Préférences de prudence; la confirmation reste une règle obligatoire."""

    confirmation_required: bool = True
    prudence: str = "high"
    show_warnings: bool = True
    allow_command_execution: bool = False

    def __post_init__(self) -> None:
        if self.confirmation_required is not True:
            raise ConfigurationError(
                "La confirmation avant une opération sensible est obligatoire."
            )


@dataclass(frozen=True, slots=True)
class UserPreferences:
    """Préférences complètes et validées d'un utilisateur local."""

    language: str = "fr"
    display: DisplayPreferences = field(default_factory=DisplayPreferences)
    ai: AIPreferences = field(default_factory=AIPreferences)
    security: SecurityPreferences = field(default_factory=SecurityPreferences)

    @property
    def resolved_language(self) -> str:
        """Résoudre `auto` en français ou anglais à partir de la locale système."""
        return resolve_language(self.language)

    def to_dict(self) -> dict[str, object]:
        """Retourner une représentation adaptée à l'affichage ou au diagnostic."""
        return asdict(self)


def resolve_language(language: str) -> str:
    """Limiter la langue effective au français ou à l'anglais."""
    if language in {"fr", "en"}:
        return language
    candidates = [os.environ.get("LC_ALL"), os.environ.get("LC_MESSAGES"), os.environ.get("LANG")]
    try:
        candidates.append(locale.getlocale(locale.LC_MESSAGES)[0])
    except (AttributeError, ValueError):
        pass
    for candidate in candidates:
        if candidate:
            language_code = (
                candidate.split(".", 1)[0]
                .split("@", 1)[0]
                .replace("-", "_")
                .split("_", 1)[0]
                .lower()
            )
            if language_code in {"fr", "en"}:
                return language_code
    return "fr"


def load_preferences(config_path: Path | str | None = None) -> UserPreferences:
    """Lire les préférences; l'absence du fichier signifie les valeurs par défaut."""
    path = Path(config_path) if config_path is not None else get_app_paths().config_file
    settings = _read_settings(path, required=False)
    return preferences_from_settings(settings)


def set_preference(
    name: str,
    value: object,
    config_path: Path | str | None = None,
) -> UserPreferences:
    """Valider puis enregistrer une préférence sans écraser les autres sections."""
    if name not in _PREFERENCE_FIELDS:
        raise ConfigurationError(f"Préférence inconnue : {name}.")
    if name == "security.confirmation_required" and value is not True:
        raise ConfigurationError("La confirmation avant une opération sensible est obligatoire.")

    path = Path(config_path) if config_path is not None else get_app_paths().config_file
    settings = _read_settings(path, required=False)
    preference_table = settings.setdefault("preferences", {})
    if not isinstance(preference_table, dict):
        raise ConfigurationError("La section [preferences] doit être une table TOML.")

    destination = _PREFERENCE_FIELDS[name]
    if destination is None:
        preference_table["language"] = value
    else:
        section_name, key = destination
        section = preference_table.setdefault(section_name, {})
        if not isinstance(section, dict):
            raise ConfigurationError(
                f"La section [preferences.{section_name}] doit être une table TOML."
            )
        section[key] = value

    updated = preferences_from_settings(settings)
    _write_settings(path, settings)
    return updated


def reset_preferences(config_path: Path | str | None = None) -> UserPreferences:
    """Restaurer toutes les préférences par défaut en conservant les autres réglages."""
    path = Path(config_path) if config_path is not None else get_app_paths().config_file
    settings = _read_settings(path, required=False)
    settings["preferences"] = UserPreferences().to_dict()
    defaults = preferences_from_settings(settings)
    _write_settings(path, settings)
    return defaults


def preferences_from_settings(
    settings: Mapping[str, object],
    *,
    fallback_language: str | None = None,
) -> UserPreferences:
    """Valider les tables de préférences lues depuis le fichier central."""
    app_settings = settings.get("app", {})
    raw = settings.get("preferences", {})
    if not isinstance(app_settings, dict):
        raise ConfigurationError("La section [app] doit être une table TOML.")
    if not isinstance(raw, dict):
        raise ConfigurationError("La section [preferences] doit être une table TOML.")
    _reject_unknown_keys(raw, {"language", "display", "ai", "security", "color"}, "preferences")

    legacy_language = fallback_language or app_settings.get("language", "fr")
    language = _string(raw.get("language", legacy_language), "language")
    if language not in _LANGUAGES:
        raise ConfigurationError("La langue doit être 'fr', 'en' ou 'auto'.")

    display_raw = _section(raw, "display")
    legacy_color = raw.get("color", True)
    if "colors" not in display_raw and "color" in raw:
        display_raw["colors"] = legacy_color
    _reject_unknown_keys(
        display_raw,
        {"colors", "layout", "show_explanations", "show_sources", "detail_level"},
        "preferences.display",
    )
    display = DisplayPreferences(
        colors=_boolean(display_raw.get("colors", True), "display.colors"),
        layout=_choice(display_raw.get("layout", "detailed"), "display.layout", _LAYOUTS),
        show_explanations=_boolean(
            display_raw.get("show_explanations", True), "display.show_explanations"
        ),
        show_sources=_boolean(display_raw.get("show_sources", True), "display.show_sources"),
        detail_level=_choice(
            display_raw.get("detail_level", "normal"), "display.detail_level", _DETAIL_LEVELS
        ),
    )

    ai_raw = _section(raw, "ai")
    _reject_unknown_keys(
        ai_raw,
        {"enabled", "provider", "mode", "model", "max_tokens", "temperature"},
        "preferences.ai",
    )
    provider = _string(ai_raw.get("provider", "ollama"), "ai.provider", allow_empty=False)
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}", provider):
        raise ConfigurationError("Le fournisseur IA doit être un identifiant simple.")
    ai = AIPreferences(
        enabled=_boolean(ai_raw.get("enabled", False), "ai.enabled"),
        provider=provider,
        mode=_choice(ai_raw.get("mode", "local"), "ai.mode", _AI_MODES),
        model=_string(ai_raw.get("model", ""), "ai.model"),
        max_tokens=_integer(ai_raw.get("max_tokens", 2048), "ai.max_tokens", 1, 128000),
        temperature=_number(ai_raw.get("temperature", 0.2), "ai.temperature", 0.0, 2.0),
    )

    security_raw = _section(raw, "security")
    _reject_unknown_keys(
        security_raw,
        {"confirmation_required", "prudence", "show_warnings", "allow_command_execution"},
        "preferences.security",
    )
    confirmation = _boolean(
        security_raw.get("confirmation_required", True), "security.confirmation_required"
    )
    if not confirmation:
        raise ConfigurationError("La confirmation avant une opération sensible est obligatoire.")
    security = SecurityPreferences(
        confirmation_required=True,
        prudence=_choice(
            security_raw.get("prudence", "high"), "security.prudence", _PRUDENCE_LEVELS
        ),
        show_warnings=_boolean(security_raw.get("show_warnings", True), "security.show_warnings"),
        allow_command_execution=_boolean(
            security_raw.get("allow_command_execution", False),
            "security.allow_command_execution",
        ),
    )
    return UserPreferences(language=language, display=display, ai=ai, security=security)


def _section(table: dict[str, object], name: str) -> dict[str, object]:
    value = table.get(name, {})
    if not isinstance(value, dict):
        raise ConfigurationError(f"La section [preferences.{name}] doit être une table TOML.")
    return dict(value)


def _reject_unknown_keys(table: dict[str, object], allowed: set[str], section: str) -> None:
    unknown = sorted(set(table) - allowed)
    if unknown:
        raise ConfigurationError(f"Option inconnue dans {section} : {unknown[0]}.")


def _string(value: object, name: str, *, allow_empty: bool = True) -> str:
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        raise ConfigurationError(f"La valeur {name} doit être un texte valide.")
    return value.strip()


def _boolean(value: object, name: str) -> bool:
    if not isinstance(value, bool):
        raise ConfigurationError(f"La valeur {name} doit être vraie ou fausse.")
    return value


def _choice(value: object, name: str, choices: set[str]) -> str:
    selected = _string(value, name)
    if selected not in choices:
        allowed = ", ".join(sorted(choices))
        raise ConfigurationError(f"La valeur {name} doit être parmi : {allowed}.")
    return selected


def _integer(value: object, name: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ConfigurationError(
            f"La valeur {name} doit être un entier entre {minimum} et {maximum}."
        )
    return value


def _number(value: object, name: str, minimum: float, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigurationError(
            f"La valeur {name} doit être un nombre entre {minimum} et {maximum}."
        )
    number = float(value)
    if not math.isfinite(number) or not minimum <= number <= maximum:
        raise ConfigurationError(
            f"La valeur {name} doit être un nombre entre {minimum} et {maximum}."
        )
    return number


def _write_settings(path: Path, settings: Mapping[str, object]) -> None:
    temporary_path: str | None = None
    try:
        serialized = _serialize_toml(settings)
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_path = temporary.name
            os.chmod(temporary_path, 0o600)
            temporary.write(serialized)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_path, path)
        path.chmod(0o600)
    except (OSError, TypeError, ValueError) as error:
        if temporary_path is not None:
            try:
                os.unlink(temporary_path)
            except FileNotFoundError:
                pass
            except OSError:
                pass
        raise ConfigurationError("Impossible d'enregistrer les préférences utilisateur.") from error


def _serialize_toml(settings: Mapping[str, object]) -> str:
    lines = _serialize_table(settings, ())
    return "\n".join(lines).rstrip() + "\n"


def _serialize_table(table: Mapping[str, object], path: tuple[str, ...]) -> list[str]:
    lines: list[str] = []
    if path:
        lines.append(f"[{'.'.join(_toml_key(part) for part in path)}]")
    for key, value in table.items():
        if not isinstance(value, dict):
            lines.append(f"{_toml_key(key)} = {_toml_value(value)}")
    for key, value in table.items():
        if isinstance(value, dict):
            if lines:
                lines.append("")
            lines.extend(_serialize_table(value, (*path, key)))
    return lines


def _toml_key(value: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9_-]+", value):
        return value
    return json.dumps(value, ensure_ascii=False)


def _toml_value(value: object) -> str:
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if math.isnan(value):
            return "nan"
        if math.isinf(value):
            return "-inf" if value < 0 else "inf"
        return repr(value)
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, list):
        return "[" + ", ".join(_toml_value(item) for item in value) + "]"
    if isinstance(value, dict):
        pairs = (f"{_toml_key(key)} = {_toml_value(item)}" for key, item in value.items())
        return "{ " + ", ".join(pairs) + " }"
    raise TypeError(f"Type TOML non pris en charge : {type(value).__name__}")
