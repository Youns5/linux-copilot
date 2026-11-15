"""Contrats et résultats communs du fournisseur IA local facultatif."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class OllamaModel:
    """Métadonnées retournées par l'API locale /api/tags."""

    name: str
    size_bytes: int
    parameter_size: str = "inconnue"


@dataclass(frozen=True, slots=True)
class OllamaStatus:
    """Disponibilité du binaire, du service local et des modèles locaux."""

    installed: bool
    running: bool
    models: tuple[OllamaModel, ...] = ()
    error: str | None = None


@dataclass(frozen=True, slots=True)
class AICommandSuggestion:
    """Commande générée, non vérifiée, à analyser avant affichage."""

    command: str
    explanation: str


@dataclass(frozen=True, slots=True)
class AIAnswer:
    """Texte généré localement, séparé des sources vérifiées."""

    text: str
    model: str
    steps: tuple[str, ...] = ()
    commands: tuple[AICommandSuggestion, ...] = ()


class LocalAIProvider(Protocol):
    """Interface minimale requise par l'orchestrateur hybride."""

    def status(self) -> OllamaStatus: ...

    def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        *,
        max_tokens: int = 2048,
        temperature: float = 0.2,
        timeout: float = 180.0,
    ) -> AIAnswer: ...
