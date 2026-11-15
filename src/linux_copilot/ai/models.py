"""Modèles Ollama recommandés et lecture indicative des ressources locales."""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ModelRecommendation:
    """Estimation d'un modèle; ne constitue pas une garantie de performance."""

    name: str
    disk_size: str
    minimum_free_ram_gib: float
    interest: str
    page_url: str


@dataclass(frozen=True, slots=True)
class SystemResources:
    """Ressources mesurées localement, sans détection de GPU."""

    available_ram_gib: float | None
    total_ram_gib: float | None
    home_free_disk_gib: float | None


MODEL_RECOMMENDATIONS = (
    ModelRecommendation(
        name="llama3.2:3b",
        disk_size="environ 2.0 Go",
        minimum_free_ram_gib=4.0,
        interest="Modèle compact multilingue pour les explications générales.",
        page_url="https://ollama.com/library/llama3.2",
    ),
    ModelRecommendation(
        name="qwen2.5:3b",
        disk_size="environ 1.9 Go",
        minimum_free_ram_gib=4.0,
        interest="Modèle compact multilingue, utile pour le code et le suivi d'instructions.",
        page_url="https://ollama.com/library/qwen2.5",
    ),
    ModelRecommendation(
        name="llama3.2:1b",
        disk_size="environ 1.3 Go",
        minimum_free_ram_gib=2.5,
        interest="Variante plus légère, avec des capacités et une qualité de réponse réduites.",
        page_url="https://ollama.com/library/llama3.2",
    ),
    ModelRecommendation(
        name="qwen2.5:1.5b",
        disk_size="environ 986 Mo",
        minimum_free_ram_gib=2.5,
        interest="Petit modèle multilingue pour les machines aux ressources limitées.",
        page_url="https://ollama.com/library/qwen2.5",
    ),
)


def get_system_resources() -> SystemResources:
    """Lire la mémoire disponible et l'espace libre dans le dossier personnel."""
    total_ram: float | None = None
    available_ram: float | None = None
    try:
        memory_info = Path("/proc/meminfo").read_text(encoding="utf-8")
        values = {
            match.group(1): int(match.group(2))
            for match in re.finditer(
                r"^(MemTotal|MemAvailable):\s+(\d+) kB$", memory_info, re.MULTILINE
            )
        }
        if "MemTotal" in values:
            total_ram = values["MemTotal"] / 1024 / 1024
        if "MemAvailable" in values:
            available_ram = values["MemAvailable"] / 1024 / 1024
    except OSError:
        pass

    try:
        free_disk = shutil.disk_usage(Path.home()).free / 1024**3
    except OSError:
        free_disk = None
    return SystemResources(available_ram, total_ram, free_disk)
