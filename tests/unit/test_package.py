"""Tests minimaux de chargement du paquet."""

import linux_copilot
from linux_copilot.core import AppConfig, AppPaths, load_config
from linux_copilot.distros import SystemInfo, detect_system


def test_package_has_version() -> None:
    assert linux_copilot.__version__ == "0.2.0"


def test_core_interfaces_are_importable() -> None:
    assert AppConfig
    assert AppPaths
    assert SystemInfo
    assert callable(load_config)
    assert callable(detect_system)
