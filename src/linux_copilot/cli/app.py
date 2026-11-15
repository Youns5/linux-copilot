"""Point d'entrée CLI : recherche locale, catégories et gestion de l'IA."""

import argparse
import sys
from collections.abc import Sequence

from linux_copilot import __version__
from linux_copilot.ai.local import OllamaClient
from linux_copilot.cli.commands import (
    run_ai_command,
    run_config_command,
    run_doctor,
    run_list_command,
)
from linux_copilot.cli.render import render_categories, render_engine_response
from linux_copilot.core.errors import (
    LinuxCopilotError,
    ResourceNotFoundError,
    SystemDetectionError,
    UnknownDistributionError,
)
from linux_copilot.core.orchestrator import CoreEngine
from linux_copilot.core.preferences import load_preferences
from linux_copilot.distros import detect_system
from linux_copilot.search.engine import CommandSearch
from linux_copilot.snippets.loader import load_catalog


def main(argv: Sequence[str] | None = None) -> int:
    """Rechercher une commande ou parcourir les catégories, sans l'exécuter."""
    parser = argparse.ArgumentParser(
        prog="copilot",
        description="Recherche locale de commandes Linux; aucune commande n'est exécutée.",
        epilog=(
            "Exemples : copilot search wifi | copilot list Réseau | copilot ai status | "
            "copilot doctor"
        ),
    )
    parser.add_argument("--version", action="version", version=f"copilot {__version__}")
    parser.add_argument(
        "request", nargs="*", help='Demande en langage naturel, ex. "voir les ports ouverts"'
    )
    parser.add_argument(
        "--category", help="Filtrer par catégorie affichée par 'copilot categories'."
    )
    parser.add_argument("--keyword", help="Rechercher directement un mot-clé.")
    parser.add_argument("--limit", type=int, default=5, help="Nombre maximal de résultats (1-20).")
    args = parser.parse_args(argv)
    if args.limit < 1 or args.limit > 20:
        parser.error("--limit doit être compris entre 1 et 20.")
    if args.keyword and args.request:
        parser.error("Utilisez soit une demande, soit --keyword, pas les deux.")
    if args.request and args.request[0].casefold() == "ai":
        return run_ai_command(args.request[1:])
    if args.request and args.request[0].casefold() == "config":
        return run_config_command(args.request[1:])
    if args.request and args.request[0].casefold() == "doctor":
        if len(args.request) > 1:
            parser.error("Syntaxe : copilot doctor")
        return run_doctor()
    if args.request and args.request[0].casefold() == "list":
        return run_list_command(args.request[1:])
    if len(args.request) == 1 and args.request[0].casefold() == "categories":
        try:
            render_categories(load_catalog())
            return 0
        except LinuxCopilotError as error:
            print(f"Erreur : {error}", file=sys.stderr)
            return 2
    keyword_mode = bool(args.keyword)
    request = args.request
    if request and request[0].casefold() == "search":
        if len(request) == 1:
            parser.error("Syntaxe : copilot search DEMANDE")
        request = request[1:]
    if request and request[0].casefold() == "keyword":
        if len(request) == 1:
            parser.error("Syntaxe : copilot keyword MOT")
        keyword_mode = True
        request = request[1:]
    query = args.keyword or " ".join(request)
    if not query.strip():
        parser.print_help()
        return 0
    try:
        preferences = load_preferences()
        try:
            distribution = detect_system().distribution_id
        except (UnknownDistributionError, ResourceNotFoundError, SystemDetectionError) as error:
            distribution = "unknown"
            print(
                f"Distribution non reconnue ou non détectable ({error}); "
                "seuls les snippets Linux génériques seront proposés.",
                file=sys.stderr,
            )
        engine = CoreEngine(search=CommandSearch(), ollama=OllamaClient())
        response = engine.respond(
            query,
            distribution=distribution,
            language=preferences.resolved_language,
            preferences=preferences.ai,
            category=args.category,
            limit=10 if keyword_mode else args.limit,
        )
    except LinuxCopilotError as error:
        print(f"Erreur : {error}", file=sys.stderr)
        return 2
    render_engine_response(response, distribution=distribution)
    return 0 if response.results or response.ai_answer else 1
