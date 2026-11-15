"""Interfaces centrales partagées par les modules de Linux Copilot."""

from linux_copilot.core.config import AppConfig, load_config
from linux_copilot.core.paths import AppPaths, get_app_paths
from linux_copilot.core.preferences import (
    AIPreferences,
    DisplayPreferences,
    SecurityPreferences,
    UserPreferences,
    load_preferences,
    reset_preferences,
    set_preference,
)

__all__ = [
    "AIPreferences",
    "AppConfig",
    "AppPaths",
    "DisplayPreferences",
    "SecurityPreferences",
    "UserPreferences",
    "get_app_paths",
    "load_config",
    "load_preferences",
    "reset_preferences",
    "set_preference",
]
