from pathlib import Path

import pytest

from ai_storyteller.speech import (
    DEFAULT_VOICE,
    VOICES,
    audio_data_uri,
    for_speech,
    resolve_voice,
    voice_choices,
)


def test_voice_keys_are_unique():
    keys = [voice.key for voice in VOICES]
    assert len(keys) == len(set(keys))


def test_choices_match_voices():
    choices = voice_choices()
    assert len(choices) == len(VOICES)
    assert all(isinstance(label, str) and key for label, key in choices)


def test_resolve_voice_accepts_key_label_and_junk():
    assert resolve_voice("camber").lang == "en"
    assert resolve_voice(resolve_voice("camber").choice).key == "camber"
    assert resolve_voice(None).key == DEFAULT_VOICE
    assert resolve_voice("nope").key == DEFAULT_VOICE


def test_for_speech_strips_markup_and_smart_punctuation():
    spoken = for_speech("  **Bold** #tag — “quoted” [x](https://example.com)  ")
    assert "*" not in spoken and "#" not in spoken and "“" not in spoken
    assert "https" not in spoken
    assert "—" not in spoken
    assert "  " not in spoken


def test_for_speech_handles_empty_text():
    assert for_speech("") == ""


def test_audio_data_uri_encodes_bytes(tmp_path: Path):
    sample = tmp_path / "sample.mp3"
    sample.write_bytes(b"\xff\xfb\x90")
    uri = audio_data_uri(sample)
    assert uri.startswith("data:audio/mpeg;base64,")


def test_missing_file_raises(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        audio_data_uri(tmp_path / "ghost.mp3")
