"""Types communs aux profils de distribution et aux informations système."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DistributionProfile:
    """Valeurs connues pour une distribution prise en charge."""

    distribution_id: str
    name: str
    package_manager: str


@dataclass(frozen=True, slots=True)
class SystemInfo:
    """Informations détectées sans exécuter de commande système."""

    distribution_id: str
    distribution: str
    version: str
    package_manager: str
    architecture: str
    python_version: str
