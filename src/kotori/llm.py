"""Factory for the LangChain chat model that writes the stories."""

from __future__ import annotations

from langchain_openai import ChatOpenAI

from .config import Settings


class EngineNotConfiguredError(RuntimeError):
    """Raised when the studio is asked to write without a key."""

    def __init__(self) -> None:
        super().__init__(
            "No model credentials found. Add MODEL_NAME, API_KEY and BASE_URL to "
            "your .env file (or the host's environment) and reload the studio."
        )


def build_chat_model(
    settings: Settings,
    *,
    streaming: bool = False,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> ChatOpenAI:
    """Create a streaming-capable chat model for any OpenAI-compatible endpoint."""
    if not settings.is_configured:
        raise EngineNotConfiguredError

    return ChatOpenAI(
        model=settings.model_name,
        api_key=settings.api_key,
        base_url=settings.base_url or None,
        temperature=settings.temperature if temperature is None else temperature,
        max_tokens=settings.max_tokens if max_tokens is None else max_tokens,
        timeout=settings.request_timeout,
        streaming=streaming,
        max_retries=2,
    )


def describe_engine(settings: Settings) -> str:
    """Short human label for the status ticker."""
    if not settings.is_configured:
        return "engine offline · add credentials"
    host = settings.base_url or "api.openai.com"
    host = host.replace("https://", "").replace("http://", "").split("/")[0]
    return f"{settings.model_name} via {host}"
