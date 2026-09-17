from pathlib import Path

from kotori.library import StoryLibrary
from kotori.models import StoryDraft


def draft(topic: str, story: str = "Once the sea answered.", genre: str = "Noir") -> StoryDraft:
    return StoryDraft(topic=topic, story=story, genre=genre)


def test_empty_library_reports_zeroes(tmp_path: Path):
    library = StoryLibrary(tmp_path / "library.jsonl")
    assert library.load() == []
    stats = library.stats()
    assert (stats.drafts, stats.words, stats.minutes) == (0, 0, 0)
    assert stats.top_genre == "—"


def test_save_then_load_is_newest_first(tmp_path: Path):
    library = StoryLibrary(tmp_path / "library.jsonl")
    library.save(draft("first"))
    library.save(draft("second"))
    topics = [d.topic for d in library.load()]
    assert topics == ["second", "first"]


def test_save_is_idempotent_per_id(tmp_path: Path):
    library = StoryLibrary(tmp_path / "library.jsonl")
    one = library.save(draft("first"))
    library.save(StoryDraft(story_id=one.story_id, topic="first", story="Rewritten."))
    drafts = library.load()
    assert len(drafts) == 1
    assert drafts[0].story == "Rewritten."


def test_get_and_delete(tmp_path: Path):
    library = StoryLibrary(tmp_path / "library.jsonl")
    saved = library.save(draft("first"))
    assert library.get(saved.story_id) is not None
    assert library.get("missing") is None
    assert library.get(None) is None
    assert library.delete(saved.story_id) is True
    assert library.delete(saved.story_id) is False
    assert library.load() == []


def test_clear_reports_removed_count(tmp_path: Path):
    library = StoryLibrary(tmp_path / "library.jsonl")
    library.save(draft("one"))
    library.save(draft("two"))
    assert library.clear() == 2
    assert library.load() == []


def test_limit_keeps_the_newest_entries(tmp_path: Path):
    library = StoryLibrary(tmp_path / "library.jsonl", limit=2)
    for index in range(5):
        library.save(draft(f"topic {index}"))
    assert [d.topic for d in library.load()] == ["topic 4", "topic 3"]


def test_corrupt_lines_are_skipped(tmp_path: Path):
    path = tmp_path / "library.jsonl"
    path.write_text('{"topic": "ok", "story": "hi"}\nnot json\n\n', encoding="utf-8")
    library = StoryLibrary(path)
    assert [d.topic for d in library.load()] == ["ok"]


def test_stats_track_words_and_top_genre(tmp_path: Path):
    library = StoryLibrary(tmp_path / "library.jsonl")
    library.save(draft("one", "The sea answered the lamp again tonight.", genre="Noir"))
    library.save(draft("two", "A quiet town forgot its own name.", genre="Noir"))
    library.save(draft("three", "Green things grew.", genre="Fable"))
    stats = library.stats()
    assert stats.drafts == 3
    assert stats.words >= 17
    assert stats.top_genre == "Noir"


def test_archive_round_trips_through_disk(tmp_path: Path):
    path = tmp_path / "library.jsonl"
    saved = StoryDraft(topic="the lamp", story="Hi.", voice_label="Aurora — English · US")
    StoryLibrary(path).save(saved)
    reloaded = StoryLibrary(path).get(saved.story_id)
    assert reloaded is not None
    assert reloaded.voice_label == "Aurora — English · US"
    assert reloaded.created_at == saved.created_at
