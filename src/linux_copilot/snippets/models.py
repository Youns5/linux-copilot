"""Modèles immuables des commandes documentées du catalogue."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

RiskLevel = Literal["low", "medium", "high"]


@dataclass(frozen=True, slots=True)
class Snippet:
    """Commande documentée avec compatibilité, effets et sources vérifiables."""

    id: str
    title: str
    description: str
    keywords: tuple[str, ...]
    category: str
    distributions: tuple[str, ...]
    commands: tuple[str, ...]
    explanation: str
    risk: RiskLevel
    prerequisites: tuple[str, ...]
    requires_admin: bool
    destructive: bool
    effects: tuple[str, ...]
    sources: tuple[str, ...]
