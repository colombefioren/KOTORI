"""The callbacks behind every button, driven without a browser."""

import asyncio

import gradio as gr
import pytest

from ai_storyteller import callbacks
from ai_storyteller.config import Settings
from ai_storyteller.prompts import TOPIC_SEEDS
from ai_storyteller.story import StoryChunk, StoryError
from ai_storyteller.studio import Studio


def arguments(**overrides) -> dict:
    return {
        "topic": "the lamp",
        "genre": "Noir",
        "mood": "Tense",
        "words": 260,
        "voice": "camber",
        "slow": False,
        **overrides,
    }


def frames(studio: Studio, **overrides) -> list[tuple[str, str, str, object]]:
    async def run():
        return [frame async for frame in callbacks.stream_story(studio, **arguments(**overrides))]

    return asyncio.run(run())


def stream(studio: Studio, **overrides) -> list[tuple[str, str, str, object]]:
    return frames(studio, **overrides)


def test_stream_story_yields_stage_frames(studio: Studio):
    collected = stream(studio)
    assert collected and all(len(frame) == 4 for frame in collected)
    stage, deck, status, _button = collected[-1]
    assert "deck__play" in deck
    assert "follow the light" in status
    assert "tp-word" in stage


def test_stream_story_shows_a_loading_state_first(studio: Studio):
    first = stream(studio)[0]
    assert "tp-skeleton" in first[0]
    assert first[3]["interactive"] is False
    assert stream(studio)[-1][3]["interactive"] is True


def test_stream_story_coerces_the_slider_value(studio: Studio):
    stage, _deck, _status, _button = stream(studio, words=0)[-1]
    assert "words" in stage


def test_stream_story_surfaces_writer_failures_as_gradio_errors(settings: Settings):
    class Broken:
        def prepare(self, request):
            return request

        async def stream(self, request):
            yield StoryChunk(text="too short", delta="too short", note="writing…")
            raise StoryError("the muse left the building")

    studio = Studio(settings, service=Broken())
    collected: list[tuple[str, str, str, object]] = []

    async def run():
        with pytest.raises(gr.Error, match="muse left"):
            async for frame in callbacks.stream_story(studio, **arguments()):
                collected.append(frame)

    asyncio.run(run())
    assert "muse left" in collected[-1][1]
    assert collected[-1][3]["interactive"] is True


def test_rearm_hands_the_composer_back(studio: Studio):
    assert callbacks.rearm(studio)["interactive"] is True


def test_refresh_archive_reports_the_shelf(studio: Studio):
    stream(studio)[-1]
    update, preview, hero, status = callbacks.refresh_archive(studio)
    assert update["choices"]
    assert "tp-word" in preview
    assert "deck__play" in preview
    assert "stories kept" in hero
    assert "1 story on the shelf" in status


def test_refresh_archive_keeps_the_selection_it_is_given(studio: Studio):
    stream(studio)
    story_id = studio.library.load()[0].story_id
    update, _preview, _hero, _status = callbacks.refresh_archive(studio, story_id)
    assert update["value"] == story_id


def test_refresh_archive_handles_an_empty_shelf(studio: Studio):
    update, preview, _hero, status = callbacks.refresh_archive(studio)
    assert update["choices"] == []
    assert update["value"] is None
    assert "nothing selected" in preview
    assert "0 stories on the shelf" in status


def test_preview_delete_and_clear_round_trip(studio: Studio):
    stream(studio)
    story_id = studio.library.load()[0].story_id

    preview = callbacks.preview_selected(studio, story_id)
    assert "from the archive" in preview
    assert "deck__play" in preview

    recorded = list(callbacks.record_voice(studio, story_id))
    assert "recording a fresh voice" in recorded[0][1]
    assert "data:audio/mpeg;base64," in recorded[-1][1]
    assert "follow the light" in recorded[-1][2]

    update, _preview, _hero, status = callbacks.delete_selected(studio, story_id)
    assert update["choices"] == []
    assert "story deleted" in status

    update, preview, _hero, status = callbacks.clear_archive(studio)
    assert update["value"] is None
    assert "nothing selected" in preview
    assert "the shelf was empty" in status


def test_recording_without_a_selection_is_reported(studio: Studio):
    frames_ = list(callbacks.record_voice(studio, None))
    assert len(frames_) == 1
    assert "nothing selected" in frames_[0][2]


def test_adopt_shared_restores_and_reports(studio: Studio):
    stage, deck, status, update, preview, hero = callbacks.adopt_shared(
        studio, "A story someone sent me. The rain never stopped."
    )
    assert "restored" in status
    assert "tp-word" in stage
    assert "press play" in deck
    assert update["choices"]
    assert "Restored" in preview
    assert "stories kept" in hero


def test_adopt_shared_rejects_empty_input(studio: Studio):
    _stage, _deck, status, *_rest = callbacks.adopt_shared(studio, "   ")
    assert "nothing to restore" in status


def test_roll_topic_returns_a_seed(studio: Studio):
    assert callbacks.roll_topic(studio) in TOPIC_SEEDS


def test_demo_reels_back_the_offline_studio(offline_studio: Studio):
    collected = stream(offline_studio)
    assert "demo" in collected[0][2]
    _stage, deck, _status, _button = collected[-1]
    assert "data:audio/mpeg;base64," in deck
    assert offline_studio.library.load()[0].model == "demo reel"
