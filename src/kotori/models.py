"""Domain models shared by the service, storage and UI layers."""

from __future__ import annotations

import re
import secrets
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

from .config import STORY_WORDS

WORD_RE = re.compile(r"[\w'’-]+", re.UNICODE)
SLUG_RE = re.compile(r"[^a-z0-9]+")
WORDS_PER_MINUTE = 150.0

_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"


def count_words(text: str) -> int:
    """Number of readable words in ``text``."""
    return len(WORD_RE.findall(text or ""))


def reading_seconds(text: str, wpm: float = WORDS_PER_MINUTE) -> int:
    """Rough silent-reading estimate, used for the meta chips and exports."""
    words = count_words(text)
    if words == 0:
        return 0
    return max(1, round(words / wpm * 60))


def new_story_id() -> str:
    """Short, URL-safe, collision-resistant identifier."""
    return "".join(secrets.choice(_ALPHABET) for _ in range(10))


def slugify(text: str, fallback: str = "story") -> str:
    """Turn a topic into a filename-safe slug."""
    slug = SLUG_RE.sub("-", (text or "").lower()).strip("-")
    return slug[:60] or fallback


def derive_title(topic: str, limit: int = 68) -> str:
    """Editorial title shown on story cards."""
    clean = re.sub(r"\s+", " ", (topic or "").strip()) or "Untitled transmission"
    if len(clean) > limit:
        clean = clean[: limit - 1].rstrip() + "…"
    return clean[0].upper() + clean[1:] if clean else "Untitled transmission"


def format_duration(seconds: float) -> str:
    """``95`` -> ``1:35``, ``9`` -> ``0:09``."""
    total = max(0, round(seconds))
    return f"{total // 60}:{total % 60:02d}"


def humanize_ms(milliseconds: int | float) -> str:
    if milliseconds < 1000:
        return f"{int(milliseconds)} ms"
    return f"{milliseconds / 1000:.1f} s"


@dataclass(frozen=True, slots=True)
class StoryRequest:
    """Everything the writer needs to invent a story."""

    topic: str
    genre: str = "Contemporary"
    mood: str = "Melancholic"
    #: Pinned: every story is written to the same length.
    target_words: int = STORY_WORDS
    voice: str = "aurora"
    slow: bool = False

    def normalised(self, fallback_topic: str) -> StoryRequest:
        """Return a copy with sane defaults for empty fields."""
        return StoryRequest(
            topic=(self.topic or "").strip() or fallback_topic,
            genre=self.genre or "Contemporary",
            mood=self.mood or "Melancholic",
            target_words=STORY_WORDS,
            voice=self.voice or "aurora",
            slow=bool(self.slow),
        )


@dataclass(slots=True)
class StoryDraft:
    """A finished story plus the metadata the studio renders and stores."""

    story_id: str = field(default_factory=new_story_id)
    topic: str = ""
    genre: str = "Contemporary"
    mood: str = "Melancholic"
    target_words: int = STORY_WORDS
    story: str = ""
    voice: str = "aurora"
    voice_label: str = ""
    model: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat(timespec="seconds"))
    elapsed_ms: int = 0
    audio_path: str | None = None

    @property
    def title(self) -> str:
        return derive_title(self.topic)

    @property
    def words(self) -> int:
        return count_words(self.story)

    @property
    def reading_seconds(self) -> int:
        return reading_seconds(self.story)

    @property
    def excerpt(self) -> str:
        clean = re.sub(r"\s+", " ", (self.story or "").strip())
        return clean[:150].rstrip() + "…" if len(clean) > 150 else clean

    @property
    def slug(self) -> str:
        return f"{slugify(self.topic)}-{self.story_id[:4]}"

    @property
    def created_label(self) -> str:
        try:
            stamp = datetime.fromisoformat(self.created_at)
        except ValueError:
            return self.created_at
        return stamp.astimezone().strftime("%d %b %Y · %H:%M")

    def markdown(self) -> str:
        """Portable export used by the download button."""
        return (
            f"# {self.title}\n\n"
            f"> {self.genre} · {self.mood} · {self.words} words · "
            f"{format_duration(self.reading_seconds)} read\n"
            f"> voiced by {self.voice_label or self.voice} · {self.model}\n\n"
            f"{self.story.strip()}\n\n"
            f"---\n*{self.created_label} · KOTORI*\n"
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["created_at"] = self.created_at
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StoryDraft:
        allowed = set(cls.__dataclass_fields__)
        return cls(**{k: v for k, v in data.items() if k in allowed})
