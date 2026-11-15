"""Commandes de gestion IA et configuration utilisateur."""

from __future__ import annotations

import sys
import tomllib
from collections.abc import Sequence
from importlib.metadata import PackageNotFoundError, version

from linux_copilot import __version__
from linux_copilot.ai.local import OllamaClient
from linux_copilot.ai.models import MODEL_RECOMMENDATIONS, get_system_resources
from linux_copilot.core.errors import LinuxCopilotError, ModelNotFoundError
from linux_copilot.core.paths import get_app_paths
from linux_copilot.core.preferences import (
    load_preferences,
    reset_preferences,
    set_preference,
)
from linux_copilot.distros import detect_system
from linux_copilot.snippets.loader import load_catalog


def run_ai_command(arguments: Sequence[str], client: OllamaClient | None = None) -> int:
    """Gérer l'état local d'Ollama sans installer ni télécharger de modèle."""
    if not arguments:
        _print_ai_help()
        return 0
    client = client or OllamaClient()
    command, *values = arguments
    try:
        if command == "status":
            return _show_ai_status(client)
        if command == "models":
            return _show_models(client)
        if command == "model":
            return _select_model(values, client)
        if command == "setup":
            return _show_setup(client)
        if command == "enable":
            set_preference("ai.provider", "ollama")
            set_preference("ai.mode", "auto")
            set_preference("ai.enabled", True)
            print(
                "IA locale activée en mode auto; sans Ollama ou modèle, la recherche locale reste active."
            )
            print("Aucun logiciel ni modèle n'a été téléchargé.")
            return 0
        if command == "disable":
            set_preference("ai.enabled", False)
            print("IA désactivée; Linux Copilot utilise la bibliothèque locale.")
            return 0
        if command == "mode":
            if len(values) != 1:
                print("Usage : copilot ai mode local|ollama|auto", file=sys.stderr)
                return 2
            preferences = set_preference("ai.mode", values[0])
            if preferences.ai.mode == "local":
                preferences = set_preference("ai.enabled", False)
                print(
                    "Mode IA enregistré : local. IA désactivée; seuls les snippets locaux sont utilisés."
                )
                return 0
            preferences = set_preference("ai.enabled", True)
            print(
                f"Mode IA enregistré : {preferences.ai.mode}. IA activée; en cas d'indisponibilité "
                "d'Ollama, la recherche par snippets reste utilisée automatiquement."
            )
            return 0
        print(f"Sous-commande IA inconnue : {command}", file=sys.stderr)
        _print_ai_help(file=sys.stderr)
        return 2
    except (LinuxCopilotError, OSError) as error:
        print(f"Erreur : {error}", file=sys.stderr)
        return 2


def run_config_command(arguments: Sequence[str]) -> int:
    """Afficher, modifier ou réinitialiser les préférences persistées."""
    command = arguments[0] if arguments else "show"
    try:
        if command == "show" and len(arguments) <= 1:
            preferences = load_preferences()
            print(f"Langue : {preferences.resolved_language}")
            print(
                f"Affichage : couleurs={preferences.display.colors}, disposition={preferences.display.layout}"
            )
            print(
                f"Explications : {preferences.display.show_explanations}; sources : {preferences.display.show_sources}"
            )
            print(
                f"IA : activée={preferences.ai.enabled}, mode={preferences.ai.mode}, "
                f"fournisseur={preferences.ai.provider}, modèle={preferences.ai.model or '(automatique)'}"
            )
            print(
                f"Sécurité : prudence={preferences.security.prudence}, "
                f"confirmation obligatoire={preferences.security.confirmation_required}, "
                f"exécution automatique désactivée"
            )
            return 0
        if command == "set" and len(arguments) == 3:
            name, raw_value = arguments[1:]
            value = _parse_config_value(raw_value)
            preferences = set_preference(name, value)
            print(f"Préférence enregistrée : {name} = {value!r}.")
            if name == "security.confirmation_required":
                print(f"Confirmation obligatoire : {preferences.security.confirmation_required}.")
            return 0
        if command == "reset" and len(arguments) == 1:
            reset_preferences()
            print("Préférences restaurées aux valeurs par défaut.")
            return 0
        print("Usage : copilot config [show | set CLÉ VALEUR | reset]", file=sys.stderr)
        return 2
    except (LinuxCopilotError, OSError) as error:
        print(f"Erreur : {error}", file=sys.stderr)
        return 2


