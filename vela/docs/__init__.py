# SPDX-License-Identifier: MPL-2.0
"""Offline Vela Docs assets and optional OpenAPI metadata."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Callable

STATIC_DIR = Path(__file__).parent / "static"


def documented(**metadata: Any) -> Callable:
    """Attach OpenAPI operation fields without changing handler invocation.

    Use tags, parameters, requestBody or responses to describe information that
    cannot be inferred from Vela's Request-based handler signature.
    """

    def decorate(handler: Callable) -> Callable:
        handler.__vela_openapi__ = deepcopy(metadata)
        return handler

    return decorate
