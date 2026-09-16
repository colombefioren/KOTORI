"""Weight-based word timing.

Real forced alignment would need a second model; instead each word gets a
duration weight derived from its length and trailing punctuation. The client
normalises those weights against the true audio duration, which tracks TTS
speech closely enough to drive karaoke highlighting.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

BASE_WEIGHT = 0.55
CHAR_WEIGHT = 0.055
PAUSE_WEIGHTS: dict[str, float] = {
    ",": 0.45,
    ";": 0.50,
    ":": 0.40,
    ".": 0.95,
    "!": 0.95,
    "?": 0.95,
    "…": 1.10,
    "—": 0.50,
    "-": 0.25,
    ")": 0.25,
    '"': 0.20,
    "'": 0.05,
}
LINE_BREAK_WEIGHT = 0.80
WORDS_PER_SECOND = 2.55

_NON_WORD_RE = re.compile(r"[^\w'’-]", re.UNICODE)


@dataclass(frozen=True, slots=True)
class WordTiming:
    """One spoken word and the slice of the timeline it owns."""

    index: int
    text: str
    weight: float
    start: float
    end: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "i": self.index,
            "w": self.text,
            "s": round(self.start, 3),
            "e": round(self.end, 3),
        }


def split_words(text: str) -> list[str]:
    """Whitespace tokens, preserving punctuation for display."""
    return [token for token in (text or "").split() if token]


def word_weight(word: str, *, line_break_after: bool = False) -> float:
    """How long ``word`` takes to speak, in arbitrary units."""
    stem = _NON_WORD_RE.sub("", word)
    weight = BASE_WEIGHT + CHAR_WEIGHT * len(stem)
    if word:
        weight += PAUSE_WEIGHTS.get(word[-1], 0.0)
    if line_break_after:
        weight += LINE_BREAK_WEIGHT
    return round(weight, 3)


def word_weights(text: str) -> list[float]:
    """Weights for every word in ``text``, in order."""
    return [word_weight(word) for word in split_words(text)]


def cumulative_fractions(weights: list[float]) -> list[float]:
    """Normalised cumulative end positions in ``[0, 1]``."""
    total = sum(weights)
    if total <= 0:
        return []
    running = 0.0
    fractions = []
    for weight in weights:
        running += weight
        fractions.append(round(running / total, 5))
    return fractions


def estimate_duration(text: str, words_per_second: float = WORDS_PER_SECOND) -> float:
    """Cheap duration guess used before the audio exists."""
    words = len(split_words(text))
    if words == 0:
        return 0.0
    return round(words / words_per_second, 2)


def word_timings(text: str, duration: float | None = None) -> list[WordTiming]:
    """Timeline for ``text``; ``duration`` defaults to the estimate."""
    words = split_words(text)
    if not words:
        return []
    weights = word_weights(text)
    total = sum(weights)
    span = duration if duration and duration > 0 else estimate_duration(text)
    timings: list[WordTiming] = []
    running = 0.0
    for index, (word, weight) in enumerate(zip(words, weights, strict=False)):
        start = running / total * span
        running += weight
        end = running / total * span
        timings.append(WordTiming(index=index, text=word, weight=weight, start=start, end=end))
    return timings
