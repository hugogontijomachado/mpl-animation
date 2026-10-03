# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy>=1.26", "matplotlib>=3.8"]
# ///
"""Averaging scans: why the noise drops. One noisy scan of a peak morphs into the mean of 4 and then of 16
scans while a table fills with the signal-to-noise ratio measured on each; then the rule: S/N grows with √n.

    uv run animations/example.py            # videos/averaging.mp4 + last frame; adds its pauses to pauses.toml
    uv run animations/example.py --sheet    # every pause on one sheet, without rendering

Plan (one pause after each step):
    scans   1 axes + one scan grows · 2 mean of 4 scans · 3 mean of 16 scans + conclusion
    rule    (veil) 1 "S/N grows with √n" · 2 the measured factor next to √4 = 2 (to the end)

A template for new animations: plan in the docstring, data and asserts at the top, one function per scene built
from steps(), SCENES at the end. The scans are simulated (said on screen); every number shown is computed here.
"""
import numpy as np

from anim import BLUE, CW, INK_2, MUTED, ORANGE, Panel, Scene, heading, main, num, ramp, steps, text_w, txt

NAME = "averaging"
FINAL_HOLD = 2.5

# --- data: simulated scans of one peak; S/N measured on them ------------------------------------------------------
rng = np.random.default_rng(3)
X = np.linspace(0, 10, 400)
PEAK = np.exp(-((X - 5) ** 2) / (2 * 0.35**2))
SCANS = PEAK + rng.normal(0, 0.35, (16, X.size))
NS = (1, 4, 16)
MEANS = {n: SCANS[:n].mean(0) for n in NS}
BASELINE = (X < 3) | (X > 7)  # noise is measured where there is no peak
SNR = {n: MEANS[n][~BASELINE].max() / MEANS[n][BASELINE].std() for n in NS}
RATIO = SNR[16] / SNR[4]
assert SNR[1] < SNR[4] < SNR[16], SNR
assert 1.6 < RATIO < 2.4, RATIO  # √4 = 2, give or take the noise of 16 simulated scans

# --- scene 1: the scans ------------------------------------------------------------------------------------------
P = Panel(16, 24, 112, 60, xlim=(0, 10), ylim=(-1.2, 2.2))
TX, TX2 = 146, 182  # table columns: n (left-aligned) and S/N (right-aligned)
SC_S, SC_P, SC_END = steps(0.6, [1.8, 1.4, 1.9])
assert text_w("scans averaged", 13) < TX2 - TX - text_w("S/N", 13) - 2


def curve(tau):
    """The curve on screen: one scan that morphs into the mean of 4, then of 16 (the same line, not a swap)."""
    y = MEANS[1]
    for k, n in enumerate(NS[1:], 1):
        y = y + (MEANS[n] - y) * ramp(tau, SC_S[k], 1.0)
    return y


def scans(tau):
    heading("Averaging scans", "the same peak measured again and again (simulated)", ramp(tau, 0, 0.5))
    a = ramp(tau, SC_S[0], 0.6)
    P.frame(a, xticks=(0, 5, 10), yticks=(0, 1, 2), xlabel="time (min)", ylabel="signal")
    P.line(X, curve(tau), color=BLUE, lw=1.8, a=a, frac=ramp(tau, SC_S[0] + 0.3, 1.2))
    txt(TX, 80, "scans averaged", size=13, color=MUTED, a=a)
    txt(TX2, 80, "S/N", size=13, color=MUTED, a=a, ha="right")
    for k, n in enumerate(NS):  # one row per step: the table keeps the story
        ra = ramp(tau, SC_S[k] + (1.3 if k == 0 else 1.0), 0.4)
        y = 72 - 9 * k
        txt(TX, y, f"{n}", size=24, weight="bold", a=ra)
        txt(TX2, y, num(SNR[n], ".1f"), size=24, weight="bold", color=ORANGE, a=ra, ha="right")
    txt(CW / 2, 9, "more scans: the same signal, less noise", size=18, weight="bold",
        a=ramp(tau, SC_S[2] + 1.4, 0.5), ha="center")


# --- scene 2: the rule -------------------------------------------------------------------------------------------
RU_S, RU_P, RU_END = steps(0.2, [1.2, 1.4])


def rule(tau):
    kw = dict(ha="center")
    txt(CW / 2, 64, "S/N grows with √n", size=40, weight="bold", a=ramp(tau, RU_S[0], 0.7), **kw)
    txt(CW / 2, 50, f"4 × more scans → S/N × {num(RATIO, '.1f')} in these scans (√4 = 2)", size=20, color=INK_2,
        a=ramp(tau, RU_S[1], 0.6), **kw)
    txt(CW / 2, 42, "to halve the noise, average four times as many scans", size=20, weight="bold",
        a=ramp(tau, RU_S[1] + 0.4, 0.6), **kw)


SCENES = [Scene("scans", scans, SC_END + 0.8, SC_P), Scene("rule", rule, RU_END + FINAL_HOLD, RU_P, veil=True)]

if __name__ == "__main__":
    main(NAME, SCENES)
