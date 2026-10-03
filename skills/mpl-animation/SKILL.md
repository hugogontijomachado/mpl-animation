---
name: mpl-animation
description: Build animated explainer videos with matplotlib - scenes made of steps, each step ending in a pause, rendered to MP4 (default) or GIF and then cut into clips at the pauses (one clip per slide, optionally a ready PowerPoint deck), so a presenter can talk between movements. Use it whenever someone wants to animate something with Python or matplotlib - a concept, a scientific process, an algorithm, real data, a paper figure - for a talk, class, thesis defense, video, website or README, even if they only say "make an animation/video/GIF of X", "anima isso", "faz um vídeo mostrando", "animação para a apresentação" or "trechos com pausas". Also use it to change, re-time, re-cut or make a new version of an existing matplotlib animation. Not for static figures or interactive dashboards.
---

# Stepwise matplotlib animations

matplotlib makes polished explainer videos when every frame is drawn from scratch as a function of time. This
skill bundles a small engine for that (`scripts/anim.py`), a cutter (`scripts/cut.py`), a complete template
(`scripts/example.py`), and the way of working that makes the videos good to present: build in steps, pause
after every step, cut at the pauses.

## The rule: build in steps, then cut into clips

Every animation is a list of scenes, and every scene a list of steps: a step moves, then holds still. The holds
are where the video is cut. In a slide deck each clip plays by itself and stops on its last frame while the
presenter talks; the next click starts the next clip from exactly that frame. The audience sees one video that
pauses; the presenter controls the pace.

Default deliverables for every animation:

| What | Where |
|---|---|
| the video, 1920×1080, 30 fps, H.264 | `videos/<name>.mp4` (and its last frame, `videos/<name>.png`) |
| the clips, cut at the pauses | `videos/clips/<name>/01.mp4`, `02.mp4`, … |
| a sheet with the frame where each clip stops | `videos/clips/<name>_pauses.png` |
| the cut points, one comment per stop | a `[<name>]` section in `animations/pauses.toml` |

The user can ask for something else, and the engine covers it:

- **GIF** as well or instead: `--gif` on the script; `cut.py --gif` for clip GIFs that play once and hold.
- **A deck ready to present**: `cut.py --pptx` (one full-screen autoplay clip per slide, in `pauses.toml` order).
- **One continuous video** (website, social media): render and skip the cut. Still build it in steps: it costs
  nothing, and the pause checks keep catching half-finished frames.
- **Another size, frame rate or aspect**: `W`, `H`, `FPS` at the top of `anim.py` (the canvas height follows).

Don't ask about these unless the request is unclear and the answer changes the work: make the default and say
what you made.

## Setup

1. If the project already has its own animation engine (a canvas/render module, a pauses file, a CLAUDE.md that
   describes them), use it and its conventions instead. Consistency across a talk matters more than this engine.
2. Otherwise copy `scripts/anim.py` and `scripts/cut.py` into `<project>/animations/`, and start every new
   animation from a copy of `scripts/example.py`. Videos go to `<project>/videos/` (`OUT` in `anim.py`).
3. Run scripts with `uv run animations/<script>.py`: each declares its dependencies in a PEP 723 header, so there
   is no environment to manage. `ffmpeg` must be on the PATH. Without uv: Python ≥ 3.11 with numpy and matplotlib
   (python-pptx for decks).

```
<project>/
  animations/  anim.py  cut.py  pauses.toml  <one script per video>.py  data/ (inputs, cached runs, images)
  videos/      <name>.mp4  <name>.png  clips/<name>/NN.mp4  clips/<name>_pauses.png  clips/deck.pptx  preview/
```

## Workflow

1. **Plan** the scenes and steps, and what is on screen at each pause, in the script's docstring. If the user
   asked for a proposal ("propose", "what do you think", "me proponha"), send the plan and wait. Otherwise build
   it and iterate: a finished draft gets better feedback than a description.
2. **Write** the script from `example.py`: data and asserts at the top, one function per scene, `SCENES` last.
3. **Check without rendering** (seconds each), and look at the PNGs with Read:
   - `--preview`: the last frame of each scene (layout, overlaps, clipped text);
   - `--frames 3.4 7.9`: any instants (transitions, the middle of a movement);
   - `--sheet`: the frame at every pause on one image, with a warning for pauses where something still moves.
