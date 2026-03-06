from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from video_to_assets.collectors.yt_dlp_adapter import YtDlpAdapter
from video_to_assets.validators.subtitle_validator import SubtitleValidator, ValidationResult


@dataclass
class SubtitleFetchResult:
    source: str
    selected_file: Path | None
    files: list[Path]
    validation: dict[str, dict]
    need_asr_fallback: bool


class SubtitleFetcher:
    def __init__(
        self,
        adapter: YtDlpAdapter,
        validator: SubtitleValidator,
        language_priority: list[str],
        allow_auto: bool,
        logger=None,
    ):
        self.adapter = adapter
        self.validator = validator
        self.language_priority = language_priority
        self.allow_auto = allow_auto
        self.logger = logger

    def fetch(self, url: str, subtitles_dir: Path, log_path: Path) -> SubtitleFetchResult:
        files = self.adapter.download_subtitles(
            url=url,
            output_dir=subtitles_dir,
            language_priority=self.language_priority,
            include_auto=self.allow_auto,
        )

        validation: dict[str, dict] = {}
        best_file: Path | None = None
        best_score = -1.0
        source = "none"

        for f in files:
            result: ValidationResult = self.validator.validate(f)
            validation[f.name] = {
                "valid": result.valid,
                "reasons": result.reasons,
                "metrics": result.metrics,
            }
            if result.valid:
                score = float(result.metrics.get("entry_count", 0)) - 100 * float(
                    result.metrics.get("duplicate_ratio", 1)
                )
                if score > best_score:
                    best_score = score
                    best_file = f

        if best_file:
            name = best_file.name.lower()
            source = "auto_subtitle" if "auto" in name else "manual_subtitle"
            need_asr = False
        else:
            need_asr = True

        payload = {
            "source": source,
            "selected_file": str(best_file) if best_file else None,
            "files": [str(x) for x in files],
            "validation": validation,
            "need_asr_fallback": need_asr,
        }
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

        return SubtitleFetchResult(
            source=source,
            selected_file=best_file,
            files=files,
            validation=validation,
            need_asr_fallback=need_asr,
        )
