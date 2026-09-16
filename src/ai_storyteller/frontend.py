"""Discovery and loading of the CSS/JS bundle shipped with the package.

Gradio 6 takes stylesheets and scripts at ``launch()`` time, so the UI stays
declarative and the assets stay plain text files that are easy to iterate on.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from .config import ASSETS_DIR
from .theme import DISPLAY_FONT, MONO_FONT, SERIF_FONT

STYLE_FILES: tuple[str, ...] = (
    "tokens.css",
    "layout.css",
    "components.css",
    "animations.css",
)

SCRIPT_FILES: tuple[str, ...] = (
    "trail.js",
    "teleprompter.js",
    "deck.js",
    "shell.js",
)

STYLE_DIR = ASSETS_DIR / "styles"
SCRIPT_DIR = ASSETS_DIR / "scripts"
FAVICON = ASSETS_DIR / "favicon.svg"


def _resolve(base: Path, names: tuple[str, ...]) -> list[Path]:
    return [base / name for name in names]


def stylesheet_paths() -> list[str]:
    """Absolute paths for ``launch(css_paths=...)``."""
    return [str(path) for path in _resolve(STYLE_DIR, STYLE_FILES)]


def script_paths() -> list[Path]:
    return _resolve(SCRIPT_DIR, SCRIPT_FILES)


@lru_cache(maxsize=1)
def script_source() -> str:
    """Every script concatenated into the single blob Gradio accepts."""
    parts: list[str] = []
    for path in script_paths():
        body = path.read_text(encoding="utf-8") if path.exists() else ""
        parts.append(f"/* ==== {path.name} ==== */\n{body}")
    return "\n\n".join(parts)


def head_html() -> str:
    """Head tags: webfonts, theme colour and the favicon."""
    families = (
        f"{DISPLAY_FONT.replace(' ', '+')}:wght@400;500;700",
        f"{MONO_FONT.replace(' ', '+')}:wght@400;600",
        f"{SERIF_FONT.replace(' ', '+')}:ital@0;1",
    )
    fonts = "&".join(f"family={family}" for family in families)
    return (
        '<meta name="theme-color" content="#07070c" />\n'
        '<meta name="color-scheme" content="dark" />\n'
        '<meta property="og:title" content="AI Storyteller" />\n'
        '<meta property="og:description" content="Stories that speak: '
        'streamed prose, synthesised voice, karaoke teleprompter." />\n'
        '<link rel="preconnect" href="https://fonts.googleapis.com" />\n'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />\n'
        f'<link rel="stylesheet" href="https://fonts.googleapis.com/css2?{fonts}&display=swap" />\n'
    )


def favicon_path() -> str | None:
    return str(FAVICON) if FAVICON.exists() else None


def missing_assets() -> list[str]:
    """Names of any expected asset that is not on disk (used by the tests)."""
    missing = [path.name for path in _resolve(STYLE_DIR, STYLE_FILES) if not path.exists()]
    missing += [path.name for path in script_paths() if not path.exists()]
    return missing
