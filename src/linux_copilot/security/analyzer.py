"""Analyse lexicale prudente des commandes; aucune interprétation ou exécution shell."""

from __future__ import annotations

from dataclasses import dataclass

from linux_copilot.security.risk import highest_risk
from linux_copilot.security.rules import (
    ADMIN_PATTERN,
    DESTRUCTIVE_PATTERNS,
    REMOTE_SHELL_PATTERN,
    SHELL_OPERATOR_PATTERN,
    WRITE_PATTERNS,
)
from linux_copilot.snippets.models import RiskLevel


@dataclass(frozen=True, slots=True)
class CommandAssessment:
    """Signaux détectés; ce classement n'est pas une garantie d'innocuité."""

    risk: RiskLevel
    requires_admin: bool
    destructive: bool
    reasons: tuple[str, ...]


def analyze_command(command: str) -> CommandAssessment:
    """Signaler les motifs connus sans lancer, développer ni évaluer la commande."""
    text = command.strip()
    if not text:
        return CommandAssessment("high", False, True, ("commande vide ou invalide",))

    reasons: list[str] = []
    requires_admin = bool(ADMIN_PATTERN.search(text))
    destructive = False
    risk_levels: list[str] = ["low"]
    if requires_admin:
        reasons.append("utilise un outil de privilège administrateur")
        risk_levels.append("medium")

    for pattern, reason in DESTRUCTIVE_PATTERNS:
        if pattern.search(text):
            destructive = True
            reasons.append(reason)
            risk_levels.append("high")
    if REMOTE_SHELL_PATTERN.search(text):
        destructive = True
        reasons.append("télécharge et exécute du contenu distant dans un shell")
        risk_levels.append("high")
    for pattern, reason in WRITE_PATTERNS:
        if pattern.search(text):
            reasons.append(reason)
            risk_levels.append("high" if "code tiers" in reason else "medium")
            if "remplacer une destination" in reason or "remplacement d'une archive" in reason:
                destructive = True
    if SHELL_OPERATOR_PATTERN.search(text):
        reasons.append("syntaxe shell composée; vérifier chaque segment séparément")
        risk_levels.append("medium")

    return CommandAssessment(
        risk=highest_risk(*risk_levels),
        requires_admin=requires_admin,
        destructive=destructive,
        reasons=tuple(dict.fromkeys(reasons)),
    )