def run_list_command(arguments: Sequence[str] = ()) -> int:
    """Lister les catégories ou les snippets d'une catégorie locale."""
    try:
        catalog = load_catalog()
        if not arguments:
            print("Catégories locales :")
            for category in catalog.categories:
                print(f"  {category} ({len(catalog.by_category(category))})")
            return 0
        category = " ".join(arguments)
        snippets = catalog.by_category(category)
        if not snippets:
            print(f"Catégorie inconnue : {category}", file=sys.stderr)
            return 2
        for snippet in snippets:
            print(f"{snippet.id} — {snippet.title} (risque {snippet.risk})")
        return 0
    except LinuxCopilotError as error:
        print(f"Erreur : {error}", file=sys.stderr)
        return 2


def run_doctor(client: OllamaClient | None = None) -> int:
    """Diagnostiquer l'installation sans créer de fichiers ni appeler de commandes système."""
    failed = False
    python_ok = sys.version_info >= (3, 11)
    print(f"{'OK' if python_ok else 'ERREUR'} Python : {sys.version.split()[0]} (minimum 3.11)")
    failed |= not python_ok

    try:
        preferences = load_preferences()
        config_path = get_app_paths().config_file
        print(f"OK Configuration : {config_path} (mode IA {preferences.ai.mode})")
    except (LinuxCopilotError, OSError) as error:
        print(f"ERREUR Configuration : {error}")
        failed = True

    try:
        catalog = load_catalog()
        print(
            f"OK Bibliothèque : {len(catalog.snippets)} snippets, {len(catalog.categories)} catégories"
        )
    except LinuxCopilotError as error:
        print(f"ERREUR Bibliothèque : {error}")
        failed = True

    try:
        system = detect_system()
        print(
            f"OK Distribution : {system.distribution} ({system.distribution_id}, {system.package_manager})"
        )
    except LinuxCopilotError as error:
        print(
            f"AVERTISSEMENT Distribution : {error}; seuls les snippets Linux génériques seront proposés."
        )

    try:
        installed_version = version("linux-copilot")
        print(f"OK Paquet : linux-copilot {installed_version}")
    except PackageNotFoundError:
        print(
            f"AVERTISSEMENT Paquet : code source {__version__} importé sans métadonnées d'installation."
        )

    try:
        ollama_status = (client or OllamaClient()).status()
        if ollama_status.running:
            print(f"OK Ollama : actif, {len(ollama_status.models)} modèle(s) local(aux)")
        else:
            print("INFO Ollama : indisponible; le moteur de snippets hors ligne reste utilisable.")
    except Exception:
        print(
            "AVERTISSEMENT Ollama : état impossible à déterminer; le moteur local reste utilisable."
        )
    return 1 if failed else 0


def _show_ai_status(client: OllamaClient) -> int:
    preferences = load_preferences()
    status = client.status()
    print(f"Binaire Ollama : {'installé' if status.installed else 'absent'}")
    print(f"Service local : {'actif' if status.running else 'indisponible'}")
    print(f"IA Linux Copilot : {'activée' if preferences.ai.enabled else 'désactivée'}")
    print(f"Mode : {preferences.ai.mode}; fournisseur : {preferences.ai.provider}")
    print(f"Modèle sélectionné : {preferences.ai.model or '(premier modèle local disponible)'}")
    if status.models:
        print(f"Modèles locaux disponibles : {', '.join(model.name for model in status.models)}")
    elif status.error:
        print(status.error)
    else:
        print("Aucun modèle local téléchargé.")
    return 0 if status.running else 1


