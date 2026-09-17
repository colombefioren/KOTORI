from pathlib import Path

import pytest

from kotori.config import (
    PROJECT_ROOT,
    Settings,
    ensure_writable_dir,
    load_settings,
    reset_settings_cache,
)

ENV_KEYS = (
    "MODEL_NAME",
    "OPENAI_MODEL",
    "OPENAI_MODEL_NAME",
    "API_KEY",
    "OPENAI_API_KEY",
    "BASE_URL",
    "OPENAI_BASE_URL",
    "TEMPERATURE",
    "MAX_TOKENS",
    "AI_STORYTELLER_DATA_DIR",
    "KOTORI_DATA_DIR",
    "KOTORI_THEME",
)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch):
    for key in ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    yield


def test_load_settings_uses_canonical_names(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("MODEL_NAME", "llama-3")
    monkeypatch.setenv("API_KEY", "secret")
    monkeypatch.setenv("BASE_URL", "https://example.test/v1")
    settings = load_settings()
    assert settings.model_name == "llama-3"
    assert settings.api_key == "secret"
    assert settings.base_url == "https://example.test/v1"
    assert settings.is_configured is True


def test_load_settings_accepts_openai_aliases(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("OPENAI_API_KEY", "alias-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://alias.test/v1")
    monkeypatch.setenv("OPENAI_MODEL", "alias-model")
    settings = load_settings()
    assert (settings.api_key, settings.base_url, settings.model_name) == (
        "alias-key",
        "https://alias.test/v1",
        "alias-model",
    )


def test_numeric_env_values_fall_back_when_nonsense(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("TEMPERATURE", "warm")
    monkeypatch.setenv("MAX_TOKENS", "many")
    settings = load_settings()
    assert settings.temperature == 0.9
    assert settings.max_tokens == 900


def test_numeric_env_values_are_read(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("TEMPERATURE", "0.4")
    monkeypatch.setenv("MAX_TOKENS", "256")
    monkeypatch.setenv("KOTORI_THEME", "dark")
    settings = load_settings()
    assert settings.temperature == 0.4
    assert settings.max_tokens == 256
    assert settings.theme == "dark"


def test_an_unknown_theme_falls_back_to_paper(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("KOTORI_THEME", "holographic")
    assert load_settings().theme == "light"


def test_the_old_data_dir_name_still_works(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AI_STORYTELLER_DATA_DIR", "legacy/archive")
    assert load_settings().data_dir == (PROJECT_ROOT / "legacy/archive").resolve()


def test_relative_data_dir_anchors_to_the_project(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AI_STORYTELLER_DATA_DIR", "var/archive")
    assert load_settings().data_dir == (PROJECT_ROOT / "var/archive").resolve()


def test_absolute_data_dir_is_kept(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AI_STORYTELLER_DATA_DIR", str(tmp_path))
    assert load_settings().data_dir == tmp_path


def test_engine_label_never_names_the_provider(tmp_path: Path):
    offline = Settings(api_key=None, data_dir=tmp_path)
    assert offline.engine_label == "the demo reels"
    assert offline.public()["has_key"] is False

    online = Settings(model_name="test-model", api_key="key", data_dir=tmp_path)
    assert online.engine_label == "a quiet writer"
    assert "test-model" not in online.engine_label
    snapshot = online.public()
    assert "key" not in snapshot.values()
    assert snapshot["has_key"] is True


def test_paths_hang_off_the_data_dir(tmp_path: Path):
    settings = Settings(data_dir=tmp_path)
    assert settings.archive_path == tmp_path / "library.jsonl"
    assert settings.audio_dir == tmp_path / "audio"
    settings.ensure_dirs()
    assert settings.audio_dir.is_dir()


def test_ensure_writable_dir_creates_and_verifies(tmp_path: Path):
    target = tmp_path / "nested" / "archive"
    assert ensure_writable_dir(target) == target
    assert target.is_dir()


def test_ensure_writable_dir_falls_back_when_blocked(tmp_path: Path):
    blocker = tmp_path / "not-a-dir"
    blocker.write_text("in the way", encoding="utf-8")
    resolved = ensure_writable_dir(blocker / "child")
    assert resolved.is_dir()
    assert resolved != blocker


def test_reset_settings_cache_returns_fresh_settings():
    assert isinstance(reset_settings_cache(), Settings)
