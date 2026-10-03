# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy>=1.26", "pillow>=10", "python-pptx>=1.0"]
# ///
"""Build a flat copy of an iteration for the skill-creator viewer (it only shows top-level files of outputs/).

    uv run evals/build_review.py <iteration dir> <review dir>

Per run: the executor's reply, a light GIF preview of the whole video (or the delivered GIF), a sheet with the
last frame of every clip, the main script, and the video/deck as downloads. Grading and metadata are copied.
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

from check_outputs import main_and_clips, probe

ENGINE = {"anim.py", "cut.py", "example.py", "check_outputs.py"}


def preview_gif(src, dst, width=480, fps=12):
    vf = (f"fps={fps},scale={width}:-1:flags=lanczos,split[a][b];[a]palettegen[p];[b][p]paletteuse=dither=bayer")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-vf", vf, str(dst)], check=True)


def clip_sheet(clips, dst, cols=3, w=480):
    with tempfile.TemporaryDirectory() as tmp:
        tiles = []
        for k, c in enumerate(clips, 1):
            n = int(probe(c).get("nb_frames", 1))
            png = Path(tmp) / f"{k}.png"
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(c), "-vf",
                            f"select=eq(n\\,{n - 1}),scale={w}:-1", "-frames:v", "1", str(png)], check=True)
            tiles.append((f"{k:02d}  {c.name}", Image.open(png).convert("RGB")))
        th = tiles[0][1].height + 22
        rows = -(-len(tiles) // cols)
        sheet = Image.new("RGB", (cols * (w + 10) + 10, rows * (th + 10) + 10), "white")
        d = ImageDraw.Draw(sheet)
        for i, (label, im) in enumerate(tiles):
            x, y = 10 + (i % cols) * (w + 10), 10 + (i // cols) * (th + 10)
            d.text((x, y), label, fill="black")
            sheet.paste(im, (x, y + 20))
            d.rectangle([x - 1, y + 19, x + w, y + 20 + im.height], outline=(190, 190, 190))
        sheet.save(dst)


def main_script(out):
    pys = [p for p in out.rglob("*.py") if p.name not in ENGINE and ".venv" not in p.parts]
    return max(pys, key=lambda p: p.stat().st_size) if pys else None


def build(run, dst):
    out = run / "outputs"
    dst_out = dst / "outputs"
    dst_out.mkdir(parents=True, exist_ok=True)
    for name in ("grading.json", "timing.json"):
        if (run / name).exists():
            shutil.copy(run / name, dst / name)
    if (run / "final_message.md").exists():
        shutil.copy(run / "final_message.md", dst_out / "0_reply.md")
    main, clips, _ = main_and_clips(out)
    gifs = sorted(out.rglob("*.gif"), key=lambda p: (len(p.relative_to(out).parts), -p.stat().st_size))
    gifs = [g for g in gifs if "clips" not in g.parts]
    if gifs and main is None or (gifs and "gif" in run.parent.name):
        shutil.copy(gifs[0], dst_out / "1_delivered.gif")
    elif main is not None:
        preview_gif(main, dst_out / "1_preview_of_video.gif")
    if clips:
        clip_sheet(clips, dst_out / "2_end_of_each_clip.png")
    sheets = list(out.rglob("*_pauses.png"))
    if sheets:
        shutil.copy(sheets[0], dst_out / "3_pause_sheet_made_by_run.png")
    script = main_script(out)
    if script:
        shutil.copy(script, dst_out / f"4_{script.name}")
    if main is not None:
        shutil.copy(main, dst_out / f"5_{main.name}")
    decks = list(out.rglob("*.pptx"))
    if decks:
        shutil.copy(decks[0], dst_out / f"6_{decks[0].name}")
    print(run.relative_to(run.parents[2]), "->", sorted(p.name for p in dst_out.iterdir()))


if __name__ == "__main__":
    it, review = Path(sys.argv[1]), Path(sys.argv[2])
    shutil.rmtree(review, ignore_errors=True)
    for ev in sorted(it.glob("eval-*")):
        (review / ev.name).mkdir(parents=True)
        shutil.copy(ev / "eval_metadata.json", review / ev.name / "eval_metadata.json")
        for run in sorted(p for p in ev.iterdir() if p.is_dir()):
            (review / ev.name / run.name).mkdir()
            shutil.copy(ev / "eval_metadata.json", review / ev.name / run.name / "eval_metadata.json")
            build(run, review / ev.name / run.name / "run-1")  # the layout aggregate_benchmark expects
