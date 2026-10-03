# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy>=1.26", "matplotlib>=3.8", "python-pptx>=1.0"]
# ///
"""Cut rendered videos into clips at the pauses in pauses.toml (one clip per slide).

    uv run animations/cut.py                # every video in pauses.toml: clips + pause sheets
    uv run animations/cut.py intro outro    # only these videos
    uv run animations/cut.py --sheet        # only the pause sheets (quick check of where the cuts fall)
    uv run animations/cut.py --gif          # also each clip as a GIF that plays once and holds its last frame
    uv run animations/cut.py --pptx         # also videos/clips/deck.pptx: one full-screen clip per slide, in order

Renders nothing new and writes only under videos/clips/:
    <video>/01.mp4, 02.mp4, ...   the last frame of each clip is the first frame of the next (seamless)
    <video>_pauses.png            the frame where each clip stops, with its instant
    deck.pptx                     slides in the order the videos were cut (pauses.toml order by default)
"""
import argparse
import shutil
import subprocess
import tempfile
import tomllib
from pathlib import Path

from anim import OUT, PAUSES_FILE, sheet, to_gif

DEST = OUT / "clips"


def run(*cmd):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *cmd], check=True)


def probe(path):
    """(frame count, fps) of a video."""
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=nb_frames,r_frame_rate", "-of", "default=noprint_wrappers=1", str(path)],
                         check=True, capture_output=True, text=True).stdout
    info = dict(line.split("=", 1) for line in out.split())
    num, den = info["r_frame_rate"].split("/")
    return int(info["nb_frames"]), int(num) / int(den)


def bounds(pauses, n, fps, name):
    """Cut frames [0, pause1, ..., last]: clip k runs from bounds[k-1] to bounds[k], both included."""
    frames = [int(round(t * fps)) for t in pauses]
    last = n - 1
    for t, f, prev in zip(pauses, frames, [0] + frames):
        if not 0 < f < last:
            raise SystemExit(f"{name}: pause {t} s is outside the video (0 to {last / fps:.2f} s)")
        if f - prev < 2:
            raise SystemExit(f"{name}: pause {t} s is out of order or glued to the previous one")
    if frames and last - frames[-1] < 2:
        raise SystemExit(f"{name}: the last pause is glued to the end of the video")
    return [0, *frames, last]


