"""Entrypoints: build the demo, launch the server, serve the studio."""

from __future__ import annotations

import os
from typing import Any

import gradio as gr

from .config import Settings, get_settings
from .frontend import favicon_path, head_html, script_source, stylesheet_paths
from .studio import Studio
from .theme import build_theme
from .ui import build_app, configure_queue

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 7860


def _env_int(*names: str, default: int) -> int:
    for name in names:
        raw = os.getenv(name)
        if raw and raw.strip().isdigit():
            return int(raw.strip())
    return default


def build_demo(settings: Settings | None = None) -> gr.Blocks:
    """Fully wired Blocks instance, queue included."""
    settings = settings or get_settings()
    return configure_queue(build_app(Studio(settings), settings))


def launch_options(settings: Settings | None = None) -> dict[str, Any]:
    """Everything Gradio 6 wants at launch time: theme, css, js and head."""
    settings = settings or get_settings()
    return {
        "theme": build_theme(),
        "css_paths": stylesheet_paths(),
        "js": script_source(),
        "head": head_html(),
        "favicon_path": favicon_path(),
        "server_name": os.getenv("GRADIO_SERVER_NAME", DEFAULT_HOST),
        "server_port": _env_int("PORT", "GRADIO_SERVER_PORT", default=DEFAULT_PORT),
        "show_error": True,
        "quiet": True,
        "pwa": True,
    }


def launch(settings: Settings | None = None, **overrides: Any) -> gr.Blocks:
    """Build and launch the studio; extra kwargs win over the defaults."""
    settings = settings or get_settings()
    demo = build_demo(settings)
    options = launch_options(settings)
    options.update(overrides)
    demo.launch(**options)
    return demo


def main() -> None:
    """Console entrypoint (``ai-storyteller``)."""
    launch()
