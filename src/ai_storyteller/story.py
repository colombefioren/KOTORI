"""The writer: turns a request into streaming prose, or a finished draft."""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from dataclasses import dataclass

from langchain_core.prompts import ChatPromptTemplate

from .config import Settings, get_settings
from .llm import build_chat_model
from .models import StoryDraft, StoryRequest
from .prompts import build_messages, clean_story, get_genre, get_mood, random_topic
from .speech import resolve_voice

OPENING_NOTE = "warming the lamp…"
WRITING_NOTE = "writing…"
CLOSING_NOTE = "closing the loop…"
MIN_USEFUL_CHARS = 24


class StoryError(RuntimeError):
    """Raised when the writer comes back empty-handed."""


@dataclass(frozen=True, slots=True)
class StoryChunk:
    """One frame of streaming prose."""

    text: str
    delta: str
    finished: bool = False
    note: str = WRITING_NOTE


class StoryService:
    """Thin, testable orchestration around LangChain."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def messages(self, request: StoryRequest) -> list[tuple[str, str]]:
        prompt = ChatPromptTemplate.from_messages(build_messages(request))
        return prompt.format_messages()

    def prepare(self, request: StoryRequest) -> StoryRequest:
        """Fill in defaults and swap an empty topic for a seed."""
        normalised = request.normalised(random_topic())
        return normalised

    async def stream(self, request: StoryRequest) -> AsyncIterator[StoryChunk]:
        """Yield cumulative prose as the model writes it."""
        prepared = self.prepare(request)
        model = build_chat_model(self.settings, streaming=True)
        buffer = ""
        yield StoryChunk(text="", delta="", note=OPENING_NOTE)

        async for chunk in model.astream(self.messages(prepared)):
            delta = chunk.text() if hasattr(chunk, "text") else str(chunk.content)
            if not delta:
                continue
            buffer += delta
            text = clean_story(buffer)
            yield StoryChunk(text=text, delta=delta, note=WRITING_NOTE)

        text = clean_story(buffer)
        if len(text) < MIN_USEFUL_CHARS:
            raise StoryError("The model returned too little text. Try again.")
        yield StoryChunk(text=text, delta="", finished=True, note=CLOSING_NOTE)

    def compose(self, request: StoryRequest) -> StoryDraft:
        """Blocking, non-streaming write used by the CLI and tests."""
        prepared = self.prepare(request)
        model = build_chat_model(self.settings)
        started = time.perf_counter()
        response = model.invoke(self.messages(prepared))
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        text = clean_story(str(response.content))
        if len(text) < MIN_USEFUL_CHARS:
            raise StoryError("The model returned too little text. Try again.")

        voice = resolve_voice(prepared.voice)
        return StoryDraft(
            topic=prepared.topic,
            genre=get_genre(prepared.genre).label,
            mood=get_mood(prepared.mood).label,
            target_words=prepared.target_words,
            story=text,
            voice=voice.key,
            voice_label=voice.choice,
            model=self.settings.model_name,
            elapsed_ms=elapsed_ms,
        )
