"""Détection système et types publics des distributions Linux."""

from linux_copilot.distros.base import DistributionProfile, SystemInfo
from linux_copilot.distros.detect import detect_system

__all__ = ["DistributionProfile", "SystemInfo", "detect_system"]
