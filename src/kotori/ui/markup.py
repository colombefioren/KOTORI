"""Server-side HTML rendering.

Everything the browser needs is rendered here: the index tabs across the top,
the three rooms they switch between, word spans carrying their spoken weight in
``data-w`` so the client can drive the karaoke, and every player carrying its
own ``<audio>`` element — so a shelf full of stories can never leak one story's
voice into another.

The look is a scrapbook: paper, washi tape, torn edges, ruled lines, a polaroid
and handwriting in the margins. Nothing here is neon, nothing glows.
"""

from __future__ import annotations

import html
from collections.abc import Mapping, Sequence

from ..config import APP_NAME, APP_TAGLINE, STORY_WORDS, Settings
from ..core.library import ArchiveStats
from ..core.models import StoryDraft, format_duration, humanize_ms
from ..core.speech import Voice, resolve_voice
from ..core.timing import word_weight
from .frontend import kotori_mark_data_uri

escape = html.escape

#: The rooms behind the index tabs, in the order they are tabbed.
ROOMS: tuple[tuple[str, str], ...] = (
    ("home", "home"),
    ("playground", "playground"),
    ("history", "history"),
)

#: The page the playground player narrates.
STAGE_PAPER = "paper-stage"


# ── small paper helpers ─────────────────────────────────────────────────────


def _tape(colour: str = "", side: str = "left") -> str:
    """A strip of washi tape, stuck over an edge."""
    cls = "tape"
    if colour:
        cls += f" tape--{colour}"
    if side:
        cls += f" tape--{side}"
    return f'<i class="{cls}" aria-hidden="true"></i>'


def _chips(items: Sequence[tuple[str, str]]) -> str:
    """``(label, colour)`` pairs rendered as torn paper labels."""
    if not items:
        return ""
    spans = "".join(
        f'<span class="tp-chip{" tp-chip--" + colour if colour else ""}">{escape(label)}</span>'
        for label, colour in items
    )
    return f'<div class="tp-meta">{spans}</div>'


def _doodle(kind: str) -> str:
    """A marker-pen doodle, drawn inline so it inherits the palette."""
    if kind == "star":
        return (
            '<svg class="doodle doodle--star" viewBox="0 0 24 24" aria-hidden="true">'
            '<path d="M12 1.6 14.9 8.4 22 9 16.5 13.7 18.2 21 12 17.1 5.8 21 '
            '7.5 13.7 2 9 9.1 8.4Z" fill="var(--pink-200)" stroke="var(--pink-500)" '
            'stroke-width="1.1" stroke-linejoin="round"/></svg>'
        )
    if kind == "arrow":
        return (
            '<svg class="doodle doodle--arrow" viewBox="0 0 96 54" aria-hidden="true">'
            '<path d="M4 6C26 46 58 48 86 24" fill="none" stroke="var(--blue-500)" '
            'stroke-width="2" stroke-linecap="round"/>'
            '<path d="M86 24 72 25M86 24 79 36" fill="none" stroke="var(--blue-500)" '
            'stroke-width="2" stroke-linecap="round"/></svg>'
        )
    if kind == "hearts":
        return (
            '<svg class="doodle doodle--hearts" viewBox="0 0 40 24" aria-hidden="true">'
            '<path d="M8 6c2.4-3.6 7.2-1 6 3-.9 3-6 6.4-6 6.4S2.9 12 2 9c-1.2-4 3.6-6.6 6-3Z" '
            'fill="var(--pink-300)" stroke="var(--pink-500)" stroke-width="1"/>'
            '<path d="M27 3c1.8-2.7 5.4-.8 4.5 2.2-.7 2.2-4.5 4.8-4.5 4.8S22.7 7.4 22 5.2 '
            'c-.9-3 2.7-4.9 4.5-2.2Z" fill="var(--blue-200)" stroke="var(--blue-500)" '
            'stroke-width="1"/></svg>'
        )
    return ""


