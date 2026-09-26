"""Best-effort Postgres capture of every submission.

The studio writes stories whether or not a database is reachable: this module is
an observation pipe, never a dependency. With ``DATABASE_URL`` unset - or the
driver missing, or the host asleep - every call here is a safe no-op that logs
and moves on, so a playwright is never held hostage by the archive.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any

from ..config import Settings
from .models import StoryDraft

LOGGER = logging.getLogger("kotori.db")

#: Neon suspends idle databases, so a slow wake-up must not hold up the studio.
CONNECT_TIMEOUT = 10
#: How many submissions the desk shows at once.
RECENT_LIMIT = 200

SCHEMA = """
CREATE TABLE IF NOT EXISTS submissions (
    story_id     TEXT PRIMARY KEY,
    created_at   TIMESTAMPTZ NOT NULL,
    topic        TEXT NOT NULL,
    genre        TEXT,
    mood         TEXT,
    voice        TEXT,
    model        TEXT,
    target_words INTEGER,
    words        INTEGER,
    elapsed_ms   INTEGER,
    source       TEXT,
    audio_path   TEXT,
    story        TEXT NOT NULL,
    stored_at    TIMESTAMPTZ NOT NULL DEFAULT now()
)
"""

UPSERT = """
INSERT INTO submissions (
    story_id, created_at, topic, genre, mood, voice, model,
    target_words, words, elapsed_ms, source, audio_path, story
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (story_id) DO UPDATE SET
    story = EXCLUDED.story,
    audio_path = EXCLUDED.audio_path,
    words = EXCLUDED.words,
    elapsed_ms = EXCLUDED.elapsed_ms
"""

RECENT = """
SELECT story_id, created_at, topic, genre, mood, voice, model, words, source, story
FROM submissions
ORDER BY stored_at DESC
LIMIT %s
"""

#: Column order of :data:`RECENT`, so rows can be read back without a row factory.
COLUMNS = (
    "story_id",
    "created_at",
    "topic",
    "genre",
    "mood",
    "voice",
    "model",
    "words",
    "source",
    "story",
)


def _open(url: str) -> Any:
    """Open a Postgres connection; the driver is imported only when needed."""
    import psycopg

    return psycopg.connect(url, connect_timeout=CONNECT_TIMEOUT)


def _timestamp(raw: str | None) -> datetime:
    """Parse a draft's ISO stamp, falling back to ``now`` for anything odd."""
    try:
        stamp = datetime.fromisoformat(raw or "")
    except ValueError:
        return datetime.now(UTC)
    return stamp if stamp.tzinfo else stamp.replace(tzinfo=UTC)


class SubmissionStore:
    """Thread-safe, fail-soft archive of everything visitors submit."""

    def __init__(self, settings: Settings, connect: Callable[[str], Any] | None = None) -> None:
        self.url = settings.database_url
        self._connect = connect or _open
        self._lock = threading.Lock()
        self._schema_ready = False

    @property
    def enabled(self) -> bool:
        """True when a DSN was configured; otherwise every call is a no-op."""
        return bool(self.url)

    def record(self, draft: StoryDraft, *, source: str = "studio") -> bool:
        """Store one submission (input and story); returns whether it landed."""
        if not self.enabled:
            return False
        try:
            with self._lock, self._connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(UPSERT, self._row(draft, source))
                connection.commit()
        except Exception as error:
            LOGGER.warning("submission not stored: %s", error)
            return False
        return True

    def recent(self, limit: int = RECENT_LIMIT) -> list[dict[str, Any]] | None:
        """Newest submissions first, or ``None`` when the archive cannot be read.

        The distinction matters at the desk: an empty list means nobody has
        submitted anything, while ``None`` means the answer is unknown.
        """
        if not self.enabled:
            return None
        try:
            with (
                self._lock,
                self._connection() as connection,
                connection.cursor() as cursor,
            ):
                cursor.execute(RECENT, (int(limit),))
                rows = cursor.fetchall()
        except Exception as error:
            LOGGER.warning("submissions not read: %s", error)
            return None
        return [dict(zip(COLUMNS, row, strict=False)) for row in rows]

    # ── internals ────────────────────────────────────────────────────────────
    @contextmanager
    def _connection(self) -> Iterator[Any]:
        """A live connection with the table guaranteed to exist."""
        connection = self._connect(self.url or "")
        try:
            if not self._schema_ready:
                with connection.cursor() as cursor:
                    cursor.execute(SCHEMA)
                connection.commit()
                self._schema_ready = True
            yield connection
        finally:
            connection.close()

    @staticmethod
    def _row(draft: StoryDraft, source: str) -> tuple[Any, ...]:
        """The insert parameters, in the order :data:`UPSERT` expects them."""
        return (
            draft.story_id,
            _timestamp(draft.created_at),
            draft.topic,
            draft.genre,
            draft.mood,
            draft.voice,
            draft.model,
            int(draft.target_words),
            int(draft.words),
            int(draft.elapsed_ms),
            source,
            draft.audio_path,
            draft.story,
        )
