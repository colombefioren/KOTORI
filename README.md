---
title: KOTORI
emoji: 🐦
colorFrom: pink
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
short_description: A pastel paper studio that writes a story and reads it aloud
---

<div align="center">

<img src="src/kotori/assets/images/kotori-mark.png" alt="KOTORI: a bird carrying a star" width="160" />

# KOTORI

**A pastel paper studio that writes you a story and reads it aloud.**

One line in. A four-hundred-word story out, typed onto the page word by word, then
spoken back while every word warms up in time with the voice.

![python](https://img.shields.io/badge/python-3.12%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![gradio](https://img.shields.io/badge/gradio-6-FF7C00?style=for-the-badge&logo=gradio&logoColor=white)
![langchain](https://img.shields.io/badge/langchain-1.4-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white)
![docker](https://img.shields.io/badge/docker-ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![uv](https://img.shields.io/badge/uv-managed-DE5FE9?style=for-the-badge&logo=uv&logoColor=white)
![tests](https://img.shields.io/badge/tests-198%20passing-2EA44F?style=for-the-badge&logo=pytest&logoColor=white)
![licence](https://img.shields.io/badge/licence-MIT-6f6573?style=for-the-badge)

</div>

---

## quickstart

```bash
git clone https://github.com/colombefioren/kotori && cd kotori
uv sync            # installs the studio and its dev tools
uv run kotori      # → http://127.0.0.1:7860
```

No key? Press **write the story** anyway. The studio ships demo reels, so the whole
experience works before you ever open `.env`. Add credentials whenever you like:

```ini
# .env — any OpenAI-compatible endpoint
MODEL_NAME=your-model
API_KEY=sk-…
BASE_URL=https://api.your-endpoint.com/v1
```

## the three rooms

| tab | what lives there |
|:--|:--|
| **home** | what KOTORI is, and how to use it |
| **playground** | the brief, the reader and the written story |
| **history** | every story ever kept, each with its own player |

Every story is four hundred words: long enough to have weather, short enough for a coffee.

## deploy it

```bash
docker compose up --build        # reads .env, mounts ./data
```

**Free:** push this repo to a [Hugging Face Space](https://huggingface.co/new-space) — the
front matter at the top of this file (`sdk: docker`, `app_port: 7860`) is all a Space needs
to build and run the Dockerfile as-is, on its free CPU tier, no card required. Add
`MODEL_NAME` / `API_KEY` / `BASE_URL` as Space secrets and it writes real stories instead of
demo reels.

Also ships `deploy.yml`, which publishes a released tag to `ghcr.io/colombefioren/kotori`,
so the same image runs on anywhere else that hosts a container and gives it a port.

## tests

```bash
uv run pytest                                   # fully offline
uv run pytest --cov=kotori --cov-fail-under=90  # what CI enforces
uv run ruff check src tests
```

More detail on the design system lives in [`docs/design.md`](docs/design.md).

---

<div align="center">
Written by <a href="https://github.com/colombefioren">colombefioren</a> · MIT licensed · see <a href="LICENSE">LICENSE</a>
</div>