4. **Render**: `uv run animations/<script>.py` (`--gif` too, if wanted). It takes about 0.5–3× the video's
   length at 1080p, depending on how much is drawn; run long renders in the background. `--draft` renders at half
   size and 15 fps to judge the motion before the full render.
5. **Pauses**: the first render writes the video's section into `pauses.toml`, with an automatic comment per stop.
   Replace each comment with what is on screen there: it documents the clips for whoever presents. Later renders
   never overwrite a section; when the timing changed they print the new pauses, and you update the section.
6. **Cut**: `uv run animations/cut.py <name>` (with `--gif` and `--pptx` as needed), then look at
   `videos/clips/<name>_pauses.png`, which is made from the real MP4.
7. **Verify and report** (last section).

## Writing a scene

A scene is a function of `tau`, the seconds since the scene started, that draws the whole frame. Nothing persists
between frames, so every property (opacity, position, color, how much of a line is drawn) is computed from `tau`,
usually through `ramp(tau, start, duration)`, which eases from 0 to 1. Coordinates are canvas units: x from 0 to
192, y from 0 to 108, origin at the bottom left, 1 unit = 10 px at 1080p.

```python
from anim import BLUE, CW, INK_2, Scene, arrow, heading, lerp, main, ramp, rbox, steps, txt

S, P, END = steps(0.6, [1.5, 2.0, 1.2])  # 3 steps: when each starts, its pause instant, end of the last hold


def flow(tau):
    heading("Title", "subtitle", ramp(tau, 0, 0.5))
    a = ramp(tau, S[0], 0.6)  # step 1: a box fades in
    rbox(20, 40, 50, 20, fc="#f3f7fd", ec=BLUE, lw=2, a=a)
    txt(45, 50, "input", size=20, weight="bold", a=a, ha="center")
    g = ramp(tau, S[1], 0.8)  # step 2: an arrow grows
    if g > 0:
        arrow((72, 50), lerp((72, 50), (118, 50), g), color=INK_2, lw=2.5)
    txt(CW / 2, 9, "the conclusion, in bold", size=18, weight="bold", a=ramp(tau, S[2], 0.5), ha="center")


SCENES = [Scene("flow", flow, END + 0.8, P),
          Scene("rule", rule, RU_END + 2.5, RU_P, veil=True)]  # veil: the previous frame fades to white first
if __name__ == "__main__":
    main("my_video", SCENES)
```

What `anim.py` provides (it is short; read it for the signatures):

- **motion**: `ramp`, `lin`, `ease`, `pop`, `lerp`, `mix` (colors), `rgba`;
- **drawing**: `txt`, `rbox`, `circle`, `arrow`, `check`, `warn`, `bubble`, `heading`, `image` (a picture as a card,
  with highlighter marks), `text_w` (text width in units), `wrap`, `line_h`, `num` (true minus sign), and `D`, the
  matplotlib axes, for anything else;
- **plots**: `Panel(x0, y0, w, h, xlim, ylim)` with `frame`, `points` (per-point opacity, to appear one by one) and
  `line(frac=…)` to grow a line;
- **structure**: `steps`, `Scene(name, draw, dur, pauses, veil)`, `main`;
- **palette**: `INK`, `INK_2`, `MUTED`, `GRID`, `AXIS`, `BLUE`, `ORANGE`, `TEAL`, `VIOLET`, `RED`, `GREEN`, `SURFACE`.

To draw the final state of another scene (to continue from it, or to put it under a veil), call its function with
a large `tau`: `flow(99)`.

## Pauses

