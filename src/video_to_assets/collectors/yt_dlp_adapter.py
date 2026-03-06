from __future__ import annotations

import json
from pathlib import Path

from video_to_assets.config import AppConfig
from video_to_assets.utils.subprocess import CommandRunner


class YtDlpAdapter:
    def __init__(self, config: AppConfig, runner: CommandRunner):
        self.config = config
        self.runner = runner
        self.bin = config.yt_dlp_bin

    def extract_metadata(self, url: str) -> dict:
        command = [
            self.bin,
            "--dump-single-json",
            "--skip-download",
            "--no-warnings",
            url,
        ]
        result = self.runner.run(command, timeout=180, check=True)
        raw = result.stdout.strip()
        if not raw:
            raise RuntimeError("yt-dlp returned empty metadata")

        for line in reversed(raw.splitlines()):
            line = line.strip()
            if line.startswith("{") and line.endswith("}"):
                return json.loads(line)
        return json.loads(raw)

    def download_thumbnail(self, url: str, output_file: Path) -> Path | None:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        command = [
            self.bin,
            "--skip-download",
            "--write-thumbnail",
            "--convert-thumbnails",
            "jpg",
            "--output",
            str(output_file.with_suffix("")),
            url,
        ]
        try:
            self.runner.run(command, timeout=180, check=True)
        except Exception:
            return None

        for p in sorted(output_file.parent.glob(output_file.stem + "*.jpg")):
            if p.is_file():
                if p != output_file:
                    p.rename(output_file)
                return output_file
        return None

    def download_subtitles(
        self,
        url: str,
        output_dir: Path,
        language_priority: list[str],
        include_auto: bool,
    ) -> list[Path]:
        output_dir.mkdir(parents=True, exist_ok=True)
        lang_expr = ",".join(language_priority)
        base_template = str(output_dir / "original.%(ext)s")

        files_before = set(output_dir.glob("*"))

        command = [
            self.bin,
            "--skip-download",
            "--write-subs",
            "--sub-langs",
            lang_expr,
            "--convert-subs",
            "srt",
            "--output",
            base_template,
            url,
        ]
        self.runner.run(command, timeout=300, check=False)

        if include_auto:
            auto_command = [
                self.bin,
                "--skip-download",
                "--write-auto-subs",
                "--sub-langs",
                lang_expr,
                "--convert-subs",
                "srt",
                "--output",
                str(output_dir / "auto.%(ext)s"),
                url,
            ]
            self.runner.run(auto_command, timeout=300, check=False)

        files_after = set(output_dir.glob("*"))
        new_files = [p for p in files_after - files_before if p.is_file()]

        if not new_files:
            new_files = [p for p in output_dir.glob("*.srt") if p.is_file()]
        if not new_files:
            new_files = [p for p in output_dir.glob("*.vtt") if p.is_file()]

        return sorted(new_files)

    def download_audio(self, url: str, output_dir: Path) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        template = str(output_dir / "audio.%(ext)s")
        command = [
            self.bin,
            "-f",
            "bestaudio/best",
            "-x",
            "--audio-format",
            "m4a",
            "--output",
            template,
            url,
        ]
        self.runner.run(command, timeout=600, check=True)

        candidates = sorted(output_dir.glob("audio.*"))
        if not candidates:
            raise RuntimeError("Audio download finished but no audio file found")
        return candidates[0]
