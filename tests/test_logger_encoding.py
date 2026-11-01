# SPDX-License-Identifier: MPL-2.0
"""Regression tests for console encoding and headless Windows builds."""

import io
import logging
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from vela.log import logger as logger_module


class LoggerEncodingTests(unittest.TestCase):
    def _new_logger(self, root):
        with (
            patch.object(logger_module, "LOG_DIR", root),
            patch.object(logger_module, "LOG_FILE", root / "vela.log"),
        ):
            return logger_module.VelaLogger("encoding_" + uuid4().hex)

    def _close_logger(self, logger):
        for handler in list(logger._logger.handlers):
            logger._logger.removeHandler(handler)
            handler.close()

    def test_cp1252_console_escapes_unicode_without_losing_file_log(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = io.BytesIO()
            console = io.TextIOWrapper(output, encoding="cp1252", errors="strict")
            with patch.object(logger_module.sys, "stderr", console):
                log = self._new_logger(root)
                try:
                    log.debug("Lifecycle → configured 🚀")
                finally:
                    self._close_logger(log)
            self.assertIn(
                "Lifecycle \\u2192 configured \\U0001f680",
                output.getvalue().decode("cp1252"),
            )
            file_log = (root / "vela.log").read_text(encoding="utf-8")
            self.assertIn("Lifecycle → configured 🚀", file_log)

    def test_ascii_console_falls_back_to_escaped_text(self):
        with tempfile.TemporaryDirectory() as directory:
            output = io.BytesIO()
            console = io.TextIOWrapper(output, encoding="ascii", errors="strict")
            with patch.object(logger_module.sys, "stderr", console):
                log = self._new_logger(Path(directory))
                try:
                    log.info("ação → running")
                finally:
                    self._close_logger(log)
            self.assertIn("a\\xe7\\xe3o \\u2192 running", output.getvalue().decode("ascii"))

    def test_windowed_app_without_stderr_still_writes_utf8_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(logger_module.sys, "stderr", None):
                log = self._new_logger(root)
                try:
                    self.assertEqual(len(log._logger.handlers), 1)
                    self.assertIsInstance(log._logger.handlers[0], logging.FileHandler)
                    log.debug("Lifecycle → configured")
                finally:
                    self._close_logger(log)
            file_log = (root / "vela.log").read_text(encoding="utf-8")
            self.assertIn("Lifecycle → configured", file_log)


if __name__ == "__main__":
    unittest.main()
