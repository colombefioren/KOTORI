"""Gradio interface assembly and event wiring.

Three index tabs across the top: **home** (what KOTORI is, and how to use it),
**playground** (the brief and the reader side by side, with the written story
full width underneath) and **history** (every story ever kept, each one with its
own player).

The tabs are drawn by :mod:`kotori.markup` rather than by Gradio, so they can
look like paper. All three rooms stay in the DOM at once — the browser never
re-mounts a player — and flipping between them is instant, client side. When the
server needs to move the reader (a demo reel, opening a story from the history)
it renders a hidden room signal, which the client watches.
"""

from __future__ import annotations

from functools import partial

import gradio as gr

from ..config import APP_NAME, Settings, get_settings
from ..core.prompts import GENRE_LABELS, MOOD_LABELS
from ..core.speech import voice_choices
from . import callbacks
from .markup import (
    render_deck_idle,
    render_home_intro,
    render_home_notes,
    render_home_steps,
    render_idle_sheet,
    render_label,
    render_room_signal,
    render_status,
    render_sticky,
    render_tabs,
)
from .studio import Studio

DEFAULT_GENRE = "Contemporary"
DEFAULT_MOOD = "Melancholic"
DEFAULT_VOICE = "aurora"

HOME = "home"
PLAYGROUND = "playground"


