"""Chargement du catalogue JSON local sans accès réseau."""

from __future__ import annotations

import json
import site
import sysconfig
from dataclasses import dataclass
from pathlib import Path

from linux_copilot.core.errors import ResourceNotFoundError, SnippetValidationError
from linux_copilot.snippets.models import Snippet
from linux_copilot.snippets.validation import validate_snippet


@dataclass(frozen=True, slots=True)
class SnippetCatalog:
    """Catalogue validé, indexable par catégorie et identifiant."""

    snippets: tuple[Snippet, ...]

    @property
    def categories(self) -> tuple[str, ...]:
        return tuple(sorted({snippet.category for snippet in self.snippets}))

    def by_category(self, category: str) -> tuple[Snippet, ...]:
        return tuple(
            snippet
            for snippet in self.snippets
            if snippet.category.casefold() == category.casefold()
        )


def default_snippets_directory() -> Path:
    """Trouver les données du dépôt ou celles installées sous share/ par pip."""
    project_directory = Path(__file__).resolve().parents[3] / "data" / "snippets"
    if project_directory.is_dir():
        return project_directory
    installed_directories = (
        Path(sysconfig.get_path("data")) / "share" / "linux-copilot" / "snippets",
        Path(site.getuserbase()) / "share" / "linux-copilot" / "snippets",
    )
    return next((path for path in installed_directories if path.is_dir()), installed_directories[0])


def load_catalog(directory: Path | str | None = None) -> SnippetCatalog:
    """Charger tous les fichiers JSON et refuser tout doublon ou donnée invalide."""
    data_directory = Path(directory) if directory is not None else default_snippets_directory()
    if not data_directory.is_dir():
        raise ResourceNotFoundError(f"Dossier de snippets introuvable : {data_directory}")
    files = sorted(data_directory.glob("*.json"))
    if not files:
        raise ResourceNotFoundError(f"Aucun fichier JSON de snippets dans : {data_directory}")

    snippets: list[Snippet] = []
    seen_ids: set[str] = set()
    for file_path in files:
        try:
            payload = json.loads(file_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise SnippetValidationError(
                f"{file_path.name}: fichier JSON illisible ou invalide."
            ) from error
        if not isinstance(payload, list):
            raise SnippetValidationError(f"{file_path.name}: la racine JSON doit être une liste.")
        for index, raw_snippet in enumerate(payload, start=1):
            snippet = validate_snippet(raw_snippet, source=f"{file_path.name}:{index}")
            if snippet.id in seen_ids:
                raise SnippetValidationError(f"Identifiant de snippet dupliqué : {snippet.id}.")
            seen_ids.add(snippet.id)
            snippets.append(snippet)
    return SnippetCatalog(tuple(snippets))
