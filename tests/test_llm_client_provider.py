from dataclasses import dataclass

import pytest

from video_to_assets.llm.client import LLMClient


@dataclass
class DummyConfig:
    llm_max_input_chars: int = 1000
    llm_provider: str = "qwen"
    llm_model: str = "qwen-plus"
    llm_temperature: float = 0.2
    llm_use_mock_without_api_key: bool = False
    llm_base_url: str | None = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    llm_api_key_env: str | None = "BAILIAN_API_KEY"


def test_qwen_without_api_key_raises_when_mock_disabled(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    client = LLMClient(config=DummyConfig())
    with pytest.raises(RuntimeError) as exc:
        client.generate(prompt="p", content="hello", task="summary_one_line")
    assert "DASHSCOPE_API_KEY" in str(exc.value)


def test_qwen_uses_mock_when_enabled(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    cfg = DummyConfig(llm_use_mock_without_api_key=True)
    client = LLMClient(config=cfg)
    resp = client.generate(prompt="p", content="hello", task="summary_one_line")
    assert resp.mode == "mock"


def test_bailian_without_api_key_raises_when_mock_disabled(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("BAILIAN_API_KEY", raising=False)
    cfg = DummyConfig(llm_provider="bailian", llm_base_url="https://coding.dashscope.aliyuncs.com/v1")
    client = LLMClient(config=cfg)
    with pytest.raises(RuntimeError) as exc:
        client.generate(prompt="p", content="hello", task="summary_one_line")
    assert "BAILIAN_API_KEY" in str(exc.value)
