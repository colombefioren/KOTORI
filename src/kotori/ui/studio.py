"""The studio: one place where writing, voicing and filing meet.

Callbacks return plain strings (HTML) and dataclasses, so this module stays
free of Gradio and can be driven from a notebook or the CLI just as easily.
"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import quote

from ..config import STORY_WORDS, Settings, ensure_writable_dir, get_settings
from ..core.db import SubmissionStore
from ..core.demo import DEMO_GENRE, DEMO_MODEL, DEMO_MOOD, demo_stream
from ..core.library import StoryLibrary
from ..core.models import StoryDraft, StoryRequest
from ..core.prompts import get_genre, get_mood, random_topic
from ..core.speech import SpeechError, resolve_voice, synthesize
from ..core.story import StoryService
from ..core.timing import estimate_duration
from .markup import (
    archive_choices,
    render_deck,
    render_deck_idle,
    render_footer,
    render_history,
    render_idle_sheet,
    render_masthead,
    render_sheet,
    render_status,
    render_thinking,
)

OPENING_STATUS = "warming up the pen…"
OPENING_DEMO = "warming up the pen… (demo reel)"
WRITING_DECK = "the voice arrives as soon as the story is finished…"
VOICE_WAIT_NOTE = "recording the voice…"
VOICE_WAIT_HINT = "good things take a moment: a fresh recording can take up to thirty seconds"
READY_NOTE = "all yours · press play and read along"
SAVED_NOTE = "filed in the history"
DEMO_STATUS = "demo mode · add credentials for your own stories"

#: Where Gradio serves the rendered mp3s from.
FILE_ROUTE = "/gradio_api/file="


@dataclass(slots=True)
class View:
    """The swappable regions of the playground."""

    stage: str = field(default_factory=render_idle_sheet)
    deck: str = field(default_factory=render_deck_idle)
    status: str = field(default_factory=render_status)
    draft: StoryDraft | None = None
    audio: str | None = None
    #: True while the studio is still working, so the UI can show it.
    busy: bool = False

    def as_outputs(self) -> tuple[str, str, str, StoryDraft | None, str | None]:
        return (self.stage, self.deck, self.status, self.draft, self.audio)


class Studio:
    """Session-agnostic controller for the whole experience."""

    def __init__(
        self,
        settings: Settings | None = None,
        library: StoryLibrary | None = None,
        service: StoryService | None = None,
        store: SubmissionStore | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.data_dir = ensure_writable_dir(self.settings.data_dir)
        self.audio_dir = self.data_dir / "audio"
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        self.library = library or StoryLibrary(self.data_dir / "library.jsonl")
        self.service = service or StoryService(self.settings)
        #: Best-effort archive of every submission; a no-op without a DSN.
        self.store = store if store is not None else SubmissionStore(self.settings)

    # ── chrome ───────────────────────────────────────────────────────────────
    def masthead(self) -> str:
        return render_masthead(self.settings, self.library.stats())

    def footer(self) -> str:
        return render_footer(self.settings, data_dir=self.data_dir)

    def idle_view(self) -> View:
        if self.settings.is_configured:
            return View(status=render_status("ready when you are"))
        return View(status=render_status(DEMO_STATUS, tone="demo"))

    def roll_topic(self) -> str:
        return random_topic()

    # ── recordings ───────────────────────────────────────────────────────────
    def audio_file(self, draft: StoryDraft | None) -> Path | None:
        """The mp3 on disk for a draft, when it is still there."""
        if draft is None or not draft.audio_path:
            return None
        path = Path(draft.audio_path)
        try:
            if not path.is_file() or path.stat().st_size == 0:
                return None
        except OSError:
            return None
        return path

    def _audio_src(self, draft: StoryDraft | None) -> str | None:
        """A URL the browser can stream, instead of a megabyte of base64."""
        path = self.audio_file(draft)
        return f"{FILE_ROUTE}{quote(str(path), safe='/')}" if path else None

    def audio_sources(self, drafts: list[StoryDraft]) -> dict[str, str]:
        """``{story_id: src}`` for the ledger, skipping anything unrecorded."""
        sources: dict[str, str] = {}
        for draft in drafts:
            src = self._audio_src(draft)
            if src:
                sources[draft.story_id] = src
        return sources

    def _deck(
        self, draft: StoryDraft, *, force: bool = False, autoplay: bool = True
    ) -> tuple[str, str | None]:
        """Render the reader for ``draft``, reusing the saved voice when possible."""
        if not force:
            existing = self._audio_src(draft)
            if existing:
                deck = render_deck(
                    draft,
                    existing,
                    duration_hint=estimate_duration(draft.story),
                    autoplay=autoplay,
                )
                return deck, draft.audio_path

        try:
            path = synthesize(
                draft.story,
                voice_key=draft.voice,
                out_dir=self.audio_dir,
                stem=draft.slug,
                slow=False,
            )
        except SpeechError as error:
            return render_deck_idle(str(error)), None

        draft.audio_path = str(path)
        self.library.save(draft)
        deck = render_deck(
            draft,
            self._audio_src(draft) or "",
            duration_hint=estimate_duration(draft.story),
            autoplay=autoplay,
        )
        return deck, str(path)

    # ── writing ──────────────────────────────────────────────────────────────
    async def ignite(
        self,
        topic: str,
        genre: str,
        mood: str,
        voice: str,
        slow: bool = False,
    ) -> AsyncIterator[View]:
        """Stream a story, then voice it, then file it away.

        The first frame is a loading state, so pressing the button always answers
        immediately — even while the model is still thinking.
        """
        request = StoryRequest(topic=topic, genre=genre, mood=mood, voice=voice, slow=slow)
        prepared = self.service.prepare(request)
        voice_option = resolve_voice(prepared.voice)
        configured = self.settings.is_configured
        opening = OPENING_STATUS if configured else OPENING_DEMO

        draft = StoryDraft(
            topic=prepared.topic,
            target_words=STORY_WORDS,
            genre=get_genre(prepared.genre).label if configured else DEMO_GENRE,
            mood=get_mood(prepared.mood).label if configured else DEMO_MOOD,
            voice=voice_option.key,
            voice_label=voice_option.choice,
            model=self.settings.model_name if configured else DEMO_MODEL,
        )

        yield View(
            stage=render_thinking(prepared.topic, opening),
            deck=render_deck_idle("getting the story ready…"),
            status=render_status(opening, tone="busy"),
            busy=True,
        )

        frames = self.service.stream(prepared) if configured else demo_stream(prepared)
        started = time.perf_counter()

        async for chunk in frames:
            draft.story = chunk.text
            stage = (
                render_sheet(draft, live=not chunk.finished, note=chunk.note)
                if draft.story.strip()
                else render_thinking(prepared.topic, chunk.note)
            )
            yield View(
                stage=stage,
                deck=render_deck_idle(WRITING_DECK),
                status=render_status(chunk.note, tone="busy"),
                busy=True,
            )

        draft.elapsed_ms = int((time.perf_counter() - started) * 1000)
        self.library.save(draft)
        self.store.record(draft)

        yield View(
            stage=render_sheet(draft, note=SAVED_NOTE),
            deck=render_deck_idle(VOICE_WAIT_NOTE, hint=VOICE_WAIT_HINT, patient=True),
            status=render_status(VOICE_WAIT_NOTE, tone="busy"),
            draft=draft,
            busy=True,
        )

        deck, audio = self._deck(draft, force=True)
        note = READY_NOTE if audio else (_deck_message(deck) or "the voice is unavailable")
        yield View(
            stage=render_sheet(draft, note="voiced" if audio else "unvoiced"),
            deck=deck,
            status=render_status(note, tone="idle" if audio else "error"),
            draft=draft,
            audio=audio,
        )

    def _voiced(self, draft: StoryDraft, *, force: bool = False, autoplay: bool = True) -> View:
        """Render the page and reader for a draft, recording it if needed."""
        deck, audio = self._deck(draft, force=force, autoplay=autoplay)
        if audio is None:
            note = _deck_message(deck) or "the voice is unavailable right now"
            return View(
                stage=render_sheet(draft, note="unvoiced"),
                deck=deck,
                status=render_status(note, tone="error"),
                draft=draft,
            )
        return View(
            stage=render_sheet(draft, note="voiced"),
            deck=deck,
            status=render_status(READY_NOTE),
            draft=draft,
            audio=audio,
        )

    def respeak(self, story_id: str | None) -> View:
        """Record a fresh voice for a story that is already on the shelf."""
        draft = self.library.get(story_id)
        if draft is None:
            return View(status=render_status("nothing selected", tone="error"))
        return self._voiced(draft, force=True)

    def open_draft(self, story_id: str | None) -> View:
        """Put an archived story back on the playground page."""
        draft = self.library.get(story_id)
        if draft is None:
            return View(status=render_status("nothing selected", tone="error"))
        deck, audio = self._deck(draft, autoplay=False)
        return View(
            stage=render_sheet(draft, note="from the history"),
            deck=deck,
            status=render_status(f"opened {draft.title}"),
            draft=draft,
            audio=audio,
        )

    # ── history ──────────────────────────────────────────────────────────────
    def drafts(self) -> list[StoryDraft]:
        return self.library.load()

    def history_html(self, drafts: list[StoryDraft] | None = None) -> str:
        """The ledger: every story, with its own recording."""
        entries = self.drafts() if drafts is None else drafts
        return render_history(entries, self.audio_sources(entries))

    def choices(self, drafts: list[StoryDraft] | None = None) -> list[tuple[str, str]]:
        return archive_choices(self.drafts() if drafts is None else drafts)

    def delete(self, story_id: str | None) -> tuple[list[tuple[str, str]], str, str, str]:
        """Drop one story; returns choices, the ledger, the masthead and a note."""
        removed = self.library.delete(story_id)
        drafts = self.drafts()
        note = "story deleted" if removed else "nothing selected"
        return (
            self.choices(drafts),
            self.history_html(drafts),
            self.masthead(),
            render_status(note, tone="idle" if removed else "error"),
        )

    def clear(self) -> tuple[list[tuple[str, str]], str, str, str]:
        """Empty the shelf; returns choices, the ledger, the masthead and a note."""
        count = self.library.clear()
        drafts = self.drafts()
        note = (
            f"cleared {count} stor{'y' if count == 1 else 'ies'}"
            if count
            else "the shelf was empty"
        )
        return self.choices(drafts), self.history_html(drafts), self.masthead(), render_status(note)

    # ── restore ──────────────────────────────────────────────────────────────
    def adopt(self, text: str | None) -> View:
        """Bring a story that arrived through a share link into the studio."""
        story = (text or "").strip()
        if not story:
            return View(status=render_status("nothing to restore", tone="error"))
        topic = story.split(".")[0][:70] or "shared transmission"
        draft = StoryDraft(
            topic=topic,
            story=story,
            genre="Restored",
            mood="Transmitted",
            voice="aurora",
            voice_label=resolve_voice("aurora").choice,
            model="shared link",
        )
        self.library.save(draft)
        self.store.record(draft, source="shared link")
        return View(
            stage=render_sheet(draft, note="restored from a link"),
            deck=render_deck_idle("press play below once this story has a voice"),
            status=render_status("restored · press play to hear it"),
            draft=draft,
        )


def _deck_message(deck: str) -> str:
    """Pull the message back out of an idle player, for the status line."""
    marker = 'class="deck__idle-note">'
    start = deck.find(marker)
    if start < 0:
        return ""
    return deck[start + len(marker) :].split("<", 1)[0].strip()
