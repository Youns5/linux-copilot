"""Tests du catalogue local, de sa validation et de sa recherche."""

import json
from dataclasses import asdict

import pytest

from linux_copilot.cli import app as cli_app
from linux_copilot.core.errors import (
    ResourceNotFoundError,
    SnippetValidationError,
    UnknownDistributionError,
)
from linux_copilot.core.preferences import UserPreferences
from linux_copilot.distros import SystemInfo
from linux_copilot.search.engine import CommandSearch
from linux_copilot.snippets.loader import SnippetCatalog, load_catalog
from linux_copilot.snippets.validation import validate_snippet


@pytest.fixture(scope="module")
def catalog() -> SnippetCatalog:
    return load_catalog()


def test_default_catalog_has_over_one_hundred_valid_snippets(catalog) -> None:
    assert len(catalog.snippets) >= 100
    assert len({snippet.id for snippet in catalog.snippets}) == len(catalog.snippets)
    assert len(catalog.categories) >= 14


def test_every_snippet_has_sources_commands_and_effect_metadata(catalog) -> None:
    for snippet in catalog.snippets:
        assert snippet.title and snippet.description and snippet.explanation
        assert snippet.keywords and snippet.distributions and snippet.commands
        assert snippet.sources and snippet.risk in {"low", "medium", "high"}
        assert isinstance(snippet.requires_admin, bool)
        assert isinstance(snippet.destructive, bool)


@pytest.mark.parametrize(
    ("query", "expected_id", "distribution"),
    [
        ("installer Brave", "fedora-install-brave", "fedora"),
        ("voir les ports ouverts", "network-open-ports", "fedora"),
        ("mettre à jour Fedora", "fedora-refresh-upgrade", "fedora"),
        ("trouver les fichiers volumineux", "files-find-large", "debian"),
        ("configurer une connexion SSH", "network-ssh-config-alias", "fedora"),
    ],
)
def test_french_natural_queries_rank_expected_result(
    catalog, query, expected_id, distribution
) -> None:
    results = CommandSearch(catalog).search(query, distribution=distribution)

    assert results
    assert results[0].snippet.id == expected_id


def test_distribution_filter_excludes_incompatible_variants(catalog) -> None:
    results = CommandSearch(catalog).search("mettre à jour Fedora", distribution="debian")

    assert all(
        "linux" in result.snippet.distributions or "debian" in result.snippet.distributions
        for result in results
    )
    assert all(result.snippet.id != "fedora-refresh-upgrade" for result in results)


def test_search_returns_multiple_results_and_handles_no_match(catalog) -> None:
    search = CommandSearch(catalog)
    assert len(search.search("ports ouverts", distribution="fedora", limit=3)) >= 2
    assert search.search("demande sans correspondance connue xyz987") == []


def test_keyword_search_and_category_filter(catalog) -> None:
    search = CommandSearch(catalog)
    results = search.search_keyword("ssh", distribution="fedora")

    assert results
    assert search.search("ports ouverts", category="Réseau", distribution="fedora")
    assert search.search("ports ouverts", category="Git et GitHub", distribution="fedora") == []


def test_validator_rejects_bad_risk_sources_and_distributions(catalog) -> None:
    record = json.loads(json.dumps(asdict(catalog.snippets[0])))
    for key, value in (
        ("risk", "unknown"),
        ("sources", ["file:///etc/passwd"]),
        ("distributions", ["unknown-linux"]),
    ):
        invalid = dict(record)
        invalid[key] = value
        with pytest.raises(SnippetValidationError):
            validate_snippet(invalid)


def test_loader_reports_missing_directory_and_duplicate_ids(tmp_path, catalog) -> None:
    with pytest.raises(ResourceNotFoundError):
        load_catalog(tmp_path / "missing")

    first = asdict(catalog.snippets[0])
    second = asdict(catalog.snippets[1])
    second["id"] = first["id"]
    (tmp_path / "duplicates.json").write_text(
        json.dumps([first, second], ensure_ascii=False), encoding="utf-8"
    )
    with pytest.raises(SnippetValidationError, match="dupliqué"):
        load_catalog(tmp_path)


def test_cli_displays_command_explanation_risk_sources_and_no_execution(
    catalog, monkeypatch, capsys
) -> None:
    monkeypatch.setattr(
        cli_app,
        "detect_system",
        lambda: SystemInfo("fedora", "Fedora Linux", "43", "dnf", "x86_64", "3.13"),
    )
    monkeypatch.setattr(cli_app, "CommandSearch", lambda: CommandSearch(catalog))
    monkeypatch.setattr(cli_app, "load_preferences", UserPreferences)

    status = cli_app.main(["voir les ports ouverts"])
    output = capsys.readouterr().out

    assert status == 0
    assert "Commande : ss -tuln" in output
    assert "Explication :" in output
    assert (
        "Compatibilité : toutes les distributions Linux; distribution détectée : Fedora" in output
    )
    assert "Risque : faible" in output
    assert "https://man7.org/linux/man-pages/man8/ss.8.html" in output
    assert "ne l'exécute pas" in output


def test_cli_lists_categories(catalog, monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli_app, "load_catalog", lambda: catalog)

    assert cli_app.main(["categories"]) == 0
    assert "Réseau" in capsys.readouterr().out


def test_unknown_distribution_cli_only_shows_generic_snippets(catalog, monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        cli_app,
        "detect_system",
        lambda: (_ for _ in ()).throw(UnknownDistributionError("test unknown")),
    )
    monkeypatch.setattr(cli_app, "load_preferences", UserPreferences)
    monkeypatch.setattr(cli_app, "CommandSearch", lambda: CommandSearch(catalog))

    status = cli_app.main(["mettre à jour Fedora"])
    output = capsys.readouterr()

    assert status in {0, 1}
    assert "Distribution non reconnue" in output.err
    assert "sudo dnf upgrade --refresh" not in output.out
    assert (
        "Compatibilité : toutes les distributions Linux" in output.out
        or "Aucune commande fiable" in output.out
    )


@pytest.mark.parametrize(
    "query",
    [
        "installer Spotify",
        "commande installation Spotify",
    ],
)
def test_search_rejects_unrelated_results_for_unknown_software(catalog, query) -> None:
    results = CommandSearch(catalog).search(query, distribution="fedora")

    assert results == []
