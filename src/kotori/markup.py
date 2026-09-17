"""Server-side HTML rendering.

Everything the browser needs is rendered here: word spans carry their timing
weight in ``data-w`` so the client can drive the karaoke, every player carries
its own ``<audio>`` element (so a shelf full of stories can never leak one
story's voice into another), and hidden payloads give the export buttons
something to copy.
"""

from __future__ import annotations

import html
from collections.abc import Mapping, Sequence

from .config import APP_NAME, APP_TAGLINE, STORY_WORDS, Settings
from .library import ArchiveStats
from .models import StoryDraft, format_duration, humanize_ms
from .speech import Voice, resolve_voice
from .timing import word_weight

escape = html.escape

#: The page the playground player narrates.
STAGE_PAPER = "paper-stage"


def _chips(items: Sequence[tuple[str, str]]) -> str:
    """``(label, colour)`` pairs rendered as torn paper labels."""
    if not items:
        return ""
    spans = "".join(
        f'<span class="tp-chip{" tp-chip--" + colour if colour else ""}">{escape(label)}</span>'
        for label, colour in items
    )
    return f'<div class="tp-meta">{spans}</div>'


def render_label(text: str, meta: str = "") -> str:
    """A typewriter rule: ``the brief`` · *one line is enough*."""
    tail = f" · {escape(meta)}" if meta else ""
    return f'<p class="ast-label">{escape(text)}{tail}</p>'


def render_masthead(settings: Settings, stats: ArchiveStats) -> str:
    """The brand, the shelf count and the theme switch."""
    kept = stats.drafts
    return f"""
<a class="ast-skip" href="#ast-tabs">skip to the studio</a>
<header class="masthead" role="banner">
  <p class="masthead__brand">
    <span class="masthead__mark">KOTO<b>RI</b></span>
    <span class="masthead__tag">{escape(APP_TAGLINE)}</span>
  </p>
  <div class="masthead__side">
    <span class="masthead__note">
      {kept} stor{'y' if kept == 1 else 'ies'} kept · {escape(settings.engine_label)}
    </span>
    <button type="button" class="theme-switch" id="ast-theme"
            aria-label="Switch between the paper and the night desk">
      <span class="theme-switch__dot" aria-hidden="true"></span>
      <span data-role="theme-word">night desk</span>
    </button>
  </div>
</header>
"""


def render_home_intro(settings: Settings) -> str:
    """What KOTORI is, in a couple of sentences."""
    return f"""
<div class="home__topic">
  <div>
    <h2 class="home__title">a little bird that writes you a story, then reads it aloud</h2>
    <p class="home__lede">
      {escape(APP_NAME)} takes one line from you — a place, a person, a problem —
      and writes a <b>{STORY_WORDS}-word story</b> into the playground. While it writes,
      the words land on the page one by one. When it is done, a small voice reads the
      whole thing back and every word warms up as it is spoken, so you can read along.
    </p>
  </div>
  <div class="card card--plain">
    <i class="tape tape--blue tape--right" aria-hidden="true"></i>
    <p class="stamp stamp--mint">how it works</p>
    <p class="handnote">
      one line in, one story out. it keeps everything you write on this machine,
      and it never asks you for an account.
    </p>
    <p class="handnote handnote--pink">start with a seed — “surprise me” is right there.</p>
  </div>
</div>
"""


STEPS: tuple[tuple[str, str], ...] = (
    (
        "give it a line",
        "A half-sentence is plenty. “A lighthouse keeper who receives letters from a "
        "ship that sank in 1912” — that is a whole story waiting to happen.",
    ),
    (
        "pick a voice",
        "Twelve narrators, from Aurora in the US to Nori in Japan. Choose a genre and "
        "a mood if you like, or leave them alone and let the studio choose.",
    ),
    (
        "read along",
        "Press play and follow the light: the word being spoken sits on a blue "
        "highlighter mark, everything behind it stays ink, everything ahead waits.",
    ),
)


def render_home_steps() -> str:
    """Three step cards, taped to the page."""
    items = "".join(
        f"""
    <li class="step">
      <span class="step__n" aria-hidden="true">{index}</span>
      <h3 class="step__title">{escape(title)}</h3>
      <p class="step__body">{escape(body)}</p>
    </li>"""
        for index, (title, body) in enumerate(STEPS, start=1)
    )
    return f'<ol class="steps">{items}</ol>'


