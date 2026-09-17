"""Discovery and loading of the CSS/JS bundle shipped with the package.

Gradio 6 takes stylesheets and scripts at ``launch()`` time, so the UI stays
declarative and the assets stay plain text files that are easy to iterate on.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from .config import ASSETS_DIR, Settings
from .theme import DISPLAY_FONT, HAND_FONT, MONO_FONT, SANS_FONT, SERIF_FONT

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


def _font(name: str, axes: str = "") -> str:
    """A Google Fonts request line, with the family name URL-encoded."""
    family = name.replace(" ", "+")
    return f"family={family}{axes}" if axes else f"family={family}"


#: Google Fonts: a bookish display face, a Garamond for prose, a friendly UI
#: sans, a marker for the margins and a typewriter for everything stamped.
FONT_REQUESTS: tuple[str, ...] = (
    _font(DISPLAY_FONT, ":ital,opsz,wght@0,9..144,400..700;1,9..144,400..700"),
    _font(SERIF_FONT, ":ital,wght@0,400..700;1,400..700"),
    _font(SANS_FONT, ":wght@400..700"),
    _font(HAND_FONT, ":wght@300..700"),
    _font(MONO_FONT),
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


def head_html(settings: Settings | None = None) -> str:
    """Head tags: webfonts, the theme bootstrap and the social card."""
    fonts = "&".join(FONT_REQUESTS)
    default = (settings.theme if settings else "light") or "light"
    return (
        '<meta name="theme-color" content="#f2e8ee" />\n'
        '<meta name="color-scheme" content="light dark" />\n'
        '<meta property="og:title" content="KOTORI" />\n'
        '<meta property="og:description" content="A pastel paper studio that writes a short '
        'story from one line, then reads it back to you word by word." />\n'
        '<link rel="preconnect" href="https://fonts.googleapis.com" />\n'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />\n'
        f'<link rel="stylesheet" href="https://fonts.googleapis.com/css2?{fonts}&display=swap" />\n'
        # paint in the right theme (and the right room) before the first frame
        "<script>(function(){var root=document.documentElement;"
        "root.setAttribute('data-room','home');"
        "try{var saved=localStorage.getItem('kotori-theme');"
        f"var theme=saved||'{default}';"
        "if(!saved&&window.matchMedia&&window.matchMedia('(prefers-color-scheme: dark)').matches)"
        "{theme='dark';}"
        "root.setAttribute('data-theme',theme);"
        "if(theme==='dark'){root.classList.add('dark');}"
        "}catch(e){root.setAttribute('data-theme','light');}})();</script>\n"
        # without scripting, show every room stacked instead of hiding two
        "<noscript><style>#room-home,#room-playground,#room-history"
        "{display:block !important}</style></noscript>\n"
    )


def favicon_path() -> str | None:
    return str(FAVICON) if FAVICON.exists() else None


def missing_assets() -> list[str]:
    """Names of any expected asset that is not on disk (used by the tests)."""
    missing = [path.name for path in _resolve(STYLE_DIR, STYLE_FILES) if not path.exists()]
    missing += [path.name for path in script_paths() if not path.exists()]
    return missing
