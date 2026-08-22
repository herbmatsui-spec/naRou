from __future__ import annotations

import json
import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        if hasattr(record, "context"):
            log_data["context"] = record.context

        return json.dumps(log_data, ensure_ascii=False)


def setup_logging(
    level: str = "INFO",
    log_dir: str = "logs",
    json_format: bool = False,
    console: bool = True,
) -> None:
    """Setup application logging."""
    Path(log_dir).mkdir(parents=True, exist_ok=True)

    log_level = getattr(logging, level.upper(), logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()

    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        Path(log_dir) / "narou.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(log_level)

    if json_format:
        file_handler.setFormatter(JSONFormatter())
    else:
        file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
    root_logger.addHandler(file_handler)

    # Error file handler (ERROR and above)
    error_handler = logging.handlers.RotatingFileHandler(
        Path(log_dir) / "narou_errors.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s\n%(exc_info)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    root_logger.addHandler(error_handler)

    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt="%H:%M:%S",
            )
        )
        root_logger.addHandler(console_handler)

    # Suppress noisy loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("PIL").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(name)


configure_logging = setup_logging


def log_exception(
    logger: logging.Logger,
    exc: Exception,
    message: str = "",
    context: dict[str, Any] | None = None,
    level: int = logging.ERROR,
) -> None:
    """Log an exception with context."""
    extra = {"context": context} if context else {}
    if message:
        logger.log(level, f"{message}: {exc}", exc_info=exc, extra=extra)
    else:
        logger.log(level, str(exc), exc_info=exc, extra=extra)
