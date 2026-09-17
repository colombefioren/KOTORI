import random

from kotori.models import StoryRequest
from kotori.prompts import (
    GENRES,
    MOODS,
    TOPIC_SEEDS,
    build_messages,
    build_system_prompt,
    clean_story,
    get_genre,
    get_mood,
    random_topic,
)


def make_request(**overrides) -> StoryRequest:
    base = {
        "topic": "a lighthouse keeper who receives letters from a sunken ship",
        "genre": "Cosmic Horror",
        "mood": "Eerie",
        "target_words": 240,
    }
    return StoryRequest(**{**base, **overrides})


def test_every_genre_and_mood_is_unique():
    assert len({genre.label for genre in GENRES}) == len(GENRES)
    assert len({mood.label for mood in MOODS}) == len(MOODS)


def test_system_prompt_carries_the_brief():
    prompt = build_system_prompt(make_request())
    assert "lighthouse keeper" in prompt
    assert "Cosmic Horror" in prompt
    assert "eerie" in prompt
    assert "240" in prompt


def test_minimum_word_floor_is_respected():
    prompt = build_system_prompt(make_request(target_words=90))
    assert "never fewer than 60" in prompt


def test_messages_start_with_the_system_brief():
    messages = build_messages(make_request())
    assert messages[0][0] == "system"
    assert messages[1][0] == "human"
    assert make_request().topic in messages[1][1]


def test_unknown_genre_and_mood_fall_back():
    assert get_genre("Interpretive Dance").key == "contemporary"
    assert get_genre(None).key == "contemporary"
    assert get_mood("nonsense").key == "melancholic"


def test_random_topic_is_seeded_and_known():
    topic = random_topic(random.Random(7))
    assert topic in TOPIC_SEEDS
    assert topic == random_topic(random.Random(7))


def test_clean_story_strips_model_chatter():
    raw = "```\nTitle: The Lamp\n\nShe waited,  and the sea ,  answered.\n```"
    assert clean_story(raw) == "She waited, and the sea, answered."


def test_clean_story_collapses_blank_lines_and_trims():
    assert clean_story("a\n\n\n\nb  \n") == "a\n\nb"


def test_clean_story_keeps_ordinary_prose_intact():
    prose = "The kettle sang. Nobody answered; the room held its breath."
    assert clean_story(prose) == prose


def test_clean_story_handles_empty_input():
    assert clean_story("") == ""
    assert clean_story("   ") == ""
