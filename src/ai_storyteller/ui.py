"""Gradio interface assembly and event wiring.

One calm page instead of a dashboard: the composer on the left, the story and
its player on the right, and the shelf of everything kept underneath.
"""

from __future__ import annotations

from functools import partial

import gradio as gr

from . import callbacks
from .config import APP_NAME, Settings, get_settings
from .markup import (
    archive_choices,
    render_deck_idle,
    render_idle_stage,
    render_section,
    render_status,
)
from .speech import voice_choices
from .studio import Studio

DEFAULT_GENRE = "Contemporary"
DEFAULT_MOOD = "Melancholic"
DEFAULT_VOICE = "aurora"

GENRES = [
    "Folk Tale",
    "Science Fiction",
    "Noir",
    "Cosmic Horror",
    "Cyberpunk",
    "Romance",
    "Contemporary",
    "Fable",
    "Historical",
    "Fairy Tale",
]

MOODS = [
    "Melancholic",
    "Eerie",
    "Hopeful",
    "Whimsical",
    "Tense",
    "Tender",
    "Wondrous",
    "Bittersweet",
]


def build_app(studio: Studio | None = None, settings: Settings | None = None) -> gr.Blocks:
    """Construct the Blocks app (no launch, so tests can build it)."""
    settings = settings or get_settings()
    studio = studio or Studio(settings)
    drafts = studio.library.load()
    initial_choices = archive_choices(drafts)
    initial_selection = initial_choices[0][1] if initial_choices else None
    initial_preview = studio.preview(initial_selection)
    initial_shelf_status = (
        render_status(f"{len(initial_choices)} stories on the shelf")
        if initial_choices
        else render_status("the shelf is empty")
    )

    with gr.Blocks(
        title=f"{APP_NAME} · stories that speak",
        fill_width=True,
        delete_cache=(3600, 3600),
    ) as demo:
        with gr.Column(elem_classes=["ast-shell"]):
            header = gr.HTML(studio.hero(), elem_id="ast-header")

            with gr.Row(elem_classes=["ast-grid"]):
                with gr.Column(scale=8, elem_id="ast-composer", elem_classes=["ast-rail"]):
                    gr.HTML(render_section("01", "the composer"))
                    with gr.Group(elem_classes=["ast-card", "ast-stack"]):
                        topic = gr.Textbox(
                            label="what should happen?",
                            placeholder=(
                                "a lighthouse keeper who receives letters from a "
                                "ship that sank in 1912"
                            ),
                            lines=3,
                            max_lines=7,
                            autofocus=True,
                            elem_id="ast-topic",
                        )
                        with gr.Row(elem_classes=["ast-actions"]):
                            ignite = gr.Button(
                                callbacks.WRITE_LABEL, variant="primary", elem_id="ast-ignite"
                            )
                            seed = gr.Button("surprise me", elem_id="ast-seed")
                            stop = gr.Button("stop", elem_id="ast-stop")
                        with gr.Accordion("more settings", open=False):
                            genre = gr.Radio(
                                choices=GENRES,
                                value=DEFAULT_GENRE,
                                label="genre",
                                elem_classes=["ast-chips"],
                            )
                            mood = gr.Dropdown(choices=MOODS, value=DEFAULT_MOOD, label="mood")
                            voice = gr.Dropdown(
                                choices=voice_choices(), value=DEFAULT_VOICE, label="voice"
                            )
                            words = gr.Slider(
                                minimum=120,
                                maximum=500,
                                value=260,
                                step=20,
                                label="how long · words",
                            )
                            slow = gr.Checkbox(value=False, label="read it slowly")
                        status = gr.HTML(studio.idle_view().status, elem_id="ast-status")

                with gr.Column(scale=12):
                    gr.HTML(render_section("02", "the story", "written here, heard here"))
                    stage = gr.HTML(render_idle_stage(), elem_id="ast-stage")
                    deck = gr.HTML(
                        render_deck_idle("press “write the story” and the voice will arrive here"),
                        elem_id="ast-deck",
                    )

            with gr.Column(elem_classes=["ast-shelf-row"]):
                gr.HTML(render_section("03", "your shelf", "everything you kept"))
                with gr.Row(elem_classes=["ast-grid"]):
                    with gr.Column(scale=8, elem_classes=["ast-rail"]):
                        with gr.Group(elem_classes=["ast-card", "ast-stack"]):
                            archive_pick = gr.Radio(
                                choices=initial_choices,
                                value=initial_selection,
                                label="stories",
                                elem_id="ast-archive-pick",
                                elem_classes=["ar-pick"],
                            )
                            archive_delete = gr.Button("delete this story", elem_id="ast-delete")
                            with gr.Accordion("more", open=False):
                                archive_speak = gr.Button(
                                    "record a new voice", elem_id="ast-record"
                                )
                                archive_clear = gr.Button(
                                    "clear the whole shelf",
                                    variant="stop",
                                    elem_id="ast-clear",
                                )
                            archive_status = gr.HTML(
                                initial_shelf_status, elem_id="ast-archive-status"
                            )
                    with gr.Column(scale=12):
                        archive_preview = gr.HTML(initial_preview, elem_id="ast-archive-preview")

            gr.HTML(studio.footer(), elem_id="ast-footer")

        # machinery for "open a shared story": rendered, never seen
        with gr.Column(elem_classes=["ast-shell", "ast-ghost"], elem_id="ast-restore"):
            incoming = gr.Textbox(elem_id="ast-incoming", container=False)
            adopt = gr.Button("adopt", elem_id="ast-adopt")

        composer_inputs = [topic, genre, mood, words, voice, slow]
        stage_targets = [stage, deck, status]
        archive_targets = [archive_pick, archive_preview, header, archive_status]

        def bind(fn):
            return partial(fn, studio)

        ignition = ignite.click(
            fn=bind(callbacks.stream_story),
            inputs=composer_inputs,
            outputs=[*stage_targets, ignite],
            api_name="ignite",
            show_progress="hidden",
        )
        submission = topic.submit(
            fn=bind(callbacks.stream_story),
            inputs=composer_inputs,
            outputs=[*stage_targets, ignite],
            api_name="ignite_from_field",
            show_progress="hidden",
        )
        # stopping cancels the stream *and* hands the button back
        stop.click(
            fn=bind(callbacks.rearm),
            outputs=ignite,
            cancels=[ignition, submission],
            api_name="stop_writing",
            show_progress="hidden",
        )

        for event, name in (
            (ignition, "refresh_after_ignite"),
            (submission, "refresh_after_submit"),
        ):
            event.then(
                fn=bind(callbacks.refresh_archive),
                inputs=archive_pick,
                outputs=archive_targets,
                api_name=name,
                show_progress="hidden",
            )

        seed.click(
            fn=bind(callbacks.roll_topic),
            outputs=topic,
            api_name="surprise_me",
            show_progress="hidden",
        )

        archive_pick.change(
            fn=bind(callbacks.preview_selected),
            inputs=archive_pick,
            outputs=archive_preview,
            api_name="preview_selected",
            show_progress="hidden",
        )
        archive_delete.click(
            fn=bind(callbacks.delete_selected),
            inputs=archive_pick,
            outputs=archive_targets,
            api_name="delete_selected",
            show_progress="hidden",
        )
        archive_clear.click(
            fn=bind(callbacks.clear_archive),
            outputs=archive_targets,
            api_name="clear_archive",
            show_progress="hidden",
        )
        recording = archive_speak.click(
            fn=bind(callbacks.record_voice),
            inputs=archive_pick,
            outputs=stage_targets,
            api_name="record_voice",
            show_progress="hidden",
        )
        recording.then(
            fn=bind(callbacks.refresh_archive),
            inputs=archive_pick,
            outputs=archive_targets,
            api_name="refresh_after_record",
            show_progress="hidden",
        )
        adopt.click(
            fn=bind(callbacks.adopt_shared),
            inputs=incoming,
            outputs=[stage, deck, status, archive_pick, archive_preview, header],
            api_name="adopt_shared",
            show_progress="hidden",
        )

    return demo


def configure_queue(demo: gr.Blocks) -> gr.Blocks:
    """Streaming needs the queue; keep a small concurrency window."""
    demo.queue(default_concurrency_limit=4)
    return demo
