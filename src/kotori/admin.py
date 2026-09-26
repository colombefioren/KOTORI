"""The keeper's desk: a password-gated view of every submission.

Mounted on the same ASGI app as the studio, but deliberately plain - no Gradio,
no template engine, nothing that can be talked into executing. The password
comes from ``KOTORI_ADMIN_PASSWORD``, and the session is a short-lived HMAC
cookie, so a leaked cookie expires and changing the password revokes every
session at once. Guessing is rate-limited per client address.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import html
import threading
import time
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from .config import DEFAULT_ADMIN_PASSWORD, Settings, get_settings
from .core.db import SubmissionStore

ADMIN_PATH = "/admin"
LOGOUT_PATH = "/admin/logout"
COOKIE_NAME = "kotori_admin"
SESSION_SECONDS = 8 * 60 * 60
MAX_ATTEMPTS = 5
LOCKOUT_SECONDS = 5 * 60

_HEADERS = {
    "Cache-Control": "no-store",
    "X-Robots-Tag": "noindex, nofollow",
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
}

_STYLE = """
:root{color-scheme:light dark}
*{box-sizing:border-box}
body{margin:0;padding:2rem 1.25rem;font:15px/1.6 system-ui,-apple-system,Segoe UI,sans-serif;
background:#f6f1e4;color:#2c2620}
h1{margin:0 0 1rem;font-size:1.1rem;letter-spacing:.18em;text-transform:uppercase}
h1 span{color:#a2803f}
main{max-width:60rem;margin:0 auto}
.card{max-width:24rem;margin:12vh auto;padding:2rem;border:1px solid #ded3bb;border-radius:14px;
background:#fffdf7;box-shadow:0 18px 40px rgb(44 38 32 / 8%)}
label{display:block;margin-bottom:.4rem;font-size:.8rem;letter-spacing:.08em;text-transform:uppercase;
color:#6d6154}
input{width:100%;padding:.7rem .8rem;border:1px solid #ded3bb;border-radius:9px;font:inherit;
background:#fff;color:inherit}
button{margin-top:1rem;width:100%;padding:.75rem;border:0;border-radius:9px;background:#2c2620;
color:#f6f1e4;font:inherit;letter-spacing:.06em;cursor:pointer}
header{display:flex;align-items:baseline;gap:1rem;flex-wrap:wrap;margin-bottom:1.5rem}
.count{margin:0;color:#6d6154;font-size:.85rem}
.out{margin-left:auto;color:#8a6d33;font-size:.85rem}
.warn{margin:0 0 1rem;padding:.6rem .8rem;border-radius:8px;background:#f7e2dc;color:#8a3b2a}
.empty{color:#6d6154}
article{margin-bottom:1rem;padding:1.1rem 1.2rem;border:1px solid #ded3bb;border-radius:12px;
background:#fffdf7}
article h2{margin:0 0 .35rem;font-size:1rem}
.meta{margin:0 0 .6rem;color:#6d6154;font-size:.8rem;letter-spacing:.02em}
.topic{margin:0 0 .6rem;color:#3d3529}
pre{margin:0;padding:.8rem;border-radius:9px;background:#f2ece0;white-space:pre-wrap;
word-break:break-word;font:13px/1.6 ui-monospace,SFMono-Regular,Menlo,monospace}
details summary{cursor:pointer;color:#8a6d33;font-size:.85rem}
"""


def _same(given: str, secret: str) -> bool:
    """Constant-time comparison that survives non-ASCII passwords."""
    return hmac.compare_digest(given.encode("utf-8"), secret.encode("utf-8"))


def _sign(secret: str, expires: int) -> str:
    return hmac.new(
        secret.encode("utf-8"), str(expires).encode("utf-8"), hashlib.sha256
    ).hexdigest()


def _mint(secret: str, now: float | None = None) -> str:
    """A session cookie value: expiry plus its signature, signed by the password."""
    expires = int((time.time() if now is None else now) + SESSION_SECONDS)
    return f"{expires}.{_sign(secret, expires)}"


def _valid(secret: str, token: str | None, now: float | None = None) -> bool:
    """True when ``token`` is an unexpired cookie minted with ``secret``."""
    if not token or "." not in token:
        return False
    raw_expires, _, signature = token.partition(".")
    if not raw_expires.isdigit():
        return False
    if int(raw_expires) <= (time.time() if now is None else now):
        return False
    return hmac.compare_digest(_sign(secret, int(raw_expires)), signature)


def _basic_token(header: str | None) -> str | None:
    """The password half of an ``Authorization: Basic`` header, if present."""
    if not header or not header.lower().startswith("basic "):
        return None
    try:
        decoded = base64.b64decode(header.split(" ", 1)[1].strip()).decode("utf-8", "replace")
    except ValueError:
        return None
    _, _, password = decoded.partition(":")
    return password or None


class Throttle:
    """An in-memory brake on password guessing, keyed by client address."""

    def __init__(self, attempts: int = MAX_ATTEMPTS, lockout: float = LOCKOUT_SECONDS) -> None:
        self.attempts = attempts
        self.lockout = lockout
        self._lock = threading.Lock()
        self._strikes: dict[str, tuple[int, float]] = {}

    def blocked(self, key: str, now: float | None = None) -> bool:
        moment = time.time() if now is None else now
        with self._lock:
            count, until = self._strikes.get(key, (0, 0.0))
        return count >= self.attempts and until > moment

    def strike(self, key: str, now: float | None = None) -> None:
        moment = time.time() if now is None else now
        with self._lock:
            count, until = self._strikes.get(key, (0, 0.0))
            if until and until <= moment:
                count = 0  # the previous lockout lapsed, start counting again
            count += 1
            if count >= self.attempts:
                until = moment + self.lockout
            self._strikes[key] = (count, until)

    def clear(self, key: str) -> None:
        with self._lock:
            self._strikes.pop(key, None)


def _page(title: str, body: str, status_code: int = 200) -> HTMLResponse:
    document = (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<meta name='robots' content='noindex,nofollow'>"
        f"<title>{html.escape(title)}</title><style>{_STYLE}</style></head>"
        f"<body>{body}</body></html>"
    )
    return HTMLResponse(document, status_code=status_code, headers=_HEADERS)


def login_form(error: str = "", status_code: int = 200) -> HTMLResponse:
    """The one field a keeper ever sees before the desk opens."""
    note = f"<p class='warn'>{html.escape(error)}</p>" if error else ""
    return _page(
        "KOTORI desk",
        f"<main class='card'><h1>KOTORI <span>desk</span></h1>{note}"
        "<form method='post' action='/admin'>"
        "<label for='password'>password</label>"
        "<input id='password' name='password' type='password' "
        "autocomplete='current-password' autofocus required>"
        "<button type='submit'>open the desk</button>"
        "</form></main>",
        status_code=status_code,
    )


def _entry(row: dict[str, Any]) -> str:
    """One submission, every field escaped."""
    meta = " · ".join(
        str(value)
        for value in (
            row.get("created_at"),
            row.get("genre"),
            row.get("mood"),
            row.get("voice"),
            f"{row.get('words')} words" if row.get("words") is not None else None,
            row.get("source"),
        )
        if value not in (None, "")
    )
    model = row.get("model")
    return (
        "<article>"
        f"<h2>{html.escape(str(row.get('topic') or 'untitled'))}</h2>"
        f"<p class='meta'>{html.escape(meta)}</p>"
        + (f"<p class='meta'>written by {html.escape(str(model))}</p>" if model else "")
        + f"<pre>{html.escape(str(row.get('story') or ''))}</pre>"
        "</article>"
    )


def dashboard(rows: list[dict[str, Any]], note: str = "") -> HTMLResponse:
    """Every captured submission, newest first."""
    if note:
        body = f"<p class='warn'>{html.escape(note)}</p>"
    elif rows:
        body = "".join(_entry(row) for row in rows)
    else:
        body = "<p class='empty'>nothing has been submitted yet</p>"
    count = len(rows)
    plural = "submission" if count == 1 else "submissions"
    return _page(
        "KOTORI desk",
        "<main><header><h1>KOTORI <span>desk</span></h1>"
        f"<p class='count'>{count} {plural}</p>"
        f"<a class='out' href='{LOGOUT_PATH}'>lock up</a></header>"
        f"{body}</main>",
    )


def register_admin(
    app: FastAPI,
    settings: Settings | None = None,
    store: SubmissionStore | None = None,
) -> None:
    """Attach the password-gated ``/admin`` desk to Gradio's ASGI app.

    Mirrors :func:`kotori.app.register_health`: the routes ride on the app
    object that survives launch, and a second call is a no-op.
    """
    if any(getattr(route, "path", None) == ADMIN_PATH for route in app.routes):
        return

    resolved = settings or get_settings()
    password = resolved.admin_password or DEFAULT_ADMIN_PASSWORD
    archive = store or SubmissionStore(resolved)
    throttle = Throttle()

    def client_key(request: Request) -> str:
        return request.client.host if request.client else "unknown"

    def signed_in(request: Request) -> bool:
        if _valid(password, request.cookies.get(COOKIE_NAME)):
            return True
        return _same(_basic_token(request.headers.get("authorization")) or "", password)

    def desk(request: Request) -> Response:
        if not signed_in(request):
            return login_form()
        if not archive.enabled:
            return dashboard([], note="no database is configured for this studio")
        rows = archive.recent()
        if rows is None:
            return dashboard([], note="the archive could not be reached just now")
        return dashboard(rows)

    async def unlock(request: Request) -> Response:
        key = client_key(request)
        if throttle.blocked(key):
            return login_form("too many attempts, wait a few minutes", status_code=429)
        form = await request.form()
        if not _same(str(form.get("password") or ""), password):
            throttle.strike(key)
            return login_form("that is not the password", status_code=401)
        throttle.clear(key)
        response = RedirectResponse(ADMIN_PATH, status_code=303)
        response.set_cookie(
            COOKIE_NAME,
            _mint(password),
            max_age=SESSION_SECONDS,
            path=ADMIN_PATH,
            httponly=True,
            samesite="lax",
            secure=request.url.scheme == "https",
        )
        return response

    def lock_up(request: Request) -> Response:
        response = RedirectResponse(ADMIN_PATH, status_code=303)
        response.delete_cookie(COOKIE_NAME, path=ADMIN_PATH)
        return response

    app.add_route(ADMIN_PATH, desk, methods=["GET"])
    app.add_route(ADMIN_PATH, unlock, methods=["POST"])
    app.add_route(LOGOUT_PATH, lock_up, methods=["GET"])
