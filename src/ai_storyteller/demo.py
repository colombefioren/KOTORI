"""Canned stories so the studio can be experienced without any credentials.

A reviewer should be able to open the app, press *ignite* and see the whole
pipeline — streaming prose, synthesised voice, karaoke — before they ever
think about obtaining an API key. The sample stories are original prose that
end on the kind of cliffhanger the real writer is asked for.
"""

from __future__ import annotations

import hashlib
import random
from collections.abc import AsyncIterator

from .models import StoryRequest
from .story import StoryChunk

DEMO_MODEL = "demo reel"
DEMO_GENRE = "Demo"
DEMO_MOOD = "Written for you"

#: Words revealed per streamed frame while the demo writes itself.
DEMO_CHUNK_WORDS = 3
#: Seconds between demo frames, so the caret looks like a typing hand.
DEMO_FRAME_SECONDS = 0.05

_WRITING = "writing… (demo reel · add credentials for your own stories)"

DEMO_STORIES: tuple[str, ...] = (
    (
        "The lighthouse keeper had letters again. They arrived with the tide, "
        "sealed in wax the colour of old blood, addressed in her own hand. "
        "The first one asked her to keep the lamp lit on the sixteenth of "
        "March. The second apologised for something she had not done yet. "
        "She wrote back, because that is what you do with letters, and the "
        "reply came three days later with postage from a port that had been "
        "sunk in nineteen twelve. It was her handwriting. It was dated "
        "tomorrow. And it said, quite calmly, that the ship was not the thing "
        "that drowned — that the town had, and that she was the only one who "
        "had noticed. She read it twice, then walked to the lamp and put her "
        "hand on the cold brass switch, listening to the sea breathe like "
        "something waiting to be introduced. The letter had one more line "
        "underneath, smaller, written in pencil: don't."
    ),
    (
        "The last video rental store on the moon opened at eighteen hundred "
        "and closed when the owner felt like it. Customers came for the films "
        "and stayed for the smell of plastic, which nobody remembered but "
        "everybody missed. On a Tuesday a woman rented a title that had never "
        "been made, and the owner — who knew every spine in the shop — found "
        "the case in her hand, warm, already out of its sleeve. They watched "
        "it together on the back-room screen, and it was footage of that same "
        "room, filmed from the ceiling, hours before either of them arrived. "
        "The woman on the screen was crying. The woman in the chair was not, "
        "yet. When the credits rolled the tape rewinded itself, and the shop "
        "lights went out one aisle at a time, and somewhere behind the beaded "
        "curtain the till rang the way it only does for a sale."
    ),
    (
        "The tailor kept a ledger of every coat he had ever cut, and beside "
        "each measurement he wrote what the owner wanted to forget. The "
        "garments held it for them, which is why they never wore the collars "
        "out. Then a stranger came in with a memory so heavy the floorboards "
        "complained, and asked for a coat with no pockets at all, nothing to "
        "carry, nothing to keep. The tailor measured the man's shoulders, his "
        "sleeves, the strange hollow where a scar had been, and recognised "
        "the measurements from a page he had written forty years ago in his "
        "own handwriting. The stranger paid in coins from a country that no "
        "longer existed. As he left he turned, and said, gently, that the "
        "coat would fit perfectly, and that the tailor should not look at the "
        "label. It was already stitched in. The needle was still moving."
    ),
)


def pick_demo_story(topic: str | None = None, rng: random.Random | None = None) -> str:
    """Choose a sample story; the same topic always yields the same one."""
    if topic and topic.strip():
        digest = hashlib.sha256(topic.strip().lower().encode("utf-8")).digest()
        return DEMO_STORIES[digest[0] % len(DEMO_STORIES)]
    return (rng or random).choice(DEMO_STORIES)


async def demo_stream(request: StoryRequest) -> AsyncIterator[StoryChunk]:
    """Fake the streaming writer with real pacing and real prose."""
    import asyncio

    story = pick_demo_story(request.topic)
    words = story.split()

    yield StoryChunk(text="", delta="", note="warming the lamp… (demo)")

    for end in range(DEMO_CHUNK_WORDS, len(words), DEMO_CHUNK_WORDS):
        await asyncio.sleep(DEMO_FRAME_SECONDS)
        yield StoryChunk(text=" ".join(words[:end]), delta="", note=_WRITING)

    yield StoryChunk(text=story, delta="", note=_WRITING)
    yield StoryChunk(text=story, delta="", finished=True, note="closing the loop…")
