from __future__ import annotations

import json
from pathlib import Path

from video_to_assets.asr.segment_parser import parse_srt_to_transcript
from video_to_assets.config import AppConfig
from video_to_assets.models.transcript import Transcript, TranscriptSegment
from video_to_assets.utils.subprocess import CommandRunner


class WhisperRunner:
    def __init__(self, config: AppConfig, runner: CommandRunner, logger=None):
        self.config = config
        self.runner = runner
        self.logger = logger

    def run(self, audio_path: Path, asr_dir: Path) -> tuple[Path, Path, bool]:
        """Return (srt_path, json_path, used_placeholder)."""
        asr_dir.mkdir(parents=True, exist_ok=True)

        for cmd_name in self.config.asr_command_candidates:
            if not self.runner.which(cmd_name):
                continue
            try:
                self._run_with_command(cmd_name, audio_path, asr_dir)
                srt_path = self._find_srt(asr_dir)
                if srt_path:
                    json_path = asr_dir / "whisper_raw.json"
                    transcript = parse_srt_to_transcript(srt_path, source="asr")
                    json_path.write_text(
                        json.dumps(transcript.to_dict(), ensure_ascii=False, indent=2),
                        encoding="utf-8",
                    )
                    final_srt = asr_dir / "whisper_raw.srt"
                    if srt_path != final_srt:
                        final_srt.write_text(srt_path.read_text(encoding="utf-8", errors="ignore"), encoding="utf-8")
                        srt_path = final_srt
                    return srt_path, json_path, False
            except Exception as exc:
                if self.logger:
                    self.logger.warning("ASR command %s failed: %s", cmd_name, exc)

        if not self.config.allow_placeholder_transcript:
            raise RuntimeError("ASR failed and placeholder transcript disabled")
        return self.create_placeholder(asr_dir)

    def _run_with_command(self, command_name: str, audio_path: Path, out_dir: Path) -> None:
        if command_name == "whisper-ctranslate2":
            command = [
                command_name,
                str(audio_path),
                "--model",
                self.config.asr_model,
                "--output_dir",
                str(out_dir),
                "--output_format",
                "srt",
                "--language",
                self.config.asr_language,
            ]
            if self.config.asr_device != "auto":
                command += ["--device", self.config.asr_device]
            if self.config.asr_compute_type != "auto":
                command += ["--compute_type", self.config.asr_compute_type]
        elif command_name == "whisper":
            command = [
                command_name,
                str(audio_path),
                "--model",
                self.config.asr_model,
                "--output_dir",
                str(out_dir),
                "--output_format",
                "srt",
                "--language",
                self.config.asr_language,
            ]
        else:
            command = [command_name, str(audio_path)]
        self.runner.run(command, timeout=7200, check=True)

    def _find_srt(self, out_dir: Path) -> Path | None:
        candidates = sorted(out_dir.glob("*.srt"))
        return candidates[0] if candidates else None

    def create_placeholder(self, asr_dir: Path, reason: str | None = None) -> tuple[Path, Path, bool]:
        srt_path = asr_dir / "whisper_raw.srt"
        json_path = asr_dir / "whisper_raw.json"

        message = "[ASR placeholder] 未检测到可用 Whisper 或音频下载失败，请配置环境后重跑。"
        if reason:
            message += f" 原因: {reason[:180]}"

        segment = TranscriptSegment(
            start=0.0,
            end=8.0,
            text=message,
            source="asr_placeholder",
        )
        transcript = Transcript(segments=[segment], source="asr_placeholder")

        srt_path.write_text(
            f"1\n00:00:00,000 --> 00:00:08,000\n{message}\n",
            encoding="utf-8",
        )
        json_path.write_text(
            json.dumps(transcript.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        if self.logger:
            self.logger.warning("ASR placeholder transcript generated at %s", srt_path)
        return srt_path, json_path, True
