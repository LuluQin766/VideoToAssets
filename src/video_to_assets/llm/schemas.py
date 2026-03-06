from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class LLMResponse:
    text: str
    mode: str
    raw: dict[str, Any]
