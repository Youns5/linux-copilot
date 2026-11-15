"""Profil de la distribution Fedora."""

from linux_copilot.distros.base import DistributionProfile

FEDORA_PROFILE = DistributionProfile(
    distribution_id="fedora",
    name="Fedora",
    package_manager="dnf",
)