def cut(src, a, b, dst):
    run("-i", str(src), "-vf", f"trim=start_frame={a}:end_frame={b + 1},setpts=PTS-STARTPTS", "-an",
        "-c:v", "libx264", "-crf", "18", "-preset", "slow", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", str(dst))


def frame_png(src, f, dst):
    run("-i", str(src), "-vf", f"select=eq(n\\,{f})", "-frames:v", "1", str(dst))


# "Start: automatically", as PowerPoint writes it: plays on entering the slide and stays on the last frame;
# the next click moves to the next slide.
AUTOPLAY = """
<p:timing xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:tnLst><p:par>
 <p:cTn id="1" dur="indefinite" restart="never" nodeType="tmRoot"><p:childTnLst>
  <p:seq concurrent="1" nextAc="seek"><p:cTn id="2" dur="indefinite" nodeType="mainSeq"><p:childTnLst>
   <p:par><p:cTn id="3" fill="hold"><p:stCondLst><p:cond delay="indefinite"/>
     <p:cond evt="onBegin" delay="0"><p:tn val="2"/></p:cond></p:stCondLst><p:childTnLst>
    <p:par><p:cTn id="4" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst>
     <p:par><p:cTn id="5" presetID="1" presetClass="mediacall" presetSubtype="0" fill="hold"
       nodeType="afterEffect"><p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst>
      <p:cmd type="call" cmd="playFrom(0.0)"><p:cBhvr><p:cTn id="6" dur="{dur}" fill="hold"/>
       <p:tgtEl><p:spTgt spid="{spid}"/></p:tgtEl></p:cBhvr></p:cmd>
     </p:childTnLst></p:cTn></p:par>
    </p:childTnLst></p:cTn></p:par>
   </p:childTnLst></p:cTn></p:par>
  </p:childTnLst></p:cTn>
  <p:prevCondLst><p:cond evt="onPrev" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:prevCondLst>
  <p:nextCondLst><p:cond evt="onNext" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:nextCondLst>
  </p:seq>
  <p:video><p:cMediaNode vol="80000"><p:cTn id="7" fill="hold" display="0"><p:stCondLst>
   <p:cond delay="indefinite"/></p:stCondLst></p:cTn><p:tgtEl><p:spTgt spid="{spid}"/></p:tgtEl></p:cMediaNode>
  </p:video>
 </p:childTnLst></p:cTn>
</p:par></p:tnLst></p:timing>"""


def build_pptx(slides, dst):
    """slides: (clip, poster PNG, duration in ms, presenter note). 16:9, video full screen, no transitions."""
    from pptx import Presentation
    from pptx.oxml import parse_xml
    from pptx.oxml.ns import qn
    from pptx.util import Emu

    prs = Presentation()
    prs.slide_width, prs.slide_height = Emu(12192000), Emu(6858000)
    for clip, poster, dur_ms, note in slides:
        slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank
        movie = slide.shapes.add_movie(str(clip), 0, 0, prs.slide_width, prs.slide_height,
                                       poster_frame_image=str(poster), mime_type="video/mp4")
        old = slide._element.find(qn("p:timing"))
        old.addprevious(parse_xml(AUTOPLAY.format(dur=dur_ms, spid=movie.shape_id)))
        slide._element.remove(old)
        slide.notes_slide.notes_text_frame.text = note
    prs.save(dst)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("videos", nargs="*", help="sections of pauses.toml (default: all, in file order)")
    ap.add_argument("--sheet", action="store_true", help="only the pause sheets: cut nothing")
    ap.add_argument("--gif", action="store_true", help="also each clip as a GIF that plays once")
    ap.add_argument("--pptx", action="store_true", help="also build videos/clips/deck.pptx from the clips")
    args = ap.parse_args()
    if not PAUSES_FILE.exists():
        raise SystemExit(f"no {PAUSES_FILE}: render a video first (it writes its section there)")
    config = tomllib.loads(PAUSES_FILE.read_text())
    names = args.videos or list(config)
    for name in names:
        if name not in config:
            raise SystemExit(f"'{name}' is not in {PAUSES_FILE.name} (there: {', '.join(config)})")
        if not (OUT / f"{name}.mp4").exists():
            raise SystemExit(f"{OUT / name}.mp4 does not exist: render it first")
    DEST.mkdir(parents=True, exist_ok=True)
    slides = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for name in names:
            src, pauses = OUT / f"{name}.mp4", [float(t) for t in config[name].get("pauses", [])]
            n, fps = probe(src)
            b = bounds(pauses, n, fps, name)
            ends = [tmp / f"{name}_end{k:02d}.png" for k in range(1, len(b))]
            for f, png in zip(b[1:], ends):
                frame_png(src, f, png)
            labels = [f"{k:02d}   stops at {t:.2f} s" for k, t in enumerate(pauses, 1)]
            labels.append(f"{len(b) - 1:02d}   to the end ({b[-1] / fps:.2f} s)")
            sheet(ends, labels, f"{name}: where each clip stops", DEST / f"{name}_pauses.png")
            if args.sheet:
                continue
            out_dir = DEST / name
            shutil.rmtree(out_dir, ignore_errors=True)  # only this video's generated clips (no stale ones)
            out_dir.mkdir()
            for k, (a, e) in enumerate(zip(b[:-1], b[1:]), 1):
                clip, poster = out_dir / f"{k:02d}.mp4", tmp / f"{name}_start{k:02d}.png"
                cut(src, a, e, clip)
                if args.gif:
                    to_gif(clip, clip.with_suffix(".gif"), loop=-1)
                frame_png(src, a, poster)
                note = f"{name} · clip {k} of {len(b) - 1} · {a / fps:.2f}–{e / fps:.2f} s"
                slides.append((clip, poster, int(round((e - a + 1) / fps * 1000)), note))
            print(f"{name}: {len(b) - 1} clips in {out_dir}")
        if args.pptx and slides:
            build_pptx(slides, DEST / "deck.pptx")
            print(f"deck.pptx: {len(slides)} slides")
    print("pause sheets in", DEST)


if __name__ == "__main__":
    main()
