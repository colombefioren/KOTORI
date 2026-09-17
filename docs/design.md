# design notes

KOTORI is meant to look like something someone made by hand: a scrapbook of pastel
paper, washi tape, index cards and handwriting, with the story typed onto a torn page and
read aloud. This is why it looks the way it does, and what it deliberately avoids.

---

## the brief, in one line

> A place to write a small story that does not look like software.

Everything below is in service of that: the story is the object, the interface is the
desk it sits on.

---

## two pastels, honestly used

The palette is two pastel families on paper — nothing else. Each colour means one thing,
and that meaning holds on both desks.

| role | light | dark | means |
|:--|:--|:--|:--|
| desk | `#f2e8ee` | `#191725` | the surface things are pinned to |
| paper | `#fffdfa` | `#262233` | a sheet laid on the desk |
| cream | `#fdf9f0` | `#2a2636` | index-card stock |
| ink | `#443b48` | `#f4eff8` | prose and the interface |
| ink-2 / ink-3 | `#6f6573` / `#9d94a2` | `#c6bdd2` / `#8f87a3` | labels, and words not yet spoken |
| pink 300/400/500 | `#f2b3cd` / `#e288ae` / `#bd5f8b` | `#8d5c74` / `#e79cbe` / `#f4b6d2` | **here**: the margin rule, stamps, the primary action |
| blue 200/300/400 | `#d8e7fa` / `#b3d0f2` / `#82aae0` | `#2a3550` / `#5d7dae` / `#9dc0ee` | **said**: tape, the highlighter, focus, the play button |

Pink is *the moment I am in*; blue is *the part that has already been read*. That is the
whole colour system, and it is why nothing needs to glow to draw the eye.

**Both desks are pastel.** The dark theme is not "light theme inverted" — it is a plum-navy
night desk where the pastels are lifted in saturation so tape still reads as tape. The two
share one set of variable names, so a component written once is correct on both.

---

## type: five faces, five jobs

| face | job | why |
|:--|:--|:--|
| **Fraunces** | headlines, story titles | a bookish display serif with a wonky axis — it looks set, not generated |
| **EB Garamond** | prose | the story should read like print, not like a textarea |
| **Karla** | the interface | neutral, small, and never in the way |
| **Kalam** | margins, status line, empty states | the handwriting of whoever kept the scrapbook |
| **Special Elite** | labels, chips, stamps, the footer | a typewriter, for anything filed rather than written |

The handwriting face is the one that gives the studio its voice: *"the page is still
blank"*, *"stuck? press surprise me"*, *"every story is four hundred words"*. Software
usually explains itself in neutral sans; a scrapbook explains itself in pencil.

---

## craft, not skeuomorphism

The paper effects are all real geometry, never a texture pasted on top:

- **Torn edges.** The story sheet is clipped with a 36-point polygon, so its silhouette is
  ragged — and the shadow is a `drop-shadow` filter on the wrapper, so it follows the rag
  instead of a rectangle.
- **Washi tape.** A strip is a translucent block with a printed sheen and an irregular
  cut, rotated between −8° and 6°, in `multiply` so it darkens the paper beneath it. It
  lifts slightly when you hover the card it holds down.
- **Index cards.** Cream stock, a rose rule under the title, a punched index number in the
  corner, a rubber-stamped date laid on at an angle, and a player stitched below the
  excerpt with dashed seams.
- **A polaroid.** The bird the studio is named after, printed flat in two pastels, taped
  into a white frame with a handwritten caption. It sways when hovered, because a photo
  hanging by one piece of tape would.
- **Doodles.** Stars, hearts and arrows, drawn inline as SVG so they inherit the palette,
  pinned to the ends of rules where a person would have doodled while thinking.
- **The desk.** Linen, drawn with two thin repeating gradients, with a few small dried
  blotches where someone put a wet brush down. No large centred gradients anywhere.

---

## motion

Motion is either *informative* or *ambient*, and only one thing in the studio is ambient.

- **Informative.** The waiting page is ruled and the status dots hop while the writer
  thinks; words land on the page as they arrive; the pastel halo tracks the word currently
  being spoken because it *is* the reading position; the page scrolls to keep the reader's
  place.
- **Ambient.** The cursor trail — a faint ink wash of pink and blue behind the pointer. It
  has a keyboard off switch (`T`), a preference in `localStorage`, and never starts at all
  under `prefers-reduced-motion`.
- **Housekeeping.** Everything else is a 0.6s settle with a slight rotation, as if the piece
  of paper had just been laid down.

The reduced-motion query in `tokens.css` collapses all of it to near-zero, and the trail
script returns before it ever touches the canvas.

---

## accessibility

A scrapbook should still be a well-built page.

- A **skip link** first in the document, a `role="banner"` masthead, and a real
  `role="tablist"` with `role="tab"` children, `aria-selected`, roving `tabindex` and
  `aria-controls` pointing at the rooms. The panels get `role="tabpanel"` from the client
  the moment the shell mounts.
- **Keyboard first.** `1`/`2`/`3` move between rooms, `←`/`→` walk the tabs, `/` jumps to
  the brief, `⌘/Ctrl + Enter` writes, `space` plays, `←`/`→` seek five seconds, `?` opens
  the whole sheet, `Esc` closes overlays.
- **Every player is labelled** — the play button, the seek rail (a real slider with
  `aria-valuenow`), and the group that holds them — and every decorative layer
  (holes, tape, halo, doodles) is `aria-hidden`.
- **Announcements are rationed.** `aria-live="polite"` appears only on the live page and the
  waiting page, so a screen reader is told a story is arriving without being read the whole
  page on every frame.
- **No-script fallback.** The rooms are hidden by CSS; a `<noscript>` block shows all three
  stacked instead, so the content is never trapped behind a class change.
- **Contrast.** Body ink on paper is around 10:1 in both themes; the palest text token
  (`--ink-3`) is reserved for words not yet spoken and secondary labels.

---

## what is deliberately absent

- **No neon, no glow, no gradient chrome.** The only gradients are paper washes and the
  highlighter.
- **No uniform corner radius.** Corners are hand-set per component (4–12px, one edge
  different from the others), because four identical corners is the visual signature of a
  component library.
- **No framework tabs.** Gradio's tab widget could not be made to look like paper, so the
  tabs are ours: three buttons, three rooms, one `data-room` attribute.
- **No third font for the sake of it, and no icon set.** Any glyph the interface needs is a
  character — `▶ ↺ ↓ ⧉ ↗ ✎`.
- **No settings sprawl.** Length is not adjustable (every story is 400 words), and genre,
  mood and voice live in one collapsed drawer.

---

## how the tokens are organised

```
assets/styles/
├── tokens.css       the two desks, the pastels, the torn edge, the shadow scale
├── layout.css       the shell, the masthead, the index tabs, the three rooms, the footer
├── components.css   paper cards, tape, stamps, the sheet, the players, the index cards
└── animations.css   settling, the caret, the halo, the hopping dots
```

`tokens.css` is the only file that names a colour. `theme.py` mirrors the same values into
Gradio's own theme, so components that ship their own CSS (dropdowns, sliders, toasts)
still look like they belong on the desk.

`tests/test_styles.py` fails the build if a class the server renders has no rule in the
bundle — the mistake that is invisible in tests and obvious in a browser.
