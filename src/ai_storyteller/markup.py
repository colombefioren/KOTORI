"""Server-side HTML rendering.

Everything the browser needs is rendered here: word spans carry their timing
weight in ``data-w`` so the client can drive karaoke highlighting, and the
hidden payload textareas give the export buttons something to copy.
"""

from __future__ import annotations

import html
import json
from collections.abc import Sequence

from .config import APP_NAME, APP_TAGLINE, Settings
from .library import ArchiveStats
from .models import StoryDraft, count_words, format_duration, humanize_ms
from .speech import Voice, resolve_voice
from .timing import word_weight

escape = html.escape

TICKER_ITEMS: tuple[str, ...] = (
    "streamed prose",
    "synthesised voice",
    "karaoke teleprompter",
    "local archive",
    "no accounts, no tracking",
    "press <b>?</b> for shortcuts",
)


def _chips(items: Sequence[tuple[str, str]]) -> str:
    """``(label, colour)`` pairs rendered as brutalist chips."""
    if not items:
        return ""
    spans = "".join(
        f'<span class="tp-chip{" tp-chip--" + colour if colour else ""}">{escape(label)}</span>'
        for label, colour in items
    )
    return f'<div class="tp-meta">{spans}</div>'


def render_section(index: str, title: str, meta: str = "") -> str:
    """Editorial section rule: ``01 — composer``."""
    tail = f" · {escape(meta)}" if meta else ""
    return f'<p class="ast-section"><b>{escape(index)}</b>{escape(title)}{tail}</p>'


def render_ticker() -> str:
    body = "".join(f"<span>{item}</span><i>✦</i>" for item in TICKER_ITEMS)
    return (
        '<div class="ast-ticker" aria-hidden="true">'
        f'<div class="ast-ticker__track">{body}{body}</div>'
        "</div>"
    )


def render_hero(settings: Settings, stats: ArchiveStats) -> str:
    """Ticker + headline + stat strip, in one swappable block."""
    dot = "ast-dot" if settings.is_configured else "ast-dot ast-dot--off"
    engine = settings.engine_label
    stat_rows = (
        ("drafts archived", f"{stats.drafts:,}", "mint"),
        ("words written", f"{stats.words:,}", "lilac"),
        ("minutes voiced", f"{stats.minutes:,}", "blush"),
        ("dominant genre", stats.top_genre, "butter"),
        ("engine", engine, "sky"),
    )
    stats_html = "".join(
        f'<div class="ast-stat ast-stat--{tone}"><dt>{escape(label)}</dt>'
        f"<dd>{escape(value)}</dd></div>"
        for label, value, tone in stat_rows
    )
    return f"""
{render_ticker()}
<div class="ast-shell">
  <header class="ast-hero">
    <div>
      <span class="ast-eyebrow"><i class="{dot}"></i>{escape(APP_NAME)} · v{escape(settings.version)}</span>
      <h1 class="ast-headline">Stories<br /><em>that speak</em><br /><span>for themselves</span></h1>
      <p class="ast-lede">
        A writer and a voice in one dark room. Type a topic, watch the prose arrive
        word by word, then let <b>{escape(engine)}</b> read it back to you while every
        word lights up in time with the audio.
      </p>
    </div>
    <p class="ast-heroblurb">
      <strong>{escape(APP_TAGLINE)}</strong>
      streamed prose<br />
      karaoke playback<br />
      mp3 + markdown export<br />
      jsonl archive<br />
      pastel brutalism
    </p>
  </header>
  <dl class="ast-stats">{stats_html}</dl>
</div>
"""


def render_status(note: str = "idle · waiting for a topic", tone: str = "idle") -> str:
    dot = (
        "ast-dot" if tone == "busy" else ("ast-dot ast-dot--off" if tone == "error" else "ast-dot")
    )
    return f'<div class="ast-status"><i class="{dot}"></i><b>{escape(note)}</b></div>'


