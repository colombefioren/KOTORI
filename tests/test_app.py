from pathlib import Path

import gradio as gr

from kotori.app import build_demo, build_studio, launch_options
from kotori.config import Settings
from kotori.frontend import (
    SCRIPT_FILES,
    STYLE_FILES,
    favicon_path,
    head_html,
    missing_assets,
    script_source,
    stylesheet_paths,
)
from kotori.theme import Washi

EXPECTED_IDS = {
    "ast-masthead",
    "ast-tabs",
    "ast-home-intro",
    "ast-home-steps",
    "ast-start",
    "ast-demo",
    "ast-topic",
    "ast-ignite",
    "ast-seed",
    "ast-stop",
    "ast-status",
    "ast-stage",
    "ast-deck",
    "ast-history",
    "ast-history-pick",
    "ast-history-status",
    "ast-refresh",
    "ast-pick",
    "ast-open",
    "ast-delete",
    "ast-incoming",
    "ast-adopt",
    "ast-footer",
}


def test_asset_bundle_is_complete():
    assert missing_assets() == []
    assert len(stylesheet_paths()) == len(STYLE_FILES)
    assert len(SCRIPT_FILES) == 4
    assert all(Path(path).is_file() for path in stylesheet_paths())


def test_scripts_expose_the_client_contract():
    source = script_source()
    for marker in (
        "window.ASTBus",
        "window.ASTPlayer",
        "window.ASTToast",
        "window.ASTCodec",
        "window.ASTTheme",
        "window.ASTVoices",
        "window.ASTRooms",
    ):
        assert marker in source
    assert "ast-trail" in source


def test_the_client_owns_the_rooms():
    source = script_source()
    # the tabs are flipped in the browser, and the server talks through a signal
    assert "index-tab" in source
    assert "data-room" in source
    assert "ast-room" in source
    assert "MutationObserver" in source
    assert 'role="tab"' not in source  # nothing queries gradio's own tab markup


def test_the_room_is_chosen_before_the_first_paint():
    head = head_html()
    assert "data-room" in head
    assert "data-theme" in head
    # with scripting off, every room is shown rather than two being hidden
    assert "<noscript>" in head
    for room in ("room-home", "room-playground", "room-history"):
        assert room in head


def test_a_light_deployment_follows_the_operating_system():
    head = head_html(Settings(theme="light"))
    assert "!saved&&true&&window.matchMedia" in head


def test_a_dark_deployment_stays_dark():
    head = head_html(Settings(theme="dark"))
    assert "!saved&&false&&window.matchMedia" in head
    assert "theme=saved||'dark'" in head


def test_head_html_loads_the_webfonts():
    head = head_html()
    assert "fonts.googleapis.com" in head
    assert "theme-color" in head
    assert "color-scheme" in head
    assert "Fraunces" in head
    assert "Kalam" in head
    assert "Special+Elite" in head
    # the theme is chosen before the first paint, so there is no flash
    assert "kotori-theme" in head
    assert "data-theme" in head


def test_favicon_is_shipped():
    path = favicon_path()
    assert path is not None and Path(path).suffix == ".svg"


def test_launch_options_are_wired(settings: Settings):
    options = launch_options(settings)
    assert isinstance(options["theme"], Washi)
    assert options["js"] and options["head"]
    assert options["css_paths"]
    assert options["favicon_path"]
    assert options["server_port"] == 7860
    assert "allowed_paths" not in options


def test_launch_options_serve_the_archive(settings: Settings, tmp_path: Path):
    studio = build_studio(Settings(data_dir=tmp_path, api_key="k"))
    options = launch_options(settings, allowed_paths=[str(studio.data_dir)])
    assert options["allowed_paths"] == [str(tmp_path)]


def test_port_can_be_overridden_by_env(settings: Settings, monkeypatch):
    monkeypatch.setenv("GRADIO_SERVER_PORT", "8123")
    assert launch_options(settings)["server_port"] == 8123
    # PORT is what container hosts inject, so it takes precedence
    monkeypatch.setenv("PORT", "9000")
    assert launch_options(settings)["server_port"] == 9000
    assert launch_options(settings)["server_name"] == "0.0.0.0"


def test_app_assembles_every_anchor(settings: Settings):
    demo = build_demo(settings)
    assert isinstance(demo, gr.Blocks)
    config = demo.get_config_file()
    ids = {component.get("props", {}).get("elem_id") for component in config["components"]}
    assert ids >= EXPECTED_IDS
    assert len(config["dependencies"]) >= 10


def test_app_renders_branding_and_controls(settings: Settings, tmp_path: Path):
    demo = build_demo(settings)
    config = demo.get_config_file()
    values = " ".join(
        str(component.get("props", {}).get("value", "")) for component in config["components"]
    )
    assert "KOTO<b>RI</b>" in values
    assert "write the story" in values
    assert "the page is still blank" in values
    assert "nothing here yet" in values


def test_the_three_rooms_and_their_tabs_are_named(settings: Settings):
    demo = build_demo(settings)
    config = demo.get_config_file()
    ids = {component.get("props", {}).get("elem_id") for component in config["components"]}
    assert {"room-home", "room-playground", "room-history"} <= ids

    strip = " ".join(
        str(component.get("props", {}).get("value", ""))
        for component in config["components"]
        if component.get("props", {}).get("elem_id") == "ast-tabs"
    )
    for room in ("home", "playground", "history"):
        assert f'data-room="{room}"' in strip
    assert strip.count('role="tab"') == 3
    assert 'aria-selected="true"' in strip


def test_history_starts_empty(settings: Settings):
    demo = build_demo(settings)
    config = demo.get_config_file()
    radios = [
        component
        for component in config["components"]
        if component.get("type") == "radio"
        and component.get("props", {}).get("elem_id") == "ast-history-pick"
    ]
    assert radios and radios[0]["props"]["choices"] == []
