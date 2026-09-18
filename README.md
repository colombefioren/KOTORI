<div align="center">

<img src="src/kotori/assets/images/kotori-mark.png" alt="kotori: a bird carrying a star" width="160" />

# KOTORI

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

## What KOTORI is

give it one line, a place, a person, a problem, and kotori writes a full story around
it: four hundred words, typed onto the page one word at a time. a voice then reads it
back, and every word lights up on the page in time with the voice, like a karaoke
lyric you can pause, skip, or scrub.

no signup or key required: the studio ships demo reels, so writing, streaming and
narration all work immediately. add a model endpoint later and the same button writes
something new, in any of ten genres and eight moods, read by one of twelve voices
across nine languages.

the interface looks like a scrapbook left open on a desk, not a software dashboard:
torn paper, washi tape, index cards, a polaroid, and margin doodles, where pink marks
what you gave it and blue marks what it wrote back. kotori is the japanese word for a
small bird, the one taped above, carrying a star.

every story you keep is filed away with its own recording, ready to reopen, replay, or
export as text or mp3.

## Quickstart

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

## The three rooms

| tab | what lives there |
|:--|:--|
| **home** | what kotori is, and how to use it |
| **playground** | the brief, the reader and the written story |
| **history** | every story ever kept, each with its own player |

## Tests

```bash
uv run pytest                                   # fully offline
uv run pytest --cov=kotori --cov-fail-under=90  # what CI enforces
uv run ruff check src tests
```
