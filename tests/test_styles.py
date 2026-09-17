"""Every class the server renders should have a rule in the stylesheet.

The interface is hand-cut CSS, which makes it very easy to rename a class in
``markup.py`` and leave the styles behind — a mistake that is invisible in tests
and obvious in a browser. This file closes that gap by comparing the classes the
server emits with the selectors the bundle defines.
"""

from __future__ import annotations

import re

from kotori.config import ASSETS_DIR, PROJECT_ROOT

MARKUP = PROJECT_ROOT / "src" / "kotori" / "ui" / "markup.py"
UI = PROJECT_ROOT / "src" / "kotori" / "ui" / "ui.py"
SCRIPTS = ASSETS_DIR / "scripts"
STYLES = ASSETS_DIR / "styles"

CLASS_ATTR = re.compile(r'class=\\?"([^"\\]+)')
ELEM_CLASSES = re.compile(r"elem_classes=\[([^\]]+)\]")
CSS_CLASS = re.compile(r"\.(-?[_a-zA-Z][\w-]*)")

#: Classes that exist for the client to add at runtime, so the server never
#: renders them. They are asserted to be styled all the same.
CLIENT_ONLY = (
    "ast-toast",
    "ast-toast--ok",
    "ast-toast--error",
    "ast-overlay",
    "ast-sheet",
    "is-current",
    "is-spoken",
    "is-pending",
    "is-fresh",
    "sheet--speaking",
    "deck__play--ready",
    "ast-lamp--busy",
)

#: Gradio's own classes, which are styled by framework CSS.
FOREIGN = ("astro-", "svelte-", "gradio-", "toast-")


def rendered_classes() -> set[str]:
    """Every class token the server writes into an element."""
    found: set[str] = set()
    for path in (MARKUP, UI):
        text = path.read_text(encoding="utf-8")
        for value in CLASS_ATTR.findall(text):
            found.update(value.split())
        for value in ELEM_CLASSES.findall(text):
            found.update(re.findall(r'"([^"]+)"', value))
    # f-string placeholders leak in as partial tokens; they are not classes
    return {
        name
        for name in found
        if not name.startswith(FOREIGN) and "{" not in name and "}" not in name
    }


def styled_classes() -> set[str]:
    found: set[str] = set()
    for path in STYLES.glob("*.css"):
        found.update(CSS_CLASS.findall(path.read_text(encoding="utf-8")))
    return found


def test_every_rendered_class_is_styled():
    missing = sorted(rendered_classes() - styled_classes())
    assert missing == [], f"unstyled classes: {missing}"


def test_the_client_only_classes_are_styled_too():
    missing = sorted(set(CLIENT_ONLY) - styled_classes())
    assert missing == [], f"unstyled client classes: {missing}"


def test_the_bundle_is_split_into_the_four_sheets():
    assert sorted(path.name for path in STYLES.glob("*.css")) == [
        "animations.css",
        "components.css",
        "layout.css",
        "tokens.css",
    ]


def test_the_scripts_do_not_reach_into_gradio_internals():
    """The client talks to ids and roles we own, never to framework classes."""
    forbidden = ("svelte-", "tab-nav", "gradio-container .tab")
    for path in SCRIPTS.glob("*.js"):
        text = path.read_text(encoding="utf-8")
        for needle in forbidden:
            assert needle not in text, f"{path.name} depends on {needle!r}"
