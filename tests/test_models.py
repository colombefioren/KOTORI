"""Small helpers that every chip, filename and export depends on."""

import pytest

from ai_storyteller.models import (
    StoryDraft,
    StoryRequest,
    count_words,
    derive_title,
    format_duration,
    humanize_ms,
    new_story_id,
    reading_seconds,
    slugify,
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("", 0),
        ("   ", 0),
        ("one", 1),
        ("It's a well-known story.", 4),
        ("Newlines\ndon't\nmatter", 3),
    ],
)
def test_count_words(text: str, expected: int):
    assert count_words(text) == expected


def test_count_words_survives_none():
    assert count_words(None) == 0  # type: ignore[arg-type]


def test_reading_time_is_zero_for_silence():
    assert reading_seconds("") == 0


def test_reading_time_rounds_up_to_a_second():
    assert reading_seconds("one two three") == 1
    assert reading_seconds(" ".join(["word"] * 150)) == 60


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [(0, "0:00"), (9, "0:09"), (95, "1:35"), (-5, "0:00"), (3600, "60:00")],
)
def test_format_duration(seconds: float, expected: str):
    assert format_duration(seconds) == expected


def test_humanize_ms_switches_units():
    assert humanize_ms(240) == "240 ms"
    assert humanize_ms(2500) == "2.5 s"


def test_story_ids_are_short_url_safe_and_unique():
    first, second = new_story_id(), new_story_id()
    assert len(first) == 10
    assert first.isalnum() and first.islower()
    assert first != second


def test_slugify_falls_back_without_letters():
    assert slugify("The Lighthouse Keeper!") == "the-lighthouse-keeper"
    assert slugify("!!! ???") == "story"
    assert slugify("") == "story"
    assert len(slugify("word " * 40)) <= 60


def test_titles_are_capitalised_and_truncated():
    assert derive_title("the lamp") == "The lamp"
    assert derive_title("   ") == "Untitled transmission"
    long = derive_title("a" * 200)
    assert len(long) <= 68
    assert long.endswith("…")


def test_slug_combines_topic_and_id():
    draft = StoryDraft(story_id="abcd234567", topic="The Lamp & The Sea", story="hi")
    assert draft.slug == "the-lamp-the-sea-abcd"


def test_draft_metrics_and_excerpt():
    draft = StoryDraft(topic="x", story="The sea answered. " * 20)
    assert draft.words == 60
    assert draft.reading_seconds >= 1
    assert draft.excerpt.endswith("…")
    assert StoryDraft(story="short.").excerpt == "short."


def test_created_label_handles_a_broken_stamp():
    draft = StoryDraft(story="hi", created_at="not-a-date")
    assert draft.created_label == "not-a-date"
    assert "·" in StoryDraft(story="hi").created_label


def test_markdown_export_carries_the_metadata():
    draft = StoryDraft(
        topic="the lamp",
        story="She waited.",
        genre="Noir",
        mood="Tense",
        voice_label="Camber — English · UK",
        model="test-model",
    )
    markdown = draft.markdown()
    assert markdown.startswith("# The lamp")
    assert "Noir · Tense" in markdown
    assert "Camber" in markdown
    assert markdown.rstrip().endswith("*")


def test_round_trip_through_a_dict():
    draft = StoryDraft(topic="the lamp", story="She waited.", genre="Noir")
    revived = StoryDraft.from_dict({**draft.to_dict(), "unknown": "ignored"})
    assert revived.story == draft.story
    assert revived.created_at == draft.created_at
    assert not hasattr(revived, "unknown")


def test_request_normalisation():
    request = StoryRequest(topic="  ", genre="", mood="", target_words=5, voice="")
    prepared = request.normalised("a fallback")
    assert prepared.topic == "a fallback"
    assert prepared.genre == "Contemporary"
    assert prepared.mood == "Melancholic"
    assert prepared.target_words == 80
    assert prepared.voice == "aurora"
    assert prepared.slow is False


def test_request_normalisation_keeps_a_sane_length():
    assert StoryRequest(topic="x", target_words=999).normalised("y").target_words == 600
