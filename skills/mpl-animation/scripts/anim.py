"""Stepwise matplotlib animations: scenes made of steps that end in pauses, rendered to MP4 (or GIF) and later
cut into clips at those pauses (cut.py).

The canvas is CW = 192 units wide (10 px per unit at 1920 px) and is cleared and redrawn for every frame, so a
frame is a pure function of time: any instant can be drawn on its own, a scene can draw another scene's last
frame, and checks need no rendering. Copy this file and cut.py next to the animation scripts; example.py is a
complete script to start from.

    uv run animations/<script>.py               # videos/<name>.mp4 + last frame PNG; adds its pauses to pauses.toml
    uv run animations/<script>.py --gif         # ... plus videos/<name>.gif
    uv run animations/<script>.py --draft       # half size, 15 fps -> videos/<name>_draft.mp4 (check motion fast)
    uv run animations/<script>.py --preview     # last frame of each scene -> videos/preview/<name>_<scene>.png
    uv run animations/<script>.py --frames 3.4 12   # frames at chosen instants (transitions, overlaps)
    uv run animations/<script>.py --sheet       # the frame at every pause on one sheet; flags pauses in motion

`uv run --with numpy --with matplotlib anim.py` runs a self-check of the timeline logic.
"""
import argparse
import re
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.animation import FFMpegWriter  # noqa: E402
from matplotlib.colors import to_rgb, to_rgba  # noqa: E402
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch, Polygon, Rectangle  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "videos"  # videos/ beside the animations folder
PAUSES_FILE = HERE / "pauses.toml"  # where each video is cut into clips (read by cut.py)

# --- format ---------------------------------------------------------------------------------------------------
FPS = 30
W, H, DPI = 1920, 1080, 120  # pixels (vertical video: 1080, 1920)
CW = 192  # canvas width in units; the height follows the aspect ratio (108 at 16:9)
CH = CW * H / W
U = W / CW  # pixels per unit
VEIL = 0.8  # seconds of white veil before a Scene(veil=True)
GIF_WIDTH, GIF_FPS = 960, 20

# --- palette (validated for color-vision deficiency, every pair included) ---------------------------------------
SURFACE = "#ffffff"
INK, INK_2, MUTED = "#0b0b0b", "#52514e", "#898781"  # text, secondary text, labels
GRID, AXIS = "#e1e0d9", "#c3c2b7"
BLUE, ORANGE = "#2a78d6", "#eb6834"
TEAL, VIOLET = "#1baf7a", "#4a3aa7"  # teal has little contrast on white: always next to a label
RED, GREEN = "#d03b3b", "#0ca30c"  # bad / ok: always with an icon (warn, check)

plt.rcParams.update({
    "font.family": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
    "font.size": 14,
    "text.color": INK,
    "axes.edgecolor": AXIS,
    "xtick.color": MUTED, "ytick.color": MUTED,
})


# --- motion and color -------------------------------------------------------------------------------------------
def ease(u):
    """Cubic in-out, clipped to 0..1."""
    u = np.clip(u, 0, 1)
    return np.where(u < 0.5, 4 * u**3, 1 - (-2 * u + 2) ** 3 / 2)


def pop(u):
    """Ease-out with a slight overshoot, for things that appear (use it on size, not on opacity)."""
    u = np.clip(u, 0, 1)
    c = 1.7
    return 1 + (c + 1) * (u - 1) ** 3 + c * (u - 1) ** 2


def ramp(tau, t0, dur):
    """0 before t0, eases to 1 over `dur` seconds: the opacity or progress of almost everything."""
    return float(ease((tau - t0) / dur))


def lin(tau, t0, dur):
    """Like ramp, without easing (steady motion: a pulse travelling, a clock)."""
    return float(np.clip((tau - t0) / dur, 0, 1))


def lerp(p, q, u):
    """Number or point between p and q; with u = ramp(...) things travel in a straight line, eased."""
    if np.ndim(p) == 0:
        return p + (q - p) * u
    return tuple(a + (b - a) * u for a, b in zip(p, q))


def mix(c1, c2, u):
    """Color between c1 and c2 (u = 0..1): highlights, dimming, a box lighting up."""
    return tuple(np.array(to_rgb(c1)) * (1 - u) + np.array(to_rgb(c2)) * u)