- `steps(t0, durations, hold=0.6)` gives every step `hold` seconds of stillness and puts its pause 0.2 s before the
  next step moves. Give each step a duration that covers all of its animation (the start of its last ramp plus
  that ramp's duration); otherwise the pause catches it mid-motion, and `--sheet` says so.
- A scene lasts `END + 0.8`; the last scene `END + 2.5`, so the video ends on a held frame.
- Pause before anything leaves the screen, not only after things arrive: the presenter needs a moment on the
  complete picture before it changes.
- Every clip ends on a still, complete frame. That is the whole point of the cut.
- Between scenes, `veil=True` fades the previous scene's last frame under white before the new scene draws; the
  engine shifts the timing and the pauses by `VEIL` itself. No hard cuts.

## Visual conventions

These defaults produced consistent, readable talks. Keep them unless the project has its own.

- White background, Helvetica Neue (Arial or DejaVu Sans as fallbacks), title and subtitle at the top left
  (`heading`), one bold conclusion line at the bottom, labels in `MUTED`, secondary text in `INK_2`.
- **Colors carry meaning.** Decide once per project what each color stands for (say, blue = data, orange = model)
  and keep it in every video, so the audience reads color without a legend. The palette is safe for color-vision
  deficiency; use `RED`/`GREEN` only with an icon (`warn`, `check`) and `TEAL` only next to a label.
- **One element leaves before another enters the same place.** Two texts crossfading on top of each other are
  unreadable for a moment. Morphing one element into another state (a curve becoming another curve) is fine.
- Lines grow along their path (`Panel.line(frac=…)`, arrows through `lerp`), points appear one by one, things
  travel in straight lines (`lerp` with `ramp`).
- Text that must be read from the back of a room: 11 pt or more (at 1080p); titles 24 pt; conclusions 16–18 pt.
- **Text fits its box**: `assert text_w(label, size, weight="bold") + 2 < box_w, label` at import time, for every
  label of a list. It catches overflow the moment a text changes.

## Content rules

- **Numbers on screen are real**: computed in the script from data, or loaded from a real run. Heavy work
  (training a model, running an LLM, a long simulation) goes into a separate `<name>_data.py` that runs once and
  saves `data/<name>.npz` or `.json`; the animation only loads it. Add asserts so the story stays true when the data
  changes (`assert SNR[16] > SNR[4]`).
- What is illustrative or simulated says so on screen.
- Facts (dates, sizes, costs, who did what) are checked before they go on screen, with the source in the
  docstring. If the user's brief has an inaccurate fact, build the correct version and tell them.
- Images (paper pages, figures, photos) are copied into `animations/data/` with their origin noted, never read from
  outside the project. Crop anything personal (download stamps, names, emails) before showing it.
- **Versions, not replacements**: when the user wants another version of a finished video ("make another version",
  "don't undo what's done", "faça outra versão"), write a new script that imports the original and overrides only
  what changes, and call `main("<name>_2", orig.SCENES)`. The original stays untouched; check that its `--preview`
  PNGs keep the same md5. Before reworking an approved video in place, back up its script and outputs.

## Output formats

- **MP4 (default)**: H.264, yuv420p, crf 18, BT.709 tags, faststart, 30 fps, 1920×1080. It plays in PowerPoint,
  Keynote, Google Slides, browsers and phones.
- **GIF** (`--gif`): 960 px wide, 20 fps, with a palette made for the video. Good for READMEs, docs and chats. Its
  limits: 256 colors (gradients band), files grow fast with motion and length (keep GIFs under ~15 s), no sound and
  no pause control. To present, prefer MP4 clips; `cut.py --gif` makes clip GIFs that play once and hold.
- Vertical video, WebM, 60 fps and other variants: `references/recipes.md`.

## Before saying it's done

1. Look at `videos/clips/<name>_pauses.png` (made from the real MP4) and at a few transition frames (`--frames`, or
   `ffmpeg -ss <t> -i videos/<name>.mp4 -frames:v 1 frame.png`). Check that every stop is complete and still, that
   nothing overlaps or is cut off, and that nothing appears before its time.
2. Delete `videos/preview/` (scratch output).
3. Tell the user: the files, the duration and the number of clips; how to change the pauses (edit `pauses.toml`,
   run `cut.py` again); and every fact or number on screen they should double-check, separating what the script
   computed from what was typed in.

## More

`references/recipes.md` has code for: continuing from another scene or video; versions; highlight and dim;
zooming an axis (timelines); sequence diagrams; images with highlighter marks; counters; several languages;
cached model runs; several videos sharing code; `FuncAnimation` for heavy data; math in the same font; other
output formats; presenting the clips (PowerPoint, Keynote, Google Slides); and environment pitfalls. Read the
section you need when the animation calls for it.