def render_home_notes(settings: Settings) -> str:
    """The small print: what is kept, what is sent, what it costs."""
    engine = (
        "Your own model — the key you set on the server writes every story."
        if settings.is_configured
        else "Demo reels — add an API key on the server and the same button writes "
        "stories nobody has read before."
    )
    notes = (
        ("Every story stays here.", "Stories and their recordings live in the studio's "
         "own data folder as readable files. Nothing is sent anywhere else."),
        ("Voices come from Google Translate's speech service.", "That is the only "
         "outbound call at playback time, and only for a new recording."),
        (engine, "The studio never shows or asks for your credentials."),
    )
    items = "".join(
        f"<li><b>{escape(title)}</b> · {escape(body)}</li>" for title, body in notes
    )
    return f"""
<div class="home__notes">
  <div class="card card--plain">
    <i class="tape tape--left" aria-hidden="true"></i>
    {render_label("field notes")}
    <ul class="fieldnotes">{items}</ul>
  </div>
  <div class="card card--plain">
    <i class="tape tape--blue tape--mid" aria-hidden="true"></i>
    {render_label("keyboard")}
    <ul class="fieldnotes">
      <li>Press <b>?</b> any time for the whole shortcut sheet.</li>
      <li><b>⌘/Ctrl + K</b> opens the command palette.</li>
      <li><b>space</b> plays and pauses the voice, <b>← →</b> skip five seconds.</li>
      <li><b>T</b> hides the pastel cursor trail if it distracts you.</li>
    </ul>
  </div>
</div>
"""


STATUS_LAMPS: dict[str, str] = {
    "idle": "ast-lamp",
    "busy": "ast-lamp",
    "demo": "ast-lamp ast-lamp--demo",
    "error": "ast-lamp ast-lamp--off",
}


def render_status(note: str = "ready when you are", tone: str = "idle") -> str:
    """The handwritten status line under the composer."""
    lamp = STATUS_LAMPS.get(tone, STATUS_LAMPS["idle"])
    return (
        f'<p class="ast-status" role="status"><i class="{lamp}" aria-hidden="true"></i>'
        f"<b>{escape(note)}</b></p>"
    )


def render_idle_sheet() -> str:
    """An empty page with instructions, not a void."""
    return f"""
<div class="sheet-wrap">
  <div class="sheet">
    <div class="sheet__holes" aria-hidden="true"><i></i><i></i><i></i></div>
    <div class="tp-empty">
      <h3>the page is still blank</h3>
      <ol>
        <li>Write a line in the brief — or press <b>surprise me</b>.</li>
        <li>Press <b>write the story</b> and watch it arrive, word by word.</li>
        <li>Press play, then read along as the story is spoken.</li>
      </ol>
    </div>
  </div>
</div>
"""


def render_thinking(topic: str = "", note: str = "shaping the first line…") -> str:
    """The waiting page: ruled lines appearing while the writer thinks."""
    chip = _chips([(topic, "lilac")]) if topic else ""
    return f"""
<div class="sheet-wrap">
  {chip}
  <div class="sheet sheet--waiting" role="status" aria-live="polite">
    <div class="sheet__holes" aria-hidden="true"><i></i><i></i><i></i></div>
    <div class="tp-skeleton" aria-hidden="true"><span></span><span></span><span></span></div>
    <p class="handnote">
      <span class="ast-dots" aria-hidden="true"><i></i><i></i><i></i></span>
      {escape(note)}
    </p>
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
    return f'<p class="sheet__prose">{body}{caret}</p>'


def render_sheet(
    draft: StoryDraft | None,
    *,
    live: bool = False,
    note: str | None = None,
) -> str:
    """The story page: prose on ruled paper, with the meta labels above it."""
    if draft is None or not draft.story.strip():
        return render_idle_sheet()

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

    live_cls = " sheet--live" if live else ""
    aria = ' aria-live="polite" aria-busy="true"' if live else ""
    return f"""
<div class="sheet-wrap" data-story-id="{escape(draft.story_id)}" role="region"
     aria-label="story page for {escape(draft.title)}">
  {_chips(chips)}
  <div class="sheet{live_cls}" id="{STAGE_PAPER}"{aria}>
    <div class="sheet__holes" aria-hidden="true"><i></i><i></i><i></i></div>
    <div class="tp-halo" aria-hidden="true"></div>
    {render_words(draft.story, live=live)}
  </div>
</div>
"""


def render_deck(
    draft: StoryDraft,
    audio_src: str,
    *,
    duration_hint: float = 0.0,
    autoplay: bool = True,
) -> str:
    """The reader: one play button, a rule to seek on, a quiet row of extras."""
    voice: Voice = resolve_voice(draft.voice)
    return f"""
