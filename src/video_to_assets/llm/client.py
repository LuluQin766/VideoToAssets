from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from video_to_assets.config import AppConfig
from video_to_assets.llm.schemas import LLMResponse


class LLMClient:
    def __init__(self, config: AppConfig, logger=None):
        self.config = config
        self.logger = logger

    def load_prompt(self, prompt_file: Path) -> str:
        return prompt_file.read_text(encoding="utf-8")

    def generate(self, prompt: str, content: str, task: str) -> LLMResponse:
        text = content[: self.config.llm_max_input_chars]
        provider = (self.config.llm_provider or "openai").strip().lower()

        if provider in {"openai", "qwen", "bailian"}:
            try:
                return self._call_provider(prompt, text, provider)
            except RuntimeError as exc:
                if self.logger:
                    self.logger.warning("%s", exc)
            except Exception as exc:
                if self.logger:
                    self.logger.warning("Provider %s call failed, fallback to mock mode: %s", provider, exc)
        elif self.logger:
            self.logger.warning("LLM provider '%s' is unsupported", provider)

        if not self.config.llm_use_mock_without_api_key:
            if provider == "qwen":
                raise RuntimeError("Qwen API unavailable and mock disabled. Configure DASHSCOPE_API_KEY.")
            if provider == "bailian":
                env_name = self.config.llm_api_key_env or "BAILIAN_API_KEY"
                raise RuntimeError(
                    f"Bailian API unavailable and mock disabled. Configure {env_name} and llm.base_url."
                )
            raise RuntimeError("LLM API unavailable and mock disabled. Configure provider API key.")

        mock_text = self._mock_response(task, text)
        return LLMResponse(text=mock_text, mode="mock", raw={"task": task, "mock": True})

    def _call_provider(self, prompt: str, text: str, provider: str) -> LLMResponse:
        from openai import OpenAI

        api_key, base_url = self._resolve_provider_credentials(provider)
        if not api_key:
            raise RuntimeError(f"Provider {provider} key is missing.")

        client = OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)
        completion = client.chat.completions.create(
            model=self.config.llm_model,
            temperature=self.config.llm_temperature,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": text},
            ],
        )
        content = completion.choices[0].message.content or ""
        raw = {
            "provider": provider,
            "base_url": base_url,
            "model": self.config.llm_model,
            "response": completion.model_dump(),
        }
        return LLMResponse(text=content, mode=provider, raw=raw)

    def _resolve_provider_credentials(self, provider: str) -> tuple[str | None, str | None]:
        provider = provider.strip().lower()
        if provider == "openai":
            return os.getenv("OPENAI_API_KEY"), self.config.llm_base_url
        if provider == "qwen":
            base_url = self.config.llm_base_url or "https://dashscope.aliyuncs.com/compatible-mode/v1"
            return os.getenv("DASHSCOPE_API_KEY"), base_url
        if provider == "bailian":
            env_name = self.config.llm_api_key_env or "BAILIAN_API_KEY"
            api_key = os.getenv(env_name) or os.getenv("DASHSCOPE_API_KEY")
            return api_key, self.config.llm_base_url
        return None, None

    def _mock_response(self, task: str, text: str) -> str:
        if task == "quality_review":
            lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
            uniq_ratio = len(set(lines)) / len(lines) if lines else 0
            grade = "A" if uniq_ratio > 0.9 else "B" if uniq_ratio > 0.75 else "C"
            return (
                f"质量评级: {grade}\n"
                f"行数: {len(lines)}\n"
                f"唯一行占比: {uniq_ratio:.2f}\n"
                "问题清单:\n- 可能存在口语重复\n- 建议人工复核专有名词\n"
                "是否建议进入下一步整理: yes"
            )

        if task == "summary_one_line":
            first_line = " ".join(x.strip() for x in text.splitlines() if x.strip())[:60]
            return first_line or "暂无可用一句话总结"

        if task == "summary_executive":
            return (
                "## 背景\n"
                "内容来自单视频转写整理，目标是提炼核心认知并支持后续创作。\n\n"
                "## 核心观点\n"
                "- 先建立结构化信息层，再进入内容再创作\n"
                "- 优先保留可验证的原始信息，避免无依据延展\n\n"
                "## 行动建议\n"
                "1. 先做最小闭环\n"
                "2. 再分任务增量执行\n"
            )

        if task == "summary_outline":
            return (
                "## 一、背景与目标\n"
                "### 1.1 问题定义\n"
                "### 1.2 目标边界\n\n"
                "## 二、方法与流程\n"
                "### 2.1 数据来源\n"
                "### 2.2 处理步骤\n"
                "### 2.3 输出规范\n\n"
                "## 三、可执行建议\n"
                "### 3.1 立即行动\n"
                "### 3.2 风险与复核\n"
            )

        if task == "summary_topic_map":
            return (
                "- 主题A：内容资产化\n"
                "  - 子主题：结构化输出\n"
                "  - 关系：支撑摘要与再创作\n"
                "- 主题B：来源归因\n"
                "  - 子主题：可追溯文件链路\n"
                "  - 关系：降低事实风险\n"
            )

        if task == "summary_key_quotes":
            lines = [x.strip() for x in text.splitlines() if x.strip()][:6]
            return "\n".join(f"- \"{x[:120]}\"（来源：转写整理）" for x in lines)

        if task == "summary_entities":
            return (
                "## 人物\n- 待核验\n\n"
                "## 组织\n- 待核验\n\n"
                "## 概念\n- 内容资产化\n- 结构化转写\n- 归因与发布边界\n"
            )

        if task == "source_profile":
            return (
                "该资产包来源于单个视频及其转写文本。所有摘要、文章、短帖和高光候选均属于派生整理内容。"
                "使用时应保留来源链接并提供可复核路径。"
            )

        if task == "publishing_notes":
            return (
                "1. 发布时标注视频来源链接。\n"
                "2. 对数据与专有名词做二次核验。\n"
                "3. 声明内容为转写整理后的二次表达。\n"
            )

        if task == "wechat_titles":
            return (
                "把一条视频变成可复用内容资产：完整流程拆解\n"
                "从转写到发布：如何做高质量内容再表达\n"
                "不是摘要，而是重构：一次内容资产化实战\n"
            )

        if task.startswith("wechat_article_"):
            return (
                "## 开篇\n基于视频转写内容，本文做结构化复盘。\n\n"
                "## 核心观点\n- 先保真，再优化表达\n- 先建立资产索引，再扩展平台分发\n\n"
                "## 实操步骤\n1. 读取摘要与归因\n2. 选择传播角度\n3. 输出可发布版本\n\n"
                "## 结语\n好的内容再创作，前提是清晰的来源与边界。"
            )

        if task.startswith("xhs_post_"):
            return (
                "# 今天的复盘笔记\n"
                "把一条视频做成可复用资产，关键不是写得多，而是结构清楚、可追溯。\n"
                "你更想先做摘要还是先做高光？\n"
                "#内容运营 #方法论 #复盘"
            )

        paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
        if not paragraphs:
            return ""
        chunks = []
        step = max(3, min(8, len(paragraphs) // 6 or 3))
        for i in range(0, len(paragraphs), step):
            chunk = " ".join(paragraphs[i : i + step])
            chunks.append(chunk)
        return "\n\n".join(chunks)
