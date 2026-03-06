from __future__ import annotations

import json
from pathlib import Path

from video_to_assets.asr.whisper_runner import WhisperRunner
from video_to_assets.canonical.canonical_content import CanonicalContent, TimestampSegment
from video_to_assets.canonical.normalizer import build_canonical
from video_to_assets.canonical.writer import write_canonical_outputs
from video_to_assets.collectors.audio_fetcher import AudioFetcher
from video_to_assets.collectors.subtitle_fetcher import SubtitleFetcher
from video_to_assets.collectors.video_metadata import VideoMetadataCollector
from video_to_assets.collectors.yt_dlp_adapter import YtDlpAdapter
from video_to_assets.config import load_config
from video_to_assets.llm.client import LLMClient
from video_to_assets.llm.quality_review import QualityReviewer
from video_to_assets.llm.transcript_polisher import TranscriptPolisher
from video_to_assets.models.source_input import SourceInput
from video_to_assets.models.video_info import VideoInfo
from video_to_assets.pipeline.source_router import SourceRouter
from video_to_assets.pipeline.stages import StageName
from video_to_assets.pipeline.state import PipelineState
from video_to_assets.pipeline.task_router import (
    TASK_HIGHLIGHTS,
    TASK_SUMMARY,
    TASK_WECHAT,
    TASK_XHS,
    normalize_tasks,
    should_run,
)
from video_to_assets.postprocess.article_generators import (
    WechatArticleGenerator,
    XiaohongshuPostGenerator,
)
from video_to_assets.postprocess.highlight_miner import HighlightMiner
from video_to_assets.postprocess.readme_builder import VideoReadmeBuilder
from video_to_assets.postprocess.source_profile import SourceProfileBuilder
from video_to_assets.postprocess.summary_generator import SummaryGenerator
from video_to_assets.preprocess.subtitle_cleaner import clean_transcript
from video_to_assets.preprocess.subtitle_normalizer import normalize_transcript
from video_to_assets.preprocess.text_converter import export_transcript_files
from video_to_assets.preprocess.transcript_builder import merge_adjacent_segments
from video_to_assets.storage.output_registry import OutputRegistry
from video_to_assets.storage.path_manager import PathManager
from video_to_assets.utils.logger import setup_logger
from video_to_assets.utils.subprocess import CommandRunner
from video_to_assets.validators.subtitle_validator import SubtitleValidator


