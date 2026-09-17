"""Event callbacks for the interface, kept apart from the Gradio layout.

Each callback takes the :class:`~kotori.studio.Studio` first and returns plain
values, so the whole interaction model is unit-testable without a browser or a
server. ``ui.py`` binds them with ``functools.partial``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator

import gradio as gr

from ..core.llm import EngineNotConfiguredError
from ..core.speech import SpeechError
from ..core.story import StoryError
from .markup import (
    render_deck_idle,
    render_room_signal,
    render_sheet,
    render_status,
    render_thinking,
)
from .studio import Studio

#: the page, the reader, the status line, and the composer button's own state
StageOutputs = tuple[str, str, str, object]
#: the hidden picker, the visible picker, the ledger, the masthead, the status
HistoryOutputs = tuple[object, object, str, str, str]
#: the page, the reader, the status line, and which room should be showing
PlayOutputs = tuple[str, str, str, str]

EXPECTED_ERRORS = (StoryError, SpeechError, EngineNotConfiguredError)

WRITE_LABEL = "write the story"
BUSY_LABEL = "writing…"
PLAYGROUND = "playground"


def _composer(busy: bool) -> object:
    """The primary button, labelled and locked while the writer works."""
    return gr.update(value=BUSY_LABEL if busy else WRITE_LABEL, interactive=not busy)


def _picks(choices: list[tuple[str, str]], value: str | None = None) -> tuple[object, object]:
    """Both pickers (the hidden bridge and the visible drawer) in step."""
    if value is None or not any(candidate == value for _label, candidate in choices):
        value = choices[0][1] if choices else None
    update = gr.update(choices=choices, value=value)
    return update, gr.update(choices=choices, value=value)


def _show_playground() -> str:
    """A room signal: the client reads it and flips the page."""
    return render_room_signal(PLAYGROUND)


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
    voice: str,
    slow: bool,
) -> AsyncIterator[StageOutputs]:
    """Stream a story into the playground; failures surface as an error toast."""
    try:
        async for view in studio.ignite(
            topic=topic,
            genre=genre,
            mood=mood,
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


async def demo_story(studio: Studio) -> AsyncIterator[tuple[str, str, str, object, str]]:
    """A demo reel, written into the playground from the home page."""
    topic = studio.roll_topic()
    async for stage, deck, status, composer in stream_story(
        studio, topic, "Fable", "Wondrous", "aurora", False
    ):
        yield stage, deck, status, composer, _show_playground()


def rearm(studio: Studio) -> object:
    """Put the composer button back after a stop."""
    return _composer(False)


def show_playground(studio: Studio) -> str:
    """Send the reader from the home page to the playground."""
    return _show_playground()


def refresh_history(studio: Studio, selected: str | None = None) -> HistoryOutputs:
    """Re-read the ledger, keeping the current selection when it still exists."""
    drafts = studio.drafts()
    choices = studio.choices(drafts)
    bridge, drawer = _picks(choices, selected)
    note = _plural(len(choices), "story", "stories") + " on the shelf"
    return bridge, drawer, studio.history_html(drafts), studio.masthead(), render_status(note)


def open_selected(studio: Studio, story_id: str | None) -> PlayOutputs:
    """Put an archived story back on the playground page and switch to it."""
    view = studio.open_draft(story_id)
    return view.stage, view.deck, view.status, _show_playground()


def record_voice(studio: Studio, story_id: str | None) -> Iterator[tuple[str, str, str]]:
    """Record a fresh voice for one story, showing the work while it happens."""
    draft = studio.library.get(story_id)
    if draft is None:
        yield (
            render_sheet(None),
            render_deck_idle("nothing selected"),
            render_status("nothing selected", tone="error"),
        )
        return

    yield (
        render_sheet(draft, note="recording…"),
        render_deck_idle("recording a fresh voice for this story…"),
        render_status("recording a fresh voice…", tone="busy"),
    )

    view = studio.respeak(story_id)
    yield view.stage, view.deck, view.status


def delete_selected(studio: Studio, story_id: str | None) -> HistoryOutputs:
    choices, ledger, masthead, status = studio.delete(story_id)
    bridge, drawer = _picks(choices)
    return bridge, drawer, ledger, masthead, status


def clear_history(studio: Studio) -> HistoryOutputs:
    choices, ledger, masthead, status = studio.clear()
    bridge, drawer = _picks(choices)
    return bridge, drawer, ledger, masthead, status


def adopt_shared(studio: Studio, text: str | None) -> StageOutputs:
    """Restore a story that arrived through a share link."""
    view = studio.adopt(text)
    return view.stage, view.deck, view.status, _composer(False)


def roll_topic(studio: Studio) -> str:
    return studio.roll_topic()