def rgba(color, alpha):
    """One RGBA row per alpha value (per-point opacity in scatter plots)."""
    alpha = np.atleast_1d(alpha)
    out = np.tile(to_rgba(color), (alpha.size, 1))
    out[:, 3] = alpha
    return out


def num(v, spec=".2f"):
    """Number as text with a true minus sign (−1.50, not -1.50)."""
    return format(v, spec).replace("-", "−")


# --- canvas and primitives ----------------------------------------------------------------------------------------
fig = plt.figure(figsize=(W / DPI, H / DPI), dpi=DPI, facecolor=SURFACE)
D = fig.add_axes((0, 0, 1, 1))
_RENDERER = fig.canvas.get_renderer()


def clear():
    D.cla()
    D.set_xlim(0, CW)
    D.set_ylim(0, CH)
    D.set_axis_off()


def txt(x, y, s, size=15, color=INK, a=1.0, **kw):
    """Text at (x, y), vertically centered unless va= says otherwise; skipped while invisible."""
    if a > 0.001:
        kw.setdefault("va", "center")
        D.text(x, y, s, fontsize=size, color=color, alpha=min(1, a), **kw)


def rbox(x, y, w, h, fc="none", ec="none", lw=1.0, a=1.0, r=0.8, z=1, ls="-"):
    """Rounded box with its lower-left corner at (x, y)."""
    if a > 0.001:
        D.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={r}", fc=fc, ec=ec, lw=lw,
                                   alpha=min(1, a), zorder=z, ls=ls))


def circle(x, y, r, fc=SURFACE, ec=INK, lw=2.0, a=1.0, z=3):
    if a > 0.001:
        D.add_patch(Circle((x, y), r, fc=fc, ec=ec, lw=lw, alpha=min(1, a), zorder=z))


def arrow(p0, p1, color=AXIS, lw=2.0, a=1.0, rad=0.0, head=True, ls="-", z=2):
    """Arrow from p0 to p1; rad bends it. To make it grow: arrow(p0, lerp(p0, p1, ramp(...)))."""
    if a > 0.001:
        style = "-|>,head_length=7,head_width=4.5" if head else "-"
        D.add_patch(FancyArrowPatch(p0, p1, arrowstyle=style, connectionstyle=f"arc3,rad={rad}", lw=lw,
                                    color=color, alpha=min(1, a), ls=ls, shrinkA=0, shrinkB=0, zorder=z,
                                    capstyle="round", joinstyle="round"))


def check(x, y, s=1.4, color=GREEN, a=1.0, lw=3.0):
    if a > 0.001:
        D.plot([x - s * 0.55, x - s * 0.12, x + s * 0.6], [y + s * 0.02, y - s * 0.42, y + s * 0.5], color=color,
               lw=lw, alpha=min(1, a), solid_capstyle="round", solid_joinstyle="round", zorder=6)


def warn(x, y, s=1.6, color=RED, a=1.0):
    if a > 0.001:
        D.add_patch(Polygon([(x - s, y - s * 0.85), (x + s, y - s * 0.85), (x, y + s * 0.95)], closed=True,
                            fc=color, ec=color, lw=2, joinstyle="round", alpha=min(1, a), zorder=6))
        txt(x, y - s * 0.3, "!", size=s * 7.5, color=SURFACE, a=a, ha="center", weight="bold", zorder=7)


_width_cache = {}


def text_w(s, size, **kw):
    """Width of a text in canvas units (measured once, then cached). Use it to lay out and to assert fits."""
    key = (s, size, tuple(sorted(kw.items())))
    if key not in _width_cache:
        t = D.text(0, 0, s, fontsize=size, **kw)
        _width_cache[key] = t.get_window_extent(_RENDERER).width / U
        t.remove()
    return _width_cache[key]


def line_h(size, spacing=1.45):
    """Line height in canvas units for a font size."""
    return size / 72 * DPI / U * spacing


def wrap(text, size, max_w, **kw):
    """Break a text into lines no wider than max_w units."""
    lines, cur = [], ""
    for word in text.split(" "):
        test = (cur + " " + word).strip()
        if cur and text_w(test, size, **kw) > max_w:
            lines.append(cur)
            cur = word
        else:
            cur = test
    return lines + [cur]


