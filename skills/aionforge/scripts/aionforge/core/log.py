from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aionforge.core.config import Settings

LOGGER_NAME = "aionforge"
_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"


def get_logger(name: str | None = None) -> logging.Logger:
    if name is None or name == LOGGER_NAME:
        return logging.getLogger(LOGGER_NAME)
    if name.startswith(LOGGER_NAME + "."):
        return logging.getLogger(name)
    return logging.getLogger(f"{LOGGER_NAME}.{name}")


def setup_logging(
    *,
    level: str = "INFO",
    console: bool = True,
    file_path: Path | None = None,
) -> None:
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.handlers.clear()
    logger.propagate = False
    formatter = logging.Formatter(_FORMAT)
    if console:
        stream = logging.StreamHandler(sys.stderr)
        stream.setFormatter(formatter)
        logger.addHandler(stream)
    if file_path is not None:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(file_path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)


def configure_logging(settings: Settings, *, console: bool | None = None) -> None:
    path = Path(settings.logging.file).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    setup_logging(
        level=settings.logging.level,
        console=settings.logging.console if console is None else console,
        file_path=path,
    )
