"""Gradio interface assembly and event wiring.

The layout is three regions: a fixed editorial header, a composer rail, and a
stage that streams prose word by word and then plays it back in karaoke.
"""

from __future__ import annotations

from functools import partial

import gradio as gr

from . import callbacks
from .config import APP_NAME, Settings, get_settings
from .markup import (
    archive_choices,
    render_archive_preview,
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


def build_app(studio: Studio | None = None, settings: Settings | None = None) -> gr.Blocks:
    """Construct the Blocks app (no launch, so tests can build it)."""
    settings = settings or get_settings()
    studio = studio or Studio(settings)
    drafts = studio.library.load()
    initial_choices = archive_choices(drafts)
    initial_preview = render_archive_preview(drafts[0] if drafts else None)

    with gr.Blocks(
        title=f"{APP_NAME} · stories that speak",
        fill_width=True,
        delete_cache=(3600, 3600),
    ) as demo:
        header = gr.HTML(studio.hero(), elem_id="ast-header")

        with gr.Column(elem_classes=["ast-shell"]):
            with gr.Tabs(elem_id="ast-tabs"):
                with gr.Tab("write", id="write"):
                    with gr.Row(elem_classes=["ast-grid"]):
                        with gr.Column(scale=8, elem_id="ast-composer", elem_classes=["ast-rail"]):
                            gr.HTML(render_section("01", "composer", "one seed is enough"))
                            with gr.Group(elem_classes=["ast-panel", "ast-stack"]):
                                topic = gr.Textbox(
                                    label="the seed",
                                    placeholder=(
                                        "a lighthouse keeper who receives letters "
                                        "from a ship that sank in 1912"
                                    ),
                                    lines=3,
                                    max_lines=6,
                                    autofocus=True,
                                    submit_btn="ignite",
                                    elem_id="ast-topic",
                                )
                                with gr.Row(elem_classes=["ast-actions"]):
                                    ignite = gr.Button(
                                        "ignite story", variant="primary", elem_id="ast-ignite"
                                    )
                                    seed = gr.Button("surprise me", elem_id="ast-seed")
                                    stop = gr.Button("stop", variant="stop", elem_id="ast-stop")
                                genre = gr.Radio(
                                    choices=[
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
                                    ],
                                    value=DEFAULT_GENRE,
                                    label="genre",
                                    elem_classes=["ast-chips"],
                                )
                                with gr.Row():
                                    mood = gr.Dropdown(
                                        choices=[
                                            "Melancholic",
                                            "Eerie",
                                            "Hopeful",
                                            "Whimsical",
                                            "Tense",
                                            "Tender",
                                            "Wondrous",
                                            "Bittersweet",
                                        ],
                                        value=DEFAULT_MOOD,
                                        label="mood",
                                    )
                                    voice = gr.Dropdown(
                                        choices=voice_choices(),
                                        value=DEFAULT_VOICE,
                                        label="voice",
                                    )
                                words = gr.Slider(
                                    minimum=120,
                                    maximum=500,
                                    value=260,
                                    step=20,
                                    label="length · words",
                                )
                                slow = gr.Checkbox(value=False, label="speak slowly")
                                status = gr.HTML(studio.idle_view().status, elem_id="ast-status")

                        with gr.Column(scale=12):
                            gr.HTML(render_section("02", "stage", "streamed, then spoken"))
                            stage = gr.HTML(render_idle_stage(), elem_id="ast-stage")
                            deck = gr.HTML(render_deck_idle(), elem_id="ast-deck")

                with gr.Tab("archive", id="archive"):
                    with gr.Row(elem_classes=["ast-grid"]):
                        with gr.Column(scale=8, elem_classes=["ast-rail"]):
                            gr.HTML(render_section("03", "shelf", "everything you kept"))
                            with gr.Group(elem_classes=["ast-panel", "ast-stack"]):
                                archive_pick = gr.Radio(
                                    choices=initial_choices,
                                    value=initial_choices[0][1] if initial_choices else None,
                                    label="drafts",
                                    elem_id="ast-archive-pick",
                                    elem_classes=["ar-pick"],
                                )
                                with gr.Row(elem_classes=["ast-actions"]):
                                    archive_open = gr.Button("open in stage")
                                    archive_speak = gr.Button("speak it again", variant="primary")
                                    archive_refresh = gr.Button("refresh")
                                with gr.Row(elem_classes=["ast-actions"]):
                                    archive_delete = gr.Button("delete draft")
                                    archive_clear = gr.Button("burn the archive", variant="stop")
                                archive_status = gr.HTML(
                                    render_status("archive ready"), elem_id="ast-archive-status"
                                )
                        with gr.Column(scale=12):
                            gr.HTML(render_section("04", "reading", "the selected draft"))
                            archive_preview = gr.HTML(
                                initial_preview, elem_id="ast-archive-preview"
                            )

            gr.HTML(render_section("·", "restore", "share links land here"))

        # machinery for "open a shared story": rendered, never seen
        with gr.Column(elem_classes=["ast-shell", "ast-ghost"], elem_id="ast-restore"):
            incoming = gr.Textbox(elem_id="ast-incoming", container=False)
            adopt = gr.Button("adopt", elem_id="ast-adopt")

        gr.HTML(studio.footer(), elem_id="ast-footer")

        composer_inputs = [topic, genre, mood, words, voice, slow]
        stage_targets = [stage, deck, status]
        archive_targets = [archive_pick, archive_preview, header, archive_status]

        # callbacks live in callbacks.py so they can be tested without a server
        def bind(fn):
            return partial(fn, studio)

        ignition = ignite.click(
            fn=bind(callbacks.stream_story),
            inputs=composer_inputs,
            outputs=stage_targets,
            api_name="ignite",
            show_progress="hidden",
        )
        submission = topic.submit(
            fn=bind(callbacks.stream_story),
            inputs=composer_inputs,
            outputs=stage_targets,
            api_name="ignite_from_field",
            show_progress="hidden",
        )
        stop.click(fn=None, cancels=[ignition, submission])

        for event, name in (
            (ignition, "refresh_after_ignite"),
            (submission, "refresh_after_submit"),
        ):
            event.then(
                fn=bind(callbacks.refresh_archive),
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
        archive_open.click(
            fn=bind(callbacks.open_selected),
            inputs=archive_pick,
            outputs=stage_targets,
            api_name="open_selected",
            show_progress="hidden",
        )
        archive_speak.click(
            fn=bind(callbacks.speak_selected),
            inputs=archive_pick,
            outputs=stage_targets,
            api_name="speak_selected",
            show_progress="hidden",
        )
        archive_refresh.click(
            fn=bind(callbacks.refresh_archive),
            outputs=archive_targets,
            api_name="refresh_archive",
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
