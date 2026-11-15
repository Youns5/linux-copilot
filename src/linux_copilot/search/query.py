"""Normalisation française et expansion de synonymes pour la recherche locale."""

from __future__ import annotations

import re
import unicodedata

_STOP_WORDS = {
    "a",
    "au",
    "aux",
    "avec",
    "comment",
    "de",
    "des",
    "du",
    "en",
    "est",
    "et",
    "la",
    "le",
    "les",
    "moi",
    "mon",
    "ma",
    "mes",
    "pour",
    "que",
    "qui",
    "sans",
    "sur",
    "un",
    "une",
    "voir",
}
# Mots fonctionnels retirés du test de phrase exacte (plus restreint volontairement).
_PHRASE_STOP_WORDS = frozenset(
    {"a", "au", "aux", "de", "des", "du", "la", "le", "les", "pour", "un", "une", "voir"}
)
_SYNONYM_GROUPS = (
    {"installer", "installe", "installation", "install", "installez", "ajouter", "add"},
    {"mettre à jour", "mise à jour", "actualiser", "maj", "update", "upgrade"},
    {"supprimer", "désinstaller", "remove", "uninstall"},
    {"ports", "port", "écoute", "écoutés", "listening", "socket", "sockets"},
    {"volumineux", "volumineuse", "gros", "grands", "large", "big", "size"},
    {"fichier", "fichiers", "file", "files"},
    {"réseau", "reseau", "network", "connexion", "connectivité", "connectivite"},
    {"paquet", "paquets", "package", "packages", "logiciel", "application"},
    {"ouvrir", "ouvert", "ouverte", "ouverts", "ouvertes", "open"},
    {"wifi", "wi-fi", "wireless", "internet"},
)


def normalize_text(value: str) -> str:
    """Normaliser accents, ponctuation et espaces sans modifier le texte source."""
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    without_accents = "".join(
        character for character in decomposed if not unicodedata.combining(character)
    )
    return " ".join(re.findall(r"[a-z0-9_./+-]+", without_accents))


def expand_query(query: str) -> set[str]:
    """Ajouter les synonymes utiles tout en retirant les mots fonctionnels."""
    normalized = normalize_text(query)
    terms = {term for term in normalized.split() if term not in _STOP_WORDS and len(term) > 1}
    for group in _SYNONYM_GROUPS:
        normalized_group = {normalize_text(term) for term in group}
        group_terms = {word for phrase in normalized_group for word in phrase.split()}
        if terms & group_terms:
            # Ne réintroduire aucun mot fonctionnel via les groupes de synonymes.
            terms.update(word for word in group_terms if word not in _STOP_WORDS and len(word) > 1)
    return terms
