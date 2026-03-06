from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT_DIR / "configs"


@dataclass
class AppConfig:
    raw: dict[str, Any]

    @property
    def output_root(self) -> Path:
        path = self.raw["paths"]["output_root"]
        return (ROOT_DIR / path).resolve()

    @property
    def prompts_root(self) -> Path:
        path = self.raw["paths"]["prompts_root"]
        return (ROOT_DIR / path).resolve()

    @property
    def log_level(self) -> str:
        env = os.getenv("VIDEO_TO_ASSETS_LOG_LEVEL")
        if env:
            return env.upper()
        return str(self.raw["app"].get("log_level", "INFO")).upper()

    @property
    def resume_enabled(self) -> bool:
        return bool(self.raw["app"].get("resume_enabled", True))

    @property
    def subtitle_language_priority(self) -> list[str]:
        return list(self.raw["subtitle"].get("language_priority", ["zh", "en"]))

    @property
    def allow_auto_subtitles(self) -> bool:
        return bool(self.raw["subtitle"].get("allow_auto_subtitles", True))

    @property
    def min_valid_entries(self) -> int:
        return int(self.raw["subtitle"].get("min_valid_entries", 8))

    @property
    def max_duplicate_line_ratio(self) -> float:
        return float(self.raw["subtitle"].get("max_duplicate_line_ratio", 0.7))

    @property
    def asr_model(self) -> str:
        return str(self.raw["asr"].get("model", "large-v3"))

    @property
    def asr_language(self) -> str:
        return str(self.raw["asr"].get("language", "zh"))

    @property
    def asr_device(self) -> str:
        return str(self.raw["asr"].get("device", "auto"))

    @property
    def asr_compute_type(self) -> str:
        return str(self.raw["asr"].get("compute_type", "auto"))

    @property
    def asr_command_candidates(self) -> list[str]:
        return list(self.raw["asr"].get("command_candidates", ["whisper"]))

    @property
    def allow_placeholder_transcript(self) -> bool:
        return bool(self.raw["asr"].get("allow_placeholder_transcript", True))

    @property
    def llm_provider(self) -> str:
        return str(self.raw["llm"].get("provider", "openai"))

    @property
    def llm_model(self) -> str:
        return str(self.raw["llm"].get("model", "gpt-4.1-mini"))

    @property
    def llm_temperature(self) -> float:
        return float(self.raw["llm"].get("temperature", 0.2))

    @property
    def llm_max_input_chars(self) -> int:
        return int(self.raw["llm"].get("max_input_chars", 48000))

    @property
    def llm_use_mock_without_api_key(self) -> bool:
        env = os.getenv("VIDEO_TO_ASSETS_USE_MOCK_LLM")
        if env is not None:
            return env.lower() in {"1", "true", "yes", "on"}
        return bool(self.raw["llm"].get("use_mock_without_api_key", True))

    @property
    def yt_dlp_bin(self) -> str:
        return str(self.raw["external_tools"].get("yt_dlp_bin", "yt-dlp"))


_cached_config: AppConfig | None = None


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Invalid YAML root in {path}")
    return data


def load_config(force_reload: bool = False) -> AppConfig:
    global _cached_config
    if _cached_config is not None and not force_reload:
        return _cached_config

    load_dotenv(ROOT_DIR / ".env", override=False)

    merged: dict[str, Any] = {}
    for name in ["app.yaml", "paths.yaml", "models.yaml", "platforms.yaml"]:
        file_data = _load_yaml(CONFIG_DIR / name)
        for k, v in file_data.items():
            if isinstance(v, dict) and isinstance(merged.get(k), dict):
                merged[k] = {**merged[k], **v}
            else:
                merged[k] = v

    _cached_config = AppConfig(raw=merged)
    return _cached_config
