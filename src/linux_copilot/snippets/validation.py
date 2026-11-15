"""Validation stricte des données JSON embarquées ou fournies localement."""

from __future__ import annotations

import re
from typing import Any

from linux_copilot.core.errors import SnippetValidationError
from linux_copilot.snippets.models import Snippet

_DISTRIBUTIONS = {"linux", "fedora", "debian", "ubuntu", "arch"}
_RISKS = {"low", "medium", "high"}
_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{1,79}$")
_URL_PATTERN = re.compile(r"^https://[^\s]+$")
_REQUIRED = {
    "id",
    "title",
    "description",
    "keywords",
    "category",
    "distributions",
    "commands",
    "explanation",
    "risk",
    "prerequisites",
    "requires_admin",
    "destructive",
    "effects",
    "sources",
}


def validate_snippet(value: Any, *, source: str = "snippet") -> Snippet:
    """Valider un objet JSON et produire un modèle immuable."""
    if not isinstance(value, dict):
        raise SnippetValidationError(f"{source}: chaque snippet doit être un objet JSON.")
    missing = sorted(_REQUIRED - value.keys())
    unknown = sorted(value.keys() - _REQUIRED)
    if missing:
        raise SnippetValidationError(
            f"{source}: champs obligatoires absents : {', '.join(missing)}."
        )
    if unknown:
        raise SnippetValidationError(f"{source}: champs inconnus : {', '.join(unknown)}.")

    snippet_id = _string(value["id"], "id", source)
    if not _ID_PATTERN.fullmatch(snippet_id):
        raise SnippetValidationError(f"{source}: identifiant invalide : {snippet_id}.")
    risk = _string(value["risk"], "risk", source)
    if risk not in _RISKS:
        raise SnippetValidationError(f"{source}: niveau de risque invalide : {risk}.")

    distributions = _strings(value["distributions"], "distributions", source, nonempty=True)
    unknown_distros = set(distributions) - _DISTRIBUTIONS
    if unknown_distros:
        raise SnippetValidationError(
            f"{source}: distribution(s) inconnue(s) : {', '.join(sorted(unknown_distros))}."
        )
    commands = _strings(value["commands"], "commands", source, nonempty=True)
    if any("\n" in command or "\r" in command for command in commands):
        raise SnippetValidationError(f"{source}: une commande doit tenir sur une seule ligne.")
    sources = _strings(value["sources"], "sources", source, nonempty=True)
    if any(not _URL_PATTERN.fullmatch(url) for url in sources):
        raise SnippetValidationError(f"{source}: chaque source doit être une URL HTTPS valide.")

    for key in ("requires_admin", "destructive"):
        if not isinstance(value[key], bool):
            raise SnippetValidationError(f"{source}: {key} doit être un booléen.")
    if value["destructive"] and risk == "low":
        raise SnippetValidationError(
            f"{source}: une commande destructive ne peut pas être à risque faible."
        )
    return Snippet(
        id=snippet_id,
        title=_string(value["title"], "title", source),
        description=_string(value["description"], "description", source),
        keywords=_strings(value["keywords"], "keywords", source, nonempty=True),
        category=_string(value["category"], "category", source),
        distributions=distributions,
        commands=commands,
        explanation=_string(value["explanation"], "explanation", source),
        risk=risk,  # type: ignore[arg-type]
        prerequisites=_strings(value["prerequisites"], "prerequisites", source),
        requires_admin=value["requires_admin"],
        destructive=value["destructive"],
        effects=_strings(value["effects"], "effects", source),
        sources=sources,
    )


def _string(value: Any, field: str, source: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SnippetValidationError(f"{source}: {field} doit être un texte non vide.")
    return value.strip()


def _strings(value: Any, field: str, source: str, *, nonempty: bool = False) -> tuple[str, ...]:
    if not isinstance(value, list) or (nonempty and not value):
        raise SnippetValidationError(
            f"{source}: {field} doit être une liste" + (" non vide." if nonempty else ".")
        )
    return tuple(_string(item, field, source) for item in value)
