"""Tests des préférences utilisateur persistées dans un fichier temporaire."""

import tomllib

import pytest

from linux_copilot.core.config import load_config
from linux_copilot.core.errors import ConfigurationError
from linux_copilot.core.preferences import (
    AIPreferences,
    DisplayPreferences,
    SecurityPreferences,
    UserPreferences,
    load_preferences,
    reset_preferences,
    set_preference,
)
from linux_copilot.distros import SystemInfo


def test_missing_file_uses_french_defaults(tmp_path) -> None:
    prefs = load_preferences(tmp_path / "missing.toml")

    assert prefs == UserPreferences()
    assert prefs.language == "fr"
    assert prefs.security.confirmation_required is True


@pytest.mark.parametrize(
    ("locale_value", "expected"),
    [("fr_FR.UTF-8", "fr"), ("en_US.UTF-8", "en"), ("de_DE.UTF-8", "fr")],
)
def test_auto_language_uses_system_locale(tmp_path, monkeypatch, locale_value, expected) -> None:
    monkeypatch.setenv("LC_ALL", locale_value)
    monkeypatch.delenv("LC_MESSAGES", raising=False)
    monkeypatch.delenv("LANG", raising=False)
    path = tmp_path / "config.toml"
    path.write_text('[preferences]\nlanguage = "auto"\n', encoding="utf-8")

    assert load_preferences(path).resolved_language == expected


def test_loads_typed_preferences_and_updates_core_config(tmp_path) -> None:
    path = tmp_path / "config.toml"
    path.write_text(
        '[app]\nname = "Test Copilot"\n'
        '[preferences]\nlanguage = "en"\n'
        '[preferences.display]\nlayout = "compact"\nshow_sources = false\n'
        '[preferences.ai]\nenabled = true\nprovider = "ollama"\nmode = "local"\nmodel = "small-model"\n'
        '[preferences.security]\nprudence = "standard"\n',
        encoding="utf-8",
    )

    prefs = load_preferences(path)
    system_info = SystemInfo("fedora", "Fedora Linux 43", "43", "dnf", "x86_64", "3.13")
    config = load_config(path, system_info=system_info)

    assert prefs.language == "en"
    assert prefs.display == DisplayPreferences(layout="compact", show_sources=False)
    assert prefs.ai == AIPreferences(enabled=True, provider="ollama", model="small-model")
    assert prefs.security == SecurityPreferences(prudence="standard")
    assert config.name == "Test Copilot"
    assert config.language == "en"


@pytest.mark.parametrize("mode", ["local", "ollama", "auto"])
def test_ai_modes_are_valid_preferences(tmp_path, mode) -> None:
    prefs = set_preference("ai.mode", mode, tmp_path / "config.toml")

    assert prefs.ai.mode == mode


def test_set_preference_persists_and_preserves_other_config(tmp_path) -> None:
    path = tmp_path / "config.toml"
    path.write_text(
        '[app]\nname = "Existing App"\nversion = "0.1"\n'
        '[other]\nflag = true\nitems = [{ name = "kept" }]\n',
        encoding="utf-8",
    )

    set_preference("ai.enabled", True, path)
    set_preference("display.layout", "compact", path)
    reloaded = load_preferences(path)
    settings = tomllib.loads(path.read_text(encoding="utf-8"))

    assert reloaded.ai.enabled is True
    assert reloaded.display.layout == "compact"
    assert settings["app"] == {"name": "Existing App", "version": "0.1"}
    assert settings["other"] == {"flag": True, "items": [{"name": "kept"}]}
    assert path.stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("language", "de"),
        ("display.layout", "wide"),
        ("display.colors", "yes"),
        ("ai.max_tokens", 0),
        ("ai.temperature", 3.0),
        ("ai.mode", "remote"),
        ("security.prudence", "reckless"),
        ("security.confirmation_required", False),
        ("ai.api_key", "must-not-be-saved"),
        ("unknown.preference", True),
    ],
)
def test_invalid_preferences_are_rejected_without_writing(tmp_path, name, value) -> None:
    path = tmp_path / "config.toml"

    with pytest.raises(ConfigurationError):
        set_preference(name, value, path)

    assert not path.exists()


def test_file_validation_rejects_corruption_and_disabled_confirmation(tmp_path) -> None:
    path = tmp_path / "config.toml"
    path.write_text(
        "[preferences.security]\nconfirmation_required = false\n",
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError, match="confirmation"):
        load_preferences(path)

    path.write_text("[preferences\n", encoding="utf-8")
    with pytest.raises(ConfigurationError, match="TOML invalide"):
        load_preferences(path)


def test_reset_restores_defaults_and_keeps_app_settings(tmp_path) -> None:
    path = tmp_path / "config.toml"
    path.write_text(
        '[app]\nname = "Keep This"\n'
        '[preferences]\nlanguage = "en"\n'
        "[preferences.ai]\nenabled = true\n"
        "[preferences.security]\nallow_command_execution = true\n",
        encoding="utf-8",
    )

    reset = reset_preferences(path)
    reloaded = load_preferences(path)
    settings = tomllib.loads(path.read_text(encoding="utf-8"))

    assert reset == UserPreferences()
    assert reloaded == UserPreferences()
    assert settings["app"]["name"] == "Keep This"
    assert reloaded.security.confirmation_required is True
    assert reloaded.security.allow_command_execution is False


def test_security_execution_preference_never_removes_confirmation(tmp_path) -> None:
    path = tmp_path / "config.toml"
    prefs = set_preference("security.allow_command_execution", True, path)

    assert prefs.security.allow_command_execution is True
    assert prefs.security.confirmation_required is True
    assert load_preferences(path).security.confirmation_required is True
    with pytest.raises(ConfigurationError, match="confirmation"):
        SecurityPreferences(confirmation_required=False)
