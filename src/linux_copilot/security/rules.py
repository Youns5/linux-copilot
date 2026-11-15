"""Motifs conservateurs pour les commandes privilégiées ou modificatrices."""

from __future__ import annotations

import re

ADMIN_PATTERN = re.compile(r"(?:^|[;&|]\s*|\s)(?:sudo|doas|pkexec)(?:\s|$)", re.IGNORECASE)
DESTRUCTIVE_PATTERNS = (
    (re.compile(r"\brm\b", re.IGNORECASE), "suppression de fichier possible"),
    (
        re.compile(r"\b(find\b.*\s-delete\b|xargs\b.*\brm\b)", re.IGNORECASE),
        "suppression récursive possible",
    ),
    (
        re.compile(r"\b(mkfs(?:\.[\w-]+)?|wipefs|shred|dd)\b", re.IGNORECASE),
        "écriture ou effacement direct de données",
    ),
    (
        re.compile(r"\b(git\s+clean\b|git\s+reset\s+--hard\b)", re.IGNORECASE),
        "suppression ou abandon de changements Git",
    ),
    (
        re.compile(
            r"\b(pacman\s+-\w*R|apt(?:-get)?\s+remove|dnf\s+(?:remove|autoremove)|rpm\s+-e)\b",
            re.IGNORECASE,
        ),
        "suppression de paquets",
    ),
    (
        re.compile(r"\b(chmod|chown)\s+(?:-[^\s]*R|--recursive)\b", re.IGNORECASE),
        "modification récursive des permissions ou propriétaires",
    ),
    (
        re.compile(
            r"\b(systemctl\s+(?:reboot|poweroff|halt)|shutdown|reboot|poweroff)\b", re.IGNORECASE
        ),
        "arrêt ou redémarrage du système",
    ),
    (
        re.compile(r"\b(?:python\d*(?:\.\d+)?|perl|ruby|node)\s+-c\b", re.IGNORECASE),
        "exécution de code fourni en argument",
    ),
    (re.compile(r"\b(?:sh|bash)\s+-c\b", re.IGNORECASE), "exécution d'un fragment shell dynamique"),
    (re.compile(r"(?:^|\s)>{1,2}\s*/dev/", re.IGNORECASE), "écriture directe vers un périphérique"),
)
REMOTE_SHELL_PATTERN = re.compile(
    r"\b(?:curl|wget)\b[^\n]*\|\s*(?:sudo\s+)?(?:sh|bash)\b", re.IGNORECASE
)
WRITE_PATTERNS = (
    (
        re.compile(r"\b(cp|mv)\b", re.IGNORECASE),
        "copie ou déplacement pouvant remplacer une destination",
    ),
    (re.compile(r"\b(tar)\s+-[^\s]*c", re.IGNORECASE), "création ou remplacement d'une archive"),
    (
        re.compile(r"\b(apt|apt-get|dnf|pacman)\s+(?:install|upgrade|update|-S)\b", re.IGNORECASE),
        "modification de paquets ou d'index",
    ),
    (
        re.compile(r"\b(pip|python\s+-m\s+pip)\s+install\b", re.IGNORECASE),
        "installation et exécution potentielle de code tiers",
    ),
    (
        re.compile(r"\b(systemctl\s+(?:start|stop|restart|enable|disable))\b", re.IGNORECASE),
        "modification de l'état d'un service",
    ),
    (
        re.compile(r"\b(ssh-copy-id|rsync)\b", re.IGNORECASE),
        "écriture potentielle sur une cible distante ou locale",
    ),
)
SHELL_OPERATOR_PATTERN = re.compile(r"(?:&&|\|\||[;|`]|\$\(|\n|(?<!<)<(?!<)|(?<!>)>(?!>))")