def bubble(x, y, text, size=15, fc=SURFACE, ec=INK_2, a=1.0, right=False, max_w=96):
    """Speech bubble with its top-left corner at (x, y) (top-right if `right`); returns its height."""
    lines = wrap(text, size, max_w)
    lh = line_h(size)
    w = max(text_w(ln, size) for ln in lines) + 6
    h = lh * len(lines) + 3.6
    x0 = x - w if right else x
    rbox(x0, y - h, w, h, fc=fc, ec=ec, lw=1.2, a=a, r=2.2)
    for j, ln in enumerate(lines):
        txt(x0 + 3, y - 1.8 - lh * (j + 0.5), ln, size=size, a=a)
    return h


def heading(title, sub="", a=1.0, y=None):
    """Title (bold) and subtitle at the top left."""
    y = CH - 9 if y is None else y
    txt(8, y, title, size=24, weight="bold", a=a)
    txt(8, y - 4.4, sub, size=15, color=INK_2, a=a)


MARKER = "#ffd84d"  # highlighter


def image(img, x, y, h, a=1.0, marks=(), mark_a=0.0, z=8):
    """A picture (paper page, figure, photo) as a card of height h with its lower-left corner at (x, y);
    `marks` are (x0, y0, x1, y1) boxes in image pixels painted with a highlighter. Returns the card width."""
    ih, iw = img.shape[:2]
    w = h * iw / ih
    if a <= 0.001:
        return w
    rbox(x + 0.9, y - 0.9, w, h, fc=INK, a=0.12 * a, r=0.4, z=z - 0.2)
    D.imshow(img, extent=(x, x + w, y, y + h), zorder=z, alpha=min(1, a), interpolation="antialiased",
             aspect="auto")
    rbox(x, y, w, h, ec=AXIS, lw=1, a=a, r=0.2, z=z + 0.1)
    for x0, y0, x1, y1 in marks:
        rbox(x + x0 / iw * w, y + (1 - y1 / ih) * h, (x1 - x0) / iw * w, (y1 - y0) / ih * h, fc=MARKER,
             a=0.5 * a * mark_a, r=0.3, z=z + 0.2)
    return w


class Panel:
    """A plot drawn in canvas units: maps data (x, y) into the rectangle (x0, y0, w, h)."""

    def __init__(self, x0, y0, w, h, xlim, ylim):
        self.x0, self.y0, self.w, self.h, self.xlim, self.ylim = x0, y0, w, h, xlim, ylim
        self.clip = Rectangle((x0, y0), w, h, transform=D.transData)

    def px(self, v):
        return self.x0 + (np.asarray(v, float) - self.xlim[0]) / (self.xlim[1] - self.xlim[0]) * self.w

    def py(self, v):
        return self.y0 + (np.asarray(v, float) - self.ylim[0]) / (self.ylim[1] - self.ylim[0]) * self.h

    def frame(self, a=1.0, xticks=(), yticks=(), xlabel="", ylabel="", size=12, fmt="g"):
        """Axes, horizontal grid lines at the y ticks, tick labels and axis names. One-letter names are italic
        (a variable); names with units are not."""
        if a <= 0.001:
            return
        self.clip = Rectangle((self.x0, self.y0), self.w, self.h, transform=D.transData)  # D.cla() drops it
        for v in yticks:
            D.plot([self.x0, self.x0 + self.w], [self.py(v)] * 2, color=GRID, lw=1, alpha=a, zorder=0)
            txt(self.x0 - 1.2, self.py(v), num(v, fmt), size=size, color=MUTED, a=a, ha="right")
        for v in xticks:
            txt(self.px(v), self.y0 - 1.3, num(v, fmt), size=size, color=MUTED, a=a, ha="center", va="top")
        D.plot([self.x0, self.x0 + self.w], [self.y0] * 2, color=AXIS, lw=1.2, alpha=a, zorder=0)
        D.plot([self.x0] * 2, [self.y0, self.y0 + self.h], color=AXIS, lw=1.2, alpha=a, zorder=0)
        if xlabel:
            txt(self.x0 + self.w / 2, self.y0 - (5.2 if xticks else 1.3), xlabel, size=size + 3, color=MUTED, a=a,
                ha="center", va="top", style="italic" if len(xlabel) == 1 else "normal")
        if ylabel:
            txt(self.x0 - (6 if yticks else 1.6), self.y0 + self.h / 2, ylabel, size=size + 3, color=MUTED, a=a,
                ha="right", style="italic" if len(ylabel) == 1 else "normal")

    def points(self, xs, ys, color=BLUE, a=1.0, size=70, hollow=False, z=4):
        """Markers; `a` and `size` may be arrays (one value per point) to make points appear one by one."""
        xs, ys = np.asarray(xs, float), np.asarray(ys, float)
        alpha = np.broadcast_to(np.asarray(a, float), xs.shape)
        sizes = np.broadcast_to(np.asarray(size, float), xs.shape)
        keep = (alpha > 0.001) & (sizes > 0.1)
        if not keep.any():
            return
        fc, ec = (rgba(SURFACE, alpha[keep]), rgba(color, alpha[keep])) if hollow else \
            (rgba(color, alpha[keep]), rgba(SURFACE, alpha[keep]))
        D.scatter(self.px(xs[keep]), self.py(ys[keep]), s=sizes[keep], facecolors=fc, edgecolors=ec,
                  linewidths=1.6, zorder=z)

    def line(self, xs, ys, color=ORANGE, lw=3.0, a=1.0, frac=1.0, ls="-", z=3):
        """Polyline clipped to the panel; `frac` (0..1) draws only its first part, so the line grows."""
        if a <= 0.001 or frac <= 0.001:
            return
        xs, ys = np.asarray(xs, float), np.asarray(ys, float)
        if frac < 1:
            k = frac * (len(xs) - 1)
            i = int(k)
            j = min(i + 1, len(xs) - 1)
            xs = np.append(xs[:i + 1], xs[i] + (xs[j] - xs[i]) * (k - i))
            ys = np.append(ys[:i + 1], ys[i] + (ys[j] - ys[i]) * (k - i))
        ln, = D.plot(self.px(xs), self.py(ys), color=color, lw=lw, alpha=min(1, a), ls=ls, zorder=z,
                     solid_capstyle="round", dash_capstyle="round")
        ln.set_clip_path(self.clip)


