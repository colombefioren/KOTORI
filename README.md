<div align="center">

<img src="src/kotori/assets/images/kotori-mark.png" alt="kotori: a bird carrying a star" width="160" />

# Kotori

**a pastel paper studio that writes you a story and reads it aloud.**

![python](https://img.shields.io/badge/python-3.12%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![gradio](https://img.shields.io/badge/gradio-6-FF7C00?style=for-the-badge&logo=gradio&logoColor=white)
![langchain](https://img.shields.io/badge/langchain-1.4-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white)
![docker](https://img.shields.io/badge/docker-ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![uv](https://img.shields.io/badge/uv-managed-DE5FE9?style=for-the-badge&logo=uv&logoColor=white)
![tests](https://img.shields.io/badge/tests-199%20passing-2EA44F?style=for-the-badge&logo=pytest&logoColor=white)
![licence](https://img.shields.io/badge/licence-MIT-6f6573?style=for-the-badge)

</div>

---

## what kotori is

give it one line, a place, a person, a problem, and kotori writes a full story around
it: four hundred words, typed onto the page one word at a time, as if someone were
writing it live in front of you. pick a genre and a mood first if you want to steer it,
or leave both alone and let the studio choose.

once the story lands, a voice reads it back. every word it speaks lights up on the page
in time with the voice, so you can follow along the way you'd follow a karaoke lyric,
and pause, skip, or scrub the recording like any other player.

there's no signup and no key required to try it: the studio ships a set of demo reels,
so writing, streaming and narration all work the moment you open it. add a model
endpoint and a key later and the same button writes something nobody has read before,
in any of ten genres and eight moods, read by one of twelve voices across nine
languages.

the interface is drawn to look like a scrapbook left open on a desk rather than a
software dashboard: torn paper edges, washi tape, index cards, a polaroid, and margin
doodles, all built as real shapes and gradients rather than a texture pasted over a
grid. pink marks what you gave it, blue marks what it wrote back, and the two colours
never swap meaning anywhere in the app. more on the paper-craft and the type system
lives in [`docs/design.md`](docs/design.md).

kotori is the japanese word for a small bird; the one taped above, carrying a star, is
who the studio is named after and who keeps an eye on the page while you write.

every story you keep gets filed away with its own recording, so a shelf full of past
work never leaks one voice into another, and anything on it can be reopened, replayed,
or exported as text or mp3 whenever you like.

## quickstart

```bash
git clone https://github.com/colombefioren/kotori && cd kotori
uv sync            # installs the studio and its dev tools
uv run kotori      # → http://127.0.0.1:7860
```

no key? press **write the story** anyway. the studio ships demo reels, so the whole
experience works before you ever open `.env`. add credentials whenever you like:

```ini
# .env — any OpenAI-compatible endpoint
MODEL_NAME=your-model
API_KEY=sk-…
BASE_URL=https://api.your-endpoint.com/v1
```

## the three rooms

| tab | what lives there |
|:--|:--|
| **home** | what kotori is, and how to use it |
| **playground** | the brief, the reader and the written story |
| **history** | every story ever kept, each with its own player |

## tests

```bash
uv run pytest                                   # fully offline
uv run pytest --cov=kotori --cov-fail-under=90  # what CI enforces
uv run ruff check src tests
```
