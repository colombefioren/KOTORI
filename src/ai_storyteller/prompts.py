"""Prompt library: genres, moods and the writer's brief."""

from __future__ import annotations

import random
import re
from dataclasses import dataclass

from .models import StoryRequest

SYSTEM_TEMPLATE = (
    "You are a storyteller with an editor's ear and a poet's restraint.\n"
    "Write one engaging, original story about: {topic}.\n"
    "Genre: {genre} ({genre_note}). Emotional register: {mood}.\n"
    "Rules:\n"
    "- Use clear, vivid language; concrete images over abstractions.\n"
    "- Land one genuine plot twist that re-reads the opening in a new light.\n"
    "- Aim for roughly {target_words} words (never fewer than {min_words}).\n"
    "- Plain prose only: no title, no headings, no lists, no markdown, no sign-off.\n"
    "- Close on a pensive cliffhanger.\n"
    "- Never mention that you are an AI, and never address the reader directly."
)

REVISION_TEMPLATE = (
    "Continue the story without repeating anything already written. "
    "Keep the same voice, and finish with the pensive cliffhanger."
)

MIN_WORDS_SLACK = 120


@dataclass(frozen=True, slots=True)
class Genre:
    """A narrative register the writer can be tuned to."""

    key: str
    label: str
    note: str
    accent: str

    def as_choice(self) -> str:
        return self.label


@dataclass(frozen=True, slots=True)
class Mood:
    """The emotional colour of an atmosphere."""

    key: str
    label: str
    accent: str

    def as_choice(self) -> str:
        return self.label


GENRES: tuple[Genre, ...] = (
    Genre("folk", "Folk Tale", "oral tradition, kettles, long memory", "mint"),
    Genre("scifi", "Science Fiction", "speculative systems, quiet catastrophe", "sky"),
    Genre("noir", "Noir", "rain, cigarettes, compromised narrators", "steel"),
    Genre("horror", "Cosmic Horror", "vast indifferent entities, fragile minds", "violet"),
    Genre("cyberpunk", "Cyberpunk", "neon rain, rented bodies, debt", "cyan"),
    Genre("romance", "Romance", "longing, restraint, almost-touch", "blush"),
    Genre("contemporary", "Contemporary", "ordinary rooms, unbearable Tuesdays", "butter"),
    Genre("fable", "Fable", "talking animals, gentle moral sting", "lime"),
    Genre("historical", "Historical", "dust, ledgers, someone's war", "clay"),
    Genre("fairy", "Fairy Tale", "bargains, thresholds, three attempts", "peach"),
)

MOODS: tuple[Mood, ...] = (
    Mood("melancholic", "Melancholic", "mint"),
    Mood("eerie", "Eerie", "violet"),
    Mood("hopeful", "Hopeful", "lime"),
    Mood("whimsical", "Whimsical", "peach"),
    Mood("tense", "Tense", "steel"),
    Mood("tender", "Tender", "blush"),
    Mood("wondrous", "Wondrous", "cyan"),
    Mood("bittersweet", "Bittersweet", "butter"),
)

GENRE_BY_LABEL = {genre.label: genre for genre in GENRES}
GENRE_BY_KEY = {genre.key: genre for genre in GENRES}
MOOD_BY_LABEL = {mood.label: mood for mood in MOODS}
GENRE_LABELS: tuple[str, ...] = tuple(genre.label for genre in GENRES)
MOOD_LABELS: tuple[str, ...] = tuple(mood.label for mood in MOODS)

TOPIC_SEEDS: tuple[str, ...] = (
    "a lighthouse keeper who receives letters from a ship that sank in 1912",
    "the last video rental store on a moon colony",
    "a woman who inherits her grandmother's unfinished apology",
    "a city where it rains only on Tuesdays and nobody remembers why",
    "an archivist cataloguing sounds that no longer exist",
    "two rivals trapped in a broken elevator that keeps opening on other decades",
    "a boy who sells his reflection for bus fare",
    "the night shift at a hospital for retired deities",
    "a cartographer mapping a country that rearranges itself each night",
    "a grief counsellor who starts receiving her own eulogies",
    "the detective hired to prove a ghost was murdered",
    "a garden that grows only the things you are trying to forget",
    "the final broadcast of a radio host talking to no one",
    "a translator who begins hearing what silence means",
    "an astronaut who wakes up to a knock on the hull",
    "a tailor stitching memories into a coat for a stranger",
)

_FENCE_RE = re.compile(r"^\s*```[a-zA-Z]*\s*|\s*```\s*$")
_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+.*\n+")
_LABEL_RE = re.compile(r"^\s*(title|story)\s*:\s*", re.IGNORECASE)
_SPACE_RE = re.compile(r"[ \t]{2,}")
_MULTI_NEWLINE_RE = re.compile(r"\n{3,}")
_SPACE_BEFORE_PUNCT_RE = re.compile(r"\s+([,.;:!?…])")
_MISSING_SPACE_RE = re.compile(r"(?<=[,;:])(?=[^\s\d])")


def get_genre(label: str | None) -> Genre:
    return GENRE_BY_LABEL.get((label or "").strip(), GENRES[6])


def get_mood(label: str | None) -> Mood:
    return MOOD_BY_LABEL.get((label or "").strip(), MOODS[0])


def random_topic(rng: random.Random | None = None) -> str:
    """Pick a seed prompt for the "surprise me" affordance."""
    return (rng or random).choice(TOPIC_SEEDS)


def build_system_prompt(request: StoryRequest) -> str:
    """Render the writer's brief for one request."""
    genre = get_genre(request.genre)
    mood = get_mood(request.mood)
    target = max(80, int(request.target_words))
    return SYSTEM_TEMPLATE.format(
        topic=request.topic,
        genre=genre.label,
        genre_note=genre.note,
        mood=mood.label.lower(),
        target_words=target,
        min_words=max(60, target - MIN_WORDS_SLACK),
    )


def build_messages(request: StoryRequest) -> list[tuple[str, str]]:
    """Chat messages handed to LangChain."""
    return [
        ("system", build_system_prompt(request)),
        (
            "human",
            f"Tell me the story: {request.topic}",
        ),
    ]


def clean_story(raw: str) -> str:
    """Strip model chatter so the teleprompter only ever sees prose."""
    text = _FENCE_RE.sub("", (raw or "").strip())
    text = _HEADING_RE.sub("", text)
    text = _LABEL_RE.sub("", text)
    text = _SPACE_BEFORE_PUNCT_RE.sub(r"\1", text)
    text = _MISSING_SPACE_RE.sub(" ", text)
    text = _SPACE_RE.sub(" ", text)
    text = _MULTI_NEWLINE_RE.sub("\n\n", text)
    return text.strip()
