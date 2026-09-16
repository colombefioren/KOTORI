"""The studio: one place where writing, voicing and archiving meet.

Callbacks return plain strings (HTML) and dataclasses, so this module stays
free of Gradio and can be driven from a notebook or the CLI just as easily.
"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

from .config import Settings, get_settings
from .library import StoryLibrary
from .markup import (
    archive_choices,
    render_archive_list,
    render_archive_preview,
    render_deck,
    render_deck_idle,
    render_hero,
    render_idle_stage,
    render_stage,
    render_status,
)
from .models import StoryDraft, StoryRequest
from .prompts import get_genre, get_mood, random_topic
from .speech import SpeechError, audio_data_uri, resolve_voice, synthesize
from .story import StoryService
from .timing import estimate_duration

VOICE_WAIT_NOTE = "synthesising the voice…"
SAVED_NOTE = "archived"


@dataclass(slots=True)
class View:
    """The four swappable regions of the stage."""

    stage: str = field(default_factory=render_idle_stage)
    deck: str = field(default_factory=render_deck_idle)
    status: str = field(default_factory=render_status)
    draft: StoryDraft | None = None
    audio: str | None = None

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
        self.settings.ensure_dirs()
        self.library = library or StoryLibrary(self.settings.archive_path)
        self.service = service or StoryService(self.settings)

    # ── chrome ───────────────────────────────────────────────────────────────
    def hero(self) -> str:
        return render_hero(self.settings, self.library.stats())

    def idle_view(self) -> View:
        note = (
            "idle · waiting for a topic"
            if self.settings.is_configured
            else "engine offline · add API_KEY, BASE_URL and MODEL_NAME to .env"
        )
        return View(
            status=render_status(note, tone="idle" if self.settings.is_configured else "error")
        )

    def roll_topic(self) -> str:
        return random_topic()

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
        """Stream a story, then voice it, then archive it."""
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

        draft = StoryDraft(
            topic=prepared.topic,
            genre=get_genre(prepared.genre).label,
            mood=get_mood(prepared.mood).label,
            target_words=prepared.target_words,
            voice=voice_option.key,
            voice_label=voice_option.choice,
            model=self.settings.model_name,
        )

        started = time.perf_counter()
        async for chunk in self.service.stream(prepared):
            draft.story = chunk.text
            yield View(
                stage=render_stage(draft, live=not chunk.finished, note=chunk.note),
                deck=render_deck_idle("listening to the writer…"),
                status=render_status(chunk.note, tone="busy"),
                draft=None,
                audio=None,
            )

        draft.elapsed_ms = int((time.perf_counter() - started) * 1000)
        self.library.save(draft)

        yield View(
            stage=render_stage(draft, note=SAVED_NOTE),
            deck=render_deck_idle(VOICE_WAIT_NOTE),
            status=render_status("synthesising the voice…", tone="busy"),
            draft=draft,
            audio=None,
        )

        yield self._voiced(draft)

    def _voiced(self, draft: StoryDraft, *, failed: str | None = None) -> View:
        """Render the deck for a draft, synthesising speech when possible."""
        if failed is None:
            try:
                path = synthesize(
                    draft.story,
                    voice_key=draft.voice,
                    out_dir=self.settings.audio_dir,
                    stem=draft.slug,
                    slow=False,
                )
                draft.audio_path = str(path)
                uri = audio_data_uri(path)
                self.library.save(draft)
                return View(
                    stage=render_stage(draft, note="voiced"),
                    deck=render_deck(draft, uri, duration_hint=estimate_duration(draft.story)),
                    status=render_status("ready · press play and follow the light", tone="idle"),
                    draft=draft,
                    audio=str(path),
                )
            except SpeechError as error:
                failed = str(error)

        return View(
            stage=render_stage(draft, note="unvoiced"),
            deck=render_deck_idle(failed or "the voice is unavailable right now"),
            status=render_status(failed or "speech failed", tone="error"),
            draft=draft,
            audio=None,
        )

    def respeak(self, story_id: str | None) -> View:
        """Re-render the voice for an archived draft."""
        draft = self.library.get(story_id)
        if draft is None:
            return View(status=render_status("nothing selected", tone="error"))
        return self._voiced(draft)

    # ── archive ──────────────────────────────────────────────────────────────
    def archive_state(self) -> tuple[list[tuple[str, str]], str, str]:
        drafts = self.library.load()
        return (
            archive_choices(drafts),
            render_archive_preview(drafts[0] if drafts else None),
            render_archive_list(drafts),
        )

    def archive_choices_only(self) -> list[tuple[str, str]]:
        return archive_choices(self.library.load())

    def preview(self, story_id: str | None) -> str:
        return render_archive_preview(self.library.get(story_id))

    def open_draft(self, story_id: str | None) -> View:
        """Load an archived story into the stage without paying for speech."""
        draft = self.library.get(story_id)
        if draft is None:
            return View(status=render_status("nothing selected", tone="error"))
        return View(
            stage=render_stage(draft, note="from the archive"),
            deck=render_deck_idle("press “speak it again” to voice this draft"),
            status=render_status(f"opened {draft.title}", tone="idle"),
            draft=draft,
            audio=None,
        )

    def delete(self, story_id: str | None) -> tuple[list[tuple[str, str]], str, str, str]:
        """Drop one draft; returns choices, preview, hero and a status line."""
        removed = self.library.delete(story_id)
        choices, preview, _listing = self.archive_state()
        note = "draft deleted" if removed else "nothing selected"
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
        note = f"burned {count} draft{'s' if count != 1 else ''}" if count else "archive was empty"
        return (choices, preview, self.hero(), render_status(note, tone="idle"))

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
            deck=render_deck_idle("press “speak it again” to voice this draft"),
            status=render_status("restored · press play once voiced", tone="idle"),
            draft=draft,
            audio=None,
        )
