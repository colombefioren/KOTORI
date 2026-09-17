---
title: AI Storyteller
emoji: "✦"
colorFrom: pink
colorTo: green
sdk: docker
app_port: 7860
pinned: false
short_description: Streamed stories that read themselves aloud
---

<div align="center">

# ✦ AI&nbsp;STORYTELLER

**Stories that speak** — a pastel, editorial-grade story studio that feels like a
scratchbook. Type a seed, watch the prose arrive word by word, then let a
synthesised voice read it back while every word warms up in time with the audio.

[![ci](https://github.com/colombefioren/ai-storyteller/actions/workflows/ci.yml/badge.svg)](https://github.com/colombefioren/ai-storyteller/actions/workflows/ci.yml)
![python](https://img.shields.io/badge/python-3.12%2B-a795e0?style=flat-square&labelColor=f7f1e7)
![gradio](https://img.shields.io/badge/gradio-6-7cb79b?style=flat-square&labelColor=f7f1e7)
![tests](https://img.shields.io/badge/tests-170-d98ea2?style=flat-square&labelColor=f7f1e7)
![coverage](https://img.shields.io/badge/coverage-96%25-d8b96b?style=flat-square&labelColor=f7f1e7)
![license](https://img.shields.io/badge/license-MIT-7a6d58?style=flat-square&labelColor=f7f1e7)

<a href="docs/preview.svg"><img src="docs/preview.svg" alt="AI Storyteller: a paper page with streaming prose, the spoken word highlighted, and a rounded player" width="100%" /></a>

<sub>↑ drawn from the live markup and palette — the real thing streams word by word, then reads itself aloud.</sub>

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

No key? **Just press *write the story*.** The studio ships three original demo reels, so the
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
| **A loading state, always** | The button answers the moment it is pressed: a ruled page and a blinking cursor appear before the model's first token, and the button locks itself while the writer works. |
| **Live teleprompter** | Tokens arrive word by word on squared paper; a lavender caret marks where the writer is looking and the page scrolls itself. |
| **Karaoke playback** | The mp3 drives word highlighting — spoken words stay ink, the current word sits on a butter highlight, the ones ahead wait, faint. |
| **Trailing halo** | A soft pastel light chases the spoken word down the page (`requestAnimationFrame`, not a CSS toy). |
| **One player per story** | Every deck carries its own `<audio>` and points at its own page, so a shelf full of stories can never play the wrong voice. |
| **A shelf you can listen to** | Pick a story and it opens with its own player, its own recording and its own karaoke — a voice is only synthesised when it is missing. |
| **Cursor trail** | A canvas ribbon of pastel ink follows the pointer, toggled with `T` and remembered in `localStorage`. |
| **Paper, not neon** | Warm paper, 18px radii, soft shadows, a ruled margin: Lora for prose, Fraunces for headlines, Karla for the interface, Caveat for the margins. |
| **One theme** | Light *and* dark slots hold the same values on purpose: the design cannot be broken by an OS preference. |
| **Twelve voices** | gTTS presets across eight languages and accents, from `Aurora (US)` to `Nori (JP)`. |
| **Ten genres × eight moods** | Every register carries a note that steers the brief ("neon rain, rented bodies, debt"). |
| **Client-side exports** | Markdown, mp3 and share links are built in the browser — no extra round-trips. |
| **A real archive** | Drafts land in an append-only JSONL shelf you can read, re-record, delete or clear. |
| **Command palette** | `⌘/Ctrl + K`, `/` to jump to the topic, `S` for the shelf, `space` to play, `?` for the full sheet. |
| **Reduced motion aware** | `prefers-reduced-motion` turns off the trail, the halo and every reveal. |
| **Deployable as-is** | Dockerfile, compose file, Render blueprint and Spaces front matter included. |

<details>
<summary><b>The four rooms of the studio</b></summary>

| # | room | what it holds |
|:--|:--|:--|
| 01 | **the composer** | your topic (or a rolled seed), and one quiet drawer with genre · mood · voice · length |
| 02 | **the page** | the story as it arrives, with meta chips: words, reading time, genre, mood, voice |
| 03 | **the player** | one round play button, a seek rule, and four extras: from the top · save the mp3 · copy the words · share a link |
| 04 | **the shelf** | every story kept, each with its own player; delete, re-record or clear from one drawer |

</details>

<details>
<summary><b>The three buttons that used to be eight</b></summary>

The old build had *ignite story*, *surprise me*, *stop*, *open in stage*, *speak it again*,
*refresh*, *delete draft* and *burn the archive*. Now the shelf is a reading pane with a
player inside it, so listening to an old story needs no button at all — and the only
remaining controls say exactly what they do.

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
                          stay ink         butter highlight + halo      wait, faint
```

Weight = a base + the word's length + a pause for its trailing punctuation, so
`debt.` really does take longer than `as`. Because the browser divides by the
audio's true `duration`, an accent, a slow-read switch or a different voice all
stay in sync without a single server round-trip after the audio exists.

<details>
<summary><b>The client contract</b> (four scripts, no build step)</summary>

| script | owns |
|:--|:--|
| `trail.js` | the shared `ASTBus` DOM bus, forced light mode, the cursor canvas |
| `teleprompter.js` | one player per deck: word timing, the halo, play/pause, the seek rail, auto-scroll |
| `deck.js` | copy, `.md`/`.mp3` saves and share links, scoped to the deck the button lives in |
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
| `FORCE_LIGHT` | `1` | the studio is paper-first (set `0` to let Gradio theme itself) |
| `PORT` / `GRADIO_SERVER_PORT` | `7860` | server port (`PORT` wins — that is what hosts inject) |
| `GRADIO_SERVER_NAME` | `0.0.0.0` | bind address |

---

## The design system

<div align="center">

![paper](https://img.shields.io/badge/-f7f1e7-f7f1e7?style=flat-square)&nbsp;![card](https://img.shields.io/badge/-fffdf8-fffdf8?style=flat-square)&nbsp;![sunk](https://img.shields.io/badge/-fdf8f0-fdf8f0?style=flat-square)&nbsp;![line](https://img.shields.io/badge/-ecdfca-ecdfca?style=flat-square)&nbsp;![ink](https://img.shields.io/badge/-4b3f2f-4b3f2f?style=flat-square)&nbsp;![soft](https://img.shields.io/badge/-7c6c57-7c6c57?style=flat-square)&nbsp;![faint](https://img.shields.io/badge/-a79579-a79579?style=flat-square)&nbsp;![sage](https://img.shields.io/badge/-b7ddc8-b7ddc8?style=flat-square)&nbsp;![lavender](https://img.shields.io/badge/-d6cbf4-d6cbf4?style=flat-square)&nbsp;![rose](https://img.shields.io/badge/-f3c1cc-f3c1cc?style=flat-square)&nbsp;![butter](https://img.shields.io/badge/-f8e6b2-f8e6b2?style=flat-square)&nbsp;![sky](https://img.shields.io/badge/-c5ddf2-c5ddf2?style=flat-square)

</div>

| token | value | used for |
|:--|:--|:--|
| `--paper` | `#f7f1e7` | the page itself, under pastel washes and a dot grid |
| `--card` / `--card-sunk` | `#fffdf8` / `#fdf8f0` | cards · inputs and the squared paper |
| `--ink` / `--ink-soft` / `--ink-faint` | `#4b3f2f` / `#7c6c57` / `#a79579` | prose and interface · labels · words not yet spoken |
| `--lavender` / `--lavender-deep` | `#d6cbf4` / `#a795e0` | the primary action, the caret, focus rings |
| `--sage-deep` | `#7cb79b` | the ready lamp, "words" chip |
| `--rose-deep` | `#d98ea2` | the margin rule, destructive actions, errors |
| `--butter` / `--butter-deep` | `#f8e6b2` / `#d8b96b` | the word being spoken · the demo lamp |
| `--sky-deep` | `#8ab3d6` | engine and model chips |
| type | Fraunces · Lora · Karla · Caveat | headlines · prose · interface · margin notes |
| geometry | 18px cards · 999px pills · soft shadows · 1px hairlines | the scratchbook |

Everything lives in `assets/styles/tokens.css`; `theme.py` mirrors the same palette
into Gradio's theme so components that ship their own CSS still match. The stylesheet
is split into **tokens → layout → components → animations** so a change of mood means
editing one file, not hunting through a thousand lines. The four typefaces are
requested once, in the document head, from Google Fonts.

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
├── markup.py       HTML for the hero, the page, the player, the shelf, footer
├── studio.py       controller: write → voice → archive (cached recordings)
├── callbacks.py    every button's handler, Gradio-free enough to unit-test
├── theme.py        Gradio theme mirroring the CSS tokens
├── frontend.py     css / js / head bundle loader
├── ui.py           Blocks layout + event wiring
├── app.py          launch(): theme, css, js, favicon, port
└── assets/
    ├── styles/     tokens · layout · components · animations   (4 files, ~1.2k lines)
    ├── scripts/    trail · teleprompter · deck · shell         (4 files, ~1.1k lines)
    └── favicon.svg
```

**Why the split?** `studio.py` returns plain HTML strings and dataclasses and
`callbacks.py` holds every button's handler, so the whole product can be driven from
tests, a notebook or a CLI with **Gradio nowhere near the logic**. `ui.py` stays a thin
skin of components and events over that controller — which is why 170 tests run
offline in about eight seconds at 96% coverage.

---

## Keyboard

| key | action | | key | action |
|:--|:--|:--|:--|:--|
| `⌘/Ctrl + K` | command palette | | `S` | scroll to your shelf |
| `/` | jump to the topic field | | `P` | open a shared story |
| `⌘/Ctrl + Enter` | write the story | | `T` | toggle the cursor trail |
| `space` | play / pause the voice | | `?` | shortcut sheet |
| `←` `→` | skip five seconds | | `Esc` | close overlays |

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
uv run pytest                       # 170 tests, fully offline, ~7 s
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

- **Paper, not dashboards.** The interface is a page you write on: one column of
  reading, rounded corners, hairline rules and a margin in rose. Pastels do the
  pointing, so nothing has to shout — no neon, no glow, no hard offsets.
- **The theme is one theme.** Light/dark slots hold identical values, so an OS
  preference can never produce the half-styled app that usually ships.
- **One accent per moment.** Lavender means *act*; sage means *ready*; butter is the
  word being spoken; rose is the margin and anything destructive.
- **Loading is part of the design.** Pressing the button paints a ruled page and a
  waiting cursor immediately — the writer is never a silent freeze — and the button is
  handed back by the last frame, or by *stop*.
- **One player per story.** Each deck owns its audio, its page and its own exports, and
  the recording on disk is reused, so "listen to that one again" is instant and correct.
- **Motion earns its place.** The halo tracks the spoken word because it *is* the
  reading position; the cursor trail is the only purely ambient effect and it has an
  off switch (`T`), a preference in `localStorage`, and respect for reduced motion.
- **Template safety.** Every user- and model-authored string goes through
  `html.escape` in `markup.py`; prose cannot inject markup into the page.
- **Nothing is hidden from the keyboard.** Skip link, landmarks, labelled player
  controls, `aria-live` only on the *live* page and the waiting page.

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
