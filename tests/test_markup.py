from ai_storyteller.config import Settings
from ai_storyteller.library import ArchiveStats
from ai_storyteller.markup import (
    SHELF_PAPER,
    STAGE_PAPER,
    archive_choices,
    render_archive_list,
    render_archive_preview,
    render_deck,
    render_deck_idle,
    render_footer,
    render_hero,
    render_idle_stage,
    render_notes,
    render_stage,
    render_status,
    render_thinking,
    render_words,
)
from ai_storyteller.models import StoryDraft

STORY = "The lamp turned twice and the sea leaned closer, patient as debt."


def draft() -> StoryDraft:
    return StoryDraft(
        story_id="abcd234567",
        topic="the lamp & the sea",
        story=STORY,
        genre="Noir",
        mood="Tense",
        voice="camber",
        voice_label="Camber — English · UK",
        model="test-model",
        elapsed_ms=2500,
    )


def test_words_are_marked_up_with_weights():
    html = render_words(STORY)
    assert html.count("tp-word") == len(STORY.split())
    assert 'data-w="' in html
    assert "patient" in html


def test_words_escape_markup_in_prose():
    html = render_words('He said "<script>alert(1)</script>" loudly')
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_live_words_render_a_caret():
    assert "tp-caret" not in render_words(STORY)
    assert "tp-caret" in render_words(STORY, live=True)


def test_stage_without_a_draft_shows_the_empty_state():
    assert "the page is still blank" in render_stage(None)
    assert render_stage(None) == render_idle_stage()


def test_stage_shows_meta_chips_and_story():
    html = render_stage(draft())
    assert "words" in html and "Noir" in html and "2.5 s" in html
    assert ">patient</span>" in html and ">debt.</span>" in html
    assert "tp-paper--live" not in html
    assert f'id="{STAGE_PAPER}"' in html


def test_stage_falls_back_to_the_empty_page_for_a_blank_story():
    blank = StoryDraft(story_id="x", topic="t", story="   ")
    assert "the page is still blank" in render_stage(blank)


def test_stage_marks_the_live_paper():
    assert "tp-paper--live" in render_stage(draft(), live=True)
    assert "new story" in render_stage(draft(), note="new story")


def test_stage_can_render_a_second_page_for_the_shelf():
    assert f'id="{SHELF_PAPER}"' in render_stage(draft(), paper_id=SHELF_PAPER)


def test_thinking_card_is_a_polite_loading_state():
    html = render_thinking("a lighthouse", "warming up the pen…")
    assert 'role="status"' in html
    assert 'aria-live="polite"' in html
    assert "tp-skeleton" in html
    assert "warming up the pen…" in html
    assert "a lighthouse" in html


def test_notes_strip_is_decorative_only():
    assert 'aria-hidden="true"' in render_notes()


def test_deck_carries_audio_payload_and_tools():
    html = render_deck(draft(), "data:audio/mpeg;base64,AAAA")
    assert 'src="data:audio/mpeg;base64,AAAA"' in html
    assert 'class="deck__audio"' in html
    for action in ("copy", "download-md", "download-mp3", "share", "restart"):
        assert f'data-act="{action}"' in html
    assert "# the lamp" not in html  # markdown payload is escaped, not raw


def test_deck_points_at_its_own_page_and_can_opt_out_of_autoplay():
    stage = render_deck(draft(), "data:audio/mpeg;base64,AAAA")
    assert f'data-paper="{STAGE_PAPER}"' in stage
    assert 'data-autoplay="1"' in stage

    shelf = render_deck(
        draft(), "data:audio/mpeg;base64,AAAA", paper_id=SHELF_PAPER, autoplay=False
    )
    assert f'data-paper="{SHELF_PAPER}"' in shelf
    assert 'data-autoplay="0"' in shelf


def test_deck_escapes_the_payload_for_copying():
    raw = StoryDraft(story_id="x", topic="t", story='He said "<b>hi</b>" softly')
    html = render_deck(raw, "data:audio/mpeg;base64,AAAA")
    assert "<b>hi" not in html
    assert "&lt;b&gt;" in html


def test_deck_idle_explains_itself():
    assert "voice arrives" in render_deck_idle()


def test_hero_reports_engine_and_stats():
    settings = Settings(model_name="test-model", api_key="key")
    html = render_hero(settings, ArchiveStats(drafts=3, words=420, minutes=2, top_genre="Noir"))
    assert "test-model" in html
    assert "420" in html and "Noir" in html
    assert "ast-dot--off" not in html


def test_hero_warns_when_the_engine_is_offline():
    html = render_hero(Settings(api_key=None), ArchiveStats())
    assert "ast-dot--demo" in html
    assert "the demo reels" in html


def test_status_tones():
    assert "ast-dot--off" in render_status("boom", tone="error")
    assert "ast-dot--off" not in render_status("writing…", tone="busy")
    assert "ast-dot--demo" in render_status("demo mode", tone="demo")


def test_archive_choices_are_labelled_and_unique():
    drafts = [draft(), StoryDraft(story_id="efgh234567", topic="other", story=STORY)]
    choices = archive_choices(drafts)
    assert len({value for _, value in choices}) == 2
    assert all(label.startswith("⟡") for label, _ in choices)


def test_archive_list_and_preview_render_or_explain():
    assert "archive is empty" in render_archive_list([])
    assert "The lamp" in render_archive_list([draft()])
    assert "nothing selected" in render_archive_preview(None)
    assert "from the archive" in render_archive_preview(draft())


def test_preview_offers_its_own_player_when_a_voice_exists():
    html = render_archive_preview(
        draft(), audio_uri="data:audio/mpeg;base64,AAAA", duration_hint=12.0
    )
    assert f'id="{SHELF_PAPER}"' in html
    assert 'class="deck"' in html
    assert 'data-autoplay="0"' in html


def test_preview_says_so_when_there_is_no_voice_yet():
    html = render_archive_preview(draft())
    assert "no recording yet" in html


def test_footer_mentions_the_data_dir():
    assert "gradio" in render_footer(Settings())
