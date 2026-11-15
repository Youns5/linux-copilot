"""Tests isolés du Core Engine et de ses accès au système de fichiers."""

import logging
from typing import get_type_hints

import pytest

from linux_copilot.core.config import AppConfig, load_config
from linux_copilot.core.errors import (
    CommunicationError,
    ConfigurationError,
    InternalError,
    LinuxCopilotError,
    ModuleUnavailableError,
    ResourceNotFoundError,
    UnknownDistributionError,
)
from linux_copilot.core.logging import configure_logging
from linux_copilot.core.paths import get_app_paths
from linux_copilot.distros import SystemInfo, detect_system


def _system_info() -> SystemInfo:
    return SystemInfo(
        distribution_id="fedora",
        distribution="Fedora Linux 43",
        version="43",
        package_manager="dnf",
        architecture="x86_64",
        python_version="3.13.0",
    )


def test_detect_fedora_from_os_release(tmp_path) -> None:
    release_file = tmp_path / "os-release"
    release_file.write_text(
        'NAME="Fedora Linux"\nID=fedora\nVERSION_ID=43\nPRETTY_NAME="Fedora Linux 43"\n',
        encoding="utf-8",
    )

    result = detect_system(release_file)

    assert result.distribution_id == "fedora"
    assert result.distribution == "Fedora Linux 43"
    assert result.version == "43"
    assert result.package_manager == "dnf"
    assert result.architecture
    assert result.python_version


def test_unknown_distribution_raises_domain_error(tmp_path) -> None:
    release_file = tmp_path / "os-release"
    release_file.write_text("ID=unknown-linux\n", encoding="utf-8")

    with pytest.raises(UnknownDistributionError, match="unknown-linux"):
        detect_system(release_file)


def test_config_reads_toml_without_writing_user_files(tmp_path) -> None:
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        '[app]\nname = "Copilot Test"\nversion = "9.1"\nlanguage = "fr"\n'
        "[preferences]\ncolor = false\n",
        encoding="utf-8",
    )

    config = load_config(config_file, system_info=_system_info())

    assert isinstance(config, AppConfig)
    assert config.name == "Copilot Test"
    assert config.version == "9.1"
    assert config.language == "fr"
    assert config.distribution.distribution_id == "fedora"
    assert config.preferences == {"color": False}
    assert not config.ai_available


def test_config_public_type_hints_are_resolvable() -> None:
    assert get_type_hints(AppConfig)["distribution"] is SystemInfo


def test_invalid_config_and_missing_explicit_file_raise_clear_errors(tmp_path) -> None:
    invalid_file = tmp_path / "invalid.toml"
    invalid_file.write_text("[app\n", encoding="utf-8")
    missing_file = tmp_path / "missing.toml"

    with pytest.raises(ConfigurationError, match="TOML invalide"):
        load_config(invalid_file, system_info=_system_info())
    with pytest.raises(ResourceNotFoundError, match="introuvable"):
        load_config(missing_file, system_info=_system_info())


@pytest.mark.parametrize(
    ("error_type", "message"),
    [
        (ModuleUnavailableError, "Le module facultatif est indisponible."),
        (CommunicationError, "La communication a échoué."),
        (InternalError, "Une erreur interne est survenue."),
    ],
)
def test_other_domain_errors_are_user_readable(error_type, message) -> None:
    error = error_type(message)

    assert isinstance(error, LinuxCopilotError)
    assert str(error) == message


def test_paths_follow_xdg_and_create_directories(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))

    paths = get_app_paths().ensure_directories()

    assert paths.config_dir.is_dir()
    assert paths.data_dir.is_dir()
    assert paths.snippets_dir.is_dir()
    assert paths.cache_dir.is_dir()
    assert paths.log_dir.is_dir()
    assert paths.database_path.parent == paths.data_dir


def test_logging_writes_levels_and_redacts_secrets(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    paths = get_app_paths()
    logger = configure_logging(paths)

    logger.info("Core Engine ready")
    logger.warning("api_key=super-secret")
    logger.error("authorization: Bearer private-token")
    logger.warning('password="a private phrase"')
    logger.warning("token='another private phrase'")
    for handler in tuple(logger.handlers):
        if getattr(handler, "_linux_copilot_managed", False):
            handler.flush()
            logger.removeHandler(handler)
            handler.close()

    contents = (paths.log_dir / "linux-copilot.log").read_text(encoding="utf-8")
    assert "INFO" in contents and "Core Engine ready" in contents
    assert "WARNING" in contents and "ERROR" in contents
    assert "[REDACTED]" in contents
    assert "super-secret" not in contents
    assert "private-token" not in contents
    assert "a private phrase" not in contents
    assert "another private phrase" not in contents
    assert logging.getLogger("linux_copilot").propagate is False