def _show_models(client: OllamaClient) -> int:
    status = client.status()
    resources = get_system_resources()
    print("Modèles Ollama recommandés (estimations indicatives) :")
    for recommendation in MODEL_RECOMMENDATIONS:
        print(f"  {recommendation.name} — {recommendation.disk_size}")
        print(f"    Intérêt : {recommendation.interest}")
        print(
            f"    RAM libre indicative : {recommendation.minimum_free_ram_gib:g} Gio ou plus; GPU non vérifié."
        )
        if resources.available_ram_gib is not None:
            if resources.available_ram_gib < recommendation.minimum_free_ram_gib:
                print(
                    f"    Avertissement : {resources.available_ram_gib:.1f} Gio disponibles mesurés, sous cette estimation."
                )
            else:
                print(
                    f"    RAM disponible mesurée : {resources.available_ram_gib:.1f} Gio; cela ne garantit pas les performances."
                )
        print(f"    Fiche : {recommendation.page_url}")
        print(f"    Installation manuelle : ollama pull {recommendation.name}")
    if resources.home_free_disk_gib is not None:
        print(
            f"Espace libre mesuré dans le dossier personnel : {resources.home_free_disk_gib:.1f} Gio."
        )
        print("Le répertoire réel des modèles Ollama peut être différent.")
    if status.models:
        print("Modèles locaux détectés :")
        for model in status.models:
            size_gib = model.size_bytes / 1024**3
            print(f"  {model.name} ({size_gib:.2f} Gio, {model.parameter_size})")
    else:
        print("Aucun modèle local détecté; aucun téléchargement n'a été lancé.")
    return 0


def _select_model(values: Sequence[str], client: OllamaClient) -> int:
    preferences = load_preferences()
    if not values:
        print(f"Modèle configuré : {preferences.ai.model or '(automatique)'}")
        status = client.status()
        print("Modèles locaux : " + (", ".join(model.name for model in status.models) or "aucun"))
        return 0
    if len(values) != 1:
        print("Usage : copilot ai model [NOM_LOCAL]", file=sys.stderr)
        return 2
    requested = values[0]
    status = client.status()
    if not any(model.name == requested for model in status.models):
        raise ModelNotFoundError(
            f"{requested} n'est pas un modèle local disponible; utilisez 'copilot ai models'."
        )
    set_preference("ai.provider", "ollama")
    set_preference("ai.model", requested)
    print(f"Modèle local sélectionné : {requested}.")
    return 0


def _show_setup(client: OllamaClient) -> int:
    status = client.status()
    print("Configuration de l'IA locale Ollama")
    print(
        "1. Installer Ollama depuis https://ollama.com/download/linux (aucun compte ni clé requis en local)."
    )
    print(
        "2. Démarrer le service avec `ollama serve` si votre installation ne le démarre pas déjà."
    )
    print(
        "3. Consulter `copilot ai models`, puis exécuter manuellement `ollama pull NOM_DU_MODELE`."
    )
    print("   Le téléchargement d'un modèle n'est jamais lancé par Linux Copilot.")
    print(
        "4. Choisir un modèle présent avec `copilot ai model NOM_LOCAL`, puis `copilot ai enable`."
    )
    if status.running:
        print(f"Ollama répond actuellement avec {len(status.models)} modèle(s) local(aux).")
    else:
        print("Ollama ne répond pas actuellement; la recherche par snippets reste disponible.")
    return 0


def _parse_config_value(raw_value: str) -> object:
    if raw_value.casefold() in {"true", "false"}:
        return raw_value.casefold() == "true"
    try:
        parsed = tomllib.loads(f"value = {raw_value}")["value"]
    except tomllib.TOMLDecodeError:
        return raw_value
    if isinstance(parsed, (str, int, float, bool)):
        return parsed
    return raw_value


def _print_ai_help(*, file=None) -> None:
    print(
        "Usage : copilot ai status|models|model [NOM]|setup|enable|disable|mode local|ollama|auto",
        file=file,
    )
