"""KOTORI — a pastel paper studio that writes a short story and reads it aloud."""

from __future__ import annotations

from .app import build_demo, launch, main
from .config import APP_NAME, APP_TAGLINE, VERSION, Settings, get_settings
from .core.library import StoryLibrary
from .core.models import StoryDraft, StoryRequest
from .ui.studio import Studio
from .ui.ui import build_app

__all__ = [
    "APP_NAME",
    "APP_TAGLINE",
    "VERSION",
    "Settings",
    "StoryDraft",
    "StoryLibrary",
    "StoryRequest",
    "Studio",
    "build_app",
    "build_demo",
    "get_settings",
    "launch",
    "main",
]
