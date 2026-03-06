from __future__ import annotations

from enum import Enum


class StageName(str, Enum):
    INIT = "init"
    METADATA = "metadata"
    SUBTITLES = "subtitles"
    ASR = "asr"
    CLEAN_EXPORT = "clean_export"
    CANONICAL = "canonical"
    LLM_REVIEW = "llm_review"
    LLM_POLISH = "llm_polish"
    SUMMARIES = "summaries"
    SOURCE_ATTRIBUTION = "source_attribution"
    WECHAT = "wechat_articles"
    XHS = "xiaohongshu_posts"
    HIGHLIGHTS = "highlights"
    README = "readme"
