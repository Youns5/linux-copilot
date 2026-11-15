"""Affichage lisible des catégories et suggestions sans lancer de commandes."""

from __future__ import annotations

from linux_copilot.core.orchestrator import EngineResponse
from linux_copilot.search.engine import SearchResult
from linux_copilot.security.analyzer import analyze_command
from linux_copilot.security.risk import highest_risk
from linux_copilot.snippets.loader import SnippetCatalog

_RISK_LABELS = {"low": "faible", "medium": "moyen", "high": "élevé"}
_DISTRIBUTION_LABELS = {
    "fedora": "Fedora",
    "debian": "Debian",
    "ubuntu": "Ubuntu",
    "arch": "Arch Linux",
}


def render_categories(catalog: SnippetCatalog) -> None:
    """Afficher catégories et nombre de commandes associées."""
    print("Catégories disponibles :")
    for category in catalog.categories:
        print(f"  {category} ({len(catalog.by_category(category))})")


def render_results(results: list[SearchResult], *, distribution: str | None = None) -> None:
    """Afficher commande, explication, compatibilité, risque et documentation."""
    if not results:
        print("Aucune commande fiable trouvée dans la bibliothèque locale.")
        return
    for index, result in enumerate(results, start=1):
        snippet = result.snippet
        assessments = [analyze_command(command) for command in snippet.commands]
        print(f"{index}. {snippet.title} [{snippet.category}]")
        print(f"   {snippet.description}")
        compatibility = (
            "toutes les distributions Linux"
            if "linux" in snippet.distributions
            else ", ".join(_DISTRIBUTION_LABELS.get(item, item) for item in snippet.distributions)
        )
        if distribution:
            detected = _DISTRIBUTION_LABELS.get(distribution, distribution)
            print(f"   Compatibilité : {compatibility}; distribution détectée : {detected}")
        else:
            print(f"   Compatibilité : {compatibility}")
        effective_risk = highest_risk(
            snippet.risk, *(assessment.risk for assessment in assessments)
        )
        requires_admin = snippet.requires_admin or any(item.requires_admin for item in assessments)
        destructive = snippet.destructive or any(item.destructive for item in assessments)
        print(f"   Risque : {_RISK_LABELS[effective_risk]}")
        if requires_admin:
            print("   Attention : nécessite les privilèges administrateur.")
        if destructive:
            print("   Attention : cette commande peut modifier ou supprimer des données.")
        for effect in snippet.effects:
            print(f"   Effet : {effect}")
        if (
            distribution
            and distribution not in snippet.distributions
            and "linux" not in snippet.distributions
        ):
            print(f"   Attention : aucune variante pour {distribution} n'est déclarée.")
        for command, assessment in zip(snippet.commands, assessments, strict=True):
            print(f"   Commande : {command}")
            command_risk = highest_risk(snippet.risk, assessment.risk)
            print(f"   Risque analysé : {_RISK_LABELS[command_risk]}")
            for reason in assessment.reasons:
                print(f"   Analyse statique : {reason}.")
        print(f"   Explication : {snippet.explanation}")
        if snippet.prerequisites:
            print(f"   Prérequis : {'; '.join(snippet.prerequisites)}")
        print("   Sources :")
        for source in snippet.sources:
            print(f"     - {source}")
        print("   Linux Copilot ne l'exécute pas.")


def render_engine_response(response: EngineResponse, *, distribution: str | None = None) -> None:
    """Afficher les références déterministes séparément de la génération IA."""
    render_results(list(response.results), distribution=distribution)
    if response.ai_answer:
        print(f"\nAnalyse IA locale générée par {response.ai_answer.model} (non vérifiée) :")
        print(response.ai_answer.text)
        for step_number, step in enumerate(response.ai_answer.steps, start=1):
            print(f"  {step_number}. {step}")
        for suggestion in response.ai_answer.commands:
            assessment = analyze_command(suggestion.command)
            ai_risk = highest_risk("medium", assessment.risk)
            print(f"  Suggestion IA non vérifiée : {suggestion.command}")
            print(f"  Risque statique estimé : {_RISK_LABELS[ai_risk]} (analyse non exhaustive)")
            if assessment.requires_admin:
                print("  Attention : semble nécessiter les privilèges administrateur.")
            if assessment.destructive:
                print("  Attention : motif potentiellement destructeur détecté.")
            for reason in assessment.reasons:
                print(f"  Motif détecté : {reason}.")
            print(f"  Explication IA non vérifiée : {suggestion.explanation}")
        print("Les commandes IA sont des suggestions non vérifiées et ne seront jamais exécutées.")
        print("Les seules sources vérifiées sont celles affichées avec les snippets.")
    if response.ai_notice:
        print(f"\n{response.ai_notice}")
