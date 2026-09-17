"""Entrypoints: build the demo, launch the server, serve the studio."""

from __future__ import annotations

import os
from typing import Any

import gradio as gr

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


def build_demo(settings: Settings | None = None, studio: Studio | None = None) -> gr.Blocks:
    """Fully wired Blocks instance: theme and assets applied, queue included.

    The theme, stylesheet, script and head markup are stamped onto the demo and
    its config regenerated so the ASGI app it builds renders correctly even when
    served directly (Vercel) instead of only through ``launch()``.
    """
    settings = settings or get_settings()
    demo = build_app(studio or Studio(settings), settings)
    _apply_frontend_options(demo, settings)
    return configure_queue(demo)


def _apply_frontend_options(demo: gr.Blocks, settings: Settings) -> None:
    """Stamp the theme/assets that ``launch()`` normally sets onto the demo.

    Gradio reads these when it generates the page config, so they must be
    present before the ASGI app is built — otherwise the index page renders
    with no theme (``body_css`` is ``None``) and the template 500s.
    """
    options = launch_options(settings)
    demo.theme = options["theme"]
    demo.css_paths = options["css_paths"]
    demo.js = options["js"]
    demo.head = options["head"]
    demo.favicon_path = options["favicon_path"]
    demo.pwa = options["pwa"]
    demo.show_error = options["show_error"]
    demo._set_html_css_theme_variables()
    demo.config = demo.get_config_file()


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
    demo = configure_queue(build_app(studio, settings))
    options = launch_options(settings, allowed_paths=[str(studio.data_dir)])
    options.update(overrides)
    demo.launch(**options)
    return demo


def main() -> None:
    """Console entrypoint (``kotori``)."""
    launch()
