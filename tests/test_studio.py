import asyncio
from pathlib import Path

import pytest

from ai_storyteller import studio as studio_module
from ai_storyteller.config import Settings
from ai_storyteller.models import StoryDraft
from ai_storyteller.story import StoryChunk
from ai_storyteller.studio import Studio

PROSE = (
    "The lamp turned twice and the sea leaned closer, patient as debt. "
    "She read the letter again and understood the ship had never sunk at all."
)


class FakeService:
    """Stands in for StoryService so the pipeline runs offline."""

    def prepare(self, request):
        return request.normalised("a quiet town")

    async def stream(self, request):
        yield StoryChunk(text=PROSE[:40], delta=PROSE[:40], note="writing…")
        yield StoryChunk(text=PROSE, delta=PROSE[40:], note="writing…")
        yield StoryChunk(text=PROSE, delta="", finished=True, note="closing the loop…")


@pytest.fixture(autouse=True)
def fake_speech(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Never touch the network: write a tiny stand-in mp3 instead."""

    def fake_synthesize(text, *, voice_key, out_dir, stem, slow=False):
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        target = out_dir / f"{stem}-{voice_key}.mp3"
        target.write_bytes(b"\xff\xfb\x90\x00")
        return target

    monkeypatch.setattr(studio_module, "synthesize", fake_synthesize)


@pytest.fixture
def studio(tmp_path: Path) -> Studio:
    settings = Settings(model_name="test-model", api_key="test-key", data_dir=tmp_path)
    return Studio(settings, service=FakeService())


def ignite(studio: Studio):
    async def collect():
        return [
            view
            async for view in studio.ignite(
                topic="the lamp",
                genre="Noir",
                mood="Tense",
                target_words=200,
                voice="camber",
                slow=False,
            )
        ]

    return asyncio.run(collect())


def test_idle_view_reports_a_ready_engine(studio: Studio):
    assert "waiting for a topic" in studio.idle_view().status


def test_idle_view_warns_without_credentials(tmp_path: Path):
    offline = Studio(Settings(api_key=None, data_dir=tmp_path), service=FakeService())
    assert "engine offline" in offline.idle_view().status


def test_ignite_streams_then_voices_and_archives(studio: Studio):
    views = ignite(studio)
    assert len(views) == 5

    live = views[1]
    assert "tp-paper--live" in live.stage
    assert ">The</span>" in live.stage and "tp-caret" in live.stage
    assert live.draft is None

    assert "tp-paper--live" not in views[2].stage
    assert "synthesising the voice…" in views[3].deck

    final = views[-1]
    assert "deck__play" in final.deck
    assert "data:audio/mpeg;base64," in final.deck
    assert final.audio is not None and Path(final.audio).exists()
    assert "follow the light" in final.status

    archived = studio.library.load()
    assert len(archived) == 1
    assert archived[0].story == PROSE
    assert archived[0].voice_label.startswith("Camber")
    assert archived[0].elapsed_ms >= 0


def test_ignite_reports_speech_failure_without_losing_the_story(
    studio: Studio, monkeypatch: pytest.MonkeyPatch
):
    def broken(*args, **kwargs):
        raise studio_module.SpeechError("voices are down")

    monkeypatch.setattr(studio_module, "synthesize", broken)
    final = ignite(studio)[-1]
    assert "voices are down" in final.deck
    assert final.audio is None
    assert studio.library.load()[0].story == PROSE


def test_archive_round_trip_and_preview(studio: Studio):
    ignite(studio)
    choices, preview, listing = studio.archive_state()
    assert len(choices) == 1
    assert "The lamp" in preview
    assert "ar-item" in listing

    story_id = choices[0][1]
    opened = studio.open_draft(story_id)
    assert "from the archive" in opened.stage
    assert openable_deck_is_idle(opened)

    re_voiced = studio.respeak(story_id)
    assert "data:audio/mpeg;base64," in re_voiced.deck


def openable_deck_is_idle(view) -> bool:
    return "speak it again" in view.deck


def test_missing_draft_is_reported(studio: Studio):
    assert "nothing selected" in studio.open_draft(None).status
    assert "nothing selected" in studio.respeak("nope").status


def test_delete_and_clear_report_their_effect(studio: Studio):
    ignite(studio)
    story_id = studio.library.load()[0].story_id

    choices, _preview, _hero, status = studio.delete(story_id)
    assert choices == []
    assert "deleted" in status

    ignite(studio)
    _choices, _preview, _hero, status = studio.clear()
    assert "burned 1 draft" in status
    assert studio.library.load() == []


def test_adopt_restores_a_shared_story(studio: Studio):
    view = studio.adopt("  A story someone sent me. It ends badly.  ")
    assert "restored" in view.status
    assert view.draft is not None
    assert view.draft.genre == "Restored"
    assert studio.library.load()[0].story.startswith("A story someone sent me")


def test_adopt_rejects_empty_input(studio: Studio):
    assert "nothing to restore" in studio.adopt("   ").status


def test_roll_topic_returns_a_seed(studio: Studio):
    assert isinstance(studio.roll_topic(), str)
    assert len(studio.roll_topic()) > 10


def test_footer_shows_the_resolved_data_dir(studio: Studio):
    assert str(studio.data_dir) in studio.footer()


def test_view_outputs_unpack_in_ui_order(studio: Studio):
    view = StoryDraft(story_id="x", topic="t", story=PROSE)
    stage, deck, status, draft, audio = studio_module.View(draft=view).as_outputs()
    assert stage and deck and status
    assert draft is view
    assert audio is None
