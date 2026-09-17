"""A tiny append-only archive for finished stories.

JSONL keeps the studio dependency-free: no database to migrate, and the file
stays human-readable (and greppable) between sessions.
"""

from __future__ import annotations

import json
import threading
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import StoryDraft

DEFAULT_LIMIT = 120


@dataclass(frozen=True, slots=True)
class ArchiveStats:
    """Headline numbers for the studio's stat strip."""

    drafts: int = 0
    words: int = 0
    minutes: int = 0
    top_genre: str = "—"

    def to_dict(self) -> dict[str, Any]:
        return {
            "drafts": self.drafts,
            "words": self.words,
            "minutes": self.minutes,
            "top_genre": self.top_genre,
        }


class StoryLibrary:
    """Thread-safe JSONL store, newest entry last on disk."""

    def __init__(self, path: str | Path, limit: int = DEFAULT_LIMIT) -> None:
        self.path = Path(path)
        self.limit = limit
        self._lock = threading.Lock()

    # ── reading ──────────────────────────────────────────────────────────────
    def load(self) -> list[StoryDraft]:
        """All drafts, newest first."""
        return list(reversed(self._read_raw()))

    def get(self, story_id: str | None) -> StoryDraft | None:
        if not story_id:
            return None
        for draft in reversed(self._read_raw()):
            if draft.story_id == story_id:
                return draft
        return None

    def stats(self) -> ArchiveStats:
        drafts = self._read_raw()
        if not drafts:
            return ArchiveStats()
        genres = Counter(draft.genre for draft in drafts if draft.genre)
        words = sum(draft.words for draft in drafts)
        return ArchiveStats(
            drafts=len(drafts),
            words=words,
            minutes=round(sum(draft.reading_seconds for draft in drafts) / 60),
            top_genre=genres.most_common(1)[0][0] if genres else "—",
        )

    # ── writing ──────────────────────────────────────────────────────────────
    def save(self, draft: StoryDraft) -> StoryDraft:
        """Append a draft, replacing any entry with the same id."""
        with self._lock:
            drafts = [d for d in self._read_raw() if d.story_id != draft.story_id]
            drafts.append(draft)
            if len(drafts) > self.limit:
                drafts = drafts[-self.limit :]
            self._write_raw(drafts)
        return draft

    def delete(self, story_id: str | None) -> bool:
        """Remove one draft; returns whether anything changed."""
        if not story_id:
            return False
        with self._lock:
            drafts = self._read_raw()
            kept = [d for d in drafts if d.story_id != story_id]
            if len(kept) == len(drafts):
                return False
            self._write_raw(kept)
        return True

    def clear(self) -> int:
        """Empty the archive and report how many drafts were dropped."""
        with self._lock:
            count = len(self._read_raw())
            self._write_raw([])
        return count

    # ── internals ────────────────────────────────────────────────────────────
    def _read_raw(self) -> list[StoryDraft]:
        if not self.path.exists():
            return []
        drafts: list[StoryDraft] = []
        try:
            lines = self.path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                drafts.append(StoryDraft.from_dict(payload))
        return drafts

    def _write_raw(self, drafts: list[StoryDraft]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        body = "\n".join(json.dumps(draft.to_dict(), ensure_ascii=False) for draft in drafts)
        temp = self.path.with_suffix(self.path.suffix + ".tmp")
        temp.write_text(body + ("\n" if body else ""), encoding="utf-8")
        temp.replace(self.path)
