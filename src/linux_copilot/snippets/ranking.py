"""Classement lexical déterministe des commandes pertinentes."""

from __future__ import annotations

from linux_copilot.search.query import _PHRASE_STOP_WORDS, expand_query, normalize_text
from linux_copilot.snippets.models import Snippet

_ACTION_TERMS = {
    "installer", "installe", "installation", "install", "installez",
    "ajouter", "add", "commande", "commandes",
    "actualiser", "maj", "update", "upgrade",
    "supprimer", "desinstaller", "remove", "uninstall",
}


def rank_snippets(
    query: str,
    snippets: tuple[Snippet, ...] | list[Snippet],
    *,
    distribution: str | None = None,
    limit: int = 5,
) -> list[tuple[Snippet, int]]:
    """Classer les correspondances; les distributions incompatibles sont exclues."""
    if limit < 1:
        return []

    query_text = normalize_text(query)
    query_terms = expand_query(query)
    target_terms = query_terms - _ACTION_TERMS
    query_phrase = " ".join(
        term for term in query_text.split() if term not in _PHRASE_STOP_WORDS
    )

    if not target_terms:
        return []

    results: list[tuple[Snippet, int]] = []

    for snippet in snippets:
        if (
            distribution
            and "linux" not in snippet.distributions
            and distribution not in snippet.distributions
        ):
            continue

        title = normalize_text(snippet.title)
        keywords = [normalize_text(keyword) for keyword in snippet.keywords]
        description = normalize_text(snippet.description)
        category = normalize_text(snippet.category)

        searchable_phrases = [title, *keywords]
        searchable_text = " ".join(
            [title, *keywords, description, category]
        )
        searchable_terms = set(searchable_text.split())

        # Un résultat doit correspondre au sujet recherché,
        # pas uniquement au verbe d'action.
        if not any(
            term in searchable_terms
            for term in target_terms
        ):
            continue

        score = 0

        for term in query_terms:
            if term in title.split():
                score += 8
            elif term in title:
                score += 4

            if any(term == keyword or term in keyword.split() for keyword in keywords):
                score += 6

            if term in description.split():
                score += 2

            if term in category.split():
                score += 2

        if query_text and query_text in title:
            score += 10

        if query_phrase and any(
            query_phrase in field for field in searchable_phrases
        ):
            score += 14

        if score:
            results.append((snippet, score))

    results.sort(
        key=lambda result: (
            -result[1],
            result[0].title.casefold(),
            result[0].id,
        )
    )

    return results[:limit]
