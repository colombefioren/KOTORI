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


class FakeStoryService:
    """A writer that never calls an API: enough for studio-level tests."""

    def prepare(self, request):
        return request.normalised("a quiet town")

    async def stream(self, request):
        from ai_storyteller.story import StoryChunk

        yield StoryChunk(text=STORY[:40], delta=STORY[:40], note="writing…")
        yield StoryChunk(text=STORY, delta=STORY[40:], note="writing…")
        yield StoryChunk(text=STORY, delta="", finished=True, note="closing the loop…")


@pytest.fixture
def fake_speech(monkeypatch: pytest.MonkeyPatch) -> None:
    """Write a stand-in mp3 instead of talking to Google."""
    from pathlib import Path

    from ai_storyteller import studio as studio_module

    def fake_synthesize(text, *, voice_key, out_dir, stem, slow=False):
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        target = out_dir / f"{stem}-{voice_key}.mp3"
        target.write_bytes(b"\xff\xfb\x90\x00")
        return target

    monkeypatch.setattr(studio_module, "synthesize", fake_synthesize)


@pytest.fixture
def studio(settings: Settings, fake_speech: None):
    """A studio with a fake writer and fake speech, on a throwaway archive."""
    from ai_storyteller.studio import Studio

    return Studio(settings, service=FakeStoryService())


@pytest.fixture
def offline_studio(offline_settings: Settings, fake_speech: None):
    """No credentials: the studio must reach for the demo reels."""
    from ai_storyteller.studio import Studio

    return Studio(offline_settings, service=FakeStoryService())
