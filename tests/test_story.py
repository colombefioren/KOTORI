import asyncio

import pytest

from ai_storyteller import story as story_module
from ai_storyteller.config import Settings
from ai_storyteller.models import StoryRequest
from ai_storyteller.story import StoryError, StoryService

PROSE = (
    "The lamp turned twice and the sea leaned closer, patient as debt. "
    "She read the letter again and understood the ship had never sunk."
)


class FakeChunk:
    def __init__(self, content: str) -> None:
        self.content = content


class FakeModel:
    def __init__(self, pieces: list[str]) -> None:
        self.pieces = pieces

    async def astream(self, messages):  # noqa: ANN001, ANN201
        for piece in self.pieces:
            yield FakeChunk(piece)

    def invoke(self, messages):  # noqa: ANN001, ANN201
        return FakeChunk("".join(self.pieces))


@pytest.fixture
def service(monkeypatch: pytest.MonkeyPatch) -> StoryService:
    settings = Settings(model_name="test-model", api_key="test-key")
    service = StoryService(settings)
    pieces = [PROSE[:40], PROSE[40:120], PROSE[120:]]
    monkeypatch.setattr(
        story_module, "build_chat_model", lambda *a, **k: FakeModel(pieces)
    )
    return service


def test_prepare_fills_empty_topic_and_clamps_length():
    request = StoryRequest(topic="   ", target_words=9999)
    prepared = StoryService(Settings(api_key="x")).prepare(request)
    assert prepared.topic
    assert prepared.target_words == 600


def test_prepare_keeps_a_real_topic():
    prepared = StoryService(Settings(api_key="x")).prepare(StoryRequest(topic="a quiet town"))
    assert prepared.topic == "a quiet town"


def test_stream_yields_growing_text_then_finishes(service: StoryService):
    async def collect():
        return [chunk async for chunk in service.stream(StoryRequest(topic="the lamp"))]

    chunks = asyncio.run(collect())
    assert chunks[0].note.startswith("warming")
    assert chunks[-1].finished is True
    assert chunks[-1].text == PROSE
    lengths = [len(chunk.text) for chunk in chunks]
    assert lengths == sorted(lengths)


def test_compose_returns_a_populated_draft(service: StoryService):
    draft = service.compose(StoryRequest(topic="the lamp", genre="Noir", mood="Tense"))
    assert draft.story == PROSE
    assert draft.genre == "Noir"
    assert draft.mood == "Tense"
    assert draft.words > 20
    assert draft.voice_label.startswith("Aurora")
    assert draft.model == "test-model"
    assert draft.elapsed_ms >= 0


def test_stream_rejects_a_stub_answer(monkeypatch: pytest.MonkeyPatch):
    service = StoryService(Settings(api_key="x"))
    monkeypatch.setattr(
        story_module, "build_chat_model", lambda *a, **k: FakeModel(["ok."])
    )

    async def collect():
        return [chunk async for chunk in service.stream(StoryRequest(topic="x"))]

    with pytest.raises(StoryError):
        asyncio.run(collect())
