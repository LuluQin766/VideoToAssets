from __future__ import annotations

from typing import Any


def merge_metadata(base: dict[str, Any], override: dict[str, Any] | None = None) -> dict[str, Any]:
    merged = dict(base)
    if override:
        merged.update({k: v for k, v in override.items() if v is not None})
    return merged
