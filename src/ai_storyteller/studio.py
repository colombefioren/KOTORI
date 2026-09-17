"""The studio: one place where writing, voicing and archiving meet.

Callbacks return plain strings (HTML) and dataclasses, so this module stays
free of Gradio and can be driven from a notebook or the CLI just as easily.
"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from pathlib import Path

from .config import Settings, ensure_writable_dir, get_settings
from .demo import DEMO_GENRE, DEMO_MODEL, DEMO_MOOD, demo_stream
from .library import StoryLibrary
from .markup import (
    STAGE_PAPER,
    archive_choices,
    render_archive_list,
    render_archive_preview,
    render_deck,
    render_deck_idle,
    render_footer,
    render_hero,
    render_idle_stage,
    render_stage,
    render_status,
    render_thinking,
)
from .models import StoryDraft, StoryRequest
from .prompts import get_genre, get_mood, random_topic
from .speech import SpeechError, audio_data_uri, resolve_voice, synthesize
from .story import StoryService
from .timing import estimate_duration

OPENING_STATUS = "warming up the pen…"
OPENING_DEMO = "warming up the pen… (demo reel)"
WRITING_DECK = "the voice arrives as soon as the story is finished…"
VOICE_WAIT_NOTE = "synthesising the voice…"
READY_NOTE = "ready · press play and follow the light"
SAVED_NOTE = "archived"
DEMO_STATUS = "demo mode · add credentials for your own stories"


@dataclass(slots=True)
class View:
    """The swappable regions of the page."""

    stage: str = field(default_factory=render_idle_stage)
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
    ) -> None:
        self.settings = settings or get_settings()
        self.data_dir = ensure_writable_dir(self.settings.data_dir)
        self.audio_dir = self.data_dir / "audio"
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        self.library = library or StoryLibrary(self.data_dir / "library.jsonl")
        self.service = service or StoryService(self.settings)

    # ── chrome ───────────────────────────────────────────────────────────────
    def hero(self) -> str:
        return render_hero(self.settings, self.library.stats())

    def footer(self) -> str:
        return render_footer(self.settings, data_dir=self.data_dir)

    def idle_view(self) -> View:
        if self.settings.is_configured:
            return View(status=render_status("ready when you are"))
        return View(status=render_status(DEMO_STATUS, tone="demo"))

    def roll_topic(self) -> str:
        return random_topic()

    # ── speech ───────────────────────────────────────────────────────────────
    def _audio_uri(self, draft: StoryDraft | None) -> str | None:
        """Inline the saved mp3 for a draft, when it is still on disk."""
        if draft is None or not draft.audio_path:
            return None
        path = Path(draft.audio_path)
        try:
            if not path.is_file() or path.stat().st_size == 0:
                return None
            return audio_data_uri(path)
        except OSError:
            return None

    def _deck(
        self,
        draft: StoryDraft,
        *,
        force: bool = False,
        paper_id: str = STAGE_PAPER,
        autoplay: bool = True,
    ) -> tuple[str, str | None]:
        """Render the player for ``draft``, reusing the saved voice when possible."""
        if not force:
            uri = self._audio_uri(draft)
            if uri:
                deck = render_deck(
                    draft,
                    uri,
                    duration_hint=estimate_duration(draft.story),
                    paper_id=paper_id,
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
            audio_data_uri(path),
            duration_hint=estimate_duration(draft.story),
            paper_id=paper_id,
            autoplay=autoplay,
        )
        return deck, str(path)

    # ── writing ──────────────────────────────────────────────────────────────
    async def ignite(
        self,
        topic: str,
        genre: str,
        mood: str,
        target_words: int,
        voice: str,
        slow: bool,
    ) -> AsyncIterator[View]:
        """Stream a story, then voice it, then archive it.

        The first frame is a loading state, so pressing the button always
        answers immediately — even while the model is still thinking.
        """
        request = StoryRequest(
            topic=topic,
            genre=genre,
            mood=mood,
            target_words=int(target_words or 260),
            voice=voice,
            slow=bool(slow),
        )
        prepared = self.service.prepare(request)
        voice_option = resolve_voice(prepared.voice)
        configured = self.settings.is_configured
        opening = OPENING_STATUS if configured else OPENING_DEMO

        draft = StoryDraft(
            topic=prepared.topic,
            genre=get_genre(prepared.genre).label if configured else DEMO_GENRE,
            mood=get_mood(prepared.mood).label if configured else DEMO_MOOD,
            target_words=prepared.target_words,
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
                render_stage(draft, live=not chunk.finished, note=chunk.note)
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

        yield View(
            stage=render_stage(draft, note=SAVED_NOTE),
            deck=render_deck_idle(VOICE_WAIT_NOTE),
            status=render_status(VOICE_WAIT_NOTE, tone="busy"),
            draft=draft,
            busy=True,
        )

        deck, audio = self._deck(draft, force=True)
        note = (
            READY_NOTE if audio else (_deck_message(deck) or "the voice is unavailable right now")
        )
        yield View(
            stage=render_stage(draft, note="voiced" if audio else "unvoiced"),
            deck=deck,
            status=render_status(note, tone="idle" if audio else "error"),
            draft=draft,
            audio=audio,
        )

    def _voiced(self, draft: StoryDraft, *, force: bool = False, autoplay: bool = True) -> View:
        """Render the stage and player for a draft, voicing it if needed."""
        deck, audio = self._deck(draft, force=force, autoplay=autoplay)
        if audio is None:
            failed = _deck_message(deck) or "the voice is unavailable right now"
            return View(
                stage=render_stage(draft, note="unvoiced"),
                deck=deck,
                status=render_status(failed, tone="error"),
                draft=draft,
            )
        return View(
            stage=render_stage(draft, note="voiced"),
            deck=deck,
            status=render_status(READY_NOTE),
            draft=draft,
            audio=audio,
        )

    def respeak(self, story_id: str | None) -> View:
        """Record a fresh voice for an archived draft."""
        draft = self.library.get(story_id)
        if draft is None:
            return View(status=render_status("nothing selected", tone="error"))
        return self._voiced(draft, force=True)

    # ── archive ──────────────────────────────────────────────────────────────
    def archive_state(self, selected: str | None = None) -> tuple[list[tuple[str, str]], str, str]:
        """Choices, the reading pane for ``selected``, and the listing."""
        drafts = self.library.load()
        chosen = self._pick(drafts, selected)
        return (
            archive_choices(drafts),
            self.preview(chosen.story_id if chosen else None),
            render_archive_list(drafts),
        )

    def preview(self, story_id: str | None) -> str:
        """The shelf reading pane, complete with that story's own player."""
        draft = self.library.get(story_id)
        if draft is None:
            return render_archive_preview(None)
        return render_archive_preview(
            draft,
            audio_uri=self._audio_uri(draft),
            duration_hint=estimate_duration(draft.story),
        )

    def open_draft(self, story_id: str | None) -> View:
        """Put an archived story back on the writing stage."""
        draft = self.library.get(story_id)
        if draft is None:
            return View(status=render_status("nothing selected", tone="error"))
        deck, audio = self._deck(draft, autoplay=False)
        return View(
            stage=render_stage(draft, note="from the archive"),
            deck=deck,
            status=render_status(f"opened {draft.title}"),
            draft=draft,
            audio=audio,
        )

    def delete(self, story_id: str | None) -> tuple[list[tuple[str, str]], str, str, str]:
        """Drop one draft; returns choices, preview, hero and a status line."""
        removed = self.library.delete(story_id)
        choices, preview, _listing = self.archive_state()
        note = "story deleted" if removed else "nothing selected"
        return (
            choices,
            preview,
            self.hero(),
            render_status(note, tone="idle" if removed else "error"),
        )

    def clear(self) -> tuple[list[tuple[str, str]], str, str, str]:
        """Burn the archive; returns choices, preview, hero and a status line."""
        count = self.library.clear()
        choices, preview, _listing = self.archive_state()
        note = (
            f"cleared {count} stor{'y' if count == 1 else 'ies'}"
            if count
            else "the shelf was empty"
        )
        return (choices, preview, self.hero(), render_status(note))

    # ── restore ──────────────────────────────────────────────────────────────
    def adopt(self, text: str | None) -> View:
        """Bring a shared story back into the studio."""
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
        return View(
            stage=render_stage(draft, note="restored from a link"),
            deck=render_deck_idle("press play below once this story has a voice"),
            status=render_status("restored · press play to hear it"),
            draft=draft,
        )

    # ── helpers ──────────────────────────────────────────────────────────────
    @staticmethod
    def _pick(drafts: list[StoryDraft], selected: str | None) -> StoryDraft | None:
        """Keep the selection when it still exists, else fall back to the newest."""
        if selected:
            for draft in drafts:
                if draft.story_id == selected:
                    return draft
        return drafts[0] if drafts else None


def _deck_message(deck: str) -> str:
    """Pull the message back out of an idle player, for the status line."""
    start = deck.find('class="deck__idle-note">')
    if start < 0:
        return ""
    body = deck[start + len('class="deck__idle-note">') :]
    return body.split("<", 1)[0].strip()
