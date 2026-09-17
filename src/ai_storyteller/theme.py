"""A Gradio theme that mirrors the CSS design tokens.

The studio is a scratchbook: warm paper, pastel ink, round corners. The light
and dark slots deliberately hold the same values, so an OS-level dark
preference can never produce a half-styled page.
"""

from __future__ import annotations

import gradio as gr

PALETTE: dict[str, str] = {
    "paper": "#f7f1e7",
    "paper_deep": "#efe6d7",
    "card": "#fffdf8",
    "card_sunk": "#fdf8f0",
    "line": "#ecdfca",
    "line_strong": "#ddc9ac",
    "ink": "#4b3f2f",
    "ink_soft": "#7c6c57",
    "ink_faint": "#a79579",
    "rose": "#f3c1cc",
    "rose_deep": "#d98ea2",
    "sage": "#b7ddc8",
    "sage_deep": "#7cb79b",
    "lavender": "#d6cbf4",
    "lavender_deep": "#a795e0",
    "butter": "#f8e6b2",
    "sky": "#c5ddf2",
    "accent_soft": "#ede8fb",
}

DISPLAY_FONT = "Fraunces"
SERIF_FONT = "Lora"
SANS_FONT = "Karla"
HAND_FONT = "Caveat"
MONO_FONT = "Karla"


class Scratchbook(gr.themes.Base):
    """Warm paper, pastel ink, soft shadows, rounded everything."""

    def __init__(self) -> None:
        super().__init__(
            primary_hue="violet",
            secondary_hue="rose",
            neutral_hue="stone",
            radius_size=gr.themes.sizes.radius_lg,
            text_size=gr.themes.sizes.text_md,
            spacing_size=gr.themes.sizes.spacing_md,
            font=(gr.themes.GoogleFont(SANS_FONT), "ui-sans-serif", "system-ui", "sans-serif"),
            font_mono=(
                gr.themes.GoogleFont(SANS_FONT),
                "ui-monospace",
                "SFMono-Regular",
                "monospace",
            ),
        )
        colors = PALETTE
        self.set(
            # surfaces — both slots identical, so the studio always looks the same
            body_background_fill=colors["paper"],
            body_background_fill_dark=colors["paper"],
            body_text_color=colors["ink"],
            body_text_color_dark=colors["ink"],
            body_text_color_subdued=colors["ink_faint"],
            body_text_color_subdued_dark=colors["ink_faint"],
            background_fill_primary=colors["card"],
            background_fill_primary_dark=colors["card"],
            background_fill_secondary=colors["card_sunk"],
            background_fill_secondary_dark=colors["card_sunk"],
            panel_background_fill=colors["card"],
            panel_background_fill_dark=colors["card"],
            panel_border_color=colors["line"],
            panel_border_color_dark=colors["line"],
            block_background_fill=colors["card"],
            block_background_fill_dark=colors["card"],
            block_border_color=colors["line"],
            block_border_color_dark=colors["line"],
            block_label_background_fill=colors["card"],
            block_label_background_fill_dark=colors["card"],
            block_label_text_color=colors["ink_faint"],
            block_label_text_color_dark=colors["ink_faint"],
            block_label_text_weight="500",
            block_label_text_size="12px",
            block_title_text_color=colors["ink_soft"],
            block_title_text_color_dark=colors["ink_soft"],
            border_color_primary=colors["line"],
            border_color_primary_dark=colors["line"],
            border_color_accent=colors["lavender_deep"],
            border_color_accent_dark=colors["lavender_deep"],
            color_accent=colors["lavender_deep"],
            color_accent_soft=colors["accent_soft"],
            color_accent_soft_dark=colors["accent_soft"],
            # type
            prose_text_size="16px",
            prose_header_text_weight="600",
            # inputs
            input_background_fill=colors["card_sunk"],
            input_background_fill_dark=colors["card_sunk"],
            input_border_color=colors["line"],
            input_border_color_dark=colors["line"],
            input_border_color_focus=colors["lavender_deep"],
            input_border_color_focus_dark=colors["lavender_deep"],
            input_placeholder_color=colors["ink_faint"],
            input_placeholder_color_dark=colors["ink_faint"],
            input_shadow="inset 0 1px 2px rgba(84, 66, 46, 0.04)",
            input_shadow_dark="inset 0 1px 2px rgba(84, 66, 46, 0.04)",
            input_shadow_focus="0 0 0 4px rgba(167, 149, 224, 0.16)",
            input_shadow_focus_dark="0 0 0 4px rgba(167, 149, 224, 0.16)",
            # buttons
            button_large_radius="999px",
            button_medium_radius="999px",
            button_small_radius="999px",
            button_primary_background_fill=colors["lavender"],
            button_primary_background_fill_dark=colors["lavender"],
            button_primary_background_fill_hover=colors["rose"],
            button_primary_background_fill_hover_dark=colors["rose"],
            button_primary_text_color=colors["ink"],
            button_primary_text_color_dark=colors["ink"],
            button_primary_border_color="transparent",
            button_primary_border_color_dark="transparent",
            button_secondary_background_fill=colors["card"],
            button_secondary_background_fill_dark=colors["card"],
            button_secondary_background_fill_hover=colors["card_sunk"],
            button_secondary_background_fill_hover_dark=colors["card_sunk"],
            button_secondary_text_color=colors["ink"],
            button_secondary_text_color_dark=colors["ink"],
            button_secondary_border_color=colors["line_strong"],
            button_secondary_border_color_dark=colors["line_strong"],
            button_cancel_background_fill=colors["card"],
            button_cancel_background_fill_dark=colors["card"],
            button_cancel_text_color=colors["rose_deep"],
            button_cancel_text_color_dark=colors["rose_deep"],
            # geometry
            block_radius="18px",
            block_title_radius="18px",
            container_radius="18px",
            input_radius="12px",
            shadow_drop="0 6px 16px -14px rgba(84, 66, 46, 0.55)",
            shadow_drop_lg="0 30px 46px -30px rgba(84, 66, 46, 0.5)",
            shadow_inset="inset 0 1px 2px rgba(84, 66, 46, 0.04)",
            loader_color=colors["lavender_deep"],
            loader_color_dark=colors["lavender_deep"],
            slider_color=colors["lavender_deep"],
            slider_color_dark=colors["lavender_deep"],
            checkbox_background_color_selected=colors["lavender_deep"],
            checkbox_background_color_selected_dark=colors["lavender_deep"],
            link_text_color=colors["lavender_deep"],
            link_text_color_dark=colors["lavender_deep"],
            link_text_color_hover=colors["rose_deep"],
            link_text_color_hover_dark=colors["rose_deep"],
        )


def build_theme() -> Scratchbook:
    return Scratchbook()