class Orchestrator:
    def __init__(self):
        self.config = load_config()

    def run(self, url: str, resume: bool = True, tasks: list[str] | None = None) -> PipelineState:
        selected_tasks = normalize_tasks(tasks)

        path_manager = PathManager(self.config.output_root)
        video_id = path_manager.infer_video_id(url)
        paths = path_manager.ensure(video_id)

        logger = setup_logger(paths.logs / "pipeline.log", self.config.log_level)
        runner = CommandRunner(logger=logger)
        registry = OutputRegistry(paths.logs / "stage_status.json")
        registry.set_context(url=url, video_id=video_id, tasks=sorted(selected_tasks), input_type="video", source_type="video", source_id=video_id)

        state = PipelineState(
            url=url,
            video_id=video_id,
            paths=paths,
            tasks=selected_tasks,
            input_type="video",
            source_type="video",
            source_id=video_id,
        )

        adapter = YtDlpAdapter(self.config, runner)
        metadata_collector = VideoMetadataCollector(adapter, logger=logger)
        subtitle_validator = SubtitleValidator(
            min_entries=self.config.min_valid_entries,
            max_duplicate_line_ratio=self.config.max_duplicate_line_ratio,
        )
        subtitle_fetcher = SubtitleFetcher(
            adapter=adapter,
            validator=subtitle_validator,
            language_priority=self.config.subtitle_language_priority,
            allow_auto=self.config.allow_auto_subtitles,
            logger=logger,
        )
        audio_fetcher = AudioFetcher(adapter)
        whisper_runner = WhisperRunner(self.config, runner=runner, logger=logger)

        llm_client = LLMClient(self.config, logger=logger)
        quality_reviewer = QualityReviewer(self.config, llm_client)
        polisher = TranscriptPolisher(self.config, llm_client)
        summary_generator = SummaryGenerator(self.config, llm_client)
        source_builder = SourceProfileBuilder(self.config, llm_client)
        wechat_generator = WechatArticleGenerator(self.config, llm_client)
        xhs_generator = XiaohongshuPostGenerator(self.config, llm_client)
        highlight_miner = HighlightMiner()
        readme_builder = VideoReadmeBuilder()

        registry.stage_start(StageName.INIT.value)
        registry.stage_success(StageName.INIT.value, outputs=[str(paths.root)], notes=f"tasks={','.join(sorted(selected_tasks))}")

        cleaned_plain = paths.subtitles_clean / "cleaned_plain.txt"
        cleaned_json = paths.subtitles_clean / "cleaned.json"

        # -------- Round 1 core dependency chain --------
        self._run_metadata_stage(
            state=state,
            resume=resume,
            registry=registry,
            collector=metadata_collector,
            logger=logger,
        )
        self._run_subtitle_asr_clean_chain(
            state=state,
            url=url,
            resume=resume,
            registry=registry,
            subtitle_fetcher=subtitle_fetcher,
            audio_fetcher=audio_fetcher,
            whisper_runner=whisper_runner,
            logger=logger,
        )

        canonical = self._run_canonical_stage_for_video(
            state=state,
            resume=resume,
            registry=registry,
            cleaned_plain=cleaned_plain,
            cleaned_json=cleaned_json,
            logger=logger,
        )
        if canonical:
            state.source_id = canonical.source_id
            state.source_type = canonical.source_type
            state.source_metadata_complete = self._metadata_complete(canonical)
            registry.set_context(
                source_id=state.source_id,
                source_type=state.source_type,
                source_metadata_complete=state.source_metadata_complete,
            )

        cleaned_plain_for_tasks = paths.normalized / "clean_text.txt"
        if not cleaned_plain_for_tasks.exists():
            cleaned_plain_for_tasks = cleaned_plain

        # Keep round1 llm outputs available for complete asset package.
        self._run_round1_llm(
            resume=resume,
            registry=registry,
            cleaned_plain=cleaned_plain_for_tasks,
            quality_reviewer=quality_reviewer,
            polisher=polisher,
            llm_review_dir=paths.llm_review,
            logger=logger,
        )

        # -------- Round 2 tasks --------
        has_min_inputs = cleaned_plain_for_tasks.exists()

        if should_run(selected_tasks, TASK_SUMMARY):
            try:
                registry.stage_start(StageName.SUMMARIES.value)
                if not has_min_inputs:
                    raise RuntimeError("summary requires cleaned text")
                if resume and (paths.summaries / "executive_summary.md").exists():
                    registry.stage_success(
                        StageName.SUMMARIES.value,
                        outputs=[str(paths.summaries / "executive_summary.md")],
                        notes="resume_hit",
                    )
                else:
                    summary_outputs = summary_generator.run(cleaned_plain_for_tasks, paths.summaries)
                    registry.stage_success(StageName.SUMMARIES.value, outputs=[str(x) for x in summary_outputs.values()])
            except Exception as exc:
                logger.exception("summaries stage failed")
                registry.stage_failed(StageName.SUMMARIES.value, str(exc))

        if should_run(selected_tasks, TASK_SUMMARY) or should_run(selected_tasks, TASK_WECHAT):
            try:
                registry.stage_start(StageName.SOURCE_ATTRIBUTION.value)
                if not cleaned_plain_for_tasks.exists():
                    raise RuntimeError("source attribution requires cleaned text")
                if resume and (paths.source_attribution / "source_profile.json").exists():
                    registry.stage_success(
                        StageName.SOURCE_ATTRIBUTION.value,
                        outputs=[str(paths.source_attribution / "source_profile.json")],
                        notes="resume_hit",
                    )
                else:
                    if canonical is None:
                        raise RuntimeError("source attribution requires canonical content")
                    source_outputs = source_builder.run(canonical, cleaned_plain_for_tasks, paths.source_attribution)
                    registry.stage_success(StageName.SOURCE_ATTRIBUTION.value, outputs=[str(x) for x in source_outputs.values()])
            except Exception as exc:
                logger.exception("source attribution stage failed")
                registry.stage_failed(StageName.SOURCE_ATTRIBUTION.value, str(exc))

        if should_run(selected_tasks, TASK_WECHAT):
            try:
                registry.stage_start(StageName.WECHAT.value)
                if not cleaned_plain_for_tasks.exists():
                    raise RuntimeError("wechat requires cleaned text")
                summary_file = paths.summaries / "executive_summary.md"
                source_profile_file = paths.source_attribution / "source_profile.json"
                if resume and (paths.articles_wechat / "article_01.md").exists() and (paths.articles_wechat / "article_03.md").exists():
                    registry.stage_success(
                        StageName.WECHAT.value,
                        outputs=[str(paths.articles_wechat / "article_01.md"), str(paths.articles_wechat / "article_03.md")],
                        notes="resume_hit",
                    )
                else:
                    wechat_outputs = wechat_generator.run(
                        cleaned_plain_file=cleaned_plain_for_tasks,
                        summary_file=summary_file,
                        source_profile_file=source_profile_file,
                        output_dir=paths.articles_wechat,
                        metadata=state.metadata,
                        source_title=canonical.title if canonical else None,
                        source_type=canonical.source_type if canonical else None,
                    )
                    registry.stage_success(StageName.WECHAT.value, outputs=[str(x) for x in wechat_outputs.values()])
            except Exception as exc:
                logger.exception("wechat stage failed")
                registry.stage_failed(StageName.WECHAT.value, str(exc))

        if should_run(selected_tasks, TASK_XHS):
            try:
                registry.stage_start(StageName.XHS.value)
                if not cleaned_plain_for_tasks.exists():
                    raise RuntimeError("xhs requires cleaned text")
                if resume and (paths.articles_xiaohongshu / "xhs_01.md").exists() and (paths.articles_xiaohongshu / "xhs_05.md").exists():
                    registry.stage_success(
                        StageName.XHS.value,
                        outputs=[str(paths.articles_xiaohongshu / "xhs_01.md"), str(paths.articles_xiaohongshu / "xhs_05.md")],
                        notes="resume_hit",
                    )
                else:
                    xhs_outputs = xhs_generator.run(
                        cleaned_plain_for_tasks,
                        paths.articles_xiaohongshu,
                        state.metadata,
                        source_profile_file=paths.source_attribution / "source_profile.json",
                        source_title=canonical.title if canonical else None,
                        source_type=canonical.source_type if canonical else None,
                    )
                    registry.stage_success(StageName.XHS.value, outputs=[str(x) for x in xhs_outputs.values()])
            except Exception as exc:
                logger.exception("xhs stage failed")
                registry.stage_failed(StageName.XHS.value, str(exc))

        if should_run(selected_tasks, TASK_HIGHLIGHTS):
            try:
                registry.stage_start(StageName.HIGHLIGHTS.value)
                if not cleaned_json.exists():
                    raise RuntimeError("highlights requires cleaned.json")
                if resume and (paths.highlights / "top10_final.json").exists():
                    registry.stage_success(
                        StageName.HIGHLIGHTS.value,
                        outputs=[str(paths.highlights / "top10_final.json")],
                        notes="resume_hit",
                    )
                else:
                    highlight_outputs = highlight_miner.run(cleaned_json, paths.highlights, source_type="video")
                    registry.stage_success(StageName.HIGHLIGHTS.value, outputs=[str(x) for x in highlight_outputs.values()])
            except Exception as exc:
                logger.exception("highlights stage failed")
                registry.stage_failed(StageName.HIGHLIGHTS.value, str(exc))

        # per-video readme / asset index
        try:
            registry.stage_start(StageName.README.value)
            readme_builder.build(state=state, stage_status=registry.data, output_file=paths.readme)
            registry.stage_success(StageName.README.value, outputs=[str(paths.readme)])
        except Exception as exc:
            logger.exception("readme stage failed")
            registry.stage_failed(StageName.README.value, str(exc))

        return state

    def run_source(self, source: SourceInput, resume: bool = True, tasks: list[str] | None = None) -> PipelineState:
        if source.input_type == "video":
            if not source.url:
                raise ValueError("video input requires url")
            return self.run(url=source.url, resume=resume, tasks=tasks)

        selected_tasks = normalize_tasks(tasks)
        path_manager = PathManager(self.config.output_root)
        router = SourceRouter(self.config.output_root)
        canonical = router.route(source)

        paths = path_manager.ensure_source(canonical.source_id, include_video_dirs=False)
        logger = setup_logger(paths.logs / "pipeline.log", self.config.log_level)
        registry = OutputRegistry(paths.logs / "stage_status.json")
        registry.set_context(
            input_type=source.input_type,
            source_type=canonical.source_type,
            source_id=canonical.source_id,
            tasks=sorted(selected_tasks),
        )

        state = PipelineState(
            url=source.source_url or source.url or (str(source.file_path) if source.file_path else ""),
            video_id=canonical.source_id,
            paths=paths,
            tasks=selected_tasks,
            input_type=source.input_type,
            source_type=canonical.source_type,
            source_id=canonical.source_id,
        )

        registry.stage_start(StageName.INIT.value)
        registry.stage_success(StageName.INIT.value, outputs=[str(paths.root)], notes=f"tasks={','.join(sorted(selected_tasks))}")

        canonical = self._run_canonical_stage_for_source(
            canonical=canonical,
            source=source,
            state=state,
            resume=resume,
            registry=registry,
            logger=logger,
        )
        state.source_metadata_complete = self._metadata_complete(canonical)
        registry.set_context(source_metadata_complete=state.source_metadata_complete)

        cleaned_plain = paths.normalized / "clean_text.txt"

        llm_client = LLMClient(self.config, logger=logger)
        quality_reviewer = QualityReviewer(self.config, llm_client)
        polisher = TranscriptPolisher(self.config, llm_client)
        summary_generator = SummaryGenerator(self.config, llm_client)
        source_builder = SourceProfileBuilder(self.config, llm_client)
        wechat_generator = WechatArticleGenerator(self.config, llm_client)
        xhs_generator = XiaohongshuPostGenerator(self.config, llm_client)
        highlight_miner = HighlightMiner()
        readme_builder = VideoReadmeBuilder()

        self._run_round1_llm(
            resume=resume,
            registry=registry,
            cleaned_plain=cleaned_plain,
            quality_reviewer=quality_reviewer,
            polisher=polisher,
            llm_review_dir=paths.llm_review,
            logger=logger,
        )

        if should_run(selected_tasks, TASK_SUMMARY):
            try:
                registry.stage_start(StageName.SUMMARIES.value)
                if not cleaned_plain.exists():
                    raise RuntimeError("summary requires cleaned text")
                if resume and (paths.summaries / "executive_summary.md").exists():
                    registry.stage_success(
                        StageName.SUMMARIES.value,
                        outputs=[str(paths.summaries / "executive_summary.md")],
                        notes="resume_hit",
                    )
                else:
                    summary_outputs = summary_generator.run(cleaned_plain, paths.summaries)
                    registry.stage_success(StageName.SUMMARIES.value, outputs=[str(x) for x in summary_outputs.values()])
            except Exception as exc:
                logger.exception("summaries stage failed")
                registry.stage_failed(StageName.SUMMARIES.value, str(exc))

        if should_run(selected_tasks, TASK_SUMMARY) or should_run(selected_tasks, TASK_WECHAT):
            try:
                registry.stage_start(StageName.SOURCE_ATTRIBUTION.value)
                if not cleaned_plain.exists():
                    raise RuntimeError("source attribution requires cleaned text")
                if resume and (paths.source_attribution / "source_profile.json").exists():
                    registry.stage_success(
                        StageName.SOURCE_ATTRIBUTION.value,
                        outputs=[str(paths.source_attribution / "source_profile.json")],
                        notes="resume_hit",
                    )
                else:
                    source_outputs = source_builder.run(canonical, cleaned_plain, paths.source_attribution)
                    registry.stage_success(StageName.SOURCE_ATTRIBUTION.value, outputs=[str(x) for x in source_outputs.values()])
            except Exception as exc:
                logger.exception("source attribution stage failed")
                registry.stage_failed(StageName.SOURCE_ATTRIBUTION.value, str(exc))

        if should_run(selected_tasks, TASK_WECHAT):
            try:
                registry.stage_start(StageName.WECHAT.value)
                if not cleaned_plain.exists():
                    raise RuntimeError("wechat requires cleaned text")
                summary_file = paths.summaries / "executive_summary.md"
                source_profile_file = paths.source_attribution / "source_profile.json"
                if resume and (paths.articles_wechat / "article_01.md").exists() and (paths.articles_wechat / "article_03.md").exists():
                    registry.stage_success(
                        StageName.WECHAT.value,
                        outputs=[str(paths.articles_wechat / "article_01.md"), str(paths.articles_wechat / "article_03.md")],
                        notes="resume_hit",
                    )
                else:
                    wechat_outputs = wechat_generator.run(
                        cleaned_plain_file=cleaned_plain,
                        summary_file=summary_file,
                        source_profile_file=source_profile_file,
                        output_dir=paths.articles_wechat,
                        metadata=None,
                        source_title=canonical.title,
                        source_type=canonical.source_type,
                    )
                    registry.stage_success(StageName.WECHAT.value, outputs=[str(x) for x in wechat_outputs.values()])
            except Exception as exc:
                logger.exception("wechat stage failed")
                registry.stage_failed(StageName.WECHAT.value, str(exc))

        if should_run(selected_tasks, TASK_XHS):
            try:
                registry.stage_start(StageName.XHS.value)
                if not cleaned_plain.exists():
                    raise RuntimeError("xhs requires cleaned text")
                if resume and (paths.articles_xiaohongshu / "xhs_01.md").exists() and (paths.articles_xiaohongshu / "xhs_05.md").exists():
                    registry.stage_success(
                        StageName.XHS.value,
                        outputs=[str(paths.articles_xiaohongshu / "xhs_01.md"), str(paths.articles_xiaohongshu / "xhs_05.md")],
                        notes="resume_hit",
                    )
                else:
                    xhs_outputs = xhs_generator.run(
                        cleaned_plain,
                        paths.articles_xiaohongshu,
                        None,
                        source_profile_file=paths.source_attribution / "source_profile.json",
                        source_title=canonical.title,
                        source_type=canonical.source_type,
                    )
                    registry.stage_success(StageName.XHS.value, outputs=[str(x) for x in xhs_outputs.values()])
            except Exception as exc:
                logger.exception("xhs stage failed")
                registry.stage_failed(StageName.XHS.value, str(exc))

        if should_run(selected_tasks, TASK_HIGHLIGHTS):
            try:
                registry.stage_start(StageName.HIGHLIGHTS.value)
                if resume and (paths.highlights / "top10_final.json").exists():
                    registry.stage_success(
                        StageName.HIGHLIGHTS.value,
                        outputs=[str(paths.highlights / "top10_final.json")],
                        notes="resume_hit",
                    )
                else:
                    highlight_outputs = highlight_miner.run_from_canonical(canonical.source_type, canonical.raw_text, paths.highlights)
                    registry.stage_success(StageName.HIGHLIGHTS.value, outputs=[str(x) for x in highlight_outputs.values()])
            except Exception as exc:
                logger.exception("highlights stage failed")
                registry.stage_failed(StageName.HIGHLIGHTS.value, str(exc))

        try:
            registry.stage_start(StageName.README.value)
            readme_builder.build(state=state, stage_status=registry.data, output_file=paths.readme)
            registry.stage_success(StageName.README.value, outputs=[str(paths.readme)])
        except Exception as exc:
            logger.exception("readme stage failed")
            registry.stage_failed(StageName.README.value, str(exc))

        return state

    def _run_metadata_stage(self, state, resume, registry, collector, logger) -> None:
        metadata_json = state.paths.metadata / "video_info.json"
        try:
            registry.stage_start(StageName.METADATA.value)
            if resume and metadata_json.exists():
                state.metadata = self._load_metadata(metadata_json, fallback_video_id=state.video_id)
                registry.stage_success(StageName.METADATA.value, outputs=[str(metadata_json)], notes="resume_hit")
            else:
                state.metadata = collector.collect(state.url, state.paths.metadata)
                registry.stage_success(
                    StageName.METADATA.value,
                    outputs=[str(state.paths.metadata / "video_info.json"), str(state.paths.metadata / "video_info.md")],
                )
        except Exception as exc:
            logger.exception("metadata stage failed")
            if metadata_json.exists():
                try:
                    state.metadata = self._load_metadata(metadata_json, fallback_video_id=state.video_id)
                except Exception:
                    pass
            registry.stage_failed(StageName.METADATA.value, str(exc))

    def _run_subtitle_asr_clean_chain(self, state, url, resume, registry, subtitle_fetcher, audio_fetcher, whisper_runner, logger) -> None:
        subtitle_log = state.paths.logs / "subtitle_fetch.json"
        asr_srt = state.paths.asr / "whisper_raw.srt"
        asr_json = state.paths.asr / "whisper_raw.json"
        cleaned_plain = state.paths.subtitles_clean / "cleaned_plain.txt"

        try:
            registry.stage_start(StageName.SUBTITLES.value)
            if resume and subtitle_log.exists():
                payload = json.loads(subtitle_log.read_text(encoding="utf-8"))
                selected = payload.get("selected_file")
                if selected and Path(selected).exists():
                    state.subtitle_file = Path(selected)
                state.subtitle_source = payload.get("source", "none")
                state.asr_triggered = bool(payload.get("need_asr_fallback", False))
                registry.set_context(subtitle_source=state.subtitle_source, asr_triggered=state.asr_triggered)
                registry.stage_success(StageName.SUBTITLES.value, outputs=[str(subtitle_log)], notes="resume_hit")
            else:
                result = subtitle_fetcher.fetch(url=url, subtitles_dir=state.paths.subtitles_raw, log_path=subtitle_log)
                state.subtitle_source = result.source
                state.subtitle_file = result.selected_file
                state.asr_triggered = result.need_asr_fallback
                registry.set_context(subtitle_source=state.subtitle_source, asr_triggered=state.asr_triggered)
                registry.stage_success(
                    StageName.SUBTITLES.value,
                    outputs=[str(x) for x in result.files] + [str(subtitle_log)],
                    notes=f"need_asr={result.need_asr_fallback}",
                )
        except Exception as exc:
            logger.exception("subtitle stage failed")
            state.asr_triggered = True
            registry.stage_failed(StageName.SUBTITLES.value, str(exc))

        if state.asr_triggered:
            try:
                registry.stage_start(StageName.ASR.value)
                if resume and asr_srt.exists() and asr_json.exists():
                    state.subtitle_file = asr_srt
                    state.subtitle_source = "asr"
                    try:
                        asr_payload = json.loads(asr_json.read_text(encoding="utf-8"))
                        state.asr_placeholder = asr_payload.get("source") == "asr_placeholder"
                    except Exception:
                        state.asr_placeholder = False
                    registry.set_context(asr_placeholder=state.asr_placeholder)
                    registry.stage_success(StageName.ASR.value, outputs=[str(asr_srt), str(asr_json)], notes="resume_hit")
                else:
                    audio_file = None
                    try:
                        audio_file = audio_fetcher.fetch_audio(url, state.paths.asr)
                        srt_path, json_path, is_placeholder = whisper_runner.run(audio_file, state.paths.asr)
                    except Exception as fetch_or_asr_exc:
                        if not self.config.allow_placeholder_transcript:
                            raise
                        logger.warning("ASR fallback to placeholder due to: %s", fetch_or_asr_exc)
                        srt_path, json_path, is_placeholder = whisper_runner.create_placeholder(
                            state.paths.asr,
                            reason=str(fetch_or_asr_exc),
                        )
                    state.subtitle_file = srt_path
                    state.subtitle_source = "asr"
                    state.asr_placeholder = is_placeholder
                    registry.set_context(asr_placeholder=is_placeholder)
                    registry.stage_success(
                        StageName.ASR.value,
                        outputs=[x for x in [str(audio_file) if audio_file else None, str(srt_path), str(json_path)] if x],
                    )
            except Exception as exc:
                logger.exception("asr stage failed")
                registry.stage_failed(StageName.ASR.value, str(exc))
        else:
            registry.stage_skipped(StageName.ASR.value, "subtitle_valid_no_fallback")

        try:
            registry.stage_start(StageName.CLEAN_EXPORT.value)
            if resume and cleaned_plain.exists():
                registry.stage_success(StageName.CLEAN_EXPORT.value, outputs=[str(cleaned_plain)], notes="resume_hit")
            else:
                source_file = state.subtitle_file
                if source_file is None:
                    raise RuntimeError("No subtitle/asr source file available")
                transcript = normalize_transcript(source_file, source=state.subtitle_source)
                transcript = clean_transcript(transcript)
                transcript = merge_adjacent_segments(transcript)
                title = state.metadata.title if state.metadata else "Video Transcript"
                exported = export_transcript_files(transcript, state.paths.subtitles_clean, state.paths.text_exports, title=title)
                registry.stage_success(StageName.CLEAN_EXPORT.value, outputs=[str(p) for p in exported.values()])
        except Exception as exc:
            logger.exception("clean/export stage failed")
            registry.stage_failed(StageName.CLEAN_EXPORT.value, str(exc))

    def _run_round1_llm(self, resume, registry, cleaned_plain, quality_reviewer, polisher, llm_review_dir, logger) -> None:
        try:
            registry.stage_start(StageName.LLM_REVIEW.value)
            if not cleaned_plain.exists():
                registry.stage_skipped(StageName.LLM_REVIEW.value, "missing_cleaned_plain_text")
            elif resume and (llm_review_dir / "quality_report.md").exists():
                registry.stage_success(
                    StageName.LLM_REVIEW.value,
                    outputs=[str(llm_review_dir / "quality_report.md")],
                    notes="resume_hit",
                )
            else:
                review_outputs = quality_reviewer.run(cleaned_plain, llm_review_dir)
                registry.stage_success(StageName.LLM_REVIEW.value, outputs=[str(x) for x in review_outputs.values()])
        except Exception as exc:
            logger.exception("llm review stage failed")
            registry.stage_failed(StageName.LLM_REVIEW.value, str(exc))

        try:
            registry.stage_start(StageName.LLM_POLISH.value)
            if not cleaned_plain.exists():
                registry.stage_skipped(StageName.LLM_POLISH.value, "missing_cleaned_plain_text")
            elif resume and (llm_review_dir / "polished_full_text.md").exists():
                registry.stage_success(
                    StageName.LLM_POLISH.value,
                    outputs=[str(llm_review_dir / "polished_full_text.md")],
                    notes="resume_hit",
                )
            else:
                polish_outputs = polisher.run(cleaned_plain, llm_review_dir)
                registry.stage_success(StageName.LLM_POLISH.value, outputs=[str(x) for x in polish_outputs.values()])
        except Exception as exc:
            logger.exception("llm polish stage failed")
            registry.stage_failed(StageName.LLM_POLISH.value, str(exc))

    def _run_canonical_stage_for_video(
        self,
        state: PipelineState,
        resume: bool,
        registry: OutputRegistry,
        cleaned_plain: Path,
        cleaned_json: Path,
        logger,
    ) -> CanonicalContent | None:
        canonical_json = state.paths.normalized / "canonical_content.json"
        try:
            registry.stage_start(StageName.CANONICAL.value)
            if resume and canonical_json.exists():
                canonical = self._load_canonical(canonical_json)
                registry.stage_success(StageName.CANONICAL.value, outputs=[str(canonical_json)], notes="resume_hit")
                return canonical
            if not cleaned_plain.exists():
                raise RuntimeError("canonical requires cleaned_plain.txt")

            raw_text = cleaned_plain.read_text(encoding="utf-8", errors="ignore")
            timestamps = self._load_timestamp_segments(cleaned_json) if cleaned_json.exists() else []
            metadata_dict = state.metadata.to_dict() if state.metadata else {}
            canonical = build_canonical(
                source_id=state.video_id,
                source_type="video",
                title=state.metadata.title if state.metadata else "Video Content",
                raw_text=raw_text,
                language=None,
                timestamps=timestamps,
                source_metadata=metadata_dict,
                attribution={
                    "source_type": "video",
                    "source_note": "derived from video pipeline outputs",
                },
                processing_flags={
                    "subtitle_source": state.subtitle_source,
                    "asr_triggered": state.asr_triggered,
                    "asr_placeholder": state.asr_placeholder,
                },
            )

            source_snapshot = self._build_video_snapshot(raw_text, metadata_dict)
            input_info = self._build_input_info(
                input_type="video",
                source_url=state.url,
                source_name=metadata_dict.get("uploader") or metadata_dict.get("channel"),
                author=metadata_dict.get("uploader") or metadata_dict.get("channel"),
                publish_date=metadata_dict.get("upload_date"),
                platform="youtube",
            )
            outputs = write_canonical_outputs(canonical, state.paths.root, source_snapshot, input_info)
            registry.stage_success(StageName.CANONICAL.value, outputs=[str(x) for x in outputs.values()])
            return canonical
        except Exception as exc:
            logger.exception("canonical stage failed")
            registry.stage_failed(StageName.CANONICAL.value, str(exc))
            return None

    def _run_canonical_stage_for_source(
        self,
        canonical: CanonicalContent,
        source: SourceInput,
        state: PipelineState,
        resume: bool,
        registry: OutputRegistry,
        logger,
    ) -> CanonicalContent:
        canonical_json = state.paths.normalized / "canonical_content.json"
        try:
            registry.stage_start(StageName.CANONICAL.value)
            if resume and canonical_json.exists():
                registry.stage_success(StageName.CANONICAL.value, outputs=[str(canonical_json)], notes="resume_hit")
                return canonical
            source_snapshot = self._load_source_snapshot(source)
            input_info = self._build_input_info(
                input_type=source.input_type,
                source_name=source.source_name,
                source_url=source.source_url or source.url,
                author=source.author,
                publish_date=source.publish_date,
                platform=source.platform,
            )
            outputs = write_canonical_outputs(canonical, state.paths.root, source_snapshot, input_info)
            registry.stage_success(StageName.CANONICAL.value, outputs=[str(x) for x in outputs.values()])
            return canonical
        except Exception as exc:
            logger.exception("canonical stage failed")
            registry.stage_failed(StageName.CANONICAL.value, str(exc))
            return canonical

    def _load_canonical(self, path: Path) -> CanonicalContent:
        payload = json.loads(path.read_text(encoding="utf-8"))
        timestamps = [TimestampSegment(**seg) for seg in payload.get("timestamps", [])]
        return CanonicalContent(
            source_id=payload.get("source_id", "unknown"),
            source_type=payload.get("source_type", "unknown"),
            title=payload.get("title", "Untitled"),
            raw_text=payload.get("raw_text", ""),
            clean_text=payload.get("clean_text", ""),
            language=payload.get("language"),
            timestamps=timestamps,
            source_metadata=payload.get("source_metadata") or {},
            attribution=payload.get("attribution") or {},
            structure_hints=payload.get("structure_hints") or {},
            processing_flags=payload.get("processing_flags") or {},
        )

    def _load_timestamp_segments(self, cleaned_json: Path) -> list[TimestampSegment]:
        payload = json.loads(cleaned_json.read_text(encoding="utf-8"))
        segments = []
        for seg in payload.get("segments", []):
            text = str(seg.get("text", "")).strip()
            if not text:
                continue
            start = float(seg.get("start", 0.0))
            end = float(seg.get("end", start))
            segments.append(TimestampSegment(start=start, end=end, text=text))
        return segments

    def _build_video_snapshot(self, raw_text: str, metadata: dict) -> str:
        if metadata:
            meta_json = json.dumps(metadata, ensure_ascii=False, indent=2)
            return f"# Source Metadata\n{meta_json}\n\n# Transcript\n{raw_text}\n"
        return raw_text

    def _build_input_info(
        self,
        input_type: str,
        source_name: str | None = None,
        source_url: str | None = None,
        author: str | None = None,
        publish_date: str | None = None,
        platform: str | None = None,
    ) -> dict[str, str]:
        info: dict[str, str] = {"input_type": input_type}
        if source_name:
            info["source_name"] = source_name
        if source_url:
            info["source_url"] = source_url
        if author:
            info["author"] = author
        if publish_date:
            info["publish_date"] = publish_date
        if platform:
            info["platform"] = platform
        return info

    def _load_source_snapshot(self, source: SourceInput) -> str:
        if source.text:
            return source.text
        if source.file_path:
            try:
                return Path(source.file_path).read_text(encoding="utf-8", errors="ignore")
            except Exception:
                return ""
        return ""

    def _metadata_complete(self, canonical: CanonicalContent) -> bool:
        if canonical.source_type == "video":
            required = ["video_id", "title", "webpage_url"]
        else:
            required = ["source_name", "source_url"]
        return all(canonical.source_metadata.get(key) for key in required)

    def _load_metadata(self, metadata_json: Path, fallback_video_id: str) -> VideoInfo:
        metadata_dict = json.loads(metadata_json.read_text(encoding="utf-8"))
        return VideoInfo(
            video_id=metadata_dict.get("video_id", fallback_video_id),
            title=metadata_dict.get("title", "Untitled"),
            uploader=metadata_dict.get("uploader"),
            channel=metadata_dict.get("channel"),
            upload_date=metadata_dict.get("upload_date"),
            duration=metadata_dict.get("duration"),
            webpage_url=metadata_dict.get("webpage_url"),
            description=metadata_dict.get("description"),
            thumbnail=metadata_dict.get("thumbnail"),
            view_count=metadata_dict.get("view_count"),
            like_count=metadata_dict.get("like_count"),
            tags=metadata_dict.get("tags") or [],
            subtitles=metadata_dict.get("subtitles") or {},
            automatic_captions=metadata_dict.get("automatic_captions") or {},
        )
