"""Unit tests for the Groq client's per-model request options (no network)."""

from app.llm.client import _model_options


def test_gpt_oss_gets_reasoning_headroom_and_low_effort():
    opts = _model_options("openai/gpt-oss-120b", 512)
    assert opts["max_tokens"] > 512
    assert opts["reasoning_effort"] == "low"


def test_qwen3_disables_reasoning():
    opts = _model_options("qwen/qwen3.8-27b", 512)
    assert opts["reasoning_effort"] == "none"


def test_other_models_keep_requested_budget():
    assert _model_options("some/other-model", 512) == {"max_tokens": 512}


def test_default_models_are_not_retired_llama_models():
    from app.config import settings

    for model in (
        settings.groq_model_ranking,
        settings.groq_model_extraction,
        settings.groq_model_chat,
        settings.groq_model_chat_vision,
    ):
        assert "llama-3" not in model and "llama-4" not in model
