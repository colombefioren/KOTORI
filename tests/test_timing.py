import itertools

from kotori.core.timing import (
    cumulative_fractions,
    estimate_duration,
    split_words,
    word_timings,
    word_weights,
)

SAMPLE = "She waited, and the city answered. Was it real?"


def test_split_words_keeps_punctuation():
    assert split_words(SAMPLE)[:3] == ["She", "waited,", "and"]


def test_split_words_handles_empty_input():
    assert split_words("") == []
    assert split_words(None) == []  # type: ignore[arg-type]


def test_weights_are_positive_and_one_per_word():
    weights = word_weights(SAMPLE)
    assert len(weights) == len(split_words(SAMPLE))
    assert all(weight > 0 for weight in weights)


def test_longer_words_weigh_more():
    short, long = word_weights("a extraordinary")
    assert long > short


def test_punctuation_adds_pause():
    plain, punctuated = word_weights("end end.")
    assert punctuated > plain


def test_cumulative_fractions_end_at_one():
    fractions = cumulative_fractions(word_weights(SAMPLE))
    assert fractions[-1] == 1.0
    assert fractions == sorted(fractions)


def test_cumulative_fractions_of_silence_is_empty():
    assert cumulative_fractions([]) == []
    assert cumulative_fractions([0.0, 0.0]) == []


def test_estimate_duration_grows_with_text():
    assert estimate_duration("") == 0.0
    assert estimate_duration(SAMPLE) > estimate_duration("She waited.")


def test_word_timings_cover_the_whole_duration():
    timings = word_timings(SAMPLE, duration=12.0)
    assert timings[0].start == 0.0
    assert timings[-1].end == 12.0
    for earlier, later in itertools.pairwise(timings):
        assert earlier.end <= later.start + 1e-9


def test_word_timings_serialise_for_the_client():
    payload = word_timings("Hello world", duration=2.0)[0].to_dict()
    assert payload.keys() == {"i", "w", "s", "e"}
    assert payload["w"] == "Hello"


def test_word_timings_without_duration_falls_back_to_estimate():
    timings = word_timings(SAMPLE)
    assert timings[-1].end == estimate_duration(SAMPLE)
