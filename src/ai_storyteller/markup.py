"""Server-side HTML rendering.

Everything the browser needs is rendered here: word spans carry their timing
weight in ``data-w`` so the client can drive karaoke highlighting, every player
carries its own ``<audio>`` element (so a shelf full of stories can never leak
one story's voice into another), and hidden payload textareas give the export
buttons something to copy.
"""

from __future__ import annotations

import html
from collections.abc import Sequence

from .config import APP_NAME, APP_TAGLINE, Settings
from .library import ArchiveStats
from .models import StoryDraft, format_duration, humanize_ms
from .speech import Voice, resolve_voice
from .timing import word_weight

escape = html.escape

#: Decorative margin notes in the hero — a scrap of the studio's own story.
NOTES: tuple[str, ...] = (
    "streamed prose",
    "a small, patient voice",
    "karaoke, word by word",
    "kept in a local book",
    "no accounts, no tracking",
)

#: The player used by the write stage.
STAGE_PAPER = "paper-stage"
#: The player used by the shelf.
SHELF_PAPER = "paper-shelf"


def _chips(items: Sequence[tuple[str, str]]) -> str:
    """``(label, colour)`` pairs rendered as pastel chips."""
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


def render_notes() -> str:
    """A decorative strip of margin notes. Never announced to assistive tech."""
    spans = "".join(f"<span>{escape(note)}</span><i>✽</i>" for note in NOTES)
    return f'<p class="ast-notes" aria-hidden="true">{spans}</p>'


def render_hero(settings: Settings, stats: ArchiveStats) -> str:
    """Skip link, headline, stat pills — the whole masthead."""
    if settings.is_configured:
        dot = "ast-dot"
        engine = settings.engine_label
    else:
        dot = "ast-dot ast-dot--demo"
        engine = "the demo reels"

    stat_rows = (
        ("stories kept", f"{stats.drafts:,}", "mint"),
        ("words written", f"{stats.words:,}", "lilac"),
        ("minutes voiced", f"{stats.minutes:,}", "blush"),
        ("favourite genre", stats.top_genre, "butter"),
        ("engine", engine, "sky"),
    )
    stats_html = "".join(
        f'<div class="ast-stat ast-stat--{tone}"><dt>{escape(label)}</dt>'
        f"<dd>{escape(value)}</dd></div>"
        for label, value, tone in stat_rows
    )
    return f"""
<a class="ast-skip" href="#ast-composer">skip to the composer</a>
<div class="ast-aurora" aria-hidden="true"></div>
<header class="ast-hero" role="banner">
  <div>
    <span class="ast-eyebrow">
      <i class="{dot}"></i>{escape(APP_NAME)}
      <span class="ast-eyebrow__tag">v{escape(settings.version)} · {escape(engine)}</span>
    </span>
    <h1 class="ast-headline">Stories that <em>speak</em> for themselves</h1>
    <p class="ast-lede">
      Write a topic on the left, or roll a seed and let it surprise you. The story
      arrives word by word on the page, then reads itself back to you while every
      word warms up as it is spoken.
    </p>
    {render_notes()}
  </div>
  <p class="ast-heroblurb">
    <strong>{escape(APP_TAGLINE)}</strong>
    a quiet page,<br />
    a small voice,<br />
    and a shelf of stories<br />
    you can keep.
  </p>
</header>
<dl class="ast-stats">{stats_html}</dl>
"""


STATUS_DOTS: dict[str, str] = {
    "idle": "ast-dot",
    "busy": "ast-dot",
    "demo": "ast-dot ast-dot--demo",
    "error": "ast-dot ast-dot--off",
}


def render_status(note: str = "ready when you are", tone: str = "idle") -> str:
    """Status line; ``tone`` picks the lamp colour."""
    dot = STATUS_DOTS.get(tone, STATUS_DOTS["idle"])
    return (
        f'<p class="ast-status" role="status"><i class="{dot}" aria-hidden="true"></i>'
        f"<b>{escape(note)}</b></p>"
    )


def render_idle_stage() -> str:
    """The empty page: an invitation instead of a void."""
    return f"""
<div class="ast-card tp-stage">
  <div class="tp-empty">
    <h3>the page is still blank</h3>
    <ol>
      <li>Write a topic in the composer — or press <b>surprise me</b>.</li>
      <li>Press <b>write the story</b> and watch it arrive, word by word.</li>
      <li>Then press play and follow the light as it is read aloud.</li>
    </ol>
  </div>
  <div class="tp-paper" id="{STAGE_PAPER}">
    <p class="tp-placeholder">
      Somewhere a lighthouse keeper is opening a letter she has not written yet…
    </p>
  </div>
</div>
"""


def render_thinking(topic: str = "", note: str = "shaping the first line…") -> str:
    """The loading state: a page being ruled while the writer thinks."""
    chips = [(topic, "lilac")] if topic else []
    return f"""
<div class="ast-card tp-stage tp-stage--waiting" role="status" aria-live="polite">
  {_chips(chips)}
  <div class="tp-paper tp-paper--waiting">
    <div class="tp-skeleton" aria-hidden="true"><span></span><span></span><span></span></div>
    <p class="tp-caption"><span class="ast-dots" aria-hidden="true"><i></i><i></i><i></i></span>
      {escape(note)}</p>
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
    paper_id: str = STAGE_PAPER,
) -> str:
    """The story page: prose plus the meta chips."""
    if draft is None or not draft.story.strip():
        return render_idle_stage()

    voice: Voice = resolve_voice(draft.voice)
    chips = [
        (f"{draft.words} words", "mint"),
        (f"{format_duration(draft.reading_seconds)} to read", "lilac"),
        (draft.genre, ""),
        (draft.mood.lower(), ""),
        (voice.choice, "blush"),
    ]
    if draft.elapsed_ms:
        chips.append((f"written in {humanize_ms(draft.elapsed_ms)}", "butter"))
    if note:
        chips.append((note, "sky"))

    live_cls = " tp-paper--live" if live else ""
    aria = ' aria-live="polite" aria-busy="true"' if live else ""
    return f"""