def _mark(*, size: int = 40, css_class: str = "kotori-mark") -> str:
    """The KOTORI mark on its own: a bird carrying a star.

    The real drawn logo, inlined as a data URI so the masthead never depends
    on a static file route. Used next to the wordmark, and again (bigger) on
    the home polaroid, so the brand reads as one thing everywhere.
    """
    src = kotori_mark_data_uri()
    if not src:
        return ""
    return (
        f'<img class="{css_class}" width="{size}" height="{size}" src="{src}" '
        f'alt="the KOTORI mark: a bird carrying a star">'
    )


def _bird() -> str:
    """The mascot on a little riso-printed card, for the home polaroid."""
    dots = (
        '<svg class="polaroid__dots" viewBox="0 0 240 176" aria-hidden="true">'
        '<g fill="var(--pink-400)">'
        '<circle cx="30" cy="30" r="3"/><circle cx="46" cy="22" r="2"/>'
        '<circle cx="20" cy="50" r="2"/><circle cx="212" cy="150" r="3"/>'
        "</g>"
        '<path d="M-6 150C58 138 120 158 246 138" fill="none" stroke="var(--blue-500)" '
        'stroke-width="2.5" stroke-linecap="round" opacity="0.6"/>'
        "</svg>"
    )
    return f'<span class="polaroid__print">{dots}{_mark(size=200, css_class="polaroid__mark")}</span>'


# ── chrome ──────────────────────────────────────────────────────────────────


def render_label(text: str, meta: str = "", doodle: str = "") -> str:
    """A typewriter rule: ``the brief`` · *one line is enough*.

    Pass ``doodle`` (``star``, ``arrow``, ``hearts``) to pin a marker-pen
    drawing to the end of the rule.
    """
    tail = f" · {escape(meta)}" if meta else ""
    art = f'<span class="doodle-slot">{_doodle(doodle)}</span>' if doodle else ""
    return f'<p class="ast-label">{escape(text)}{tail}{art}</p>'


def render_tabs(active: str = "home", kept: int = 0) -> str:
    """The index tabs across the top of the page.

    Three paper tabs: the client flips between them without asking the server,
    and the server can send the reader to one of them by rendering a signal
    (see :func:`render_room_signal`). The little count on the history tab is
    kept fresh by the client, which can count the index cards itself.
    """
    buttons: list[str] = []
    for index, (room, label) in enumerate(ROOMS, start=1):
        on = room == active
        badge = ""
        if room == "history":
            shown = "" if kept else " hidden"
            badge = f'<span class="index-tab__count"{shown} data-role="count">{kept}</span>'
        aria = ' aria-selected="true"' if on else ' aria-selected="false"'
        tabindex = "0" if on else "-1"
        buttons.append(
            f'<button type="button" role="tab" class="index-tab" data-room="{room}" '
            f'id="tab-{room}" aria-controls="room-{room}"{aria} tabindex="{tabindex}">'
            f'<span class="index-tab__n">{index:02d}</span>'
            f'<span class="index-tab__label">{escape(label)}</span>{badge}</button>'
        )
    flap = '<span class="index-tabs__flap" aria-hidden="true"></span>'
    return (
        f'<nav class="index-tabs" role="tablist" '
        f'aria-label="{escape(APP_NAME)} rooms">{flap}{"".join(buttons)}</nav>'
    )


def render_room_signal(active: str = "home") -> str:
    """A hidden note telling the client which room to show.

    The rooms are all in the DOM at once (so the browser never re-mounts a
    player), and this is how the server asks the client to flip the page.
    """
    room = active if active in {name for name, _ in ROOMS} else "home"
    return f'<span class="room-signal" data-room="{room}">{room}</span>'


