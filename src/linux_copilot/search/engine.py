"""Moteur de recherche local réutilisable par la CLI et les modules futurs."""

from __future__ import annotations

from dataclasses import dataclass

from linux_copilot.snippets.loader import SnippetCatalog, load_catalog
from linux_copilot.snippets.models import Snippet
from linux_copilot.snippets.ranking import rank_snippets


@dataclass(frozen=True, slots=True)
class SearchResult:
    """Snippet accompagné de son score lexical de pertinence."""

    snippet: Snippet
    score: int


class CommandSearch:
    """Recherche hors ligne avec filtrage de distribution et de catégorie."""

    def __init__(self, catalog: SnippetCatalog | None = None) -> None:
        self.catalog = catalog or load_catalog()

    def search(
        self,
        query: str,
        *,
        distribution: str | None = None,
        category: str | None = None,
        limit: int = 5,
    ) -> list[SearchResult]:
        """Retourner les meilleurs résultats compatibles, sans appel réseau."""
        candidates = self.catalog.snippets
        if category:
            candidates = tuple(
                item for item in candidates if item.category.casefold() == category.casefold()
            )
        return [
            SearchResult(snippet=snippet, score=score)
            for snippet, score in rank_snippets(
                query, candidates, distribution=distribution, limit=limit
            )
        ]

    def search_keyword(
        self, keyword: str, *, distribution: str | None = None, limit: int = 10
    ) -> list[SearchResult]:
        """Recherche directe d'un terme ou mot-clé."""
        return self.search(keyword, distribution=distribution, limit=limit)