<div class="ast-card tp-stage" data-story-id="{escape(draft.story_id)}" role="region"
     aria-label="story stage for {escape(draft.title)}">
  {_chips(chips)}
  <div class="tp-paper{live_cls}" id="{escape(paper_id)}"{aria}>
    <div class="tp-halo" aria-hidden="true"></div>
    {render_words(draft.story, live=live)}
  </div>
</div>
"""


def render_deck(
    draft: StoryDraft,
    audio_uri: str,
    *,
    duration_hint: float = 0.0,
    paper_id: str = STAGE_PAPER,
    autoplay: bool = True,
) -> str:
    """The player: one play button, a rail, and a quiet row of extras."""
    voice: Voice = resolve_voice(draft.voice)
    return f"""
<div class="deck" data-paper="{escape(paper_id)}" data-story-id="{escape(draft.story_id)}"
     data-slug="{escape(draft.slug)}" data-duration-hint="{duration_hint:.2f}"
     data-autoplay="{"1" if autoplay else "0"}"
     role="group" aria-label="story player and exports">
  <audio class="deck__audio" preload="metadata" src="{escape(audio_uri, quote=True)}"></audio>
  <textarea hidden class="deck__payload" data-kind="text">{escape(draft.story)}</textarea>
  <textarea hidden class="deck__payload" data-kind="markdown">{escape(draft.markdown())}</textarea>

  <div class="deck__top">
    <button type="button" class="deck__play" data-role="toggle"
            aria-label="Play or pause the spoken story">
      <span data-role="glyph">▶</span>
    </button>
    <div class="deck__body">
      <p class="deck__label"><b data-role="caption">now speaking · {escape(voice.choice)}</b></p>
      <div class="deck__rail" data-role="rail" role="slider" aria-label="Seek in the narration"
           aria-valuemin="0" aria-valuemax="100" aria-valuenow="0" tabindex="0">
        <div class="deck__fill" data-role="fill"></div>
      </div>
      <span class="deck__time" data-role="time">0:00 / 0:00</span>
    </div>
  </div>

  <p class="deck__hint" data-role="hint">
    space plays and pauses · ← → skip five seconds · click the rule to seek
  </p>

  <div class="deck__tools">
    <button type="button" class="deck__btn" data-act="restart">↺ from the top</button>
    <button type="button" class="deck__btn" data-act="download-mp3">↓ save the mp3</button>
    <button type="button" class="deck__btn" data-act="copy">⧉ copy the words</button>
    <button type="button" class="deck__btn" data-act="download-md">↓ save as markdown</button>
    <button type="button" class="deck__btn" data-act="share">↗ share a link</button>
  </div>
</div>
"""


def render_deck_idle(message: str = "the voice arrives once a story exists") -> str:
    """The player while there is nothing to play yet."""
    return f"""
<div class="deck deck--idle" role="status" aria-live="polite">
  <div class="deck__top">
    <span class="ast-dots" aria-hidden="true"><i></i><i></i><i></i></span>
    <p class="deck__idle-note">{escape(message)}</p>
  </div>
</div>
"""


def render_archive_preview(
    draft: StoryDraft | None,
    *,
    audio_uri: str | None = None,
    duration_hint: float = 0.0,
) -> str:
    """The shelf's reading pane: the story, its chips and its own player."""
    if draft is None:
        return """
<div class="ast-card">
  <div class="ar-empty">nothing selected yet · pick a story on the left</div>
</div>
"""
    chips = [
        (f"{draft.words} words", "mint"),
        (f"{format_duration(draft.reading_seconds)} to read", "lilac"),
        (draft.genre, ""),
        (draft.mood.lower(), ""),
        (draft.created_label, "butter"),
        (draft.model, "sky"),
    ]
    player = (
        render_deck(
            draft,
            audio_uri,
            duration_hint=duration_hint,
            paper_id=SHELF_PAPER,
            autoplay=False,
        )
        if audio_uri
        else render_deck_idle("this story has no recording yet · record one to hear it")
    )
    return f"""
<div class="ast-card">
  <div class="ar-head">
    <h3 class="ar-title">{escape(draft.title)}</h3>
    <p class="ar-meta">from the archive · {escape(draft.story_id)}</p>
  </div>
  {_chips(chips)}
  <div class="tp-paper" id="{SHELF_PAPER}">{render_words(draft.story)}</div>
</div>
{player}
"""


def archive_choices(drafts: Sequence[StoryDraft]) -> list[tuple[str, str]]:
    """``(label, id)`` pairs for the shelf picker."""
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
<footer class="ast-footer">
  <span>{escape(APP_NAME)} · {escape(APP_TAGLINE)} · written with gradio {escape(_gradio_version())}</span>
  <span>
    <a href="https://github.com/colombefioren/ai-storyteller" target="_blank" rel="noreferrer">source</a> ·
    <a href="/gradio_api/info" target="_blank" rel="noreferrer">api</a>
  </span>
  <span>kept in {escape(str(location))}</span>
</footer>
"""


def _gradio_version() -> str:
    import gradio as gr

    return gr.__version__