def render_idle_stage() -> str:
    """The empty stage: instructions instead of a void."""
    return """
<div class="tp-stage">
  <div class="tp-empty">
    <span>the stage is empty</span>
    <p class="tp-placeholder">
      Write a topic on the left — or roll a seed — and the story will arrive here,
      word by word, with a caret blinking where the writer is looking.
    </p>
    <span>then press play to hear it read aloud</span>
  </div>
</div>
"""


def render_words(text: str, *, live: bool = False) -> str:
    """Prose as word spans carrying their spoken weight."""
    tokens = (text or "").split()
    if not tokens:
        return ""

    spans: list[str] = []
    for index, token in enumerate(tokens):
        weight = word_weight(token)
        cls = "tp-word is-fresh" if live and index >= len(tokens) - 2 else "tp-word"
        spans.append(
            f'<span class="{cls}" data-i="{index}" data-w="{weight:.3f}">{escape(token)}</span>'
        )

    body = "\n".join(spans)
    caret = '<span class="tp-caret" aria-hidden="true"></span>' if live else ""
    return f'<p class="tp-text">{body}{caret}</p>'


def render_stage(
    draft: StoryDraft | None,
    *,
    live: bool = False,
    note: str | None = None,
) -> str:
    """The teleprompter paper: prose plus the meta chips."""
    if draft is None or not draft.story.strip():
        return render_idle_stage()

    voice: Voice = resolve_voice(draft.voice)
    chips = [
        (f"{draft.words} words", "mint"),
        (f"{format_duration(draft.reading_seconds)} read", "lilac"),
        (draft.genre, ""),
        (draft.mood.lower(), ""),
        (voice.choice, "blush"),
    ]
    if draft.elapsed_ms:
        chips.append((f"written in {humanize_ms(draft.elapsed_ms)}", "butter"))
    if note:
        chips.append((note, "sky"))

    live_cls = " tp-paper--live" if live else ""
    aria = ' aria-live="polite"' if live else ""
    return f"""
<div class="tp-stage" data-story-id="{escape(draft.story_id)}">
  {_chips(chips)}
  <div class="tp-paper{live_cls}" id="ast-paper"{aria}>
    <div class="tp-halo" aria-hidden="true"></div>
    {render_words(draft.story, live=live)}
  </div>
</div>
"""


def render_deck(draft: StoryDraft, audio_uri: str, *, duration_hint: float = 0.0) -> str:
    """Custom player plus client-side export tools."""
    markdown = draft.markdown()
    voice: Voice = resolve_voice(draft.voice)
    return f"""
<div class="deck" data-story-id="{escape(draft.story_id)}"
     data-slug="{escape(draft.slug)}" data-duration-hint="{duration_hint:.2f}">
  <audio id="ast-audio" preload="metadata" src="{escape(audio_uri, quote=True)}"></audio>
  <textarea hidden class="deck__payload" data-kind="text">{escape(draft.story)}</textarea>
  <textarea hidden class="deck__payload" data-kind="markdown">{escape(markdown)}</textarea>

  <div class="deck__top">
    <button type="button" class="deck__play" data-role="toggle" aria-label="Play or pause">
      <span data-role="glyph">▶</span>
    </button>
    <span class="deck__label">{escape("now speaking")} · {escape(voice.choice)}</span>
    <div class="deck__rail" data-role="rail" role="slider" aria-label="Seek" tabindex="0">
      <div class="deck__fill" data-role="fill"></div>
    </div>
    <span class="deck__time" data-role="time">0:00 / 0:00</span>
  </div>

  <p class="deck__scribble" data-role="caption">
    follow the light: the current word glows, everything behind it stays lit.
  </p>

  <div class="deck__tools">
    <button type="button" class="deck__btn" data-act="restart">↺ from the top</button>
    <button type="button" class="deck__btn" data-act="copy">⧉ copy prose</button>
    <button type="button" class="deck__btn" data-act="download-md">↓ markdown</button>
    <button type="button" class="deck__btn" data-act="download-txt">↓ plain text</button>
    <button type="button" class="deck__btn" data-act="download-mp3">↓ mp3</button>
    <button type="button" class="deck__btn" data-act="share">↗ share link</button>
  </div>
  <p class="deck__hint" data-role="hint">
    space = play/pause · ← → = scrub 5s · click the rail to seek
  </p>
</div>
"""


