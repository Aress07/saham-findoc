from __future__ import annotations

import logging
from pathlib import Path

from findoc.config import get_config

_CONFIGURED = False


def setup_logging(log_file: str | None = None, console: bool = True) -> None:
    """Configure the ``findoc`` logger: console and/or a rotating file.

    Safe to call multiple times; only the first call configures handlers.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return

    config = get_config()
    log_file = log_file or config.log_file
    level = getattr(logging, config.log_level.upper(), logging.INFO)

    logger = logging.getLogger("findoc")
    logger.setLevel(level)
    logger.propagate = False

    fmt = logging.Formatter(
        "%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(fmt)
        logger.addHandler(console_handler)

    if log_file:
        path = Path(log_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(path, encoding="utf-8")
        file_handler.setFormatter(fmt)
        logger.addHandler(file_handler)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a logger under the ``findoc`` namespace (e.g. ``findoc.pipeline``)."""
    return logging.getLogger(f"findoc.{name}")