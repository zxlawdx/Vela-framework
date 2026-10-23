# SPDX-License-Identifier: MPL-2.0
"""Logging padronizado do Vela."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

LOG_DIR = Path.cwd() / "logs"
LOG_FILE = LOG_DIR / f"vela_{datetime.now().strftime('%Y-%m-%d')}.log"


def _setup_logger(name: str) -> logging.Logger:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    fmt = logging.Formatter(
        "%(asctime)s  %(levelname)-8s  [%(name)s]  %(message)s",
        datefmt="%H:%M:%S",
    )
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    console.setFormatter(fmt)
    logger.addHandler(console)
    try:
        file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(fmt)
        logger.addHandler(file_handler)
    except OSError:
        logger.debug("Não foi possível abrir arquivo de log", exc_info=True)
    return logger


class VelaLogger:
    def __init__(self, name: str):
        normalized = name if name.startswith("vela.") else f"vela.{name}"
        self._logger = _setup_logger(normalized)

    def info(self, msg: str):
        self._logger.info(msg)

    def warning(self, msg: str):
        self._logger.warning(msg)

    def error(self, msg: str):
        self._logger.error(msg)

    def debug(self, msg: str):
        self._logger.debug(msg)

    def exception(self, msg: str):
        self._logger.exception(msg)
