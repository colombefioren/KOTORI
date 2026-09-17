"""The callbacks behind every button, driven without a browser."""

import asyncio

import gradio as gr
import pytest

from kotori import callbacks
from kotori.config import Settings
from kotori.prompts import TOPIC_SEEDS
from kotori.story import StoryChunk, StoryError
from kotori.studio import Studio


def arguments(**overrides) -> dict:
    return {
        "topic": "the lamp",
        "genre": "Noir",
        "mood": "Tense",
        "voice": "camber",
        "slow": False,
        **overrides,
    }


def frames(studio: Studio, **overrides) -> list[tuple[str, str, str, object]]:
    async def run():
        return [frame async for frame in callbacks.stream_story(studio, **arguments(**overrides))]

    return asyncio.run(run())


def test_stream_story_yields_four_parts_including_the_button(studio: Studio):
    collected = frames(studio)
    assert collected and all(len(frame) == 4 for frame in collected)
    stage, deck, status, _button = collected[-1]
    assert "deck__play" in deck
    assert "read along" in status
    assert "tp-word" in stage


def test_stream_story_shows_a_loading_state_first(studio: Studio):
    first = frames(studio)[0]
    assert "tp-skeleton" in first[0]
    assert first[3]["interactive"] is False
    assert frames(studio)[-1][3]["interactive"] is True


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


def test_show_playground_switches_tab(studio: Studio):
    assert callbacks.show_playground(studio)["selected"] == "playground"


def test_demo_story_writes_a_reel_and_moves_to_the_playground(offline_studio: Studio):
    async def run():
        return [frame async for frame in callbacks.demo_story(offline_studio)]

    collected = asyncio.run(run())
    assert collected and all(len(frame) == 5 for frame in collected)
    _stage, deck, _status, _button, tabs = collected[-1]
    assert "deck__play" in deck
    assert tabs["selected"] == "playground"


def test_refresh_history_reports_the_ledger(studio: Studio):
    frames(studio)
    bridge, drawer, ledger, masthead, status = callbacks.refresh_history(studio)
    assert bridge["choices"] and drawer["choices"]
    assert "story-card" in ledger
    assert "1 story kept" in masthead
    assert "1 story on the shelf" in status


def test_refresh_history_keeps_the_selection_it_is_given(studio: Studio):
    frames(studio)
    story_id = studio.library.load()[0].story_id
    bridge, drawer, _ledger, _masthead, _status = callbacks.refresh_history(studio, story_id)
    assert bridge["value"] == story_id
    assert drawer["value"] == story_id


def test_refresh_history_handles_an_empty_shelf(studio: Studio):
    bridge, drawer, ledger, _masthead, status = callbacks.refresh_history(studio)
    assert bridge["choices"] == [] and bridge["value"] is None
    assert drawer["choices"] == []
    assert "nothing here yet" in ledger
    assert "0 stories on the shelf" in status


def test_open_selected_puts_a_story_on_the_page_and_switches_tab(studio: Studio):
    frames(studio)
    story_id = studio.library.load()[0].story_id
    stage, deck, status, tabs = callbacks.open_selected(studio, story_id)
    assert "from the history" in stage
    assert "deck__play" in deck
    assert "opened" in status
    assert tabs["selected"] == "playground"


def test_record_voice_shows_the_work_then_the_recording(studio: Studio):
    frames(studio)
    story_id = studio.library.load()[0].story_id
    collected = list(callbacks.record_voice(studio, story_id))
    assert len(collected) == 2
    assert "recording" in collected[0][1]
    assert "deck__play" in collected[-1][1]
    assert "read along" in collected[-1][2]


def test_record_voice_without_a_selection_is_reported(studio: Studio):
    collected = list(callbacks.record_voice(studio, None))
    assert len(collected) == 1
    assert "nothing selected" in collected[0][2]


def test_delete_and_clear_report_their_effect(studio: Studio):
    frames(studio)
    story_id = studio.library.load()[0].story_id

    bridge, drawer, ledger, _masthead, status = callbacks.delete_selected(studio, story_id)
    assert bridge["choices"] == [] and drawer["choices"] == []
    assert "nothing here yet" in ledger
    assert "story deleted" in status

    bridge, _drawer, _ledger, _masthead, status = callbacks.clear_history(studio)
    assert bridge["value"] is None
    assert "the shelf was empty" in status


def test_adopt_shared_restores_and_reports(studio: Studio):
    stage, deck, status, _button = callbacks.adopt_shared(
        studio, "A story someone sent me. The rain never stopped."
    )
    assert "restored" in status
    assert "tp-word" in stage
    assert "press play" in deck
    assert studio.library.load()[0].story.startswith("A story someone sent me")


def test_adopt_shared_rejects_empty_input(studio: Studio):
    _stage, _deck, status, _button = callbacks.adopt_shared(studio, "   ")
    assert "nothing to restore" in status


def test_roll_topic_returns_a_seed(studio: Studio):
    assert callbacks.roll_topic(studio) in TOPIC_SEEDS


def test_demo_reels_back_the_offline_studio(offline_studio: Studio):
    collected = frames(offline_studio)
    assert "demo" in collected[0][2]
    _stage, deck, _status, _button = collected[-1]
    assert "deck__play" in deck
    assert offline_studio.library.load()[0].model == "demo reel"
