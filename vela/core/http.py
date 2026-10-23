# SPDX-License-Identifier: MPL-2.0
"""Contratos HTTP explícitos e serialização centralizada."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import date, datetime
from enum import Enum
from typing import Any, Mapping
from uuid import UUID


@dataclass(frozen=True, slots=True)
class Request:
    method: str
    path: str
    query: Mapping[str, str]
    headers: Mapping[str, str]
    json: Any = None
    body: bytes | None = None


@dataclass(slots=True)
class Response:
    body: Any = None
    status: int = 200
    headers: dict[str, str] = field(default_factory=dict)
    content_type: str | None = None


class ResponseEncoder:
    """Converte respostas Vela em bytes/strings aceitos pelo Bottle."""

    @classmethod
    def to_jsonable(cls, value: Any) -> Any:
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="replace")
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        if isinstance(value, UUID):
            return str(value)
        if isinstance(value, Enum):
            return cls.to_jsonable(value.value)
        if is_dataclass(value) and not isinstance(value, type):
            return cls.to_jsonable(asdict(value))
        if hasattr(value, "model_dump"):
            return cls.to_jsonable(value.model_dump(mode="json"))
        if isinstance(value, Mapping):
            return {str(key): cls.to_jsonable(item) for key, item in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [cls.to_jsonable(item) for item in value]
        return str(value)

    @classmethod
    def json_dumps(cls, value: Any) -> str:
        return json.dumps(cls.to_jsonable(value), ensure_ascii=False)
