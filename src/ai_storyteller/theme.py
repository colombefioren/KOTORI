"""A Gradio theme that mirrors the CSS design tokens.

The studio is dark by design, so the light slots are filled with the same
values as the dark slots: the app looks identical whatever the OS prefers.
"""

from __future__ import annotations

import gradio as gr

PALETTE: dict[str, str] = {
    "void": "#07070c",
    "ink": "#0b0b13",
    "panel": "#101021",
    "panel_2": "#16162c",
    "panel_3": "#1d1d38",
    "line": "#2a2a48",
    "chalk": "#f5f4ff",
    "mist": "#b6b3d8",
    "dust": "#7c7aa0",
    "mint": "#96f7d2",
    "lilac": "#cbb8ff",
    "blush": "#ffb2cb",
    "butter": "#ffe8a3",
    "sky": "#a6d8ff",
}

DISPLAY_FONT = "Space Grotesk"
MONO_FONT = "JetBrains Mono"
SERIF_FONT = "Instrument Serif"


class NeonEditorial(gr.themes.Base):
    """Hard shadows, pastel neons, mono labels, editorial type."""

    def __init__(self) -> None:
        super().__init__(
            primary_hue="emerald",
            secondary_hue="violet",
            neutral_hue="slate",
            radius_size=gr.themes.sizes.radius_sm,
            text_size=gr.themes.sizes.text_md,
            spacing_size=gr.themes.sizes.spacing_md,
            font=(gr.themes.GoogleFont(DISPLAY_FONT), "ui-sans-serif", "system-ui", "sans-serif"),
            font_mono=(
                gr.themes.GoogleFont(MONO_FONT),
                "ui-monospace",
                "Consolas",
                "monospace",
            ),
        )
        colors = PALETTE
        self.set(
            # surfaces — light and dark slots intentionally identical
            body_background_fill=colors["void"],
            body_background_fill_dark=colors["void"],
            body_text_color=colors["chalk"],
            body_text_color_dark=colors["chalk"],
            body_text_color_subdued=colors["dust"],
            body_text_color_subdued_dark=colors["dust"],
            background_fill_primary=colors["ink"],
            background_fill_primary_dark=colors["ink"],
            background_fill_secondary=colors["panel"],
            background_fill_secondary_dark=colors["panel"],
            panel_background_fill=colors["panel"],
            panel_background_fill_dark=colors["panel"],
            panel_border_color=colors["line"],
            panel_border_color_dark=colors["line"],
            block_background_fill=colors["panel"],
            block_background_fill_dark=colors["panel"],
            block_border_color=colors["line"],
            block_border_color_dark=colors["line"],
            block_label_background_fill=colors["void"],
            block_label_background_fill_dark=colors["void"],
            block_label_text_color=colors["dust"],
            block_label_text_color_dark=colors["dust"],
            block_label_text_weight="500",
            block_label_text_size="11px",
            block_title_text_color=colors["mist"],
            block_title_text_color_dark=colors["mist"],
            border_color_primary=colors["line"],
            border_color_primary_dark=colors["line"],
            border_color_accent=colors["mint"],
            border_color_accent_dark=colors["mint"],
            color_accent=colors["mint"],
            color_accent_soft="rgba(150, 247, 210, 0.14)",
            color_accent_soft_dark="rgba(150, 247, 210, 0.14)",
            # type
            prose_text_size="17px",
            prose_header_text_weight="700",
            # inputs
            input_background_fill=colors["void"],
            input_background_fill_dark=colors["void"],
            input_border_color=colors["line"],
            input_border_color_dark=colors["line"],
            input_border_color_focus=colors["mint"],
            input_border_color_focus_dark=colors["mint"],
            input_placeholder_color=colors["dust"],
            input_placeholder_color_dark=colors["dust"],
            input_shadow="3px 3px 0 rgba(0, 0, 0, 0.6)",
            input_shadow_dark="3px 3px 0 rgba(0, 0, 0, 0.6)",
            input_shadow_focus="0 0 22px rgba(150, 247, 210, 0.35)",
            input_shadow_focus_dark="0 0 22px rgba(150, 247, 210, 0.35)",
            # buttons
            button_large_radius="2px",
            button_medium_radius="2px",
            button_small_radius="2px",
            button_primary_background_fill=colors["mint"],
            button_primary_background_fill_dark=colors["mint"],
            button_primary_background_fill_hover=colors["lilac"],
            button_primary_background_fill_hover_dark=colors["lilac"],
            button_primary_text_color=colors["void"],
            button_primary_text_color_dark=colors["void"],
            button_primary_border_color="#000",
            button_primary_border_color_dark="#000",
            button_secondary_background_fill=colors["panel_2"],
            button_secondary_background_fill_dark=colors["panel_2"],
            button_secondary_background_fill_hover=colors["panel_3"],
            button_secondary_background_fill_hover_dark=colors["panel_3"],
            button_secondary_text_color=colors["chalk"],
            button_secondary_text_color_dark=colors["chalk"],
            button_secondary_border_color=colors["line"],
            button_secondary_border_color_dark=colors["line"],
            button_cancel_background_fill=colors["blush"],
            button_cancel_background_fill_dark=colors["blush"],
            button_cancel_text_color=colors["void"],
            button_cancel_text_color_dark=colors["void"],
            # geometry
            block_radius="2px",
            block_title_radius="0",
            container_radius="2px",
            input_radius="2px",
            shadow_drop="6px 6px 0 rgba(0, 0, 0, 0.85)",
            shadow_drop_lg="8px 8px 0 rgba(0, 0, 0, 0.9)",
            shadow_inset="inset 0 2px 0 rgba(0, 0, 0, 0.45)",
            loader_color=colors["mint"],
            loader_color_dark=colors["mint"],
            slider_color=colors["mint"],
            slider_color_dark=colors["mint"],
            checkbox_background_color_selected=colors["mint"],
            checkbox_background_color_selected_dark=colors["mint"],
            link_text_color=colors["mint"],
            link_text_color_dark=colors["mint"],
            link_text_color_hover=colors["butter"],
            link_text_color_hover_dark=colors["butter"],
        )


def build_theme() -> NeonEditorial:
    return NeonEditorial()
