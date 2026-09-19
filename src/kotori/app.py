"""Entrypoints: build the demo, launch the server, serve the studio."""

from __future__ import annotations

import os
from typing import Any

import gradio as gr
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse

from .config import Settings, get_settings
from .ui.frontend import favicon_path, head_html, script_source, stylesheet_paths
from .ui.studio import Studio
from .ui.theme import build_theme
from .ui.ui import build_app, configure_queue

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 7860


def _env_int(*names: str, default: int) -> int:
    for name in names:
        raw = os.getenv(name)
        if raw and raw.strip().isdigit():
            return int(raw.strip())
    return default


def build_studio(settings: Settings | None = None) -> Studio:
    """One studio per process; its resolved data dir is what Gradio serves."""
    return Studio(settings or get_settings())


def health(request: Request) -> PlainTextResponse:
    """Liveness/readiness probe — answers with a plain ``hi``."""
    return PlainTextResponse("hi", status_code=200)


def register_health(app: FastAPI) -> None:
    """Attach the ``/health`` probe to Gradio's underlying ASGI app.

    ``Blocks.launch`` rebuilds its FastAPI app, which would drop any route
    registered before launch. The route is therefore attached to the app
    object and that same object is reused at launch via the ``_app`` kwarg —
    the same mechanism ``gradio.Server`` relies on — so the probe survives.
    """
    if not any(getattr(route, "path", None) == "/health" for route in app.routes):
        app.add_route("/health", health, methods=["GET"])


def build_demo(settings: Settings | None = None, studio: Studio | None = None) -> gr.Blocks:
    """Fully wired Blocks instance, queue included."""
    settings = settings or get_settings()
    demo = configure_queue(build_app(studio or Studio(settings), settings))
    register_health(demo.app)
    return demo


def launch_options(
    settings: Settings | None = None, allowed_paths: list[str] | None = None
) -> dict[str, Any]:
    """Everything Gradio 6 wants at launch time: theme, css, js, head, files."""
    settings = settings or get_settings()
    options: dict[str, Any] = {
        "theme": build_theme(),
        "css_paths": stylesheet_paths(),
        "js": script_source(),
        "head": head_html(settings),
        "favicon_path": favicon_path(),
        "server_name": os.getenv("GRADIO_SERVER_NAME", DEFAULT_HOST),
        "server_port": _env_int("PORT", "GRADIO_SERVER_PORT", default=DEFAULT_PORT),
        "show_error": True,
        "quiet": True,
        "pwa": True,
    }
    if allowed_paths:
        # the rendered mp3s live in the data dir, and the browser streams them
        options["allowed_paths"] = list(allowed_paths)
    return options


def launch(settings: Settings | None = None, **overrides: Any) -> gr.Blocks:
    """Build and launch the studio; extra kwargs win over the defaults."""
    settings = settings or get_settings()
    studio = build_studio(settings)
    demo = build_demo(settings, studio)
    options = launch_options(settings, allowed_paths=[str(studio.data_dir)])
    options.update(overrides)
    options["_app"] = demo.app
    demo.launch(**options)
    return demo


def main() -> None:
    """Console entrypoint (``kotori``)."""
    launch()
