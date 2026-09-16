"""The callbacks behind every button, driven without a browser."""

import asyncio

import gradio as gr
import pytest

from ai_storyteller import callbacks
from ai_storyteller.config import Settings
from ai_storyteller.prompts import TOPIC_SEEDS
from ai_storyteller.story import StoryChunk, StoryError
from ai_storyteller.studio import Studio


def stream(studio: Studio, **overrides) -> list[tuple[str, str, str]]:
    arguments = {
        "topic": "the lamp",
        "genre": "Noir",
        "mood": "Tense",
        "words": 260,
        "voice": "camber",
        "slow": False,
        **overrides,
    }

    async def run():
        return [frame async for frame in callbacks.stream_story(studio, **arguments)]

    return asyncio.run(run())


def test_stream_story_yields_stage_frames(studio: Studio):
    frames = stream(studio)
    assert frames and all(len(frame) == 3 for frame in frames)
    stage, deck, status = frames[-1]
    assert "deck__play" in deck
    assert "follow the light" in status
    assert "tp-word" in stage


def test_stream_story_coerces_the_slider_value(studio: Studio):
    stage, _deck, _status = stream(studio, words=0)[-1]
    assert "words" in stage


def test_stream_story_surfaces_writer_failures_as_gradio_errors(settings: Settings):
    class Broken:
        def prepare(self, request):
            return request

        async def stream(self, request):
            yield StoryChunk(text="too short", delta="too short", note="writing…")
            raise StoryError("the muse left the building")

    studio = Studio(settings, service=Broken())
    with pytest.raises(gr.Error, match="muse left"):
        stream(studio)


def test_refresh_archive_reports_the_shelf(studio: Studio):
    _stage, _deck, _status = stream(studio)[-1]
    update, preview, hero, status = callbacks.refresh_archive(studio)
    assert update["choices"]
    assert "tp-word" in preview
    assert "drafts archived" in hero
    assert "1 draft on the shelf" in status


def test_refresh_archive_handles_an_empty_shelf(studio: Studio):
    update, preview, _hero, status = callbacks.refresh_archive(studio)
    assert update["choices"] == []
    assert update["value"] is None
    assert "nothing selected" in preview
    assert "0 drafts on the shelf" in status


def test_preview_open_speak_delete_clear_round_trip(studio: Studio):
    stream(studio)
    story_id = studio.library.load()[0].story_id

    assert "archive ·" in callbacks.preview_selected(studio, story_id)

    stage, deck, status = callbacks.open_selected(studio, story_id)
    assert "from the archive" in stage
    assert "speak it again" in deck
    assert "opened" in status

    _stage, deck, status = callbacks.speak_selected(studio, story_id)
    assert "data:audio/mpeg;base64," in deck
    assert "follow the light" in status

    update, _preview, _hero, status = callbacks.delete_selected(studio, story_id)
    assert update["choices"] == []
    assert "draft deleted" in status

    update, preview, _hero, status = callbacks.clear_archive(studio)
    assert update["value"] is None
    assert "nothing selected" in preview
    assert "archive was empty" in status


def test_missing_selection_is_reported(studio: Studio):
    _stage, _deck, status = callbacks.open_selected(studio, None)
    assert "nothing selected" in status
    assert "nothing selected" in callbacks.refresh_archive(studio)[1]


def test_adopt_shared_restores_and_reports(studio: Studio):
    stage, deck, status, update, preview, hero = callbacks.adopt_shared(
        studio, "A story someone sent me. The rain never stopped."
    )
    assert "restored" in status
    assert "tp-word" in stage
    assert "speak it again" in deck
    assert update["choices"]
    assert "Restored" in preview
    assert "drafts archived" in hero


def test_adopt_shared_rejects_empty_input(studio: Studio):
    _stage, _deck, status, *_rest = callbacks.adopt_shared(studio, "   ")
    assert "nothing to restore" in status


def test_roll_topic_returns_a_seed(studio: Studio):
    assert callbacks.roll_topic(studio) in TOPIC_SEEDS


def test_demo_reels_back_the_offline_studio(offline_studio: Studio):
    frames = stream(offline_studio)
    assert "demo" in frames[0][2]
    _stage, deck, _status = frames[-1]
    assert "data:audio/mpeg;base64," in deck
    assert offline_studio.library.load()[0].model == "demo reel"
