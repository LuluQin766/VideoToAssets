from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


class OutputRegistry:
    def __init__(self, status_file: Path):
        self.status_file = status_file
        self.status_file.parent.mkdir(parents=True, exist_ok=True)
        if self.status_file.exists():
            self._data = self._load()
        else:
            self._data = {
                "created_at": self._now(),
                "updated_at": self._now(),
                "context": {},
                "stages": {},
            }
            self.flush()

    def _now(self) -> str:
        return datetime.utcnow().isoformat() + "Z"

    def _load(self) -> dict[str, Any]:
        with self.status_file.open("r", encoding="utf-8") as f:
            return json.load(f)

    def set_context(self, **kwargs: Any) -> None:
        self._data.setdefault("context", {}).update(kwargs)
        self._touch()

    def stage_start(self, stage: str) -> None:
        stage_data = self._data.setdefault("stages", {}).setdefault(stage, {})
        stage_data.update(
            {
                "status": "running",
                "started_at": self._now(),
                "ended_at": None,
                "error": None,
            }
        )
        self._touch()

    def stage_success(self, stage: str, outputs: list[str] | None = None, notes: str | None = None) -> None:
        stage_data = self._data.setdefault("stages", {}).setdefault(stage, {})
        stage_data.update(
            {
                "status": "success",
                "ended_at": self._now(),
                "outputs": outputs or [],
                "notes": notes,
            }
        )
        self._touch()

    def stage_failed(self, stage: str, error: str) -> None:
        stage_data = self._data.setdefault("stages", {}).setdefault(stage, {})
        stage_data.update(
            {
                "status": "failed",
                "ended_at": self._now(),
                "error": error,
            }
        )
        self._touch()

    def stage_skipped(self, stage: str, reason: str) -> None:
        stage_data = self._data.setdefault("stages", {}).setdefault(stage, {})
        stage_data.update(
            {
                "status": "skipped",
                "ended_at": self._now(),
                "notes": reason,
            }
        )
        self._touch()

    def _touch(self) -> None:
        self._data["updated_at"] = self._now()
        self.flush()

    def flush(self) -> None:
        with self.status_file.open("w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    @property
    def data(self) -> dict[str, Any]:
        return self._data