def render_masthead(settings: Settings, stats: ArchiveStats) -> str:
    """The brand, the shelf count and the theme switch."""
    kept = stats.drafts
    words = f"{stats.words} words" if stats.words else "no words yet"
    return f"""
<a class="ast-skip" href="#ast-tabs">skip to the studio</a>
<header class="masthead" role="banner">
  <div class="masthead__brand">
    {_mark(size=46)}
    <div class="masthead__word">
      <p class="masthead__title">KOTO<b>RI</b></p>
      <p class="masthead__tag">{escape(APP_TAGLINE)}</p>
    </div>
  </div>
  <div class="masthead__side">
    <p class="masthead__note">
      {kept} stor{"y" if kept == 1 else "ies"} kept · {words}<br>
      {escape(settings.engine_label)}
    </p>
    <button type="button" class="theme-switch" id="ast-theme"
            aria-label="Switch between the paper and the night desk">
      <span class="theme-switch__dot" aria-hidden="true"></span>
      <span data-role="theme-word">night desk</span>
    </button>
  </div>
</header>
"""


# ── home ────────────────────────────────────────────────────────────────────


def render_home_intro(settings: Settings) -> str:
    """What KOTORI is, in a couple of sentences and a polaroid."""
    engine = (
        "The key on this server is a real writer: everything it makes is yours."
        if settings.is_configured
        else "No key is set, so the shelves hold demo reels. Add one and the same "
        "button writes something nobody has read before."
    )
    return f"""
<div class="home__topic">
  <div class="home__say">
    <p class="home__kicker">what is this?</p>
    <h2 class="home__title">a little bird that writes you a story, then reads it aloud</h2>
    <p class="home__lede">
      {escape(APP_NAME)} takes one line from you, a place, a person, a problem, and
      writes a <b>{STORY_WORDS}-word story</b> onto the page. While it writes, the words
      land one by one, as if someone were typing. Then a small voice reads the whole
      thing back and every word warms as it is spoken, so you can read along.
    </p>
    <p class="home__lede home__lede--soft">{escape(engine)}</p>
  </div>
  <figure class="polaroid">
    {_tape("blue", "mid")}
    {_bird()}
    <figcaption>kotori, <i>“the little bird”</i></figcaption>
  </figure>
</div>
"""


