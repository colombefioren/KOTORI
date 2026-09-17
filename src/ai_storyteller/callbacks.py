"""Event callbacks for the interface, kept apart from the Gradio layout.

Each callback takes the :class:`~ai_storyteller.studio.Studio` first and returns
plain values, so the whole interaction model is unit-testable without a browser
or a server. ``ui.py`` binds them with ``functools.partial``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator

import gradio as gr

from .llm import EngineNotConfiguredError
from .markup import render_deck_idle, render_stage, render_status, render_thinking
from .speech import SpeechError
from .story import StoryError
from .studio import Studio

#: stage, deck, status, and the composer button's own state
StageOutputs = tuple[str, str, str, object]
ArchiveOutputs = tuple[object, str, str, str]

EXPECTED_ERRORS = (StoryError, SpeechError, EngineNotConfiguredError)

WRITE_LABEL = "write the story"
BUSY_LABEL = "writing…"


def _radio_update(choices: list[tuple[str, str]], value: str | None = None) -> object:
    if value is None:
        value = choices[0][1] if choices else None
    return gr.update(choices=choices, value=value)


def _composer(busy: bool) -> object:
    """The primary button, labelled and locked while the writer works."""
    return gr.update(value=BUSY_LABEL if busy else WRITE_LABEL, interactive=not busy)


def _plural(count: int, singular: str, plural: str | None = None) -> str:
    """``1 story`` / ``3 stories`` without an awkward ``storys``."""
    if count == 1:
        return f"1 {singular}"
    return f"{count} {plural or singular + 's'}"


async def stream_story(
    studio: Studio,
    topic: str,
    genre: str,
    mood: str,
    words: float,
    voice: str,
    slow: bool,
) -> AsyncIterator[StageOutputs]:
    """Stream a story into the page; failures surface as a Gradio error toast."""
    try:
        async for view in studio.ignite(
            topic=topic,
            genre=genre,
            mood=mood,
            target_words=int(words or 260),
            voice=voice,
            slow=bool(slow),
        ):
            yield view.stage, view.deck, view.status, _composer(view.busy)
    except EXPECTED_ERRORS as error:
        # hand the studio back to the writer before the toast appears
        yield (
            render_thinking(topic, "the writer stopped early"),
            render_deck_idle(str(error)),
            render_status(str(error), tone="error"),
            _composer(False),
        )
        raise gr.Error(str(error)) from error


def rearm(studio: Studio) -> object:
    """Put the composer button back after a stop."""
    return _composer(False)


def refresh_archive(studio: Studio, selected: str | None = None) -> ArchiveOutputs:
    """Re-read the shelf, keeping the current selection when it still exists."""
    choices, preview, _listing = studio.archive_state(selected)
    value = selected if any(value == selected for _label, value in choices) else None
    note = _plural(len(choices), "story", "stories") + " on the shelf"
    return _radio_update(choices, value), preview, studio.hero(), render_status(note)


def preview_selected(studio: Studio, story_id: str | None) -> str:
    """The reading pane for the story picked on the shelf."""
    return studio.preview(story_id)


def record_voice(studio: Studio, story_id: str | None) -> Iterator[tuple[str, str, str]]:
    """Re-record a story's voice, showing the work while it happens."""
    draft = studio.library.get(story_id)
    if draft is None:
        yield (
            render_stage(None),
            render_deck_idle("nothing selected"),
            render_status("nothing selected", tone="error"),
        )
        return

    yield (
        render_stage(draft, note="recording…"),
        render_deck_idle("recording a fresh voice for this story…"),
        render_status("recording a fresh voice…", tone="busy"),
    )

    view = studio.respeak(story_id)
    yield view.stage, view.deck, view.status


def delete_selected(studio: Studio, story_id: str | None) -> ArchiveOutputs:
    choices, preview, hero, status = studio.delete(story_id)
    return _radio_update(choices), preview, hero, status


def clear_archive(studio: Studio) -> ArchiveOutputs:
    choices, preview, hero, status = studio.clear()
    return gr.update(choices=choices, value=None), preview, hero, status


def adopt_shared(studio: Studio, text: str | None) -> tuple[str, str, str, object, str, str]:
    """Restore a story that arrived through a share link."""
    view = studio.adopt(text)
    choices, preview, _listing = studio.archive_state()
    return (
        view.stage,
        view.deck,
        view.status,
        _radio_update(choices),
        preview,
        studio.hero(),
    )


def roll_topic(studio: Studio) -> str:
    return studio.roll_topic()
