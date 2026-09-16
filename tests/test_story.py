import asyncio

import pytest

from ai_storyteller import story as story_module
from ai_storyteller.config import Settings
from ai_storyteller.models import StoryRequest
from ai_storyteller.story import StoryError, StoryService


@pytest.fixture
def service(story_service: StoryService) -> StoryService:
    return story_service


def collect_chunks(service: StoryService, request: StoryRequest):
    async def run():
        return [chunk async for chunk in service.stream(request)]

    return asyncio.run(run())


def test_prepare_fills_empty_topic_and_clamps_length():
    request = StoryRequest(topic="   ", target_words=9999)
    prepared = StoryService(Settings(api_key="x")).prepare(request)
    assert prepared.topic
    assert prepared.target_words == 600


def test_prepare_keeps_a_real_topic():
    prepared = StoryService(Settings(api_key="x")).prepare(StoryRequest(topic="a quiet town"))
    assert prepared.topic == "a quiet town"


def test_stream_yields_growing_text_then_finishes(service: StoryService, story_text: str):
    chunks = collect_chunks(service, StoryRequest(topic="the lamp"))
    assert chunks[0].note.startswith("warming")
    assert chunks[-1].finished is True
    assert chunks[-1].text == story_text
    lengths = [len(chunk.text) for chunk in chunks]
    assert lengths == sorted(lengths)


def test_stream_paces_itself_to_one_frame_per_burst(service: StoryService, story_text: str):
    chunks = collect_chunks(service, StoryRequest(topic="the lamp"))
    # warm-up frame, one frame per burst, then the closing frame
    assert len(chunks) <= 4
    assert any(chunk.text == story_text for chunk in chunks)


def test_compose_returns_a_populated_draft(service: StoryService, story_text: str):
    draft = service.compose(StoryRequest(topic="the lamp", genre="Noir", mood="Tense"))
    assert draft.story == story_text
    assert draft.genre == "Noir"
    assert draft.mood == "Tense"
    assert draft.words > 20
    assert draft.voice_label.startswith("Aurora")
    assert draft.model == "test-model"
    assert draft.elapsed_ms >= 0


def test_stream_rejects_a_stub_answer(settings: Settings, monkeypatch, fake_model):
    service = StoryService(settings)
    monkeypatch.setattr(story_module, "build_chat_model", lambda *a, **k: fake_model(["ok."]))

    with pytest.raises(StoryError):
        collect_chunks(service, StoryRequest(topic="x"))


def test_messages_start_with_the_brief(service: StoryService):
    messages = service.messages(StoryRequest(topic="a lighthouse", genre="Noir", mood="Tense"))
    assert messages[0].type == "system"
    assert "a lighthouse" in messages[1].content
