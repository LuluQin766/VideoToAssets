from __future__ import annotations

from video_to_assets.models.source_input import SourceInput
from video_to_assets.pipeline.orchestrator import Orchestrator


def run_single_url(url: str, resume: bool = True, tasks: list[str] | None = None) -> None:
    orchestrator = Orchestrator()
    state = orchestrator.run(url=url, resume=resume, tasks=tasks)
    print(f"Done. Output: {state.paths.root}")


def run_single_source(source: SourceInput, resume: bool = True, tasks: list[str] | None = None) -> None:
    orchestrator = Orchestrator()
    state = orchestrator.run_source(source=source, resume=resume, tasks=tasks)
    print(f"Done. Output: {state.paths.root}")
