"""Détection Linux à partir de /etc/os-release, sans appel de sous-processus."""

from __future__ import annotations

import platform
import shlex
from pathlib import Path

from linux_copilot.core.errors import (
    ResourceNotFoundError,
    SystemDetectionError,
    UnknownDistributionError,
)
from linux_copilot.distros.base import DistributionProfile, SystemInfo
from linux_copilot.distros.fedora import FEDORA_PROFILE

_OS_RELEASE = Path("/etc/os-release")
_PROFILES = {
    "fedora": FEDORA_PROFILE,
    "ubuntu": DistributionProfile("ubuntu", "Ubuntu", "apt"),
    "debian": DistributionProfile("debian", "Debian", "apt"),
    "arch": DistributionProfile("arch", "Arch Linux", "pacman"),
}


def detect_system(os_release_path: Path | str = _OS_RELEASE) -> SystemInfo:
    """Détecter distribution, gestionnaire de paquets et versions locales."""
    release_path = Path(os_release_path)
    values = _parse_os_release(release_path)
    distribution_id = values.get("ID", "").lower()
    profile = _PROFILES.get(distribution_id)
    if profile is None:
        raise UnknownDistributionError(
            f"Distribution Linux non reconnue : {distribution_id or 'identifiant absent'}."
        )

    return SystemInfo(
        distribution_id=profile.distribution_id,
        distribution=values.get("PRETTY_NAME") or values.get("NAME") or profile.name,
        version=values.get("VERSION_ID") or values.get("VERSION") or "inconnue",
        package_manager=profile.package_manager,
        architecture=platform.machine() or "inconnue",
        python_version=platform.python_version(),
    )


def _parse_os_release(path: Path) -> dict[str, str]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError as error:
        raise ResourceNotFoundError(f"Fichier système introuvable : {path}") from error
    except OSError as error:
        raise SystemDetectionError(
            "Impossible de lire les informations de distribution."
        ) from error

    values: dict[str, str] = {}
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, raw_value = stripped.split("=", maxsplit=1)
        try:
            parsed = shlex.split(raw_value, comments=False, posix=True)
        except ValueError as error:
            raise SystemDetectionError("Le fichier os-release est mal formé.") from error
        if key and parsed:
            values[key] = parsed[0]
    return values
