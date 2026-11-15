"""Ordre commun des niveaux de risque utilisés par les métadonnées et l'analyseur."""

from __future__ import annotations

from linux_copilot.snippets.models import RiskLevel

_RISK_ORDER: dict[str, int] = {"low": 0, "medium": 1, "high": 2}


def highest_risk(*levels: str) -> RiskLevel:
    """Retourner le niveau le plus élevé, faible par défaut."""
    selected = max(levels or ("low",), key=lambda level: _RISK_ORDER.get(level, 2))
    return selected  # type: ignore[return-value]