<div class="deck" data-paper="{STAGE_PAPER}" data-story-id="{escape(draft.story_id)}"
     data-slug="{escape(draft.slug)}" data-duration-hint="{duration_hint:.2f}"
     data-autoplay="{'1' if autoplay else '0'}"
     role="group" aria-label="story player and extras">
  <i class="tape tape--blue tape--left" aria-hidden="true"></i>
  <audio class="deck__audio" preload="metadata" src="{escape(audio_src, quote=True)}"></audio>
  <textarea hidden class="deck__payload" data-kind="text">{escape(draft.story)}</textarea>
  <textarea hidden class="deck__payload" data-kind="markdown">{escape(draft.markdown())}</textarea>

  <div class="deck__top">
    <button type="button" class="deck__play" data-role="toggle"
            aria-label="Play or pause the spoken story">
      <span data-role="glyph">▶</span>
    </button>
    <div class="deck__body">
      <p class="deck__label">now speaking · <b data-role="caption">{escape(voice.choice)}</b></p>
      <div class="deck__rail" data-role="rail" role="slider" aria-label="Seek in the narration"
           aria-valuemin="0" aria-valuemax="100" aria-valuenow="0" tabindex="0">
        <div class="deck__fill" data-role="fill"></div>
      </div>
      <span class="deck__time" data-role="time">0:00 / 0:00</span>
    </div>
  </div>

  <p class="deck__hint">space plays and pauses · ← → skip five seconds · drag the rule to seek</p>

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
    """The reader while there is nothing to play yet."""
    return f"""
<div class="deck deck--idle" role="status" aria-live="polite">
  <i class="tape tape--blue tape--left" aria-hidden="true"></i>
  <div class="deck__top">
    <span class="ast-dots" aria-hidden="true"><i></i><i></i><i></i></span>
    <p class="deck__idle-note">{escape(message)}</p>
  </div>
</div>
"""


def render_history(
    drafts: Sequence[StoryDraft],
    audio_srcs: Mapping[str, str] | None = None,
) -> str:
    """Every story ever written, as index cards taped to the ledger."""
    if not drafts:
        return """
<div class="ledger__empty">
  <h3>nothing here yet</h3>
  <p>Write your first story in the playground and it will be filed here, voice and all.</p>
</div>
"""
    sources = audio_srcs or {}
    cards = "".join(
        _history_card(draft, sources.get(draft.story_id)) for draft in drafts
    )
    return f'<div class="ledger__grid">{cards}</div>'


def _history_card(draft: StoryDraft, audio_src: str | None) -> str:
    """One index card: title, stamp, excerpt, its own player, its actions."""
    player = (
        f"""
  <div class="mini" data-story-id="{escape(draft.story_id)}" data-slug="{escape(draft.slug)}"
       role="group" aria-label="player for {escape(draft.title)}">
    <audio class="mini__audio" preload="none" src="{escape(audio_src, quote=True)}"></audio>
    <button type="button" class="mini__play" data-role="toggle"
            aria-label="Play or pause this story"><span data-role="glyph">▶</span></button>
    <div class="mini__rail" data-role="rail" role="slider" aria-label="Seek in this story"
         aria-valuemin="0" aria-valuemax="100" aria-valuenow="0" tabindex="0">
      <div class="mini__fill" data-role="fill"></div>
    </div>
    <span class="mini__time" data-role="time">0:00 / --:--</span>
  </div>"""
        if audio_src
        else '<p class="handnote">no voice recorded yet</p>'
    )
    return f"""
<article class="story-card" data-story-id="{escape(draft.story_id)}"
         data-slug="{escape(draft.slug)}">
  <i class="tape tape--left" aria-hidden="true"></i>
  <header class="story-card__head">
    <h3 class="story-card__title">{escape(draft.title)}</h3>
    <span class="stamp">{escape(draft.created_label)}</span>
  </header>
  <p class="story-card__meta">
    <span>{escape(draft.genre)}</span>
    <span>{draft.words} words</span>
    <span>{format_duration(draft.reading_seconds)} to read</span>
  </p>
  <p class="story-card__excerpt">{escape(draft.excerpt)}</p>
  {player}
  <div class="story-card__acts">
    <button type="button" class="act" data-act="open">open in the playground</button>
    <button type="button" class="act" data-act="download-mp3">save the mp3</button>
    <button type="button" class="act act--danger" data-act="delete">delete</button>
  </div>
</article>"""


def archive_choices(drafts: Sequence[StoryDraft]) -> list[tuple[str, str]]:
    """``(label, id)`` pairs for the drawer's picker."""
    return [
        (f"{draft.title} — {draft.genre} · {draft.words} words · {draft.created_label}", draft.story_id)
        for draft in drafts
    ]


def render_footer(settings: Settings, data_dir: object | None = None) -> str:
    """Credits, licence note and where the stories are kept."""
    location = data_dir or settings.data_dir
    return f"""
<footer class="ast-footer">
  <span>{escape(APP_NAME)} · {escape(APP_TAGLINE)} · written with gradio {escape(_gradio_version())}</span>
  <span>
    <a href="https://github.com/colombefioren/kotori" target="_blank" rel="noreferrer">source</a> ·
    <a href="/gradio_api/info" target="_blank" rel="noreferrer">api</a>
  </span>
  <span>kept in {escape(str(location))}</span>
</footer>
"""


def _gradio_version() -> str:
    import gradio as gr

    return gr.__version__
