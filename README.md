---
title: AI Storyteller
emoji: ✦
colorFrom: gray
colorTo: green
sdk: docker
app_port: 7860
pinned: false
short_description: Streamed stories that read themselves aloud
---

# ✦ AI Storyteller

**Stories that speak.** A dark, editorial-grade story studio: type a seed, watch the
prose arrive word by word, then let a synthesised voice read it back while every word
lights up in time with the audio.

Built with **Gradio 6**, **LangChain** and **gTTS** — no database, no accounts, no tracking.

[![ci](https://github.com/colombefioren/ai-storyteller/actions/workflows/ci.yml/badge.svg)](https://github.com/colombefioren/ai-storyteller/actions/workflows/ci.yml)
![python](https://img.shields.io/badge/python-3.12%2B-96f7d2?style=flat-square)
![gradio](https://img.shields.io/badge/gradio-6-cbb8ff?style=flat-square)
![license](https://img.shields.io/badge/license-MIT-ffb2cb?style=flat-square)

<!-- Replace the line below with a screenshot or a short screen recording. -->
> 🖼️ _Add `docs/screenshot.png` here — a still of the stage mid-playback sells this the fastest._

---

## What makes it feel alive

| | |
|---|---|
| **Live teleprompter** | Tokens stream into the stage as the model writes; a neon caret marks the exact word being written. |
| **Karaoke playback** | The mp3 drives word highlighting: spoken words stay lit, the current word glows, the ones ahead wait in the dark. |
| **Trailing halo** | A pastel glow chases the spoken word down the page and the paper scrolls itself. |
| **Cursor trail** | A canvas trail of pastel neon follows the pointer across the whole studio. |
| **Editorial voice** | A serif reading face, mono micro-labels, hard 6px shadows, sharp 2px corners — brutalism with a soft palette. |
| **One dark theme** | Light and dark slots are identical on purpose: the design cannot be broken by an OS preference. |
| **Client-side exports** | Markdown, plain text, mp3 and share links are generated in the browser — no extra round-trips. |
| **A real archive** | Finished drafts land in an append-only JSONL shelf you can browse, reopen and re-voice. |
| **Keyboard first** | `⌘K` palette, `/` to focus the seed, `space` to play, `?` for the full sheet. |
| **Deployable** | Multi-stage-free Dockerfile, Render blueprint, compose file and Spaces front matter included. |

### The eight seats in the studio

1. **the seed** — your topic, or roll one of sixteen hand-written prompts
2. **genre × mood** — ten registers, eight atmospheres, rendered as pastel chips
3. **length** — 120–500 words, with a floor the writer is told to respect
4. **voice** — twelve gTTS presets across eight languages and accents
5. **the stage** — streaming prose on editorial paper
6. **the deck** — custom player, karaoke rail, exports and share link
7. **the shelf** — the JSONL archive with preview, re-voice, delete, burn
8. **the shell** — command palette, shortcuts, toasts, restored share links