STEPS: tuple[tuple[str, str], ...] = (
    (
        "give it a line",
        "A half-sentence is plenty. “A lighthouse keeper who receives letters from a "
        "ship that sank in 1912” is already a whole story waiting to happen.",
    ),
    (
        "pick a genre and a voice",
        "Type a genre, or paste one of your own. Twelve narrators, from Aurora in the "
        "US to Nori in Japan. Mood and pace are yours to leave alone.",
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
    return f"""
<div class="home__start">
  <p class="ast-label">how it goes</p>
  <ol class="steps">{items}</ol>
</div>
"""


def render_home_notes(settings: Settings) -> str:
    """The small print: what is kept, what is sent, what it costs."""
    engine = (
        "Your own model: the key you set on the server writes every story."
        if settings.is_configured
        else "Demo reels: add an API key on the server and the same button writes "
        "stories nobody has read before."
    )
    notes = (
        (
            "Every story stays here.",
            "Stories and their recordings live in the studio's own data folder as "
            "readable files. Nothing is sent anywhere else.",
        ),
        (
            "Voices come from Google Translate's speech service.",
            "That is the only outbound call at playback time, and only for a new recording.",
        ),
        (engine, "The studio never shows or asks for your credentials."),
    )
    items = "".join(f"<li><b>{escape(title)}</b> · {escape(body)}</li>" for title, body in notes)
    return f"""
<div class="home__notes">
  <div class="card card--plain">
    {_tape("", "left")}
    {render_label("field notes")}
    <ul class="fieldnotes">{items}</ul>
  </div>
  <div class="card card--plain">
    {_tape("blue", "mid")}
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


def render_sticky(text: str, *, tone: str = "") -> str:
    """A sticky note, for a tip that would otherwise be a tooltip."""
    cls = f"sticky{f' sticky--{tone}' if tone else ''}"
    return f'<p class="{cls}">{escape(text)}</p>'


# ── the status line ─────────────────────────────────────────────────────────

STATUS_LAMPS: dict[str, str] = {
    "idle": "ast-lamp",
    "busy": "ast-lamp ast-lamp--busy",
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


# ── the story page ──────────────────────────────────────────────────────────


def render_idle_sheet() -> str:
    """An empty page with instructions, not a void."""
    return f"""
<div class="sheet-wrap">
  <div class="sheet sheet--empty">
    <div class="sheet__holes" aria-hidden="true"><i></i><i></i><i></i></div>
    <div class="tp-empty">
      <h3>the page is still blank</h3>
      <ol>
        <li>Write a line in the brief, or press <b>surprise me</b>.</li>
        <li>Press <b>write the story</b> and watch it arrive, word by word.</li>
        <li>Press play, then read along as the story is spoken.</li>
      </ol>
    </div>
    {_tape("blue", "right")}
  </div>
</div>
"""


def render_thinking(topic: str = "", note: str = "shaping the first line…") -> str:
    """The waiting page: ruled lines appearing while the writer thinks."""
    chip = _chips([(topic, "blue")]) if topic else ""
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
        (f"{draft.words} words", "blue"),
        (f"{format_duration(draft.reading_seconds)} to read", "pink"),
        (draft.genre, ""),
        (draft.mood.lower(), ""),
        (voice.choice, "pink"),
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
    <div class="sheet__tape" aria-hidden="true">{_tape("blue", "right")}</div>
    <div class="tp-halo" aria-hidden="true"></div>
    {render_words(draft.story, live=live)}
  </div>
</div>
"""


# ── the reader ──────────────────────────────────────────────────────────────


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
     data-autoplay="{"1" if autoplay else "0"}"
     role="group" aria-label="story player and extras">
  {_tape("blue", "left")}
  <audio class="deck__audio" preload="metadata" src="{escape(audio_src, quote=True)}"></audio>
  <textarea hidden class="deck__payload" data-kind="text">{escape(draft.story)}</textarea>
  <textarea hidden class="deck__payload" data-kind="markdown">{escape(draft.markdown())}</textarea>

  <p class="deck__head">{escape(draft.title)}</p>

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
  {_tape("blue", "left")}
  <div class="deck__top">
    <span class="ast-dots" aria-hidden="true"><i></i><i></i><i></i></span>
    <p class="deck__idle-note">{escape(message)}</p>
  </div>
  <p class="deck__hint">a story has to exist before it can be read aloud</p>
</div>
"""


# ── the history ─────────────────────────────────────────────────────────────


def render_history(
    drafts: Sequence[StoryDraft],
    audio_srcs: Mapping[str, str] | None = None,
) -> str:
    """Every story ever written, as index cards in the ledger."""
    if not drafts:
        return f"""
<div class="ledger__empty">
  {_tape("", "left")}
  <h3>nothing here yet</h3>
  <p>Write your first story in the playground and it will be filed here, voice and all.</p>
  <p class="handnote">every card keeps its own recording; nothing is re-recorded.</p>
</div>
"""
    sources = audio_srcs or {}
    cards = "".join(_index_card(draft, sources.get(draft.story_id)) for draft in drafts)
    return f'<div class="ledger__grid">{cards}</div>'


def _index_card(draft: StoryDraft, audio_src: str | None) -> str:
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
        else '<p class="handnote handnote--quiet">no voice recorded yet</p>'
    )
    return f"""
<article class="story-card" data-story-id="{escape(draft.story_id)}"
         data-slug="{escape(draft.slug)}">
  {_tape("", "left")}
  <p class="story-card__index" aria-hidden="true">{escape(draft.story_id[:4].upper())}</p>
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
        (
            f"{draft.title} · {draft.genre} · {draft.words} words · {draft.created_label}",
            draft.story_id,
        )
        for draft in drafts
    ]


def render_footer(settings: Settings, data_dir: object | None = None) -> str:
    """Credits, licence note and where the stories are kept."""
    return f"""
<footer class="ast-footer">
  <span>{escape(APP_NAME)} · {escape(APP_TAGLINE)}</span>
  <span>
    <a href="https://github.com/colombefioren/kotori" target="_blank" rel="noreferrer">source</a> ·
    <a href="/gradio_api/info" target="_blank" rel="noreferrer">api</a>
  </span>
</footer>
"""