def build_app(studio: Studio | None = None, settings: Settings | None = None) -> gr.Blocks:
    """Construct the Blocks app (no launch, so tests can build it)."""
    settings = settings or get_settings()
    studio = studio or Studio(settings)
    drafts = studio.drafts()
    choices = studio.choices(drafts)
    selection = choices[0][1] if choices else None
    initial_ledger = studio.history_html(drafts)
    initial_shelf = (
        render_status(f"{len(choices)} stories on the shelf")
        if choices
        else render_status("the shelf is empty")
    )

    with gr.Blocks(
        title=f"{APP_NAME} · stories that speak",
        fill_width=True,
        delete_cache=(3600, 3600),
    ) as demo:
        with gr.Column(elem_classes=["ast-shell"]):
            masthead = gr.HTML(studio.masthead(), elem_id="ast-masthead")
            gr.HTML(render_tabs(HOME, len(choices)), elem_id="ast-tabs")
            room_signal = gr.HTML(render_room_signal(HOME), elem_id="ast-room")

            with gr.Column(elem_id="room-home", elem_classes=["room", "home"]):
                gr.HTML(render_home_intro(settings), elem_id="ast-home-intro")
                with gr.Row(elem_classes=["home__cta"]):
                    start = gr.Button("start writing", variant="primary", elem_id="ast-start")
                    hear_demo = gr.Button("hear a demo reel", elem_id="ast-demo")
                gr.HTML(render_home_steps(), elem_id="ast-home-steps")
                gr.HTML(render_home_notes(settings), elem_id="ast-home-notes")

            with gr.Column(elem_id="room-playground", elem_classes=["room"]):
                with gr.Row(elem_classes=["ast-grid"]):
                    with gr.Column(scale=5, elem_id="ast-composer"):
                        gr.HTML(render_label("the brief", "one line is enough", doodle="arrow"))
                        with gr.Group(elem_classes=["card", "ast-stack"]):
                            topic = gr.Textbox(
                                label="what should happen?",
                                placeholder=(
                                    "a lighthouse keeper who receives letters from a "
                                    "ship that sank in 1912"
                                ),
                                lines=3,
                                max_lines=6,
                                autofocus=True,
                                elem_id="ast-topic",
                            )
                            genre = gr.Dropdown(
                                choices=GENRE_LABELS,
                                value=DEFAULT_GENRE,
                                label="genre — pick one, or paste your own",
                                allow_custom_value=True,
                            )
                            with gr.Row():
                                mood = gr.Dropdown(
                                    choices=MOOD_LABELS,
                                    value=DEFAULT_MOOD,
                                    label="mood",
                                    allow_custom_value=True,
                                )
                                voice = gr.Dropdown(
                                    choices=voice_choices(),
                                    value=DEFAULT_VOICE,
                                    label="voice",
                                )
                            with gr.Accordion("more settings", open=False):
                                slow = gr.Checkbox(value=False, label="read it slowly")
                            with gr.Row(elem_classes=["ast-actions"]):
                                ignite = gr.Button(
                                    callbacks.WRITE_LABEL,
                                    variant="primary",
                                    elem_id="ast-ignite",
                                )
                                seed = gr.Button("surprise me", elem_id="ast-seed")
                                stop = gr.Button("stop", elem_id="ast-stop")
                            status = gr.HTML(studio.idle_view().status, elem_id="ast-status")
                        gr.HTML(
                            render_sticky(
                                "stuck? press surprise me and the bird picks a line for you"
                            )
                        )

                    with gr.Column(scale=6):
                        gr.HTML(render_label("the reader", "press play and read along"))
                        deck = gr.HTML(
                            render_deck_idle(
                                "press “write the story” and the voice will land here"
                            ),
                            elem_id="ast-deck",
                        )
                        gr.HTML(
                            '<p class="handnote">every story is four hundred words — '
                            "long enough to have weather, short enough for a coffee.</p>"
                        )

                with gr.Column(elem_classes=["ast-full"]):
                    gr.HTML(render_label("the page", "written here, heard here", doodle="hearts"))
                    stage = gr.HTML(render_idle_sheet(), elem_id="ast-stage")

            with gr.Column(elem_id="room-history", elem_classes=["room", "ledger"]):
                with gr.Row(elem_classes=["ledger__bar"]):
                    gr.HTML(render_label("the ledger", "every story you kept", doodle="star"))
                    refresh = gr.Button("refresh", elem_id="ast-refresh")
                history = gr.HTML(initial_ledger, elem_id="ast-history")
                with gr.Accordion("manage the shelf", open=False):
                    gr.HTML(
                        '<p class="handnote">if a card’s own buttons ever fail, '
                        "pick a story here and use these.</p>"
                    )
                    drawer_pick = gr.Radio(
                        choices=choices,
                        value=selection,
                        label="stories",
                        elem_id="ast-history-pick",
                        elem_classes=["ar-pick"],
                    )
                    with gr.Row(elem_classes=["ast-actions"]):
                        drawer_open = gr.Button("open in the playground")
                        record = gr.Button("record a new voice")
                        drawer_delete = gr.Button("delete this story")
                        clear = gr.Button("clear the whole shelf", variant="stop")
                    history_status = gr.HTML(initial_shelf, elem_id="ast-history-status")

            gr.HTML(studio.footer(), elem_id="ast-footer")

        # machinery the index cards click into, plus "open a shared story":
        # rendered, never seen: the cards set the hidden picker and press a button
        with gr.Column(elem_classes=["ast-ghost"], elem_id="ast-bridge"):
            bridge_pick = gr.Radio(choices=choices, value=selection, elem_id="ast-pick")
            bridge_open = gr.Button("open", elem_id="ast-open")
            bridge_delete = gr.Button("delete", elem_id="ast-delete")
            incoming = gr.Textbox(elem_id="ast-incoming", container=False)
            adopt = gr.Button("adopt", elem_id="ast-adopt")

        composer_inputs = [topic, genre, mood, voice, slow]
        stage_targets = [stage, deck, status]
        play_targets = [stage, deck, status, room_signal]
        history_targets = [bridge_pick, drawer_pick, history, masthead, history_status]

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
                fn=bind(callbacks.refresh_history),
                inputs=bridge_pick,
                outputs=history_targets,
                api_name=name,
                show_progress="hidden",
            )

        seed.click(
            fn=bind(callbacks.roll_topic),
            outputs=topic,
            api_name="surprise_me",
            show_progress="hidden",
        )

        # the home page sends you into the playground, with or without a demo
        start.click(
            fn=bind(callbacks.show_playground),
            outputs=room_signal,
            api_name="start_writing",
            show_progress="hidden",
        )
        hear_demo.click(
            fn=bind(callbacks.demo_story),
            outputs=[*stage_targets, ignite, room_signal],
            api_name="hear_demo",
            show_progress="hidden",
        )

        # one callback, two ways in: the index cards (hidden picker) and the drawer
        for picker, button, name in (
            (bridge_pick, bridge_open, "open_selected"),
            (drawer_pick, drawer_open, "open_from_drawer"),
        ):
            button.click(
                fn=bind(callbacks.open_selected),
                inputs=picker,
                outputs=play_targets,
                api_name=name,
                show_progress="hidden",
            )
        for picker, button, name in (
            (bridge_pick, bridge_delete, "delete_selected"),
            (drawer_pick, drawer_delete, "delete_from_drawer"),
        ):
            button.click(
                fn=bind(callbacks.delete_selected),
                inputs=picker,
                outputs=history_targets,
                api_name=name,
                show_progress="hidden",
            )

        recording = record.click(
            fn=bind(callbacks.record_voice),
            inputs=drawer_pick,
            outputs=stage_targets,
            api_name="record_voice",
            show_progress="hidden",
        )
        recording.then(
            fn=bind(callbacks.refresh_history),
            inputs=drawer_pick,
            outputs=history_targets,
            api_name="refresh_after_record",
            show_progress="hidden",
        )
        clear.click(
            fn=bind(callbacks.clear_history),
            outputs=history_targets,
            api_name="clear_history",
            show_progress="hidden",
        )
        refresh.click(
            fn=bind(callbacks.refresh_history),
            inputs=drawer_pick,
            outputs=history_targets,
            api_name="refresh_history",
            show_progress="hidden",
        )

        adopting = adopt.click(
            fn=bind(callbacks.adopt_shared),
            inputs=incoming,
            outputs=[*stage_targets, ignite],
            api_name="adopt_shared",
            show_progress="hidden",
        )
        adopting.then(
            fn=bind(callbacks.refresh_history),
            inputs=bridge_pick,
            outputs=history_targets,
            api_name="refresh_after_adopt",
            show_progress="hidden",
        )

    return demo


def configure_queue(demo: gr.Blocks) -> gr.Blocks:
    """Streaming needs the queue; keep a small concurrency window."""
    demo.queue(default_concurrency_limit=4)
    return demo
