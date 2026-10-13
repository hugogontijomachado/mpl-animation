# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy>=1.26", "matplotlib>=3.10"]
# ///
"""Style: timeline. A short history of data visualization: the long view (1750–2030) with milestones entering one
per step while the earlier ones dim, pictures next to them; then the axis zooms into 1990–2030 for the software era.

    uv run animations/timeline.py            # videos/timeline.mp4 + last frame; adds its pauses to pauses.toml
    uv run animations/timeline.py --sheet    # every pause on one sheet, without rendering

Fits: history, chronology, milestones, project phases, software releases: events in time, each seen in the
context of the ones before it, with a zoom when the story moves to a shorter period.

What to edit (keep the style's functions, between the two rulers):
    MILESTONES   start, end (= start for an event, later for an era), labels, side, color; in entering order
    RANGES       the axis interval of each scene; the zoom blends one into the next
    the pictures one function each, drawn here (redrawn, illustrative). For real ones, copy the image into
                 animations/data/ (note where it came from, crop names and download stamps) and use plt.imread
    the scenes   which milestone enters at which step, the cards' places, the headings and the closing line

Plan (one pause after each step):
    long   1 the axis · 2 Playfair + chart · 3 the golden age, Nightingale + rose · 4 Minard + march ·
           5 Tukey + page with a highlighted line
    zoom   6 the cards leave, the axis zooms into 1990–2030 · 7 matplotlib · 8 D3.js ·
           9 Jupyter + the closing line (to the end)

Facts (checked 2026-10-13; the pictures are redrawn with made-up numbers, as the cards say):
    1786  William Playfair, The Commercial and Political Atlas: the first line and bar charts of economic data
          (the Atlas, London, 1786; Wikipedia, "William Playfair")
    1850–1900  "the Golden Age of statistical graphics" (M. Friendly, Statistical Science 23(4), 2008)
    1858  Florence Nightingale's polar-area ("rose") diagrams of the deaths in the Crimean War (her Notes on Matters
          Affecting the Health, Efficiency and Hospital Administration of the British Army, 1858)
    1869  Charles Joseph Minard's map of Napoleon's 1812 march on Moscow (Carte figurative des pertes successives
          en hommes de l'Armée Française dans la campagne de Russie 1812–1813, Paris, 20 November 1869)
    1977  John W. Tukey, Exploratory Data Analysis (Addison-Wesley), which made the box plot known; the quote on
          the page card is attributed to this book (FlowingData, 2007; N. Yau, Data Points, 2013)
    2003  matplotlib's first release, by John D. Hunter (Hunter, Computing in Science & Engineering 9(3), 2007)
    2011  D3.js (Bostock, Ogievetsky & Heer, "D3: Data-Driven Documents", IEEE TVCG 17(12), 2011)
    2014  Project Jupyter, spun off from IPython (announced by Fernando Pérez in 2014; Wikipedia, "Project Jupyter")
"""
import numpy as np
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from anim import (BLUE, CW, D, INK, INK_2, MUTED, SURFACE, Scene, arrow, circle, heading, image, lerp, line_h, main,
                  mix, pop, ramp, steps, text_w, txt)

NAME = "timeline"
FINAL_HOLD = 2.5

# --- data -----------------------------------------------------------------------------------------------------------
MILESTONES = [  # start, end, year label, name, detail lines, side (+1 above the axis, -1 below), color
    (1786, 1786, "1786", "Playfair", ["the first line and bar charts", "of trade and debt"], +1, INK),
    (1850, 1900, "1850–1900", "golden age", ["1858 · Nightingale's rose diagrams", "1869 · Minard's march on Moscow"],
     -1, INK),
    (1977, 1977, "1977", "Tukey", ["Exploratory Data Analysis", "the box plot"], -1, INK),
    (2003, 2003, "2003", "matplotlib", ["plots from Python code", "by John D. Hunter"], +1, BLUE),
    (2011, 2011, "2011", "D3.js", ["data-driven documents", "charts on the web"], -1, BLUE),
    (2014, 2014, "2014", "Jupyter", ["code, charts and text", "in one notebook"], +1, BLUE),
]
RANGES = [(1750, 2030), (1990, 2030)]  # the long view, then the zoom
SHOWN_IN = [0, 0, 0, 1, 1, 1]  # the range where each milestone enters (its labels must fit there)
QUOTE = ["The greatest value of a picture is when it forces",
         "us to notice what we never expected to see."]

