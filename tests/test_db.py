"""The submission archive: fail-soft, offline, and boring on purpose."""

from __future__ import annotations

import sys
import time
from datetime import UTC, datetime
from typing import Any

from kotori.config import Settings
from kotori.core import db as db_module
from kotori.core.db import COLUMNS, SubmissionStore, _open, _timestamp
from kotori.core.models import StoryDraft

DSN = "postgresql://example.test/kotori"


class FakeCursor:
    """Records every statement so the SQL contract stays pinned."""

    def __init__(self, rows: list[tuple[Any, ...]] | None = None, blow_up: bool = False) -> None:
        self.calls: list[tuple[str, Any]] = []
        self.rows = rows or []
        self.blow_up = blow_up

    def __enter__(self) -> FakeCursor:
        return self

    def __exit__(self, *exc: object) -> bool:
        return False

    def execute(self, sql: str, params: Any = None) -> None:
        if self.blow_up:
            raise RuntimeError("the host is asleep")
        self.calls.append((sql, params))

    def fetchall(self) -> list[tuple[Any, ...]]:
        return self.rows


class FakeConnection:
    def __init__(self, cursor: FakeCursor) -> None:
        self._cursor = cursor
        self.commits = 0
        self.closed = False

    def cursor(self) -> FakeCursor:
        return self._cursor

    def commit(self) -> None:
        self.commits += 1

    def close(self) -> None:
        self.closed = True


def opened(
    url: str | None = DSN, cursor: FakeCursor | None = None
) -> tuple[SubmissionStore, list[FakeConnection], FakeCursor]:
    """A store wired to a fake driver, plus everything it touched."""
    connections: list[FakeConnection] = []
    shared = cursor or FakeCursor()

    def connect(dsn: str) -> FakeConnection:
        connection = FakeConnection(shared)
        connections.append(connection)
        return connection

    store = SubmissionStore(Settings(database_url=url), connect=connect)
    return store, connections, shared


def test_a_store_without_a_dsn_is_a_no_op():
    store, connections, _ = opened(url=None)
    draft = StoryDraft(topic="a quiet town", story="It rained.")
    assert store.enabled is False
    assert store.record(draft) is False
    assert store.recent() is None
    assert connections == []


def test_recording_creates_the_table_then_upserts_the_submission():
    store, connections, cursor = opened()
    draft = StoryDraft(topic="a quiet town", story="It rained and nobody minded.")
    draft.elapsed_ms = 1200
    assert store.record(draft) is True
    assert len(connections) == 1
    assert connections[0].closed is True
    assert connections[0].commits == 2  # the schema, then the row
    schema_sql, schema_params = cursor.calls[0]
    assert "CREATE TABLE IF NOT EXISTS submissions" in schema_sql
    assert schema_params is None
    insert_sql, params = cursor.calls[1]
    assert "INSERT INTO submissions" in insert_sql
    assert params[0] == draft.story_id
    assert params[1] == _timestamp(draft.created_at)
    assert params[2:7] == (
        draft.topic,
        draft.genre,
        draft.mood,
        draft.voice,
        draft.model,
    )
    assert params[7] == draft.target_words
    assert params[8] == draft.words
    assert params[9] == 1200
    assert params[10] == "studio"
    assert params[12] == draft.story
    # the row's parameters line up with the placeholder count
    assert insert_sql.count("%s") == len(params)


def test_the_schema_is_only_created_once_per_store():
    store, connections, cursor = opened()
    store.record(StoryDraft(topic="one", story="First."))
    store.record(StoryDraft(topic="two", story="Second."))
    assert len(connections) == 2
    statements = [sql for sql, _ in cursor.calls if "CREATE TABLE" in sql]
    assert len(statements) == 1


def test_the_source_of_a_submission_is_kept():
    store, _, cursor = opened()
    store.record(StoryDraft(topic="shared", story="Arrived by link."), source="shared link")
    assert cursor.calls[1][1][10] == "shared link"


def test_a_broken_submission_is_swallowed():
    def connect(dsn: str) -> FakeConnection:
        raise OSError("no route to the host")

    store = SubmissionStore(Settings(database_url=DSN), connect=connect)
    assert store.record(StoryDraft(topic="one", story="First.")) is False


def test_a_failing_statement_leaves_no_half_open_connection():
    store, connections, _ = opened(cursor=FakeCursor(blow_up=True))
    assert store.record(StoryDraft(topic="one", story="First.")) is False
    assert connections[0].closed is True


def test_recent_maps_rows_onto_columns():
    row = (
        "abc",
        datetime(2026, 1, 1, tzinfo=UTC),
        "topic",
        "Noir",
        "Warm",
        "aurora",
        "m",
        4,
        "studio",
        "A story.",
    )
    store, _, _ = opened(cursor=FakeCursor(rows=[row]))
    rows = store.recent()
    assert rows == [dict(zip(COLUMNS, row, strict=False))]


def test_recent_reports_an_unreadable_archive_as_unknown():
    store, _, _ = opened(cursor=FakeCursor(blow_up=True))
    assert store.recent(limit=5) is None


def test_recent_passes_its_limit_through():
    store, _, cursor = opened()
    store.recent(limit=5)
    statement, params = cursor.calls[-1]
    assert "SELECT story_id" in statement
    assert params == (5,)


def test_timestamp_parses_and_repairs_stamps():
    assert _timestamp("2026-01-02T03:04:05+00:00") == datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
    naive = _timestamp("2026-01-02T03:04:05")
    assert naive.tzinfo == UTC
    junk = _timestamp("not a date")
    assert junk.tzinfo == UTC
    assert abs(junk.timestamp() - time.time()) < 30


def test_open_uses_psycopg_lazily(monkeypatch):
    seen: dict[str, Any] = {}

    class FakePsycopg:
        @staticmethod
        def connect(url: str, **kwargs: Any) -> str:
            seen["url"] = url
            seen["kwargs"] = kwargs
            return "a connection"

    monkeypatch.setitem(sys.modules, "psycopg", FakePsycopg)
    assert _open(DSN) == "a connection"
    assert seen["url"] == DSN
    assert seen["kwargs"]["connect_timeout"] == db_module.CONNECT_TIMEOUT
