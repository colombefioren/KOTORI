"""The paperwork: the readme, the env example and the shipped text.

Two things are checked here that a reviewer would otherwise have to remember: that
nobody reading the project can tell which model vendor it happens to be pointed at,
and that the old studio name is gone from everything a visitor can see.
"""

from pathlib import Path

import yaml

from kotori.config import PROJECT_ROOT

README = PROJECT_ROOT / "README.md"
ENV_EXAMPLE = PROJECT_ROOT / ".env.example"
PREVIEW = PROJECT_ROOT / "docs" / "preview.svg"

#: Nothing a visitor can read should name the model provider.
BANNED_IN_PROSE = ("deepseek", "openai/gpt-oss", "anthropic")

#: The old studio identity, which only survives as a compatibility env var.
BANNED_IN_PATHS = ("ai-storyteller", "ai_storyteller/", "ai storyteller", "AI-STORYTELLER")

SHIPPED = (
    README,
    ENV_EXAMPLE,
    PREVIEW,
    PROJECT_ROOT / "docs",
    PROJECT_ROOT / "src" / "kotori",
    PROJECT_ROOT / "Dockerfile",
    PROJECT_ROOT / "docker-compose.yml",
    PROJECT_ROOT / "render.yaml",
    PROJECT_ROOT / ".github" / "workflows",
)


def shipped_files() -> list[Path]:
    files: list[Path] = []
    for entry in SHIPPED:
        if entry.is_dir():
            files.extend(
                path
                for path in entry.rglob("*")
                if path.is_file()
                and path.suffix in {".py", ".css", ".js", ".svg", ".md", ".yml", ".yaml", ".toml"}
            )
        else:
            files.append(entry)
    return files


def test_the_readme_has_valid_space_front_matter():
    text = README.read_text(encoding="utf-8")
    _, _, body = text.partition("---\n")
    front_matter, _, _ = body.partition("---\n")
    meta = yaml.safe_load(front_matter)
    assert meta["title"] == "KOTORI"
    assert meta["sdk"] == "docker"
    assert meta["app_port"] == 7860


def test_no_shipped_file_names_the_model_vendor():
    for path in shipped_files():
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        for word in BANNED_IN_PROSE:
            assert word not in text, f"{path} mentions {word!r}"


def test_the_old_studio_name_is_gone_from_the_paths():
    for path in shipped_files():
        text = path.read_text(encoding="utf-8", errors="ignore")
        for word in BANNED_IN_PATHS:
            assert word not in text, f"{path} still says {word!r}"


def test_the_old_data_dir_name_still_works_for_old_volumes():
    """It is a compatibility alias now, not a name anything else uses."""
    config = (PROJECT_ROOT / "src" / "kotori" / "config.py").read_text(encoding="utf-8")
    assert "AI_STORYTELLER_DATA_DIR" in config
    assert config.count("AI_STORYTELLER") == 2  # the comment and the alias itself


def test_the_readme_documents_the_real_command_and_package():
    text = README.read_text(encoding="utf-8")
    assert "uv run kotori" in text
    assert "--cov=kotori" in text
    assert "github.com/colombefioren/kotori" in text
    assert "FORCE_LIGHT" not in text


def test_the_readme_names_the_three_tabs():
    text = README.read_text(encoding="utf-8").lower()
    for room in ("home", "playground", "history"):
        assert room in text
    assert "four hundred words" in text
