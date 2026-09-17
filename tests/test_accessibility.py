"""The studio should be navigable without a mouse and legible to a screen reader."""

from kotori.config import Settings
from kotori.library import ArchiveStats
from kotori.markup import (
    render_deck,
    render_deck_idle,
    render_footer,
    render_history,
    render_idle_sheet,
    render_masthead,
    render_sheet,
    render_status,
    render_thinking,
    render_words,
)
from kotori.models import StoryDraft

STORY = "She waited, and the city answered. Was it real?"
AUDIO = "/gradio_api/file=/tmp/kotori/audio/the-lamp-a11y-aurora.mp3"


def draft() -> StoryDraft:
    return StoryDraft(
        story_id="a11y234567",
        topic="the lamp",
        story=STORY,
        genre="Noir",
        mood="Tense",
        voice="aurora",
        voice_label="Aurora — English · US",
    )


def test_the_masthead_offers_a_skip_link_and_a_landmark():
    masthead = render_masthead(Settings(api_key="x"), ArchiveStats(drafts=1))
    assert 'href="#ast-tabs"' in masthead
    assert 'role="banner"' in masthead
    assert 'aria-label="Switch between the paper and the night desk"' in masthead


def test_the_sheet_is_a_labelled_region():
    sheet = render_sheet(draft())
    assert 'role="region"' in sheet
    assert 'aria-label="story page for The lamp"' in sheet


def test_only_the_live_sheet_announces_itself():
    assert "aria-live" not in render_sheet(draft())
    live = render_sheet(draft(), live=True)
    assert 'aria-live="polite"' in live
    assert 'aria-busy="true"' in live


def test_waiting_is_announced_once():
    assert render_thinking("a topic").count("aria-live") == 1


def test_the_reader_controls_are_described():
    deck = render_deck(draft(), AUDIO)
    assert 'role="group"' in deck
    assert 'aria-label="story player and extras"' in deck
    assert 'aria-label="Play or pause the spoken story"' in deck
    assert 'aria-label="Seek in the narration"' in deck
    assert 'aria-valuemin="0"' in deck


def test_the_index_cards_describe_their_own_player():
    cards = render_history([draft()], {draft().story_id: AUDIO})
    assert 'aria-label="player for The lamp"' in cards
    assert 'aria-label="Play or pause this story"' in cards
    assert 'aria-label="Seek in this story"' in cards


def test_buttons_declare_their_type_so_forms_never_submit():
    deck = render_deck(draft(), AUDIO)
    assert deck.count('type="button"') == 6


def test_decorative_layer_is_hidden_from_assistive_tech():
    assert 'aria-hidden="true"' in render_sheet(draft())
    assert 'aria-hidden="true"' in render_deck(draft(), AUDIO)
    assert 'aria-hidden="true"' in render_history([draft()], {draft().story_id: AUDIO})


def test_status_line_is_read_out():
    status = render_status("writing…", tone="busy")
    assert 'role="status"' in status
    assert "writing…" in status
    assert "<b>" in status


def test_words_keep_punctuation_for_readers_and_copiers():
    assert ">answered.</span>" in render_words(STORY)


def test_empty_states_explain_themselves():
    assert "the page is still blank" in render_idle_sheet()
    assert "nothing here yet" in render_history([])
    assert "voice arrives" in render_deck_idle()


def test_footer_links_are_described():
    footer = render_footer(Settings())
    assert 'rel="noreferrer"' in footer
    assert "source" in footer
