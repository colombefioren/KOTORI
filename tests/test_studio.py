import asyncio
from pathlib import Path

import pytest

from kotori import studio as studio_module
from kotori.config import STORY_WORDS, Settings
from kotori.models import StoryDraft
from kotori.story import StoryChunk
from kotori.studio import Studio

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
def fake_speech(monkeypatch: pytest.MonkeyPatch) -> None:
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
                topic="the lamp", genre="Noir", mood="Tense", voice="camber", slow=False
            )
        ]

    return asyncio.run(collect())


def frame_with(views, needle: str):
    """The first view whose reader mentions ``needle``."""
    for view in views:
        if needle in view.deck:
            return view
    raise AssertionError(f"no frame mentions {needle!r}")


def test_idle_view_reports_a_ready_engine(studio: Studio):
    assert "ready when you are" in studio.idle_view().status


def test_idle_view_offers_the_demo_without_credentials(tmp_path: Path):
    offline = Studio(Settings(api_key=None, data_dir=tmp_path), service=FakeService())
    assert "demo mode" in offline.idle_view().status
    assert "credentials" in offline.idle_view().status


def test_stories_are_always_the_same_length(studio: Studio):
    views = ignite(studio)
    assert views[-1].draft is not None
    assert views[-1].draft.target_words == STORY_WORDS


def test_ignite_without_credentials_streams_a_demo_reel(tmp_path: Path):
    offline = Studio(Settings(api_key=None, data_dir=tmp_path), service=FakeService())
    views = ignite(offline)
    assert views[-1].draft is not None
    assert views[-1].draft.model == "demo reel"
    assert "deck__play" in views[-1].deck
    assert "read along" in views[-1].status


def test_ignite_answers_immediately_with_a_loading_state(studio: Studio):
    first = ignite(studio)[0]
    assert "tp-skeleton" in first.stage
    assert "getting the story ready" in first.deck
    assert first.busy is True
    assert first.draft is None


def test_ignite_streams_then_records_and_files(studio: Studio):
    views = ignite(studio)
    assert len(views) == 6
    assert views[-1].busy is False

    live = [view for view in views if "sheet--live" in view.stage]
    assert live and all(view.draft is None for view in live)
    assert ">The</span>" in live[0].stage and "tp-caret" in live[0].stage

    assert "recording the voice…" in frame_with(views, "recording").deck

    final = views[-1]
    assert "deck__play" in final.deck
    assert "/gradio_api/file=" in final.deck
    assert final.audio is not None and Path(final.audio).exists()
    assert "read along" in final.status

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
    assert "voices are down" in final.status
    assert studio.library.load()[0].story == PROSE


def test_the_ledger_gives_every_story_its_own_player(studio: Studio):
    ignite(studio)
    drafts = studio.drafts()
    ledger = studio.history_html(drafts)
    story_id = drafts[0].story_id

    assert "story-card" in ledger
    assert f'data-story-id="{story_id}"' in ledger
    assert "/gradio_api/file=" in ledger
    assert studio.audio_sources(drafts)[story_id].startswith("/gradio_api/file=")


def test_opening_an_archived_story_reuses_its_recording(
    studio: Studio, monkeypatch: pytest.MonkeyPatch
):
    ignite(studio)
    story_id = studio.library.load()[0].story_id

    def no_network(*args, **kwargs):
        raise AssertionError("a saved voice must not be recorded twice")

    monkeypatch.setattr(studio_module, "synthesize", no_network)
    opened = studio.open_draft(story_id)
    assert "from the history" in opened.stage
    assert "/gradio_api/file=" in opened.deck
    assert opened.audio is not None and Path(opened.audio).exists()


def test_a_recording_that_vanished_is_made_again(studio: Studio, monkeypatch: pytest.MonkeyPatch):
    ignite(studio)
    draft = studio.library.load()[0]
    assert draft.audio_path
    Path(draft.audio_path).unlink()

    calls: list[str] = []

    def counting_synthesize(text, *, voice_key, out_dir, stem, slow=False):
        calls.append(stem)
        target = Path(out_dir) / f"{stem}-{voice_key}.mp3"
        target.write_bytes(b"\xff\xfb\x90\x00")
        return target

    monkeypatch.setattr(studio_module, "synthesize", counting_synthesize)
    opened = studio.open_draft(draft.story_id)
    assert calls == [draft.slug]
    assert "/gradio_api/file=" in opened.deck


def test_an_audio_file_that_is_gone_is_not_offered(studio: Studio, tmp_path: Path):
    missing = StoryDraft(
        story_id="x", topic="t", story=PROSE, audio_path=str(tmp_path / "gone.mp3")
    )
    assert studio.audio_file(missing) is None
    assert studio._audio_src(missing) is None
    assert studio.history_html([missing]).count("mini__audio") == 0


def test_respeak_records_a_new_voice(studio: Studio):
    ignite(studio)
    story_id = studio.library.load()[0].story_id
    re_voiced = studio.respeak(story_id)
    assert "/gradio_api/file=" in re_voiced.deck
    assert "read along" in re_voiced.status


def test_respeak_reports_a_failed_recording(studio: Studio, monkeypatch: pytest.MonkeyPatch):
    ignite(studio)
    story_id = studio.library.load()[0].story_id

    def broken(*args, **kwargs):
        raise studio_module.SpeechError("the voice is unwell")

    monkeypatch.setattr(studio_module, "synthesize", broken)
    view = studio.respeak(story_id)
    assert view.audio is None
    assert "unvoiced" in view.stage
    assert "the voice is unwell" in view.status


def test_missing_draft_is_reported(studio: Studio):
    assert "nothing selected" in studio.open_draft(None).status
    assert "nothing selected" in studio.respeak("nope").status


def test_delete_and_clear_report_their_effect(studio: Studio):
    ignite(studio)
    story_id = studio.library.load()[0].story_id

    choices, ledger, _masthead, status = studio.delete(story_id)
    assert choices == []
    assert "nothing here yet" in ledger
    assert "deleted" in status

    ignite(studio)
    _choices, _ledger, _masthead, status = studio.clear()
    assert "cleared 1 story" in status
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


def test_masthead_and_footer_describe_the_studio(studio: Studio):
    assert "KOTO<b>RI</b>" in studio.masthead()
    assert str(studio.data_dir) in studio.footer()


def test_view_outputs_unpack_in_ui_order(studio: Studio):
    view = StoryDraft(story_id="x", topic="t", story=PROSE)
    stage, deck, status, draft, audio = studio_module.View(draft=view).as_outputs()
    assert stage and deck and status
    assert draft is view
    assert audio is None
