"""Environment-driven configuration for the AI Storyteller studio.

Every tunable lives here so the rest of the codebase stays free of ``os.getenv``.
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_DIR.parents[1]
ASSETS_DIR = PACKAGE_DIR / "assets"
DEFAULT_DATA_DIR = PROJECT_ROOT / "data"

APP_NAME = "KOTORI"
APP_TAGLINE = "a little bird that tells you stories"
VERSION = "0.3.0"

#: The length every story is written to. There is no slider any more.
STORY_WORDS = 400

#: The two moods the studio knows how to dress itself in.
THEMES = ("light", "dark")

load_dotenv(PROJECT_ROOT / ".env")


def _first_env(*names: str) -> str | None:
    """Return the first non-empty environment value among ``names``."""
    for name in names:
        value = os.getenv(name)
        if value and value.strip():
            return value.strip()
    return None


def _env_float(name: str, default: float) -> float:
    raw = _first_env(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    raw = _first_env(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def ensure_writable_dir(path: Path) -> Path:
    """Create ``path``, falling back to a temp dir on read-only hosts."""
    for candidate in (path, Path(tempfile.gettempdir()) / "ai-storyteller"):
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            probe = candidate / ".write-probe"
            probe.touch()
            probe.unlink()
            return candidate
        except OSError:
            continue
    raise RuntimeError(f"no writable directory among {[str(path)]}") from None


def _env_bool(name: str, default: bool = False) -> bool:
    raw = _first_env(name)
    if raw is None:
        return default
    return raw.lower() in {"1", "true", "yes", "on"}


def _theme(raw: str | None) -> str:
    """Only the two themes the studio actually ships."""
    value = (raw or "").strip().lower()
    return value if value in THEMES else "light"


@dataclass(frozen=True, slots=True)
class Settings:
    """Immutable snapshot of the runtime configuration."""

    model_name: str = "gpt-4o-mini"
    api_key: str | None = None
    base_url: str | None = None
    temperature: float = 0.9
    max_tokens: int = 900
    request_timeout: float = 60.0
    data_dir: Path = DEFAULT_DATA_DIR
    #: Which theme to open in; the toggle in the UI overrides it per visitor.
    theme: str = "light"
    version: str = VERSION

    @property
    def is_configured(self) -> bool:
        """True when the studio has everything it needs to open a story."""
        return bool(self.api_key and self.model_name)

    @property
    def engine_label(self) -> str:
        """A neutral name for the writer — never the model, never the provider."""
        return "a quiet writer" if self.is_configured else "the demo reels"

    @property
    def archive_path(self) -> Path:
        return self.data_dir / "library.jsonl"

    @property
    def audio_dir(self) -> Path:
        return self.data_dir / "audio"

    def ensure_dirs(self) -> None:
        """Create the writable directories the studio needs."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.audio_dir.mkdir(parents=True, exist_ok=True)

    def public(self) -> dict[str, object]:
        """Configuration safe to render in the UI (never leaks the key)."""
        return {
            "model": self.model_name,
            "engine": self.engine_label,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "has_key": bool(self.api_key),
            "base_url": self.base_url or "default",
            "version": self.version,
        }


def load_settings() -> Settings:
    """Build a :class:`Settings` instance from the process environment."""
    # the old AI_STORYTELLER_ name is still honoured so existing volumes keep working
    data_dir_raw = (
        _first_env("KOTORI_DATA_DIR", "AI_STORYTELLER_DATA_DIR") or str(DEFAULT_DATA_DIR)
    )
    data_dir = Path(data_dir_raw).expanduser()
    if not data_dir.is_absolute():
        data_dir = (PROJECT_ROOT / data_dir).resolve()

    return Settings(
        model_name=_first_env("MODEL_NAME", "OPENAI_MODEL", "OPENAI_MODEL_NAME") or "gpt-4o-mini",
        api_key=_first_env("API_KEY", "OPENAI_API_KEY"),
        base_url=_first_env("BASE_URL", "OPENAI_BASE_URL", "OPENAI_API_BASE"),
        temperature=_env_float("TEMPERATURE", 0.9),
        max_tokens=_env_int("MAX_TOKENS", 900),
        request_timeout=_env_float("REQUEST_TIMEOUT", 60.0),
        data_dir=data_dir,
        theme=_theme(_first_env("KOTORI_THEME")),
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached accessor used by the UI layer."""
    return load_settings()


def reset_settings_cache() -> Settings:
    """Drop the cache (used by tests and by the ``.env`` reload button)."""
    get_settings.cache_clear()
    load_dotenv(PROJECT_ROOT / ".env", override=True)
    return get_settings()
