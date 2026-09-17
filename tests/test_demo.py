import asyncio
import random

import pytest

from kotori import demo as demo_module
from kotori.demo import (
    DEMO_CHUNK_WORDS,
    DEMO_STORIES,
    demo_stream,
    pick_demo_story,
)
from kotori.models import StoryRequest


@pytest.fixture(autouse=True)
def no_waiting(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the suite fast: the pacing itself is asserted, not waited on."""
    monkeypatch.setattr(demo_module, "DEMO_FRAME_SECONDS", 0.0)


def test_frame_pacing_is_gentle_by_default(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.undo()
    assert 0 < demo_module.DEMO_FRAME_SECONDS <= 0.2
    assert DEMO_CHUNK_WORDS >= 1


def collect(request: StoryRequest):
    async def run():
        return [chunk async for chunk in demo_stream(request)]

    return asyncio.run(run())


def test_there_are_several_original_reels():
    assert len(DEMO_STORIES) >= 3
    assert all(len(story.split()) > 100 for story in DEMO_STORIES)
    assert len(set(DEMO_STORIES)) == len(DEMO_STORIES)


def test_each_reel_ends_on_a_cliffhanger():
    for story in DEMO_STORIES:
        assert story.rstrip().endswith((".", "!", "?", "…"))


def test_pick_is_stable_for_a_topic():
    first = pick_demo_story("the sunken ship")
    assert first == pick_demo_story("The Sunken Ship  ")
    assert first in DEMO_STORIES


def test_pick_without_a_topic_respects_the_rng():
    rng = random.Random(3)
    assert pick_demo_story(None, rng) == pick_demo_story(None, random.Random(3))


def test_demo_stream_paces_the_prose_and_finishes():
    chunks = collect(StoryRequest(topic="a quiet town"))
    assert chunks[0].note.startswith("warming")
    assert chunks[-1].finished is True
    assert chunks[-1].text == pick_demo_story("a quiet town")

    lengths = [len(chunk.text.split()) for chunk in chunks[:-1]]
    assert lengths == sorted(lengths)
    assert lengths[1] == DEMO_CHUNK_WORDS


def test_demo_stream_reuses_frames_for_repeated_reels():
    chunks = collect(StoryRequest(topic="same seed"))
    assert all(chunk.text in pick_demo_story("same seed") for chunk in chunks)