# === the style: axis, milestones, cards ===================================================================================
AX = 50  # height of the axis on the canvas
X0, X1 = 14, 172  # where a range's first and last years land
FADED = "#cfcdc4"  # where a dimmed milestone ends up: still legible, clearly in the past
STEM = 7


def X(year, rng):
    """Year -> x on the canvas. rng = (first year, last year), or (rng0, rng1, z) during a zoom: the two mappings
    blend, so every mark travels in a straight line from its old place to its new one."""
    if len(rng) == 3:
        r0, r1, z = rng
        return (1 - z) * X(year, r0) + z * X(year, r1)
    lo, hi = rng
    return X0 + (year - lo) / (hi - lo) * (X1 - X0)


def axis(rng, grow=1.0):
    """The axis with its arrow, ticks and year labels: every 50 years on a long range, every 10 on a short one
    (crossfading during a zoom). `grow` (0..1) draws it from the left."""
    if grow <= 0.001:
        return
    end = lerp(X0 - 6, X1 + 8, grow)
    D.plot([X0 - 6, end], [AX, AX], color=INK_2, lw=2, solid_capstyle="round", zorder=2)
    if grow > 0.99:
        arrow((X1 + 6, AX), (X1 + 10, AX), color=INK_2, lw=2)
    sets = [(rng[0], 1 - rng[2]), (rng[1], rng[2])] if len(rng) == 3 else [(rng, 1.0)]
    for (lo, hi), w in sets:
        step = 50 if hi - lo > 150 else 10
        for year in range(-(-lo // step) * step, hi + 1, step):
            x = X(year, rng)
            if w > 0.01 and X0 - 5 < x < min(end, X1 + 4):
                D.plot([x, x], [AX - 0.9, AX + 0.9], color=INK_2, lw=1.2, alpha=w, zorder=2)
                txt(x, AX - 3.6, str(year), size=11, color=MUTED, a=w, ha="center")


def milestone(m, rng, a, dim=0.0, details_a=None):
    """A milestone entering with `a` (0..1): a dot (an event) or a bar that grows along the axis (an era), a stem,
    and its year, name and details above or below the axis. `dim` (0..1) turns it gray; `details_a` gives each
    detail line its own opacity (lines that enter in a later step)."""
    start, end, year, name, details, side, color = m
    if a <= 0.001:
        return
    x0, x1 = X(start, rng), X(end, rng)
    c, c2, c3 = (mix(k, FADED, 0.85 * dim) for k in (color, INK_2, MUTED))
    if end > start:
        D.plot([x0, lerp(x0, x1, a)], [AX, AX], color=c, lw=9, solid_capstyle="round", zorder=3)
    else:
        circle(x0, AX, 1.4 * pop(a), fc=c, ec=SURFACE, lw=1.5, z=4)
    x = (x0 + x1) / 2
    D.plot([x, x], [AX + side * 2, AX + side * (2 + STEM * a)], color=c, lw=1.5, zorder=2)
    details_a = details_a or [1.0] * len(details)
    rows = [(year, 14, c3, "normal", 1.0), (name, 22, c, "bold", 1.0)]
    rows += [(d, 13, c2, "normal", k) for d, k in zip(details, details_a)]
    y, prev = AX + side * (2 + STEM), 0.0
    for s, size, col, weight, k in (rows[::-1] if side > 0 else rows):
        h = line_h(size)
        y += side * (prev + h) / 2
        txt(x, y, s, size=size, color=col, a=a * k, ha="center", weight=weight)
        prev = h


def timeline(rng, enter, details_a=None):
    """Every milestone at its entering opacity (`enter`, in MILESTONES order); each one dims as later ones enter."""
    for i, m in enumerate(MILESTONES):
        milestone(m, rng, enter[i], max(enter[i + 1:], default=0.0), (details_a or {}).get(i))


def card(img, x, y, h, a, dim=0.0, marks=(), mark_a=0.0):
    """A picture next to its milestone, dimming with it."""
    image(img, x, y, h, a=a * (1 - 0.6 * dim), marks=marks, mark_a=mark_a)


def picture(w, h, draw):
    """A picture drawn off screen by matplotlib, w × h inches at 100 dpi -> (RGB array for image(), what draw
    returned)."""
    f = Figure(figsize=(w, h), dpi=100, facecolor="white")
    FigureCanvasAgg(f)
    out = draw(f)
    f.canvas.draw()
    return np.asarray(f.canvas.buffer_rgba())[..., :3].copy(), out


def label_w(m):
    return max([text_w(m[3], 22, weight="bold")] + [text_w(d, 13) for d in m[4]])


for i, (m, r) in enumerate(zip(MILESTONES, SHOWN_IN)):  # labels inside the canvas, and apart from their neighbors
    x, w = (X(m[0], RANGES[r]) + X(m[1], RANGES[r])) / 2, label_w(m)
    assert 2 < x - w / 2 and x + w / 2 < CW - 2, (m[3], x, w)
    for n, r2 in zip(MILESTONES[i + 1:], SHOWN_IN[i + 1:]):
        x2 = (X(n[0], RANGES[r]) + X(n[1], RANGES[r])) / 2
        if r2 == r and n[5] == m[5]:
            assert abs(x2 - x) > (w + label_w(n)) / 2 + 2, (m[3], n[3])
# ===========================================================================================================================


# --- the pictures (redrawn in the spirit of the originals, made-up numbers) ---------------------------------------------
def _caption(f, text, y):
    f.text(0.5, y, text, ha="center", fontsize=8, family="serif", style="italic", color="#555555")


def _playfair(f):  # two series and the gap between them, as in Playfair's trade charts
    ax = f.add_axes((0.08, 0.2, 0.88, 0.66))
    t = np.linspace(1700, 1780, 81)
    exports = 0.5 + 1.1 / (1 + np.exp(-(t - 1752) / 7))
    imports = 0.7 + 0.5 * (t - 1700) / 80
    ax.fill_between(t, exports, imports, color="#ecd5b4")
    ax.plot(t, exports, color="#8c2d19", lw=2)
    ax.plot(t, imports, color="#b48a1e", lw=2)
    ax.set_xlim(1700, 1780)
    ax.set_ylim(0, 2)
    ax.grid(color="#ddd5c5", lw=0.6)
    ax.tick_params(labelsize=7, length=0)
    ax.set_yticklabels([])
    _caption(f, "exports and imports · redrawn, illustrative", 0.05)


def _rose(f):  # a polar-area diagram: one wedge per month, its area the deaths
    ax = f.add_axes((0.06, 0.14, 0.88, 0.8), projection="polar")
    r = np.sqrt([3, 4, 6, 9, 14, 20, 16, 11, 8, 6, 4, 3])
    ax.bar(np.arange(12) * np.pi / 6, r, width=np.pi / 6, color="#b9c7d8", edgecolor="#4d6178", lw=0.8)
    ax.set_axis_off()
    _caption(f, "deaths by month · redrawn, illustrative", 0.05)


def _march(f):  # a band as wide as the army, as in Minard's map
    ax = f.add_axes((0.03, 0.2, 0.94, 0.75))
    x = np.linspace(0, 10, 200)
    y = 0.4 * np.sin(x / 2)
    w = 1.3 * np.exp(-x / 4)
    ax.fill_between(x, y - w / 2, y + w / 2, color="#d9b98c")
    ax.fill_between(x, y - 1.3 - w / 6, y - 1.3 + w / 6, color="#333333")
    ax.set_xlim(0, 10)
    ax.set_ylim(-2.2, 1.3)
    ax.set_axis_off()
    _caption(f, "the army, going and coming back · redrawn, illustrative", 0.06)


def _tukey(f):  # a page with the quote and a box plot; returns the line to highlight
    f.text(0.08, 0.9, "Exploratory Data Analysis", fontsize=12, weight="bold", family="serif")
    f.text(0.08, 0.84, "J. W. Tukey, 1977 · redrawn, illustrative", fontsize=7, style="italic", family="serif")
    lines = [f.text(0.08, 0.74 - 0.06 * i, s, fontsize=7.5, family="serif") for i, s in enumerate(QUOTE)]
    ax = f.add_axes((0.12, 0.1, 0.76, 0.42))
    ax.boxplot(np.random.default_rng(1).normal(0, 1, (60, 3)), orientation="horizontal", widths=0.5)
    ax.tick_params(labelsize=6)
    return lines[1]


PLAYFAIR, _ = picture(3.4, 2.4, _playfair)
ROSE, _ = picture(2.6, 2.6, _rose)
MARCH, _ = picture(3.6, 2.0, _march)
TUKEY, _line = picture(3.0, 3.4, _tukey)
_bb = _line.get_window_extent()
TUKEY_MARK = [(_bb.x0 - 2, TUKEY.shape[0] - _bb.y1 - 1, _bb.x1 + 2, TUKEY.shape[0] - _bb.y0 + 1)]


# --- scenes -----------------------------------------------------------------------------------------------------------
TITLE, SUB = "A short history of data visualization", "milestones, one at a time"
LS, LP, LEND = steps(0.6, [1.4, 1.6, 1.8, 1.2, 2.3])  # axis · Playfair · golden age · Minard · Tukey


def long_cards(tau, leave=0.0):
    """The pictures of the long view: each enters just after its milestone and dims with it."""
    k = 1 - leave
    card(PLAYFAIR, 12, 12, 30, ramp(tau, LS[1] + 0.8, 0.6) * k, ramp(tau, LS[2], 0.6))
    card(ROSE, 60, 57, 30, ramp(tau, LS[2] + 1.0, 0.6) * k, ramp(tau, LS[4], 0.6))
    card(MARCH, 94, 60, 22, ramp(tau, LS[3] + 0.4, 0.6) * k, ramp(tau, LS[4], 0.6))
    card(TUKEY, 140, 55, 34, ramp(tau, LS[4] + 0.8, 0.6) * k, 0.0, TUKEY_MARK, ramp(tau, LS[4] + 1.6, 0.5))


def long_view(tau):
    heading(TITLE, SUB, ramp(tau, 0, 0.5))
    axis(RANGES[0], ramp(tau, LS[0], 1.2))
    enter = [ramp(tau, LS[1], 1.0), ramp(tau, LS[2], 1.2), ramp(tau, LS[4], 1.0), 0, 0, 0]
    timeline(RANGES[0], enter, {1: [1.0, ramp(tau, LS[3], 0.6)]})
    long_cards(tau)


ZS, ZP, ZEND = steps(0.2, [2.6, 1.2, 1.2, 1.8])  # zoom · matplotlib · D3.js · Jupyter + closing line


def zoom(tau):
    leave = ramp(tau, ZS[0], 0.5)  # the cards and the heading leave before the axis moves
    rng = (*RANGES, ramp(tau, ZS[0] + 0.6, 1.8))
    heading(TITLE, SUB, 1 - leave)
    heading("The software era", "the axis zooms into 1990–2030", ramp(tau, ZS[0] + 2.0, 0.5))
    axis(rng)
    enter = [1, 1, 1, ramp(tau, ZS[1], 1.0), ramp(tau, ZS[2], 1.0), ramp(tau, ZS[3], 1.0)]
    timeline(rng, enter)
    long_cards(99, leave)
    txt(CW / 2, 9, "old ideas, new tools: every chart stands on the ones before it", size=18, weight="bold",
        ha="center", a=ramp(tau, ZS[3] + 1.0, 0.6))


SCENES = [Scene("long", long_view, LEND + 0.8, LP),
          Scene("zoom", zoom, ZEND + FINAL_HOLD, ZP)]

if __name__ == "__main__":
    main(NAME, SCENES)