# --- scenes, steps and pauses -----------------------------------------------------------------------------------
@dataclass
class Scene:
    name: str
    draw: Callable[[float], None]  # draw(tau): tau = seconds since this scene started (after its veil)
    dur: float  # seconds, veil not included
    pauses: Sequence[float] = ()  # instants (in tau) where the video may be cut: the `pauses` from steps()
    veil: bool = False  # first fade the previous scene's last frame under a white veil


def steps(t0, durs, hold=0.6):
    """Plan a scene as consecutive steps starting at t0: step k moves during durs[k], then holds still for
    `hold` s. Returns (starts, pauses, end): when each step starts, the cut instant inside each hold (0.2 s
    before the next step moves), and when the last hold ends."""
    starts, pauses, t = [], [], t0
    for d in durs:
        starts.append(t)
        t += d + hold
        pauses.append(round(t - 0.2, 2))
    return starts, pauses, t


class Timeline:
    def __init__(self, scenes):
        self.items, t = [], 0.0  # (start, veil, scene)
        for i, s in enumerate(scenes):
            pre = VEIL if s.veil and i else 0.0
            self.items.append((t, pre, s))
            t += pre + s.dur
        self.total = t

    def locate(self, t):
        starts = [st for st, _, _ in self.items]
        i = max(0, min(int(np.searchsorted(starts, t, side="right")) - 1, len(self.items) - 1))
        return i, t - self.items[i][0]

    def draw(self, t):
        i, tau = self.locate(t)
        _, pre, scene = self.items[i]
        clear()
        if tau < pre:
            prev = self.items[i - 1][2]
            prev.draw(prev.dur)
            rbox(0, 0, CW, CH, fc=SURFACE, a=ramp(tau, 0, pre * 0.875), r=0, z=50)
        else:
            scene.draw(tau - pre)

    def pauses(self):
        """[(t, scene, step)] for the whole video. The last pause of the last scene is dropped: the last clip
        runs to the end."""
        out = [(round(st + pre + p, 2), s.name, k) for st, pre, s in self.items for k, p in enumerate(s.pauses, 1)]
        if out and out[-1][1] == self.items[-1][2].name:
            out.pop()
        return out


