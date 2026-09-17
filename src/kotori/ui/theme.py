"""A Gradio theme that mirrors the CSS design tokens.

KOTORI is a scrapbook kept on the night desk: pink and blue washi pastels,
ink outlines, nothing that glows, and just the one room. This mirrors
``assets/styles/tokens.css`` so any native Gradio chrome our own CSS doesn't
reach still matches.
"""

from __future__ import annotations

import gradio as gr

PALETTE: dict[str, str] = {
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
    "pink_100": "#3a2634",
    "pink_200": "#4c2f42",
    "pink_300": "#f2b3cd",
    "pink_400": "#e288ae",
    "pink_500": "#bd5f8b",
    "blue_100": "#1f2740",
    "blue_200": "#283358",
    "blue_300": "#b3d0f2",
    "blue_400": "#82aae0",
    "blue_500": "#5b83b6",
}

DISPLAY_FONT = "Fraunces"
SERIF_FONT = "EB Garamond"
SANS_FONT = "Karla"
HAND_FONT = "Kalam"
MONO_FONT = "Special Elite"


class Washi(gr.themes.Base):
    """Paper, washi tape, typewriter labels, ink outlines. One desk: dark."""

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
        p = PALETTE
        self.set(
            # ── surfaces ──────────────────────────────────────────────────────
            body_background_fill=p["desk"],
            body_background_fill_dark=p["desk"],
            body_text_color=p["ink"],
            body_text_color_dark=p["ink"],
            body_text_color_subdued=p["ink_3"],
            body_text_color_subdued_dark=p["ink_3"],
            background_fill_primary=p["paper"],
            background_fill_primary_dark=p["paper"],
            background_fill_secondary=p["paper_2"],
            background_fill_secondary_dark=p["paper_2"],
            panel_background_fill=p["paper"],
            panel_background_fill_dark=p["paper"],
            panel_border_color=p["line"],
            panel_border_color_dark=p["line"],
            block_background_fill=p["paper"],
            block_background_fill_dark=p["paper"],
            block_border_color=p["line"],
            block_border_color_dark=p["line"],
            block_label_background_fill=p["paper"],
            block_label_background_fill_dark=p["paper"],
            block_label_text_color=p["ink_3"],
            block_label_text_color_dark=p["ink_3"],
            block_label_text_weight="400",
            block_label_text_size="11px",
            block_title_text_color=p["ink_2"],
            block_title_text_color_dark=p["ink_2"],
            border_color_primary=p["line_2"],
            border_color_primary_dark=p["line_2"],
            border_color_accent=p["pink_400"],
            border_color_accent_dark=p["pink_400"],
            color_accent=p["pink_400"],
            color_accent_soft=p["pink_100"],
            color_accent_soft_dark=p["pink_200"],
            # ── type ─────────────────────────────────────────────────────────
            prose_text_size="17px",
            prose_header_text_weight="600",
            # ── inputs ───────────────────────────────────────────────────────
            input_background_fill=p["paper_2"],
            input_background_fill_dark=p["paper_2"],
            input_border_color=p["line_2"],
            input_border_color_dark=p["line_2"],
            input_border_color_focus=p["blue_400"],
            input_border_color_focus_dark=p["blue_400"],
            input_placeholder_color=p["ink_3"],
            input_placeholder_color_dark=p["ink_3"],
            input_shadow="none",
            input_shadow_dark="none",
            input_shadow_focus=f"0 0 0 3px {p['blue_100']}",
            input_shadow_focus_dark=f"0 0 0 3px {p['blue_100']}",
            input_radius="14px",
            # ── buttons: paper labels, slightly off-square ───────────────────
            button_large_radius="14px 16px 13px 15px",
            button_medium_radius="14px 16px 13px 15px",
            button_small_radius="12px 13px 10px 14px",
            button_primary_background_fill=p["pink_200"],
            button_primary_background_fill_dark=p["pink_200"],
            button_primary_background_fill_hover=p["pink_300"],
            button_primary_background_fill_hover_dark=p["pink_300"],
            button_primary_text_color=p["ink"],
            button_primary_text_color_dark=p["ink"],
            button_primary_border_color=p["pink_500"],
            button_primary_border_color_dark=p["pink_500"],
            button_secondary_background_fill=p["paper"],
            button_secondary_background_fill_dark=p["paper"],
            button_secondary_background_fill_hover=p["blue_200"],
            button_secondary_background_fill_hover_dark=p["blue_200"],
            button_secondary_text_color=p["ink"],
            button_secondary_text_color_dark=p["ink"],
            button_secondary_border_color=p["line_2"],
            button_secondary_border_color_dark=p["line_2"],
            button_cancel_background_fill=p["paper"],
            button_cancel_background_fill_dark=p["paper"],
            button_cancel_text_color=p["pink_500"],
            button_cancel_text_color_dark=p["pink_500"],
            # ── geometry ─────────────────────────────────────────────────────
            block_radius="20px 24px 22px 26px",
            block_title_radius="10px",
            container_radius="8px",
            shadow_drop=f"2px 3px 0 {p['line_2']}",
            shadow_drop_lg="0 2px 4px rgba(0, 0, 0, 0.4), 0 20px 34px -28px rgba(0, 0, 0, 0.9)",
            shadow_inset="none",
            loader_color=p["pink_400"],
            loader_color_dark=p["pink_400"],
            slider_color=p["pink_400"],
            slider_color_dark=p["pink_400"],
            checkbox_background_color_selected=p["pink_400"],
            checkbox_background_color_selected_dark=p["pink_400"],
            link_text_color=p["pink_500"],
            link_text_color_dark=p["pink_500"],
            link_text_color_hover=p["blue_500"],
            link_text_color_hover_dark=p["blue_500"],
        )


def build_theme() -> Washi:
    return Washi()
