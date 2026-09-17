"""The studio should be navigable without a mouse and legible to a screen reader."""

from ai_storyteller.config import Settings
from ai_storyteller.markup import (
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

STORY = "She waited, and the city answered. Was it real?"


def draft() -> StoryDraft:
    return StoryDraft(
        story_id="a11y234567",
        topic="the lamp",
        story=STORY,
        genre="Noir",
        mood="Tense",
        voice="aurora",
        voice_label="Aurora — English · US",
        model="test-model",
    )


def test_hero_offers_a_skip_link_and_a_landmark():
    hero = render_hero(Settings(api_key="x"), _stats())
    assert 'href="#ast-composer"' in hero
    assert 'role="banner"' in hero


def test_stage_is_a_labelled_region():
    stage = render_stage(draft())
    assert 'role="region"' in stage
    assert 'aria-label="story stage for The lamp"' in stage


def test_only_the_live_paper_announces_itself():
    assert "aria-live" not in render_stage(draft())
    live = render_stage(draft(), live=True)
    assert 'aria-live="polite"' in live
    assert 'aria-busy="true"' in live


def test_waiting_is_announced_once():
    assert render_thinking("a topic").count("aria-live") == 1


def test_deck_controls_are_described():
    deck = render_deck(draft(), "data:audio/mpeg;base64,AAAA")
    assert 'role="group"' in deck
    assert 'aria-label="story player and exports"' in deck
    assert 'aria-label="Play or pause the spoken story"' in deck
    assert 'aria-label="Seek in the narration"' in deck
    assert 'aria-valuemin="0"' in deck


def test_buttons_declare_their_type_so_forms_never_submit():
    deck = render_deck(draft(), "data:audio/mpeg;base64,AAAA")
    assert deck.count('type="button"') == 6


def test_decorative_layer_is_hidden_from_assistive_tech():
    assert 'aria-hidden="true"' in render_notes()
    assert 'aria-hidden="true"' in render_stage(draft())


def test_status_line_is_read_out():
    status = render_status("writing…", tone="busy")
    assert 'role="status"' in status
    assert "writing…" in status
    assert "<b>" in status


def test_words_keep_punctuation_for_readers_and_copiers():
    assert ">answered.</span>" in render_words(STORY)


def test_empty_states_explain_themselves():
    assert "the page is still blank" in render_idle_stage()
    assert "archive is empty" in render_archive_list([])
    assert "nothing selected" in render_archive_preview(None)
    assert "voice arrives" in render_deck_idle()


def test_footer_links_are_described():
    footer = render_footer(Settings())
    assert 'rel="noreferrer"' in footer
    assert "source" in footer


def _stats():
    from ai_storyteller.library import ArchiveStats

    return ArchiveStats(drafts=1, words=12, minutes=1, top_genre="Noir")