# --- output -----------------------------------------------------------------------------------------------------
def mp4_writer(fps=FPS):
    """H.264, yuv420p, BT.709, faststart: plays in PowerPoint, Keynote, browsers and phones."""
    return FFMpegWriter(fps=fps, codec="libx264", extra_args=[
        "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "slow", "-movflags", "+faststart",
        "-vf", "scale=out_color_matrix=bt709", "-colorspace", "bt709", "-color_primaries", "bt709",
        "-color_trc", "bt709"])


def to_gif(src, dst, width=GIF_WIDTH, fps=GIF_FPS, loop=0):
    """GIF from a video with a palette made for it (sharper and smaller than PillowWriter). loop=0 repeats
    forever; loop=-1 plays once and stays on the last frame."""
    vf = (f"fps={fps},scale={width}:-1:flags=lanczos,split[a][b];"
          "[a]palettegen=stats_mode=full[p];[b][p]paletteuse=dither=sierra2_4a")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-vf", vf, "-loop", str(loop),
                    str(dst)], check=True)


def sheet(pngs, labels, title, dst, cols=3):
    """Contact sheet: images in a grid, each with its label (labels containing 'MOVING' in red)."""
    rows = -(-len(pngs) // cols)
    f, axs = plt.subplots(rows, cols, figsize=(cols * 6.4, rows * 4.3), facecolor=SURFACE, squeeze=False)
    for ax in axs.flat:
        ax.set_axis_off()
    for ax, png, label in zip(axs.flat, pngs, labels):
        ax.set_axis_on()
        ax.imshow(plt.imread(png))
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_title(label, fontsize=15, loc="left", color=RED if "MOVING" in label else INK)
    f.suptitle(title, fontsize=18, x=0.01, ha="left", weight="bold")
    f.tight_layout(rect=(0, 0, 1, 1 - 0.6 / f.get_figheight()))
    f.savefig(dst, dpi=80, facecolor=SURFACE)
    plt.close(f)


def _pixels():
    fig.canvas.draw()
    return np.asarray(fig.canvas.buffer_rgba()).copy()


_TOML_HEAD = """\
# Where each video is cut into clips (one clip per slide). Each number is an instant of the video, in seconds:
# the clip before it stops on that frame and the next clip starts from it. Delete a number to merge two clips,
# add one to split. Describe in each comment what is on screen at that stop.
# Section order = slide order in `cut.py --pptx`.
"""


def sync_pauses(name, total, pauses):
    """Add the video's section to pauses.toml if it has none; if it has one that differs, only warn (it may
    have been edited on purpose)."""
    text = PAUSES_FILE.read_text() if PAUSES_FILE.exists() else _TOML_HEAD
    times = [t for t, _, _ in pauses]
    have = tomllib.loads(text).get(name)
    if have is None:
        key = name if re.fullmatch(r"[A-Za-z0-9_-]+", name) else f'"{name}"'
        rows = [f"  {f'{t},':<8}# {k:<2} {scene}, step {j}" for k, (t, scene, j) in enumerate(pauses, 1)]
        rows.append(f"  {'':<8}# {len(pauses) + 1:<2} (to the end)")
        block = "\n".join([f"\n[{key}]  # {total:.1f} s", "pauses = [", *rows, "]"])
        PAUSES_FILE.write_text(text.rstrip("\n") + "\n" + block + "\n")
        print(f"added [{name}] to {PAUSES_FILE.name}: replace the step comments with what is on screen")
    elif [float(x) for x in have.get("pauses", [])] != times:
        print(f"note: {PAUSES_FILE.name} [{name}] differs from the script's timing. Fine if edited on purpose; "
              f"if the timing changed, the script's pauses are now: {times}")


def main(name, scenes):
    """Command line for one video: render, or check it without rendering (see the module docstring)."""
    doc = getattr(sys.modules.get("__main__"), "__doc__", None) or name
    ap = argparse.ArgumentParser(description=doc, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--gif", action="store_true", help=f"also write videos/{name}.gif")
    ap.add_argument("--draft", action="store_true", help="half size, 15 fps: check the motion quickly")
    ap.add_argument("--preview", action="store_true", help="only the last frame of each scene, as PNG")
    ap.add_argument("--frames", nargs="+", type=float, metavar="T", help="only the frames at these instants (s)")
    ap.add_argument("--sheet", action="store_true", help="only a sheet with the frame at every pause")
    args = ap.parse_args()
    tl = Timeline(scenes)
    pauses = tl.pauses()
    print(f"{name}: {tl.total:.1f} s · {len(pauses) + 1} clips · pauses {[t for t, _, _ in pauses]}")
    prev_dir = OUT / "preview"
    if args.preview or args.frames or args.sheet:
        prev_dir.mkdir(parents=True, exist_ok=True)
    if args.preview:
        for st, pre, s in tl.items:
            tl.draw(st + pre + s.dur - 0.01)
            fig.savefig(prev_dir / f"{name}_{s.name}.png", facecolor=SURFACE)
        print("previews in", prev_dir)
    elif args.frames:
        for t in args.frames:
            tl.draw(t)
            path = prev_dir / f"{name}_{t:g}.png"
            fig.savefig(path, facecolor=SURFACE)
            print(path)
    elif args.sheet:
        stops = pauses + [(round(tl.total - 1 / FPS, 2), "end", 0)]
        pngs, labels, moving = [], [], []
        for k, (t, scene, j) in enumerate(stops, 1):
            tl.draw(t - 0.1)
            before = _pixels()
            tl.draw(t)
            still = np.array_equal(before, _pixels())
            png = prev_dir / f"{name}_stop{k:02d}.png"
            fig.savefig(png, facecolor=SURFACE)
            where = "end of video" if scene == "end" else f"{scene}, step {j}"
            labels.append(f"{k:02d}  {t:.2f} s · {where}" + ("" if still else "  · MOVING"))
            pngs.append(png)
            if not still:
                moving.append(t)
        dst = prev_dir / f"{name}_pauses.png"
        sheet(pngs, labels, f"{name}: the frame where each clip stops", dst)
        for p in pngs:
            p.unlink()
        print("sheet:", dst)
        if moving:
            print(f"warning: still moving at {moving} (0.1 s before differs): lengthen the step's duration or "
                  "finish its animation sooner")
    else:
        fps, dpi = (15, DPI / 2) if args.draft else (FPS, DPI)
        OUT.mkdir(parents=True, exist_ok=True)
        path = OUT / f"{name}{'_draft' if args.draft else ''}.mp4"
        n = int(round(tl.total * fps))
        writer = mp4_writer(fps)
        with writer.saving(fig, str(path), dpi):
            for f in range(n):
                tl.draw(f / fps)
                writer.grab_frame(facecolor=SURFACE)
                if f % max(1, n // 10) == 0:
                    print(f"  {100 * f // n}%", flush=True)
        print("video:", path)
        if not args.draft:
            fig.savefig(OUT / f"{name}.png", facecolor=SURFACE)  # last frame: poster, thumbnail, handout
            sync_pauses(name, tl.total, pauses)
        if args.gif:
            gif = path.with_suffix(".gif")
            to_gif(path, gif)
            print("gif:", gif)


def _selftest():
    s, p, end = steps(0.5, [1.0, 2.0], hold=0.6)
    assert np.allclose(s, [0.5, 2.1]) and p == [1.9, 4.5] and np.isclose(end, 4.7), (s, p, end)
    idle = lambda tau: None  # noqa: E731
    tl = Timeline([Scene("a", idle, 5.0, [1.9, 4.5]), Scene("b", idle, 3.0, [1.0, 2.5], veil=True),
                   Scene("c", idle, 2.0)])
    assert np.isclose(tl.total, 5.0 + VEIL + 3.0 + 2.0)
    # the last pause is kept here (it belongs to "b", not to the last scene); "b"'s pauses shift by the veil
    assert [t for t, _, _ in tl.pauses()] == [1.9, 4.5, round(5 + VEIL + 1, 2), round(5 + VEIL + 2.5, 2)]
    assert [t for t, _, _ in Timeline([Scene("a", idle, 5.0, [1.9, 4.5])]).pauses()] == [1.9]
    assert tl.locate(5.0 + VEIL / 2)[0] == 1 and tl.locate(99)[0] == 2 and tl.locate(0)[0] == 0
    assert num(-1.5) == "−1.50" and lerp(0, 10, 0.5) == 5 and lerp((0, 0), (2, 4), 0.5) == (1, 2)
    assert wrap("a b c", 15, 1e9) == ["a b c"]
    print("anim.py self-check ok")


if __name__ == "__main__":
    _selftest()
