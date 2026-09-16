"""Event callbacks for the interface, kept apart from the Gradio layout.

Each callback takes the :class:`~ai_storyteller.studio.Studio` first and returns
plain values, so the whole interaction model is unit-testable without a browser
or a server. ``ui.py`` binds them with ``functools.partial``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import gradio as gr

from .llm import EngineNotConfiguredError
from .markup import render_status
from .speech import SpeechError
from .story import StoryError
from .studio import Studio

StageOutputs = tuple[str, str, str]
ArchiveOutputs = tuple[object, str, str, str]

EXPECTED_ERRORS = (StoryError, SpeechError, EngineNotConfiguredError)


def _radio_update(choices: list[tuple[str, str]]) -> object:
    return gr.update(choices=choices, value=choices[0][1] if choices else None)


def _plural(count: int, noun: str) -> str:
    return f"{count} {noun}" + ("" if count == 1 else "s")


async def stream_story(
    studio: Studio,
    topic: str,
    genre: str,
    mood: str,
    words: float,
    voice: str,
    slow: bool,
) -> AsyncIterator[StageOutputs]:
    """Stream a story into the stage; failures surface as a Gradio error toast."""
    try:
        async for view in studio.ignite(
            topic=topic,
            genre=genre,
            mood=mood,
            target_words=int(words or 260),
            voice=voice,
            slow=bool(slow),
        ):
            yield view.stage, view.deck, view.status
    except EXPECTED_ERRORS as error:
        raise gr.Error(str(error)) from error


def refresh_archive(studio: Studio) -> ArchiveOutputs:
    """Re-read the shelf and refresh the hero stats."""
    choices, preview, _listing = studio.archive_state()
    note = _plural(len(choices), "draft") + " on the shelf"
    return _radio_update(choices), preview, studio.hero(), render_status(note)


def preview_selected(studio: Studio, story_id: str | None) -> str:
    return studio.preview(story_id)


def open_selected(studio: Studio, story_id: str | None) -> StageOutputs:
    view = studio.open_draft(story_id)
    return view.stage, view.deck, view.status


def speak_selected(studio: Studio, story_id: str | None) -> StageOutputs:
    view = studio.respeak(story_id)
    return view.stage, view.deck, view.status


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
