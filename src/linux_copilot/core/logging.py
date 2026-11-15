"""Journalisation locale avec filtrage des identifiants courants."""

from __future__ import annotations

import logging
import re
from logging.handlers import RotatingFileHandler

from linux_copilot.core.errors import InternalError
from linux_copilot.core.paths import AppPaths

_SECRET_PATTERN = re.compile(
    r"""(?i)(\b(?:password|passwd|api[_-]?key|token|secret)\b["']?\s*[:=]\s*)"""
    r"""("[^"\n]*"|'[^'\n]*'|[^\s,;]+)"""
)
_BEARER_PATTERN = re.compile(r"""(?i)(\bbearer\s+)("[^"\n]*"|'[^'\n]*'|[^\s,;]+)""")
_LOGGER_NAME = "linux_copilot"


def _redact(message: str) -> str:
    message = _SECRET_PATTERN.sub(r"\1[REDACTED]", message)
    return _BEARER_PATTERN.sub(r"\1[REDACTED]", message)


class SensitiveDataFilter(logging.Filter):
    """Masquer les secrets usuels dans les messages et exceptions journalisés."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            record.msg = _redact(record.getMessage())
            record.args = ()
        except Exception:
            record.msg = "[Message de journalisation indisponible]"
            record.args = ()
        if record.exc_info:
            record.exc_text = _redact(logging.Formatter().formatException(record.exc_info))
            record.exc_info = None
        return True


def configure_logging(paths: AppPaths, level: int = logging.INFO) -> logging.Logger:
    """Configurer un journal rotatif dans le dossier local de cache."""
    try:
        paths.ensure_directories()
        log_path = paths.log_dir / "linux-copilot.log"
        logger = logging.getLogger(_LOGGER_NAME)
        logger.setLevel(level)
        logger.propagate = False

        for handler in tuple(logger.handlers):
            if getattr(handler, "_linux_copilot_managed", False):
                logger.removeHandler(handler)
                handler.close()

        handler = RotatingFileHandler(
            log_path,
            maxBytes=1_000_000,
            backupCount=3,
            encoding="utf-8",
        )
        log_path.chmod(0o600)
        handler._linux_copilot_managed = True
        handler.addFilter(SensitiveDataFilter())
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(handler)
        return logger
    except OSError as error:
        raise InternalError("Impossible de préparer le journal local.") from error
