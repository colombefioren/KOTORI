"""A Gradio theme that mirrors the CSS design tokens.

KOTORI is a scrapbook, so the theme is paper: pink and blue washi pastels, ink
outlines, nothing that glows. Both the light and the dark slots are filled in —
the switch in the masthead flips `data-theme` *and* Gradio's own `dark` class,
so the two systems never disagree.
"""

from __future__ import annotations

import gradio as gr

LIGHT: dict[str, str] = {
    "desk": "#f2e8ee",
    "paper": "#fffdfa",
    "paper_2": "#fdf7f8",
    "paper_3": "#f7eef2",
    "cream": "#fdf9f0",
    "line": "#e8dbe2",
    "line_2": "#cdbac5",
    "ink": "#443b48",
    "ink_2": "#6f6573",
    "ink_3": "#9d94a2",
    "pink_100": "#fdeef4",
    "pink_200": "#f9d5e4",
    "pink_300": "#f2b3cd",
    "pink_400": "#e288ae",
    "pink_500": "#bd5f8b",
    "blue_100": "#edf3fd",
    "blue_200": "#d8e7fa",
    "blue_300": "#b3d0f2",
    "blue_400": "#82aae0",
    "blue_500": "#5b83b6",
}

DARK: dict[str, str] = {
    "desk": "#191725",
    "paper": "#262233",
    "paper_2": "#221f2e",
    "paper_3": "#2d2839",
    "cream": "#2a2636",
    "line": "#3a3449",
    "line_2": "#514863",
    "ink": "#f4eff8",
    "ink_2": "#c6bdd2",
    "ink_3": "#8f87a3",
    "pink_200": "#3a2a3c",
    "pink_300": "#8d5c74",
    "pink_400": "#e79cbe",
    "pink_500": "#f4b6d2",
    "blue_200": "#2a3550",
    "blue_300": "#5d7dae",
    "blue_400": "#9dc0ee",
    "blue_500": "#c0d6f7",
}

DISPLAY_FONT = "Fraunces"
SERIF_FONT = "EB Garamond"
SANS_FONT = "Karla"
HAND_FONT = "Kalam"
MONO_FONT = "Special Elite"


class Washi(gr.themes.Base):
    """Paper, washi tape, typewriter labels, ink outlines."""

    def __init__(self) -> None:
        super().__init__(
            primary_hue="pink",
            secondary_hue="blue",
            neutral_hue="slate",
            radius_size=gr.themes.sizes.radius_sm,
            text_size=gr.themes.sizes.text_md,
            spacing_size=gr.themes.sizes.spacing_md,
            font=(gr.themes.GoogleFont(SANS_FONT), "ui-sans-serif", "system-ui", "sans-serif"),
            font_mono=(gr.themes.GoogleFont(MONO_FONT), "Courier New", "monospace"),
        )
        light, dark = LIGHT, DARK
        self.set(
            # ── surfaces ──────────────────────────────────────────────────────
            body_background_fill=light["desk"],
            body_background_fill_dark=dark["desk"],
            body_text_color=light["ink"],
            body_text_color_dark=dark["ink"],
            body_text_color_subdued=light["ink_3"],
            body_text_color_subdued_dark=dark["ink_3"],
            background_fill_primary=light["paper"],
            background_fill_primary_dark=dark["paper"],
            background_fill_secondary=light["paper_2"],
            background_fill_secondary_dark=dark["paper_2"],
            panel_background_fill=light["paper"],
            panel_background_fill_dark=dark["paper"],
            panel_border_color=light["line"],
            panel_border_color_dark=dark["line"],
            block_background_fill=light["paper"],
            block_background_fill_dark=dark["paper"],
            block_border_color=light["line"],
            block_border_color_dark=dark["line"],
            block_label_background_fill=light["paper"],
            block_label_background_fill_dark=dark["paper"],
            block_label_text_color=light["ink_3"],
            block_label_text_color_dark=dark["ink_3"],
            block_label_text_weight="400",
            block_label_text_size="11px",
            block_title_text_color=light["ink_2"],
            block_title_text_color_dark=dark["ink_2"],
            border_color_primary=light["line_2"],
            border_color_primary_dark=dark["line_2"],
            border_color_accent=light["pink_400"],
            border_color_accent_dark=dark["pink_400"],
            color_accent=light["pink_400"],
            color_accent_soft=light["pink_100"],
            color_accent_soft_dark=dark["pink_200"],
            # ── type ─────────────────────────────────────────────────────────
            prose_text_size="17px",
            prose_header_text_weight="600",
            # ── inputs ───────────────────────────────────────────────────────
            input_background_fill=light["paper_2"],
            input_background_fill_dark=dark["paper_2"],
            input_border_color=light["line_2"],
            input_border_color_dark=dark["line_2"],
            input_border_color_focus=light["blue_400"],
            input_border_color_focus_dark=dark["blue_400"],
            input_placeholder_color=light["ink_3"],
            input_placeholder_color_dark=dark["ink_3"],
            input_shadow="none",
            input_shadow_dark="none",
            input_shadow_focus="0 0 0 3px #edf3fd",
            input_shadow_focus_dark="0 0 0 3px #1f2436",
            input_radius="8px",
            # ── buttons: paper labels, slightly off-square ───────────────────
            button_large_radius="8px 9px 6px 10px",
            button_medium_radius="8px 9px 6px 10px",
            button_small_radius="7px 8px 5px 9px",
            button_primary_background_fill=light["pink_200"],
            button_primary_background_fill_dark=light["pink_200"],
            button_primary_background_fill_hover=light["pink_300"],
            button_primary_background_fill_hover_dark=light["pink_300"],
            button_primary_text_color=light["ink"],
            button_primary_text_color_dark=light["ink"],
            button_primary_border_color=light["pink_500"],
            button_primary_border_color_dark=light["pink_500"],
            button_secondary_background_fill=light["paper"],
            button_secondary_background_fill_dark=dark["paper"],
            button_secondary_background_fill_hover=light["blue_100"],
            button_secondary_background_fill_hover_dark=dark["blue_200"],
            button_secondary_text_color=light["ink"],
            button_secondary_text_color_dark=dark["ink"],
            button_secondary_border_color=light["line_2"],
            button_secondary_border_color_dark=dark["line_2"],
            button_cancel_background_fill=light["paper"],
            button_cancel_background_fill_dark=dark["paper"],
            button_cancel_text_color=light["pink_500"],
            button_cancel_text_color_dark=dark["pink_500"],
            # ── geometry ─────────────────────────────────────────────────────
            block_radius="7px 11px 8px 12px",
            block_title_radius="10px",
            container_radius="8px",
            shadow_drop="2px 3px 0 rgba(205, 186, 197, 1)",
            shadow_drop_lg="0 2px 3px rgba(68, 59, 72, 0.05), 0 18px 30px -26px rgba(68, 59, 72, 0.6)",
            shadow_inset="none",
            loader_color=light["pink_400"],
            loader_color_dark=dark["pink_400"],
            slider_color=light["pink_400"],
            slider_color_dark=dark["pink_400"],
            checkbox_background_color_selected=light["pink_400"],
            checkbox_background_color_selected_dark=dark["pink_400"],
            link_text_color=light["pink_500"],
            link_text_color_dark=dark["pink_500"],
            link_text_color_hover=light["blue_500"],
            link_text_color_hover_dark=dark["blue_500"],
        )


def build_theme() -> Washi:
    return Washi()
