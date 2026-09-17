"""The writer's engine: factory defaults, overrides and the offline guard."""

import pytest
from langchain_openai import ChatOpenAI

from kotori.config import Settings
from kotori.llm import EngineNotConfiguredError, build_chat_model, describe_engine


def test_missing_credentials_raise_a_readable_error():
    with pytest.raises(EngineNotConfiguredError, match="MODEL_NAME"):
        build_chat_model(Settings(model_name="test-model", api_key=None))


def test_settings_flow_into_the_client(settings: Settings):
    model = build_chat_model(settings)
    assert isinstance(model, ChatOpenAI)
    assert model.model_name == "test-model"
    assert model.temperature == settings.temperature
    assert model.max_tokens == settings.max_tokens


def test_overrides_beat_the_settings(settings: Settings):
    model = build_chat_model(settings, streaming=True, temperature=0.1, max_tokens=42)
    assert model.streaming is True
    assert model.temperature == 0.1
    assert model.max_tokens == 42


def test_base_url_is_optional(settings: Settings):
    assert build_chat_model(settings).openai_api_base is None


def test_endpoint_is_forwarded(settings: Settings):
    custom = Settings(model_name="m", api_key="k", base_url="https://api.example.test/v1")
    assert build_chat_model(custom).openai_api_base == "https://api.example.test/v1"


def test_engine_labels_read_like_status_lines():
    assert describe_engine(Settings(api_key=None)) == "engine offline · add credentials"
    assert (
        describe_engine(
            Settings(model_name="m1", api_key="k", base_url="https://api.example.test/v1")
        )
        == "m1 via api.example.test"
    )
    assert describe_engine(Settings(model_name="m1", api_key="k")) == "m1 via api.openai.com"
