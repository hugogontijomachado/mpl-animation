# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy>=1.26", "pillow>=10", "python-pptx>=1.0"]
# ///
"""Programmatic assertions for the mpl-animation evals.

    uv run evals/check_outputs.py <run_dir> <eval_id>     # writes <run_dir>/checks.json

run_dir is .../eval-N-name/<configuration>/ (it holds outputs/).
"""
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=codec_name,width,height,pix_fmt,nb_frames,r_frame_rate:format=duration",
                          "-of", "default=noprint_wrappers=1", str(path)], capture_output=True, text=True).stdout
    info = dict(line.split("=", 1) for line in out.split() if "=" in line)
    return info


def frame(path, n):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(path), "-vf", f"select=eq(n\\,{n})",
                          "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).astype(float)


def diff(a, b):
    return float(np.abs(a - b).mean()) if a.size and a.size == b.size else 999.0


def videos(out):
    vids = [p for p in out.rglob("*.mp4") if "draft" not in p.name and "preview" not in p.parts]
    info = {p: probe(p) for p in vids}
    return {p: i for p, i in info.items() if "duration" in i}


def main_and_clips(out):
    info = videos(out)
    if not info:
        return None, [], info
    main = max(info, key=lambda p: (float(info[p]["duration"]), int(info[p].get("width", 0))))
    rest = [p for p in info if p != main and float(info[p]["duration"]) < float(info[main]["duration"]) - 0.3]
    by_dir = {}
    for p in rest:
        by_dir.setdefault(p.parent, []).append(p)
    clips = sorted(max(by_dir.values(), key=len), key=lambda p: p.name) if by_dir else []
    return main, clips, info


def check(text, passed, evidence):
    return {"text": text, "passed": bool(passed), "evidence": evidence}


def video_checks(out, min_clips):
    main, clips, info = main_and_clips(out)
    res = []
    if main is None:
        return [check("Delivers an MP4 video at 1920x1080, H.264, yuv420p", False, "no MP4 found"),
                check(f"The video is cut into at least {min_clips} clips", False, "no MP4 found"),
                check("Every clip ends on a still frame (last frame equals the frame 0.1 s before)", False, "no clips"),
                check("Clips join seamlessly (last frame of each clip = first frame of the next)", False, "no clips")], None, []
    i = info[main]
    ok = (i.get("width"), i.get("height"), i.get("codec_name"), i.get("pix_fmt")) == ("1920", "1080", "h264", "yuv420p")
    res.append(check("Delivers an MP4 video at 1920x1080, H.264, yuv420p", ok,
                     f"{main.relative_to(out)}: {i.get('width')}x{i.get('height')} {i.get('codec_name')} "
                     f"{i.get('pix_fmt')} {float(i['duration']):.1f} s"))
    res.append(check(f"The video is cut into at least {min_clips} clips", len(clips) >= min_clips,
                     f"{len(clips)} clips in {clips[0].parent.relative_to(out) if clips else '-'}"))
    still, bad = [], []
    for c in clips:
        n = int(info[c].get("nb_frames", 0))
        d = diff(frame(c, n - 1), frame(c, max(0, n - 4)))
        still.append(d)
        if d >= 0.5:
            bad.append(f"{c.name} ({d:.2f})")
    res.append(check("Every clip ends on a still frame (last frame equals the frame 0.1 s before)",
                     clips and not bad, f"mean |diff| per clip: {[round(s, 2) for s in still]}; moving: {bad}"))
    seams = []
    for a, b in zip(clips, clips[1:]):
        n = int(info[a].get("nb_frames", 0))
        seams.append(round(diff(frame(a, n - 1), frame(b, 0)), 2))
    res.append(check("Clips join seamlessly (last frame of each clip = first frame of the next)",
                     clips and len(clips) > 1 and max(seams) < 1.0, f"mean |diff| at each seam: {seams}"))
    return res, main, clips


def gif_checks(out):
    gifs = sorted(out.rglob("*.gif"), key=lambda p: (len(p.relative_to(out).parts), -p.stat().st_size))
    if not gifs:
        return [check("Delivers a GIF", False, "no GIF found")]
    g = gifs[0]
    im = Image.open(g)
    durs, frames = [], []
    try:
        while True:
            durs.append(im.info.get("duration", 0))
            frames.append(np.asarray(im.convert("L"), float))
            im.seek(im.tell() + 1)
    except EOFError:
        pass
    total = sum(durs) / 1000
    hold = 0.0
    for f, d in zip(reversed(frames), reversed(durs)):
        if diff(f, frames[-1]) < 0.5:
            hold += d / 1000
        else:
            break
    loop = Image.open(g).info.get("loop")
    mb = g.stat().st_size / 1e6
    return [check("Delivers a GIF", True, str(g.relative_to(out))),
            check("GIF lasts between 6 and 15 s", 6 <= total <= 15, f"{total:.1f} s, {len(frames)} frames"),
            check("GIF is README-sized: width <= 1000 px and file <= 8 MB", Image.open(g).width <= 1000 and mb <= 8,
                  f"{Image.open(g).width}x{Image.open(g).height}, {mb:.2f} MB"),
            check("GIF loops forever", loop == 0, f"loop = {loop}"),
            check("GIF holds its final state for at least 1 s before looping", hold >= 1.0, f"final hold {hold:.2f} s")]


def pptx_checks(out, clips):
    decks = list(out.rglob("*.pptx"))
    if not decks:
        return [check("Delivers a .pptx with one clip per slide", False, "no .pptx found"),
                check("Every slide's video starts automatically (no click needed)", False, "no .pptx found")]
    deck = decks[0]
    z = zipfile.ZipFile(deck)
    slides = sorted(n for n in z.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", n))
    with_video, auto = 0, 0
    for s in slides:
        xml = z.read(s).decode("utf8", "ignore")
        if "videoFile" in xml:
            with_video += 1
            if "mediacall" in xml and "clickEffect" not in xml:
                auto += 1
    return [check("Delivers a .pptx with one clip per slide",
                  len(slides) >= 4 and with_video == len(slides) and (not clips or len(slides) == len(clips)),
                  f"{deck.relative_to(out)}: {len(slides)} slides, {with_video} with video, {len(clips)} clips"),
            check("Every slide's video starts automatically (no click needed)", slides and auto == len(slides),
                  f"{auto} of {len(slides)} slides autoplay")]


if __name__ == "__main__":
    run, eid = Path(sys.argv[1]), int(sys.argv[2])
    out = run / "outputs"
    if eid == 1:
        res, _, _ = video_checks(out, 4)
    elif eid == 2:
        res = gif_checks(out)
    else:
        res, _, clips = video_checks(out, 4)
        res += pptx_checks(out, clips)
    (run / "checks.json").write_text(json.dumps(res, indent=2, ensure_ascii=False))
    for r in res:
        print("PASS" if r["passed"] else "FAIL", r["text"], "|", r["evidence"])
