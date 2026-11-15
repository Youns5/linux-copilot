"""Tests des alias CLI finaux et du diagnostic en mode hors ligne."""

from linux_copilot.ai.base import OllamaStatus
from linux_copilot.cli import app as cli_app
from linux_copilot.cli import commands as cli_commands
from linux_copilot.core.paths import get_app_paths
from linux_copilot.core.preferences import UserPreferences
from linux_copilot.distros import SystemInfo
from linux_copilot.search.engine import CommandSearch
from linux_copilot.snippets.loader import load_catalog


class OfflineOllama:
    def status(self) -> OllamaStatus:
        return OllamaStatus(installed=False, running=False, error="service arrêté")


def test_search_alias_runs_local_query(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        cli_app,
        "detect_system",
        lambda: SystemInfo("fedora", "Fedora Linux 43", "43", "dnf", "x86_64", "3.13"),
    )
    monkeypatch.setattr(cli_app, "load_preferences", UserPreferences)
    monkeypatch.setattr(cli_app, "CommandSearch", lambda: CommandSearch(load_catalog()))
    monkeypatch.setattr(cli_app, "OllamaClient", OfflineOllama)

    assert cli_app.main(["search", "wifi", "--limit", "1"]) == 0
    assert "Commande : nmcli device wifi list" in capsys.readouterr().out


def test_list_alias_shows_local_categories(capsys) -> None:
    assert cli_app.main(["list"]) == 0
    assert "Réseau" in capsys.readouterr().out


def test_doctor_reports_core_health_without_ollama(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli_commands, "load_preferences", UserPreferences)
    monkeypatch.setattr(cli_commands, "get_app_paths", get_app_paths)
    monkeypatch.setattr(
        cli_commands,
        "detect_system",
        lambda: SystemInfo("fedora", "Fedora", "43", "dnf", "x86_64", "3.13"),
    )
    monkeypatch.setattr(cli_commands, "OllamaClient", OfflineOllama)

    assert cli_app.main(["doctor"]) == 0
    output = capsys.readouterr().out
    snippet_count = len(load_catalog().snippets)
    assert f"OK Bibliothèque : {snippet_count} snippets" in output
    assert "OK Distribution : Fedora" in output
    assert "Ollama : indisponible" in output
