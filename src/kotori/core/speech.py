"""Text to speech: curated voice presets, synthesis and data-URI delivery."""

from __future__ import annotations

import base64
import re
from dataclasses import dataclass
from pathlib import Path

from gtts import gTTS

DEFAULT_VOICE = "aurora"
MAX_SPEECH_CHARS = 5000


class SpeechError(RuntimeError):
    """Raised when speech synthesis fails (usually a network hiccup)."""


@dataclass(frozen=True, slots=True)
class Voice:
    """A gTTS preset: a language plus the accent host it borrows."""

    key: str
    label: str
    region: str
    lang: str
    tld: str

    @property
    def choice(self) -> str:
        return f"{self.label} · {self.region}"


VOICES: tuple[Voice, ...] = (
    Voice("aurora", "Aurora", "English · US", "en", "com"),
    Voice("camber", "Camber", "English · UK", "en", "co.uk"),
    Voice("wren", "Wren", "English · AU", "en", "com.au"),
    Voice("monsoon", "Monsoon", "English · IN", "en", "co.in"),
    Voice("sable", "Sable", "Français · FR", "fr", "fr"),
    Voice("quill", "Quill", "Español · ES", "es", "es"),
    Voice("linden", "Linden", "Deutsch · DE", "de", "de"),
    Voice("saffron", "Saffron", "हिन्दी · IN", "hi", "co.in"),
    Voice("ember", "Ember", "Português · BR", "pt", "com.br"),
    Voice("ink", "Ink", "Italiano · IT", "it", "it"),
    Voice("kestrel", "Kestrel", "Nederlands · NL", "nl", "nl"),
    Voice("nori", "Nori", "日本語 · JP", "ja", "co.jp"),
)

VOICE_BY_KEY = {voice.key: voice for voice in VOICES}
VOICE_BY_CHOICE = {voice.choice: voice for voice in VOICES}

_MARKDOWN_RE = re.compile(r"[*_`#>~]+")
_QUOTES_RE = re.compile(r"[“”„]")
_DASH_RE = re.compile(r"\s*[—–]\s*")
_URL_RE = re.compile(r"https?://\S+")
_SPACE_RE = re.compile(r"\s{2,}")


def voice_choices() -> list[tuple[str, str]]:
    """``(label, value)`` pairs for the Gradio dropdown."""
    return [(voice.choice, voice.key) for voice in VOICES]


def resolve_voice(key: str | None) -> Voice:
    """Look up a voice by key or by rendered choice label."""
    if key and key in VOICE_BY_KEY:
        return VOICE_BY_KEY[key]
    if key and key in VOICE_BY_CHOICE:
        return VOICE_BY_CHOICE[key]
    return VOICE_BY_KEY[DEFAULT_VOICE]


def for_speech(text: str) -> str:
    """Normalise prose so the synthesiser reads it gracefully."""
    cleaned = _URL_RE.sub("", text or "")
    cleaned = _MARKDOWN_RE.sub("", cleaned)
    cleaned = _QUOTES_RE.sub('"', cleaned)
    cleaned = _DASH_RE.sub(", ", cleaned)
    cleaned = _SPACE_RE.sub(" ", cleaned)
    return cleaned.strip()[:MAX_SPEECH_CHARS]


def synthesize(
    text: str,
    *,
    voice_key: str = DEFAULT_VOICE,
    out_dir: Path,
    stem: str = "story",
    slow: bool = False,
) -> Path:
    """Render ``text`` to an mp3 and return the file path."""
    spoken = for_speech(text)
    if not spoken:
        raise SpeechError("Nothing to read aloud yet.")

    voice = resolve_voice(voice_key)
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"{stem}-{voice.key}.mp3"

    try:
        gTTS(text=spoken, lang=voice.lang, tld=voice.tld, slow=slow).save(str(target))
    except Exception as error:  # pragma: no cover - network dependent
        raise SpeechError(f"The voice synthesizer failed: {error}") from error

    return target


def audio_data_uri(path: str | Path, mime: str = "audio/mpeg") -> str:
    """Inline the mp3 so the custom player needs no extra request."""
    data = Path(path).read_bytes()
    return f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"
