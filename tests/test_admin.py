"""The keeper's desk: gated, escaped, and quiet without a database."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from starlette.testclient import TestClient

from kotori.admin import (
    ADMIN_PATH,
    COOKIE_NAME,
    LOGOUT_PATH,
    SESSION_SECONDS,
    Throttle,
    _mint,
    _valid,
    register_admin,
)
from kotori.app import build_demo
from kotori.config import DEFAULT_ADMIN_PASSWORD, Settings

DSN = "postgresql://example.test/kotori"
PASSWORD = "a-keeper-knows"

ROWS: list[dict[str, Any]] = [
    {
        "story_id": "bb",
        "created_at": "2026-01-02 03:04",
        "topic": "the second lamp",
        "genre": "Noir",
        "mood": "Warm",
        "voice": "aurora",
        "model": "a quiet writer",
        "words": 12,
        "source": "studio",
        "story": "Second story, told twice.",
    },
    {
        "story_id": "aa",
        "created_at": "2026-01-01 09:00",
        "topic": "the first lamp",
        "genre": "Fable",
        "mood": "Bright",
        "voice": "aurora",
        "model": "a quiet writer",
        "words": 7,
        "source": "shared link",
        "story": "First story.",
    },
]


class FakeStore:
    """Stands in for the Postgres archive so the desk stays offline."""

    def __init__(
        self,
        rows: list[dict[str, Any]] | None = None,
        enabled: bool = True,
        unreachable: bool = False,
    ) -> None:
        self.rows = list(rows or [])
        self.enabled = enabled
        self.unreachable = unreachable

    def recent(self, limit: int = 200) -> list[dict[str, Any]] | None:
        if self.unreachable:
            return None
        return list(self.rows)[:limit]


def build_client(admin_password: str | None = None, store: FakeStore | None = None) -> TestClient:
    app = FastAPI()
    settings = Settings(database_url=DSN, admin_password=admin_password)
    register_admin(app, settings, store or FakeStore())
    return TestClient(app)


def test_the_desk_is_locked_until_the_password_arrives():
    client = build_client()
    response = client.get(ADMIN_PATH)
    assert response.status_code == 200
    assert "type='password'" in response.text
    assert "open the desk" in response.text
    # nothing about the desk may be cached or indexed
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-robots-tag"] == "noindex, nofollow"
    assert response.headers["x-content-type-options"] == "nosniff"


def test_the_default_password_is_the_documented_fallback():
    assert DEFAULT_ADMIN_PASSWORD == "cocoyourlittleboo"
    app = FastAPI()
    register_admin(app, Settings(database_url=DSN), FakeStore())
    response = TestClient(app).post(
        ADMIN_PATH, data={"password": DEFAULT_ADMIN_PASSWORD}, follow_redirects=False
    )
    assert response.status_code == 303
    assert response.headers["location"] == ADMIN_PATH


def test_a_wrong_password_is_refused():
    client = build_client()
    response = client.post(ADMIN_PATH, data={"password": "nope"})
    assert response.status_code == 401
    assert "not the password" in response.text
    assert COOKIE_NAME not in response.cookies


def test_the_right_password_opens_the_desk():
    client = build_client(admin_password=PASSWORD, store=FakeStore(ROWS))
    response = client.post(ADMIN_PATH, data={"password": PASSWORD}, follow_redirects=True)
    assert response.status_code == 200
    assert "the second lamp" in response.text


def test_passwords_with_accents_are_fine():
    client = build_client(admin_password="caf\u00e9")
    response = client.post(ADMIN_PATH, data={"password": "caf\u00e9"}, follow_redirects=False)
    assert response.status_code == 303


def test_basic_auth_opens_the_desk_without_a_form():
    client = build_client(admin_password=PASSWORD, store=FakeStore(ROWS))
    opened = client.get(ADMIN_PATH, auth=("keeper", PASSWORD))
    assert "the second lamp" in opened.text
    # a wrong password, or a header that is not Basic at all, falls back to the form
    assert "type='password'" in client.get(ADMIN_PATH, auth=("keeper", "nope")).text
    assert "type='password'" in client.get(ADMIN_PATH, headers={"Authorization": "x"}).text
    assert "type='password'" in client.get(ADMIN_PATH, headers={"Authorization": "Basic aaa"}).text


def test_a_forged_cookie_is_ignored():
    client = build_client(admin_password=PASSWORD)
    client.cookies.set(COOKIE_NAME, "9999999999.0000", path=ADMIN_PATH)
    assert "type='password'" in client.get(ADMIN_PATH).text


def test_logging_out_closes_the_desk_again():
    client = build_client(admin_password=PASSWORD, store=FakeStore(ROWS))
    client.post(ADMIN_PATH, data={"password": PASSWORD})
    assert "the second lamp" in client.get(ADMIN_PATH).text
    client.get(LOGOUT_PATH, follow_redirects=True)
    assert "type='password'" in client.get(ADMIN_PATH).text


def test_repeated_guesses_are_locked_out():
    client = build_client(admin_password=PASSWORD)
    for _ in range(5):
        assert (
            client.post(ADMIN_PATH, data={"password": "nope"}, follow_redirects=False).status_code
            == 401
        )
    refused = client.post(ADMIN_PATH, data={"password": PASSWORD}, follow_redirects=False)
    assert refused.status_code == 429
    assert "too many attempts" in refused.text


def test_the_desk_lists_every_submission_newest_first():
    client = build_client(admin_password=PASSWORD, store=FakeStore(ROWS))
    text = client.post(ADMIN_PATH, data={"password": PASSWORD}, follow_redirects=True).text
    assert "2 submissions" in text
    assert text.index("the second lamp") < text.index("the first lamp")
    # the input, the story, and who wrote it are all visible
    assert "Second story, told twice." in text
    assert "shared link" in text
    assert "a quiet writer" in text


def test_the_desk_says_when_there_is_nothing_yet():
    client = build_client(admin_password=PASSWORD, store=FakeStore([]))
    text = client.post(ADMIN_PATH, data={"password": PASSWORD}, follow_redirects=True).text
    assert "nothing has been submitted yet" in text


def test_the_desk_explains_itself_without_a_database():
    client = build_client(admin_password=PASSWORD, store=FakeStore(enabled=False))
    text = client.post(ADMIN_PATH, data={"password": PASSWORD}, follow_redirects=True).text
    assert "no database is configured" in text


def test_the_desk_says_so_when_the_archive_is_unreachable():
    client = build_client(admin_password=PASSWORD, store=FakeStore(unreachable=True))
    text = client.post(ADMIN_PATH, data={"password": PASSWORD}, follow_redirects=True).text
    assert "could not be reached" in text
    assert "nothing has been submitted yet" not in text


def test_submitted_text_is_escaped():
    hostile = "<script>alert(1)</script>"
    rows = [
        {
            "story_id": "x",
            "created_at": "2026-01-01",
            "topic": hostile,
            "genre": hostile,
            "model": hostile,
            "words": 1,
            "source": hostile,
            "story": hostile,
        }
    ]
    client = build_client(admin_password=PASSWORD, store=FakeStore(rows))
    text = client.post(ADMIN_PATH, data={"password": PASSWORD}, follow_redirects=True).text
    assert hostile not in text
    assert "&lt;script&gt;" in text


def test_registering_the_desk_twice_is_a_no_op():
    app = FastAPI()
    settings = Settings(database_url=DSN)
    register_admin(app, settings, FakeStore())
    register_admin(app, settings, FakeStore())
    paths = [getattr(route, "path", None) for route in app.routes]
    assert paths.count(ADMIN_PATH) == 2  # the GET and the POST
    assert paths.count(LOGOUT_PATH) == 1


def test_the_desk_rides_along_with_the_demo(tmp_path: Path):
    settings = Settings(data_dir=tmp_path, api_key="k")
    demo = build_demo(settings)
    paths = [getattr(route, "path", None) for route in demo.app.routes]
    assert ADMIN_PATH in paths
    with TestClient(demo.app) as client:
        assert "open the desk" in client.get(ADMIN_PATH).text


def test_session_tokens_expire_and_reject_tampering():
    token = _mint(PASSWORD)
    assert _valid(PASSWORD, token) is True
    assert _valid(PASSWORD, None) is False
    assert _valid(PASSWORD, "garbage") is False
    assert _valid(PASSWORD, "not-a-number.abc") is False
    assert _valid("another password", token) is False
    assert _valid(PASSWORD, token, now=time.time() + SESSION_SECONDS + 1) is False
    expires, _, signature = token.partition(".")
    assert _valid(PASSWORD, f"{expires}.{'0' * len(signature)}") is False
    assert _valid(PASSWORD, f"{expires}.{signature}0") is False


def test_the_throttle_forgets_once_the_lockout_lapses():
    throttle = Throttle(attempts=2, lockout=60)
    assert throttle.blocked("1.2.3.4", now=0) is False
    throttle.strike("1.2.3.4", now=0)
    assert throttle.blocked("1.2.3.4", now=0) is False
    throttle.strike("1.2.3.4", now=0)
    assert throttle.blocked("1.2.3.4", now=0) is True
    assert throttle.blocked("1.2.3.4", now=61) is False
    throttle.strike("1.2.3.4", now=61)  # a fresh strike after the lockout
    assert throttle.blocked("1.2.3.4", now=61) is False
    throttle.clear("1.2.3.4")
    assert throttle.blocked("1.2.3.4", now=0) is False
