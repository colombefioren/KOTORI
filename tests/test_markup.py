from kotori.config import Settings
from kotori.core.library import ArchiveStats
from kotori.core.models import StoryDraft
from kotori.ui.markup import (
    ROOMS,
    STAGE_PAPER,
    archive_choices,
    render_deck,
    render_deck_idle,
    render_footer,
    render_history,
    render_home_intro,
    render_home_notes,
    render_home_steps,
    render_idle_sheet,
    render_label,
    render_masthead,
    render_room_signal,
    render_sheet,
    render_status,
    render_sticky,
    render_tabs,
    render_thinking,
    render_words,
)

STORY = "The lamp turned twice and the sea leaned closer, patient as debt."
AUDIO = "/gradio_api/file=/tmp/kotori/audio/the-lamp-abcd-aurora.mp3"


def draft() -> StoryDraft:
    return StoryDraft(
        story_id="abcd234567",
        topic="the lamp & the sea",
        story=STORY,
        genre="Noir",
        mood="Tense",
        voice="camber",
        voice_label="Camber · English · UK",
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


def test_the_empty_page_explains_itself():
    assert "the page is still blank" in render_idle_sheet()
    assert render_sheet(None) == render_idle_sheet()
    assert render_sheet(StoryDraft(story="   ")) == render_idle_sheet()


def test_the_waiting_page_is_a_polite_loading_state():
    html = render_thinking("a lighthouse", "warming up the pen…")
    assert 'role="status"' in html
    assert 'aria-live="polite"' in html
    assert "sheet--waiting" in html
    assert "tp-skeleton" in html
    assert "warming up the pen…" in html
    assert "a lighthouse" in html


def test_the_sheet_carries_chips_ruled_paper_and_a_story():
    html = render_sheet(draft())
    assert "words" in html and "Noir" in html and "2.5 s" in html
    assert ">patient</span>" in html and ">debt.</span>" in html
    assert "sheet--live" not in html
    assert f'id="{STAGE_PAPER}"' in html
    assert "sheet__holes" in html


def test_the_live_sheet_announces_itself():
    assert "sheet--live" in render_sheet(draft(), live=True)
    assert "from the history" in render_sheet(draft(), note="from the history")


def test_the_reader_streams_its_own_recording():
    html = render_deck(draft(), AUDIO)
    assert f'src="{AUDIO}"' in html
    assert 'class="deck__audio"' in html
    assert f'data-paper="{STAGE_PAPER}"' in html
    assert 'data-autoplay="1"' in html
    for action in ("copy", "download-md", "download-mp3", "share", "restart"):
        assert f'data-act="{action}"' in html


def test_the_reader_can_be_told_not_to_autoplay():
    assert 'data-autoplay="0"' in render_deck(draft(), AUDIO, autoplay=False)


def test_the_reader_escapes_everything_it_carries():
    raw = StoryDraft(story_id="x", topic="t", story='He said "<b>hi</b>" softly')
    html = render_deck(raw, '"/><script>')
    assert "<b>hi" not in html
    assert "&lt;b&gt;" in html
    assert "<script>" not in html


def test_the_idle_reader_explains_itself():
    assert "voice arrives" in render_deck_idle()


def test_the_masthead_names_the_studio_and_counts_the_shelf():
    settings = Settings(api_key="key")
    one = render_masthead(settings, ArchiveStats(drafts=1, words=400, minutes=3, top_genre="Noir"))
    assert "KOTO<b>RI</b>" in one
    assert "1 story kept" in one
    assert "a quiet writer" in one


def test_the_masthead_never_names_the_model():
    settings = Settings(model_name="some-vendor/some-model", api_key="key")
    html = render_masthead(settings, ArchiveStats())
    assert "some-vendor" not in html
    assert "some-model" not in html


def test_the_masthead_says_demo_reels_without_a_key():
    html = render_masthead(Settings(api_key=None), ArchiveStats())
    assert "the demo reels" in html


def test_the_home_page_explains_what_this_is():
    intro = render_home_intro(Settings())
    assert "KOTORI" in intro
    assert "400-word" in intro

    steps = render_home_steps()
    assert steps.count("step__title") == 3
    assert "read along" in steps

    notes = render_home_notes(Settings(api_key=None))
    assert "Demo reels" in notes
    assert "field notes" in notes
    assert "keyboard" in notes


def test_labels_are_typewritten_rules():
    assert "the brief" in render_label("the brief", "one line is enough")
    assert "one line is enough" in render_label("the brief", "one line is enough")
    assert "doodle-slot" not in render_label("the brief")
    assert "doodle-slot" in render_label("the brief", doodle="arrow")


def test_the_index_tabs_are_three_paper_tabs():
    strip = render_tabs("home", kept=2)
    assert strip.count('role="tab"') == 3
    assert 'role="tablist"' in strip
    assert [room for room, _ in ROOMS] == ["home", "playground", "history"]
    for room in ("home", "playground", "history"):
        assert f'data-room="{room}"' in strip
        assert f'aria-controls="room-{room}"' in strip
        assert f'id="tab-{room}"' in strip
    # the open room is the one marked selected
    assert 'id="tab-home" aria-controls="room-home" aria-selected="true"' in strip
    assert 'id="tab-playground" aria-controls="room-playground" aria-selected="false"' in strip


def test_the_history_tab_carries_a_hidden_count():
    assert 'data-role="count">3<' in render_tabs("home", kept=3)
    assert "hidden" in render_tabs("home", kept=0)


def test_the_room_signal_names_a_real_room():
    assert 'data-room="playground">playground<' in render_room_signal("playground")
    assert 'data-room="home"' in render_room_signal("somewhere-else")
    assert 'data-room="home"' in render_room_signal()


def test_sticky_notes_are_pastel_and_optional():
    note = render_sticky("press surprise me")
    assert "press surprise me" in note
    assert 'class="sticky"' in note
    assert "sticky--blue" in render_sticky("a tip", tone="blue")
    assert "<script>" not in render_sticky("<script>alert(1)</script>")


def test_the_home_page_tapes_up_a_polaroid():
    intro = render_home_intro(Settings(api_key="key"))
    assert 'class="polaroid paper-light"' in intro
    assert "polaroid__print" in intro
    assert "the little bird" in intro
    assert "tape" in intro


def test_status_tones_pick_a_lamp():
    assert "ast-lamp--off" in render_status("boom", tone="error")
    assert "ast-lamp--off" not in render_status("writing…", tone="busy")
    assert "ast-lamp--demo" in render_status("demo", tone="demo")


def test_history_is_empty_until_something_is_written():
    html = render_history([])
    assert "nothing here yet" in html


def test_every_history_card_gets_its_own_player():
    cards = render_history([draft()], {draft().story_id: AUDIO})
    assert "story-card" in cards
    assert f'src="{AUDIO}"' in cards
    assert 'class="mini__audio"' in cards
    assert "The lamp" in cards
    assert "tape" in cards
    assert 'data-act="open"' in cards
    assert 'data-act="delete"' in cards


def test_the_index_cards_are_index_cards():
    cards = render_history([draft()], {draft().story_id: AUDIO})
    # the punched index number, and a rose rule under the title
    assert 'class="story-card__index"' in cards
    assert "ABCD" in cards
    assert 'class="story-card__head"' in cards
    assert "stamp" in cards


def test_a_story_without_a_recording_says_so():
    html = render_history([draft()])
    assert "no voice recorded yet" in html
    assert "mini__audio" not in html


def test_the_ledger_pager_stays_hidden_under_one_page():
    html = render_history([draft()])
    assert 'data-page="1"' in html
    assert 'data-role="pager" hidden' in html


def test_the_ledger_pages_past_a_full_page():
    drafts = [
        StoryDraft(story_id=f"story{i:04d}", topic=f"topic {i}", story=STORY) for i in range(7)
    ]
    html = render_history(drafts)
    # six cards to a page: the seventh spills onto page 2
    assert html.count('data-page="1"') == 6
    assert html.count('data-page="2"') == 1
    assert "page 1 of 2" in html
    assert 'data-role="pager" hidden' not in html


def test_archive_choices_describe_each_story():
    drafts = [draft(), StoryDraft(story_id="efgh234567", topic="other", story=STORY)]
    choices = archive_choices(drafts)
    assert len({value for _, value in choices}) == 2
    assert choices[0][0].startswith("The lamp")


def test_footer_mentions_the_source():
    footer = render_footer(Settings(data_dir="/tmp/archive"))

    assert "github.com/colombefioren/kotori" in footer
