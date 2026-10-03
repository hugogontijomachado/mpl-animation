# Recipes

Code for situations that come up again and again. Everything assumes `from anim import *`-style imports of the
names used.

1. Continue from another scene or video
2. Versions of a finished video
3. Highlight and dim
4. Moving things, zooming an axis
5. Sequence diagram
6. Images, pages and figures
7. Counters
8. Several languages
9. Cached heavy computation
10. Several videos sharing code
11. Heavy data: FuncAnimation
12. Math in the same font
13. Other output formats
14. Presenting the clips
15. Pitfalls

## 1. Continue from another scene or video

Inside a video, a scene can start from another scene's final frame by drawing it first, then changing it:

```python
def detail(tau):
    overview(99)  # the final frame of the previous scene
    rbox(0, 0, 192, 60, fc=SURFACE, a=ramp(tau, 0, 0.5), r=0, z=40)  # its lower half fades out
    ...  # the new content enters after 0.5 s
```

A cleaner variant gives the previous scene's helpers an opacity parameter (`boxes(a=1 - ramp(...))`) so only
chosen parts leave.

Across videos (video 2 opens on video 1's last frame, so the deck flows from one into the other): import the first
script and draw its last scene at the start of the second one. Check that the frames really match:

```bash
uv run animations/part1.py --frames 41.69   # its total length minus 0.01 s
uv run animations/part2.py --frames 0
md5 videos/preview/part1_41.69.png videos/preview/part2_0.png
```

## 2. Versions of a finished video

```python
# animations/intro_2.py: the intro with another title; intro.py stays as it is
import intro as orig
from anim import Scene, main

orig.TITLE = "Another title"  # scene functions read module globals when they draw

if __name__ == "__main__":
    main("intro_2", orig.SCENES)
```

To replace a scene, reuse the others: `SCENES = [orig.SCENES[0], Scene("new", new_scene, END + 0.8, P),
*orig.SCENES[2:]]`. Constants computed at import from other constants (a width measured from a title) do not
follow an override: override or recompute them too. Check the original is unchanged by running its `--preview`
before and after and comparing md5. Put the version's `pauses.toml` section right after the original's, and keep
versions out of the deck until the user chooses.

## 3. Highlight and dim

```python
dim = ramp(tau, S[2], 0.5)  # everything except the chosen item fades to 30 %
for k, item in enumerate(ITEMS):
    focus = 1.0 if k == CHOSEN else 1 - 0.7 * dim
    item_box(item, a=a * focus)
```

A box that lights up: `fc=mix(SURFACE, ORANGE, 0.1 * lit), ec=mix(GRID, ORANGE, lit), lw=1.3 + 1.2 * lit`.

## 4. Moving things, zooming an axis

Travel: `x, y = lerp(home, target, ramp(tau, t0, 0.8))`. Something that flies into place and shrinks: lerp its
position and its size with the same ramp. A path with several legs: `np.interp(tau, knot_times, knot_xs)`.

Zoom (a timeline from 1940–2025 that zooms into 2015–2026): blend the two mappings, so that every mark travels in a
straight line from its old position to its new one.

```python
def X(year, rng):  # rng = (left year, right year), or (rng0, rng1, z) while zooming
    if len(rng) == 3:
        r0, r1, z = rng
        return (1 - z) * X(year, r0) + z * X(year, r1)
    lo, hi = rng
    return 14 + (year - lo) / (hi - lo) * 164


z = ramp(tau, S[1], 1.6)
for year, label in EVENTS:
    x = X(year, ((1940, 2025), (2015, 2026), z))
    if 4 < x < 188:  # draw only what is on screen
        ...
```

A plot that zooms: build the `Panel` inside the scene function with `xlim=lerp(xl0, xl1, z)`, `ylim=lerp(yl0, yl1, z)`.

## 5. Sequence diagram

Actors on top with dashed lifelines, messages as arrows that grow, activity bars on the lifelines.

```python
def actor(name, x, a, top=80, bottom=14, color=INK):
    w = text_w(name, 13, weight="bold") + 4
    rbox(x - w / 2, top, w, 5, fc=SURFACE, ec=color, lw=1.6, a=a, z=3)
    txt(x, top + 2.5, name, size=13, weight="bold", a=a, ha="center", zorder=4)
    D.plot([x, x], [bottom, top - 0.4], color=GRID, lw=1.3, ls=(0, (2, 2)), alpha=a, zorder=1)


def message(tau, t0, x0, x1, y, label, color=INK, grow=0.5):
    g = ramp(tau, t0, grow)
    if g > 0.001:
        arrow((x0, y), (lerp(x0, x1, g), y), color=color, lw=2)
        txt((x0 + x1) / 2, y + 2, label, size=12, color=INK_2, a=ramp(tau, t0 + grow * 0.6, 0.4), ha="center")


def busy(x, y0, y1, color, a):  # the model thinking, a tool running
    rbox(x - 1.1, y1, 2.2, y0 - y1, fc=mix(SURFACE, color, 0.35), ec=color, lw=1.2, a=a, r=0.4, z=2)
```

Close with a count the audience can compare ("1 call to the model" × "2 calls · 1 Python run").

## 6. Images, pages and figures

```python
from pathlib import Path
import matplotlib.pyplot as plt

PAGE = plt.imread(Path(__file__).with_name("data") / "turing_1950_p1.png")[..., :3]  # source: <where it came from>

w = image(PAGE, 20, 15, 70, a=ramp(tau, S[0], 0.6),
          marks=[(120, 340, 880, 420)], mark_a=ramp(tau, S[1], 0.5))  # highlighter, in image pixels
```

- Measure mark boxes in image pixels (an image viewer's cursor readout, or a temporary grid drawn over the image).
- A card that grows out of a small icon or a file name: lerp `x`, `y` and `h` with one ramp.
- Screenshots of pages often carry colored anti-aliasing fringes: `g = img.mean(axis=2); img = np.dstack([g] * 3)`.
- PDF page to PNG: `pdftoppm -png -r 150 -f 2 -l 2 report.pdf data/report_p2`.

## 7. Counters

```python
v = lerp(0, TOTAL, ramp(tau, S[1], 1.5))
txt(150, 60, f"{v:,.0f}", size=30, weight="bold", ha="right")  # right-aligned: the digits don't jitter
```

`ramp` reaches exactly 1.0, so the counter lands on the exact final value.

## 8. Several languages

```python
import os

LANG = os.environ.get("ANIM_LANG", "en")


def L(pt, en):
    return pt if LANG == "pt" else en


NAME = "averaging" + ("_pt" if LANG == "pt" else "")
TITLE = L("Média de varreduras", "Averaging scans")
```

`ANIM_LANG=pt uv run animations/averaging.py` writes `videos/averaging_pt.mp4` and its own `pauses.toml` section
(same timing, same pauses). Text widths differ between languages: run the fit asserts in both.

## 9. Cached heavy computation

```python
# animations/llm_data.py: run once with `uv run animations/llm_data.py`
# /// script
# requires-python = ">=3.11,<3.14"
# dependencies = ["numpy", "torch", "transformers"]
# ///
...  # run the model for real, greedy decoding, fixed seeds
np.savez(Path(__file__).with_name("data") / "llm.npz", tokens=tokens, probs=probs)
```

```python
# in the animation
CACHE = Path(__file__).with_name("data") / "llm.npz"
if not CACHE.exists():
    raise SystemExit("run first: uv run animations/llm_data.py")
RUN = np.load(CACHE)
```

Prefer one real run of a small open model over an invented example. Show long outputs with […] and assert that
the text on screen matches the real output.

## 10. Several videos sharing code

One script per video. Share helpers by importing another script (`from intro import box, ITEMS`): importing runs
its top level (data, asserts) but not `main()`. Keep what the audience must recognize across videos (a list of
components, their colors, an icon set) in one place and import it, so every video stays in sync.

## 11. Heavy data: FuncAnimation

The canvas recreates every artist on every frame. With thousands of artists per frame (large scatter plots,
particle simulations, long data playback), create the artists once and update them in place, which is
matplotlib's `FuncAnimation` pattern, and keep the rest of the workflow:

```python
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from anim import DPI, FPS, OUT, SURFACE, mp4_writer

fig2, ax = plt.subplots(figsize=(16, 9), dpi=DPI, facecolor=SURFACE)
dots = ax.scatter(POS[0, :, 0], POS[0, :, 1], s=4)


def update(i):
    dots.set_offsets(POS[i])
    return (dots,)


FuncAnimation(fig2, update, frames=len(POS)).save(
    str(OUT / "particles.mp4"), writer=mp4_writer(), dpi=DPI, savefig_kwargs={"facecolor": SURFACE})
```

Plan the steps as usual, write the pause instants into `pauses.toml` by hand, and cut with `cut.py`: it only needs
the MP4 and the pauses. (`blit=True` speeds up on-screen display only, not saving.)

## 12. Math in the same font

```python
plt.rcParams.update({"mathtext.fontset": "custom", "mathtext.rm": "Helvetica Neue",
                     "mathtext.it": "Helvetica Neue:italic", "mathtext.bf": "Helvetica Neue:bold",
                     "mathtext.cal": "Helvetica Neue"})  # without .cal matplotlib warns about a missing font
txt(96, 50, r"$P(x_{t+1} \mid x_1 \ldots x_t)$", size=30, ha="center")
```

- In Helvetica "l" and "I" look the same: write a path length as ℓ.
- Two `$` in one string start math mode: escape money as `\$`.

## 13. Other output formats

- **Vertical** (stories, reels): `W, H = 1080, 1920` in `anim.py`; the canvas becomes 192 × 341 units. Lay out again.
- **60 fps**: `FPS = 60` (renders take twice as long; `cut.py` reads the rate from the file).
- **WebM** for websites (smaller): `ffmpeg -i videos/x.mp4 -c:v libvpx-vp9 -crf 32 -b:v 0 videos/x.webm`.
- **Stills for a handout or the slide itself**: `videos/<name>.png` is the last frame; `--frames` gives any other.

## 14. Presenting the clips

`cut.py --pptx` writes `videos/clips/deck.pptx`: 16:9, one clip per slide, full screen, starts automatically,
no transitions, and a presenter note naming each clip. Copy its slides into the real deck (paste with "keep source
formatting"). The deck is checked in structure; test it once in presentation mode on the presenting computer.

By hand, on every slide:

- **PowerPoint**: the clip full screen, always at the same position; Playback → Start: Automatically; "Rewind
  after playing" off (keeps the last frame on screen); "Hide while not playing" off; Transitions → None.
- **Keynote**: the clip full screen; in the Movie tab of the Format sidebar, start the movie automatically and set
  Repeat to None; no transition.
- **Google Slides**: insert the clip from Drive; Format options → Video playback → Play (automatically). Slides
  shows a poster frame between clips, so the joins are less seamless.

While presenting, a click while a clip is still moving jumps to the next slide and cuts the movement: wait for it
to stop.

## 15. Pitfalls

- A system Python whose numpy/matplotlib builds don't match the machine: always run the scripts with `uv run`.
- Helvetica Neue exists on macOS only. Elsewhere matplotlib falls back to Arial or DejaVu Sans (with a findfont
  warning), widths change, and layouts need another `--preview`; the fit asserts catch overflow.
- Background renders: use absolute paths. A relative `cd` that leaves the project makes the render land elsewhere.
- `cut.py` replaces only the clip folder of the videos it cuts; old PNGs stay in `videos/preview/` until deleted.
- `cut.py` stops with a message when a pause is outside the video, out of order, or less than 2 frames from its
  neighbor: fix `pauses.toml`.
- zsh: `echo =====` fails (`=` expansion); quote it.
