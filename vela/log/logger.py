# SPDX-License-Identifier: MPL-2.0
"""Logging padronizado do Vela."""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime
from pathlib import Path


def _log_dir() -> Path:
    override = os.environ.get("VELA_LOG_DIR")
    if override:
        return Path(override).expanduser()
    if getattr(sys, "frozen", False):
        if sys.platform == "win32":
            root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        else:
            root = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state"))
        return root / "vela" / "logs"
    return Path.cwd() / "logs"


LOG_DIR = _log_dir()
LOG_FILE = LOG_DIR / f"vela_{datetime.now().strftime('%Y-%m-%d')}.log"


class _SafeConsoleHandler(logging.StreamHandler):
    """Keep console logging working even with legacy Windows encodings."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = self.format(record) + self.terminator
            try:
                self.stream.write(message)
            except UnicodeEncodeError:
                # ASCII escapes work on cp1252 and other limited console encodings.
                safe_message = message.encode("ascii", errors="backslashreplace").decode("ascii")
                self.stream.write(safe_message)
            self.flush()
        except Exception:
            self.handleError(record)


def _setup_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    fmt = logging.Formatter(
        "%(asctime)s  %(levelname)-8s  [%(name)s]  %(message)s",
        datefmt="%H:%M:%S",
    )
    # --windowed PyInstaller executables may have no stderr stream.
    if sys.stderr is not None:
        console = _SafeConsoleHandler(sys.stderr)
        console.setLevel(logging.DEBUG)
        console.setFormatter(fmt)
        logger.addHandler(console)
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
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
