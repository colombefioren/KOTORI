---
title: AI Storyteller
emoji: "✦"
colorFrom: gray
colorTo: green
sdk: docker
app_port: 7860
pinned: false
short_description: Streamed stories that read themselves aloud
---

<div align="center">

# ✦ AI&nbsp;STORYTELLER

**Stories that speak** — a dark, editorial-grade story studio.
Type a seed, watch the prose arrive word by word, then let a synthesised voice
read it back while every word lights up in time with the audio.

[![ci](https://github.com/colombefioren/ai-storyteller/actions/workflows/ci.yml/badge.svg)](https://github.com/colombefioren/ai-storyteller/actions/workflows/ci.yml)
![python](https://img.shields.io/badge/python-3.12%2B-07070c?style=flat-square&labelColor=07070c)
![gradio](https://img.shields.io/badge/gradio-6-96f7d2?style=flat-square&labelColor=07070c)
![tests](https://img.shields.io/badge/tests-150-cbb8ff?style=flat-square&labelColor=07070c)
![coverage](https://img.shields.io/badge/coverage-95%25-96f7d2?style=flat-square&labelColor=07070c)
![license](https://img.shields.io/badge/license-MIT-ffb2cb?style=flat-square&labelColor=07070c)

<a href="docs/preview.svg"><img src="docs/preview.svg" alt="AI Storyteller: streaming prose with the spoken word glowing in mint" width="100%" /></a>

<sub>↑ drawn from the real markup and palette — the live thing streams, scrolls and glows.</sub>

</div>

---

## Contents

- [The thirty-second version](#the-thirty-second-version)
- [What is actually in here](#what-is-actually-in-here)
- [How the karaoke works](#how-the-karaoke-works)
- [Run it locally](#run-it-locally)
- [The design system](#the-design-system)
- [Architecture](#architecture)
- [Keyboard](#keyboard)
- [Deploy it](#deploy-it)
- [Tests, lint and CI](#tests-lint-and-ci)
- [Notes on taste](#notes-on-taste)
- [Roadmap](#roadmap)
- [Credits](#credits)

---

## The thirty-second version

```bash
git clone https://github.com/colombefioren/ai-storyteller && cd ai-storyteller
uv sync          # installs the studio itself
uv run ai-storyteller
# → http://127.0.0.1:7860
```

No key? **Just press *ignite*.** The studio ships three original demo reels, so the
full pipeline — streaming prose, synthesised voice, karaoke, archive, exports —
works before you have ever opened `.env`. Add credentials later and the same button
writes something nobody has read before.

```ini
# .env
MODEL_NAME=deepseek-v4-pro                    # or gpt-4o-mini, llama-3.3-70b, …
API_KEY=sk-…                                  # any OpenAI-compatible endpoint
BASE_URL=https://api.your-endpoint.com/v1
```

---

## What is actually in here

| | |
|:---|:---|
| **Live teleprompter** | Tokens stream into the stage as the writer thinks; a neon caret marks the exact word being written and the paper scrolls itself. |
| **Karaoke playback** | The mp3 drives word highlighting — spoken words stay lit, the current word glows, the ones ahead wait in the dark. |
| **Trailing halo** | A pastel glow chases the spoken word down the page (`requestAnimationFrame`, not a CSS toy). |
| **Cursor trail** | A canvas ribbon of pastel neon follows the pointer across the studio, toggled with `T`. |
| **Editorial voice** | Serif reading face, mono micro-labels, 6px hard shadows, 2px corners — brutalism on a soft palette. |
| **One dark theme** | Light *and* dark slots hold the same values on purpose: the design cannot be broken by an OS preference. |
| **Twelve voices** | gTTS presets across eight languages and accents, from `Aurora (US)` to `Nori (JP)`. |
| **Ten genres × eight moods** | Every register carries a note that steers the brief ("neon rain, rented bodies, debt"). |
| **Client-side exports** | Markdown, plain text, mp3 and share links are built in the browser — no extra round-trips. |
| **A real archive** | Drafts land in an append-only JSONL shelf you can preview, reopen, re-voice, delete or burn. |
| **Command palette** | `⌘/Ctrl + K`, `/` to focus the seed, `space` to play, `?` for the full sheet. |
| **Reduced motion aware** | `prefers-reduced-motion` turns off the trail, the halo and every reveal. |
| **Deployable as-is** | Dockerfile, compose file, Render blueprint and Spaces front matter included. |

<details>
<summary><b>The eight seats in the studio</b></summary>

| # | seat | what it does |
|:--|:--|:--|
| 01 | **the seed** | your topic, or one of sixteen hand-written prompts |
| 02 | **genre × mood** | ten registers, eight atmospheres, rendered as pastel chips |
| 03 | **length** | 120–500 words, with a floor the writer is explicitly told to respect |
| 04 | **voice** | twelve gTTS presets, plus a "speak slowly" switch |
| 05 | **the stage** | streaming prose on editorial paper, with meta chips |
| 06 | **the deck** | custom player, karaoke rail, exports, share link |
| 07 | **the shelf** | the JSONL archive: preview, reopen, re-voice, delete, burn |
| 08 | **the shell** | palette, shortcuts, toasts, restored share links, cursor trail |

</details>

---

## How the karaoke works

No forced-alignment model, no second API call — the timing engine is about sixty
lines and fully unit-tested.

```text
prose ──▶ word weights ──▶ data-w on every <span> ──▶ cumulative fractions
   timing.py                    markup.py                    trail/teleprompter
                                                                  │
   mp3 duration ───────────────────────────────────────────────────┤
                                                                  ▼
                                 currentTime ÷ duration ──▶ word index
                                                                  │
                                ┌─────────────────────────────────┴──────────┐
                                ▼               ▼                            ▼
                          words behind     current word                 words ahead
                          stay lit         glows + halo                 wait in the dark
```

Weight = a base + the word's length + a pause for its trailing punctuation, so
`debt.` really does take longer than `as`. Because the browser divides by the
audio's true `duration`, an accent, a slow-read switch or a different voice all
stay in sync without a single server round-trip after the audio exists.

<details>
<summary><b>The client contract</b> (four scripts, no build step)</summary>

| script | owns |
|:--|:--|
| `trail.js` | the shared `ASTBus` DOM bus, forced dark mode, the cursor canvas |
| `teleprompter.js` | word timing, the halo, play/pause, the seek rail, auto-scroll |
| `deck.js` | copy, `.md`/`.txt`/`.mp3` downloads, share links, the story codec |
| `shell.js` | toasts, command palette, shortcuts sheet, `#s=` link restore |

`ASTBus` is a `MutationObserver` plus one `requestAnimationFrame` flush, so a
script re-binds its own nodes whenever Gradio swaps component HTML — no hacks,
no polling, and nothing binds twice.

</details>

---

## Run it locally

```bash
uv sync                 # uv installs the project (and dev tools) into .venv
cp .env.example .env    # then edit MODEL_NAME / API_KEY / BASE_URL
uv run ai-storyteller   # same as: uv run python app.py  ·  uv run python -m ai_storyteller
```

### Configuration

| variable | default | purpose |
|:--|:--|:--|
| `MODEL_NAME` | `gpt-4o-mini` | any chat model your endpoint serves |
| `API_KEY` | — | required for real writers (`OPENAI_API_KEY` also read) |
| `BASE_URL` | OpenAI | Groq · OpenRouter · Together · Ollama · vLLM · LM Studio … |
| `TEMPERATURE` | `0.9` | the writer's temperature |
| `MAX_TOKENS` | `900` | hard ceiling per story |
| `REQUEST_TIMEOUT` | `60` | seconds before a write is abandoned |
| `AI_STORYTELLER_DATA_DIR` | `./data` | archive + rendered mp3s (falls back to a temp dir if read-only) |
| `FORCE_DARK` | `1` | the studio ships dark-first |
| `PORT` / `GRADIO_SERVER_PORT` | `7860` | server port (`PORT` wins — that is what hosts inject) |
| `GRADIO_SERVER_NAME` | `0.0.0.0` | bind address |

---

## The design system

<div align="center">

![void](https://img.shields.io/badge/-07070c-07070c?style=flat-square)&nbsp;![ink](https://img.shields.io/badge/-0b0b13-0b0b13?style=flat-square)&nbsp;![panel](https://img.shields.io/badge/-101021-101021?style=flat-square)&nbsp;![line](https://img.shields.io/badge/-2a2a48-2a2a48?style=flat-square)&nbsp;![mist](https://img.shields.io/badge/-b6b3d8-b6b3d8?style=flat-square)&nbsp;![chalk](https://img.shields.io/badge/-f5f4ff-f5f4ff?style=flat-square)&nbsp;![mint](https://img.shields.io/badge/-96f7d2-96f7d2?style=flat-square)&nbsp;![lilac](https://img.shields.io/badge/-cbb8ff-cbb8ff?style=flat-square)&nbsp;![blush](https://img.shields.io/badge/-ffb2cb-ffb2cb?style=flat-square)&nbsp;![butter](https://img.shields.io/badge/-ffe8a3-ffe8a3?style=flat-square)&nbsp;![sky](https://img.shields.io/badge/-a6d8ff-a6d8ff?style=flat-square)

</div>

| token | value | used for |
|:--|:--|:--|
| `--ast-void` | `#07070c` | page canvas, paper |
| `--ast-panel` | `#101021` | panels, cards, ticker |
| `--ast-mint` | `#96f7d2` | primary action, the current word |
| `--ast-lilac` | `#cbb8ff` | secondary accent, focus, chips |
| `--ast-blush` | `#ffb2cb` | destructive, warnings, voice chips |
| `--ast-butter` | `#ffe8a3` | playful highlights, demo mode lamp |
| `--ast-sky` | `#a6d8ff` | engine and model chips |
| type | Space Grotesk · JetBrains Mono · Instrument Serif | interface · labels · prose |
| geometry | 2px radius · 2px borders · 6px hard shadows | the brutalism |

Everything lives in `assets/styles/tokens.css`; `theme.py` mirrors the same palette
into Gradio's theme so components that ship their own CSS still match. The stylesheet
is split into **tokens → layout → components → animations** so a change of mood means
editing one file, not hunting through a thousand lines.

<p align="center">
  <img src="docs/preview.svg" alt="the same palette applied to the studio" width="620" />
</p>

---

## Architecture

```text
src/ai_storyteller/
├── config.py       env → Settings (aliases, coercion, writable-dir fallback)
├── llm.py          ChatOpenAI factory for any OpenAI-compatible endpoint
├── prompts.py      genres, moods, the brief, prose cleanup
├── story.py        streaming writer (frames are paced, not dumped)
├── demo.py         three original reels so the studio opens without a key
├── speech.py       voice presets, gTTS synthesis, data-URI delivery
├── timing.py       word weights → the karaoke timeline
├── library.py      append-only JSONL archive + stats
├── models.py       StoryRequest / StoryDraft + reading-time maths
├── markup.py       HTML for hero, stage, deck, archive, footer
├── studio.py       controller: write → voice → archive
├── callbacks.py    every button's handler, Gradio-free enough to unit-test
└── ui.py           Blocks layout + event wiring
├── theme.py        Gradio theme mirroring the CSS tokens
├── frontend.py     css / js / head bundle loader
├── ui.py           Blocks layout + event wiring
├── app.py          launch(): theme, css, js, favicon, port
└── assets/
    ├── styles/     tokens · layout · components · animations   (4 files, ~1.1k lines)
    ├── scripts/    trail · teleprompter · deck · shell         (4 files, ~1.1k lines)
    └── favicon.svg
```

**Why the split?** `studio.py` returns plain HTML strings and dataclasses and
`callbacks.py` holds every button's handler, so the whole product can be driven from
tests, a notebook or a CLI with **Gradio nowhere near the logic**. `ui.py` stays a thin
skin of components and events over that controller — which is why 150 tests run
offline in under eight seconds at 95% coverage.

---

## Keyboard

| key | action | | key | action |
|:--|:--|:--|:--|:--|
| `⌘/Ctrl + K` | command palette | | `A` | jump to the archive |
| `/` | focus the seed field | | `P` | open a shared story |
| `⌘/Ctrl + Enter` | ignite a story | | `T` | toggle the cursor trail |
| `space` | play / pause the voice | | `?` | shortcut sheet |
| `←` `→` | scrub five seconds | | `Esc` | close overlays |

---

## Deploy it

Anything that runs a container and gives you a public port will host this untouched.
The image is a single Python 3.12 stage, runs as an unprivileged user, declares a
`HEALTHCHECK`, and writes its archive to `AI_STORYTELLER_DATA_DIR` (default `/data`).

| path | best for | how |
|:--|:--|:--|
| **Hugging Face Spaces** | free public demo | front matter here already says `sdk: docker` + `app_port: 7860`; add the three secrets, attach storage for `/data` |
| **Render** | blueprint + disk | `render.yaml` describes a Docker service with a 1 GB disk at `/var/data` → *New → Blueprint* |
| **Docker anywhere** | VPS, homelab, CI | `docker build -t ai-storyteller .` then run with `-v storyteller-data:/data` |
| **Fly.io / Cloud Run / Koyeb** | managed containers | point them at the Dockerfile, create a volume for `/data` |

```bash
# the whole thing, locally, in a container
docker compose up --build        # reads .env, mounts ./data
```

<details>
<summary><b>Space secrets</b></summary>

| secret | example |
|:--|:--|
| `MODEL_NAME` | `gpt-4o-mini` |
| `API_KEY` | `sk-…` |
| `BASE_URL` | `https://api.openai.com/v1` |

> Serverless and edge platforms are a poor fit: this is a long-running server with
> WebSocket streaming and a writable disk, not a request/response function.
</details>

---

## Tests, lint and CI

```bash
uv run pytest                       # 150 tests, fully offline, ~7 s
uv run ruff check src tests         # E F I UP B SIM C4 RUF
uv run ruff format --check src tests

# what CI runs on top of that
uv run pytest -q --cov=ai_storyteller \
  --cov-report=term-missing:skip-covered --cov-fail-under=90
```

The network is never touched: the writer is faked, speech synthesis is monkeypatched,
and the app is assembled without ever being launched. Eleven modules cover env parsing,
the chat factory, prose cleanup, word timing, the archive, the HTML renderers, the
domain model, the studio pipeline, every interface callback, the demo reels,
accessibility landmarks and the assembled app.

### Continuous integration and delivery

| workflow | trigger | what it does |
|:--|:--|:--|
| [`ci.yml`](.github/workflows/ci.yml) | every push and PR | lint → format check → tests with a **90% coverage floor** → docker build |
| [`deploy.yml`](.github/workflows/deploy.yml) | `v*` tags or manual | publishes a **multi-arch image to GHCR** (`linux/amd64`, `linux/arm64`) and, if the `HF_SPACE` repository variable is set, mirrors the commit to a Space |

```bash
# a released image, ready to run
docker run -p 7860:7860 -v storyteller-data:/data \
  -e MODEL_NAME=gpt-4o-mini -e API_KEY=sk-… \
  ghcr.io/colombefioren/ai-storyteller:latest
```

To enable the Space mirror: add a repository **variable** `HF_SPACE` (`user/space-name`)
and a secret `HF_TOKEN` with write access. Skip both and the job simply does not run.

---

## Notes on taste

- **The theme is one theme.** Light/dark slots hold identical values, so an OS
  preference can never produce the half-styled app that usually ships.
- **One accent per moment.** Mint means *act* or *here*; lilac is structure; blush is
  danger; butter is play. Nothing decorative borrows a semantic colour.
- **Motion earns its place.** The halo tracks the spoken word because it *is* the
  reading position; the cursor trail is the only purely ambient effect and it has an
  off switch (`T`), a preference in `localStorage`, and respect for reduced motion.
- **Template safety.** Every user- and model-authored string goes through
  `html.escape` in `markup.py`; prose cannot inject markup into the stage.
- **Nothing is hidden from the keyboard.** Skip link, landmarks, labelled player
  controls, `aria-live` only on the *live* paper.

---

## Roadmap

- Real forced alignment (Whisper timestamps) for per-word accuracy.
- A "keep going" loop that extends a draft without losing the thread.
- Optional SQLite/Redis store so several replicas can share one shelf.
- Export a bundle (text + audio) or a printable broadsheet PDF.

---

## Credits

Written by **[colombefioren](https://github.com/colombefioren)**. Voices come from
Google Translate's TTS endpoint via [gTTS](https://github.com/pndurette/gTTS); the
interface is [Gradio 6](https://www.gradio.app) wearing a hand-cut stylesheet; the
prose is whatever your model dreams up at `temperature=0.9`.

**MIT** — see [LICENSE](LICENSE). Take it, restyle it, ship it.

<div align="center"><sub>✦ drafts are yours, keys are yours, nothing is tracked ✦</sub></div>
