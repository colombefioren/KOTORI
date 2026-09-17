"""Discovery and loading of the CSS/JS bundle shipped with the package.

Gradio 6 takes stylesheets and scripts at ``launch()`` time, so the UI stays
declarative and the assets stay plain text files that are easy to iterate on.

The ship's own stylesheet and script are passed to ``launch(css_paths=…, js=…,
head=…)``.  Gradio 6 stores those in ``window.gradio_config`` but its shipped
``index.html`` template does not render them back into the page — so the tabs
that ``shell.js`` drives never become visible.  :func:`_patch_gradio_template`
fixes that at import time by inserting three Jinja2 guards into the installed
template; the call is idempotent, so it is safe to run on every start-up and
survives ``uv sync`` re-installs.
"""

from __future__ import annotations

import base64
import importlib.resources
import logging
from functools import lru_cache
from pathlib import Path

from ..config import ASSETS_DIR, Settings
from .theme import DISPLAY_FONT, HAND_FONT, MONO_FONT, SANS_FONT, SERIF_FONT

_LOG = logging.getLogger("kotori")

_TEMPLATE_INJECTION = (
    "\t\t{% if config.get('css') %}"
    "<style>{{ config.get('css') | safe }}</style>{% endif %}\n"
    "\t\t{% if config.get('head') %}"
    "{{ config.get('head') | safe }}{% endif %}\n"
    "\t\t{% if config.get('js') %}"
    "<script>{{ config.get('js') | safe }}</script>{% endif %}\n"
)

#: Unique marker that is present only when our three injection lines have
#: already been written into the template.  Used to make the patch idempotent.
_TEMPLATE_MARKER = "config.get('css') | safe }}"


def _gradio_template_path() -> Path | None:
    """Return the path to the installed ``index.html`` template, or ``None``."""
    try:
        path = importlib.resources.files("gradio").joinpath(
            "templates/frontend/index.html"
        )
        if path.is_file():
            return Path(str(path))
    except Exception:
        pass
    return None


def _patch_gradio_template() -> bool:
    """Inject CSS / JS / head rendering into Gradio 6's index template.

    Gradio 6 reads ``css_paths``, ``js`` and ``head`` from ``launch()`` and
    stores them in the page config, but the shipped template never writes them
    into the DOM.  Without them the custom stylesheet and script that make the
    index tabs work are silently dropped.

    The fix is a three-line Jinja2 insertion before the
    ``<script data-gradio-mode>`` block.  It is idempotent — the function
    checks for a marker before patching and returns ``False`` immediately when
    the template is already patched or cannot be located.
    """
    path = _gradio_template_path()
    if path is None:
        _LOG.warning(
            "KOTORI could not locate the Gradio index template; "
            "custom CSS/JS/head may not be injected."
        )
        return False
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        _LOG.warning("KOTORI could not read the Gradio index template.")
        return False
    if _TEMPLATE_MARKER in text:
        return False
    anchor = "\t\t<script data-gradio-mode>"
    idx = text.find(anchor)
    if idx == -1:
        _LOG.warning(
            "KOTORI could not find the injection point in the Gradio template."
        )
        return False
    patched = text[:idx] + _TEMPLATE_INJECTION + text[idx:]
    try:
        path.write_text(patched, encoding="utf-8")
    except OSError:
        # a read-only install (some managed platforms ship a read-only
        # site-packages) must not take the whole app down with it — the app
        # still boots, just without the custom tabs/CSS/JS until the host
        # gives the venv write access.
        _LOG.warning(
            "KOTORI could not write the patched Gradio template (read-only "
            "install?); custom CSS/JS/head will not be injected."
        )
        return False
    _LOG.info("KOTORI patched the Gradio index template for CSS/JS/head.")
    return True


_patch_gradio_template()

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
FAVICON = ASSETS_DIR / "favicon.png"
KOTORI_MARK = ASSETS_DIR / "images" / "kotori-mark.png"


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
    # a deployment that opens on the night desk stays there: only a light
    # deployment lets the visitor's OS preference decide
    follow_os = "false" if default == "dark" else "true"
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
        f"if(!saved&&{follow_os}&&window.matchMedia"
        "&&window.matchMedia('(prefers-color-scheme: dark)').matches)"
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


@lru_cache(maxsize=1)
def kotori_mark_data_uri() -> str:
    """The KOTORI mark (a bird carrying a star) as a data URI.

    Inlined rather than served from a path so the masthead logo and the home
    polaroid never depend on ``allowed_paths`` or a static route.
    """
    if not KOTORI_MARK.exists():
        return ""
    encoded = base64.b64encode(KOTORI_MARK.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def missing_assets() -> list[str]:
    """Names of any expected asset that is not on disk (used by the tests)."""
    missing = [path.name for path in _resolve(STYLE_DIR, STYLE_FILES) if not path.exists()]
    missing += [path.name for path in script_paths() if not path.exists()]
    if not KOTORI_MARK.exists():
        missing.append(KOTORI_MARK.name)
    return missing