def render_deck_idle(message: str = "the voice arrives once a story exists") -> str:
    return f"""
<div class="deck">
  <div class="deck__top">
    <span class="deck__label">{escape(message)}</span>
  </div>
  <span class="ast-loading"></span>
</div>
"""


def render_archive_preview(draft: StoryDraft | None) -> str:
    """Read-only archive card with the full prose."""
    if draft is None:
        return """
<div class="ast-panel">
  <div class="ar-empty">nothing selected yet · pick a draft on the left</div>
</div>
"""
    chips = [
        (f"{draft.words} words", "mint"),
        (f"{format_duration(draft.reading_seconds)} read", "lilac"),
        (draft.genre, ""),
        (draft.mood.lower(), ""),
        (draft.created_label, "butter"),
        (draft.model, "sky"),
    ]
    return f"""
<div class="ast-panel">
  <div class="ar-head">
    <h4 class="ar-meta">archive · {escape(draft.title)}</h4>
    <span class="ar-meta">{escape(draft.story_id)}</span>
  </div>
  {_chips(chips)}
  <div class="tp-paper" id="ast-paper">{render_words(draft.story)}</div>
</div>
"""


def archive_choices(drafts: Sequence[StoryDraft]) -> list[tuple[str, str]]:
    """``(label, id)`` pairs for the archive picker."""
    return [
        (
            f"⟡ {draft.title} — {draft.genre} · {draft.words} words · {draft.created_label}",
            draft.story_id,
        )
        for draft in drafts
    ]


def render_archive_list(drafts: Sequence[StoryDraft]) -> str:
    """A compact list of everything in the archive."""
    if not drafts:
        return '<div class="ar-empty">the archive is empty · write something</div>'
    items = "".join(
        f"""
    <article class="ar-item">
      <h4>{escape(draft.title)}</h4>
      <p>{escape(draft.excerpt)}</p>
      <div class="ar-meta">
        <span>{escape(draft.genre)}</span>
        <span>{draft.words} words</span>
        <span>{escape(draft.mood)}</span>
        <span>{escape(draft.created_label)}</span>
      </div>
    </article>"""
        for draft in drafts
    )
    return f'<div class="ar-list">{items}</div>'


def render_footer(settings: Settings, data_dir: object | None = None) -> str:
    """Credits, licence note and the storage location."""
    location = data_dir or settings.data_dir
    return f"""
<div class="ast-shell">
  <footer class="ast-footer">
    <span>{escape(APP_NAME)} · {escape(APP_TAGLINE)} · built with gradio {escape(_gradio_version())}</span>
    <span>
      <a href="https://github.com/colombefioren/ai-storyteller" target="_blank" rel="noreferrer">source</a> ·
      <a href="/gradio_api/info" target="_blank" rel="noreferrer">api</a> ·
      <a href="?__theme=dark">dark</a>
    </span>
    <span>drafts: {escape(str(location))}</span>
  </footer>
</div>
"""


def _gradio_version() -> str:
    import gradio as gr

    return gr.__version__


def payload_json(payload: dict[str, object]) -> str:
    """Small helper for embedding JSON in attributes."""
    return escape(json.dumps(payload, separators=(",", ":")))


def summarise(draft: StoryDraft | None) -> str:
    """One-line description used by status ticker messages."""
    if draft is None:
        return "no active story"
    return f"{draft.words} words · {format_duration(draft.reading_seconds)} · {draft.genre}"


def word_count(text: str) -> int:
    return count_words(text)
