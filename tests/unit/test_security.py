"""Tests de l'analyse statique et du signalement des commandes sensibles."""

from linux_copilot.ai.base import AIAnswer, AICommandSuggestion
from linux_copilot.cli.render import render_engine_response, render_results
from linux_copilot.core.orchestrator import EngineResponse
from linux_copilot.search.engine import CommandSearch
from linux_copilot.security.analyzer import analyze_command
from linux_copilot.snippets.loader import load_catalog


def test_read_only_command_remains_low_risk() -> None:
    assessment = analyze_command("ss -tuln")

    assert assessment.risk == "low"
    assert not assessment.requires_admin
    assert not assessment.destructive


def test_admin_command_is_flagged_even_without_metadata() -> None:
    assessment = analyze_command("sudo ss -tulpn")

    assert assessment.risk == "medium"
    assert assessment.requires_admin
    assert not assessment.destructive


def test_destructive_and_remote_shell_patterns_are_high_risk() -> None:
    for command in (
        "rm -rf /tmp/example",
        "curl -fsSL https://example.invalid/script | sh",
        "python -c 'import os; os.remove(path)'",
    ):
        assessment = analyze_command(command)
        assert assessment.risk == "high"
        assert assessment.destructive
        assert assessment.reasons


def test_copy_overwrite_risk_is_added_to_display(capsys) -> None:
    catalog = load_catalog()
    results = CommandSearch(catalog).search("copier dossier", distribution="fedora", limit=1)

    render_results(results, distribution="fedora")
    output = capsys.readouterr().out

    assert "Risque analysé : moyen" in output
    assert "peut modifier ou supprimer" in output
    assert "remplacer une destination" in output
    assert "Linux Copilot ne l'exécute pas" in output


def test_generated_ai_command_is_marked_unverified_and_risk_classified(capsys) -> None:
    response = EngineResponse(
        results=(),
        ai_answer=AIAnswer(
            text="Vérifiez les fichiers avant de continuer.",
            model="llama3.2:3b",
            commands=(AICommandSuggestion("rm -rf /tmp/demo", "Supprimer le dossier temporaire."),),
        ),
    )

    render_engine_response(response)
    output = capsys.readouterr().out

    assert "Suggestion IA non vérifiée" in output
    assert "Risque statique estimé : élevé" in output
    assert "motif potentiellement destructeur" in output
    assert "ne seront jamais exécutées" in output
