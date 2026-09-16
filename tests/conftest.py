"""Shared fixtures: no test in this suite ever touches the network."""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_storyteller.config import Settings

STORY = (
    "The lamp turned twice and the sea leaned closer, patient as debt. "
    "She read the letter again and understood the ship had never sunk at all."
)


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    """A configured studio pointed at a throwaway data directory."""
    return Settings(model_name="test-model", api_key="test-key", data_dir=tmp_path)


@pytest.fixture
def offline_settings(tmp_path: Path) -> Settings:
    """No credentials: the studio must fall back to the demo reels."""
    return Settings(model_name="test-model", api_key=None, data_dir=tmp_path)


class FakeChunk:
    """Stands in for a LangChain message chunk."""

    def __init__(self, content: str) -> None:
        self.content = content


class FakeModel:
    """Streams pre-baked prose without an API call."""

    def __init__(self, pieces: list[str]) -> None:
        self.pieces = pieces

    async def astream(self, messages):
        for piece in self.pieces:
            yield FakeChunk(piece)

    def invoke(self, messages):
        return FakeChunk("".join(self.pieces))


@pytest.fixture
def fake_model_factory(monkeypatch: pytest.MonkeyPatch, story_text: str):
    """Patch the writer so `StoryService` streams `story_text` in pieces."""
    from ai_storyteller import story as story_module

    pieces = [story_text[:40], story_text[40:120], story_text[120:]]
    monkeypatch.setattr(story_module, "build_chat_model", lambda *a, **k: FakeModel(pieces))
    return FakeModel(pieces)


@pytest.fixture
def fake_model():
    """The fake chunk/model classes, for tests that need a custom answer."""
    return FakeModel


@pytest.fixture
def story_text() -> str:
    return STORY


@pytest.fixture
def story_service(settings: Settings, fake_model_factory):
    """A writer wired to the fake model."""
    from ai_storyteller.story import StoryService

    return StoryService(settings)
