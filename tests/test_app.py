from pathlib import Path

import gradio as gr

from kotori.app import build_demo, launch_options
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
from kotori.theme import Scratchbook

EXPECTED_IDS = {
    "ast-header",
    "ast-topic",
    "ast-ignite",
    "ast-seed",
    "ast-stop",
    "ast-status",
    "ast-stage",
    "ast-deck",
    "ast-archive-pick",
    "ast-archive-preview",
    "ast-archive-status",
    "ast-delete",
    "ast-record",
    "ast-clear",
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
    for marker in ("window.ASTBus", "window.ASTPlayer", "window.ASTToast", "window.ASTCodec"):
        assert marker in source
    assert "ast-trail" in source


def test_head_html_loads_the_webfonts():
    head = head_html()
    assert "fonts.googleapis.com" in head
    assert "theme-color" in head
    assert "color-scheme" in head
    assert "Fraunces" in head
    assert "Caveat" in head


def test_favicon_is_shipped():
    path = favicon_path()
    assert path is not None and Path(path).suffix == ".svg"


def test_launch_options_are_wired(settings: Settings):
    options = launch_options(settings)
    assert isinstance(options["theme"], Scratchbook)
    assert options["js"] and options["head"]
    assert options["css_paths"]
    assert options["favicon_path"]
    assert options["server_port"] == 7860


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
    assert "Stories" in values
    assert "write the story" in values
    assert "the page is still blank" in values


def test_archive_tab_starts_empty(settings: Settings):
    demo = build_demo(settings)
    config = demo.get_config_file()
    radios = [
        component
        for component in config["components"]
        if component.get("type") == "radio"
        and component.get("props", {}).get("elem_id") == "ast-archive-pick"
    ]
    assert radios and radios[0]["props"]["choices"] == []
