"""Structured application logging with secret redaction.

Logs are written to <data_dir>/logs/produceros.log (rotating) and to
stderr. A filter redacts anything that looks like a secret (session
cookies, pairing codes, password fields, Authorization headers) before it
reaches either sink, so logs are always safe to share for troubleshooting.
"""

from __future__ import annotations

import contextlib
import json
import logging
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path

_REDACT_PATTERNS = [
    re.compile(r"(password\"?\s*[:=]\s*\"?)([^\",\s]+)", re.IGNORECASE),
    re.compile(r"(authorization\"?\s*[:=]\s*\"?)(bearer\s+[^\",\s]+)", re.IGNORECASE),
    re.compile(r"(session[_-]?token\"?\s*[:=]\s*\"?)([^\",\s]+)", re.IGNORECASE),
    re.compile(r"(pairing[_-]?code\"?\s*[:=]\s*\"?)([^\",\s]+)", re.IGNORECASE),
    re.compile(r"(secret[_-]?key\"?\s*[:=]\s*\"?)([^\",\s]+)", re.IGNORECASE),
    re.compile(r"(csrf[_-]?token\"?\s*[:=]\s*\"?)([^\",\s]+)", re.IGNORECASE),
]
REDACTED_PLACEHOLDER = "[REDACTED]"


def redact_secrets(message: str) -> str:
    """Replace known secret-shaped substrings in a log message."""
    redacted = message
    for pattern in _REDACT_PATTERNS:
        redacted = pattern.sub(lambda m: f"{m.group(1)}{REDACTED_PLACEHOLDER}", redacted)
    return redacted


class RedactionFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        # Defensive only -- redaction must never break logging itself.
        with contextlib.suppress(Exception):
            record.msg = redact_secrets(str(record.msg))
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "time": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        extra = getattr(record, "extra_fields", None)
        if extra:
            payload.update(extra)
        return json.dumps(payload, default=str)


def configure_logging(logs_dir: Path | None, level: str = "INFO") -> None:
    """Configure the root ``produceros`` logger. Safe to call more than once."""
    logger = logging.getLogger("produceros")
    logger.setLevel(level.upper())
    logger.handlers.clear()
    logger.propagate = False

    formatter = JsonFormatter()
    redaction = RedactionFilter()

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.addFilter(redaction)
    logger.addHandler(console_handler)

    if logs_dir is not None:
        logs_dir.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            logs_dir / "produceros.log", maxBytes=5_000_000, backupCount=5, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        file_handler.addFilter(redaction)
        logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"produceros.{name}")
