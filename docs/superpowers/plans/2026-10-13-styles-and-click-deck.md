# Deck por cliques, pergunta do produto final e estilos — plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** o plugin `mpl-animation` passa a (1) gerar um `.pptx` com um slide por vídeo cujos trechos aparecem e tocam
a cada clique, abaixo de uma barra de título; (2) perguntar o produto final (.gif/.mp4, e o .pptx) antes de planejar;
(3) oferecer estilos prontos, começando pela linha do tempo.

**Architecture:** o deck continua em `scripts/cut.py` (que já corta os trechos): funções pequenas e testáveis
(`clip_comments`, `video_box`, `bar_color`, `refuse_if_open`, `timing`, `build_pptx`, `check_deck`) e o `main` que as
liga. A pergunta e os estilos são texto no `SKILL.md`. Cada estilo é uma pasta `styles/<nome>/` com um script completo
(copiado para o projeto como o `example.py`), `preview.gif` e `sheet.png`.

**Tech Stack:** Python ≥ 3.11 com cabeçalhos PEP 723 e `uv run`; numpy, matplotlib, python-pptx (lxml vem com ele);
ffmpeg/ffprobe no PATH; pytest só para os testes (`uv run --with pytest …`).

**Spec:** `docs/superpowers/specs/2026-10-13-styles-and-click-deck-design.md`

## Global Constraints

- Nunca escrever em `/Users/hugocemep/GitHub/cemep/harness_presentation` (só leitura; outra sessão usa).
- Texto da skill (`SKILL.md`, `recipes.md`, docstrings, mensagens dos scripts) em inglês; `README.md` em português;
  texto na tela do estilo em inglês.
- Estilo do código: o dos scripts existentes — linhas até 120 colunas, docstrings curtas, poucos comentários, sem
  abstrações novas. Não há linter configurado.
- Slide 16:9 = 12192000 × 6858000 EMU; barra de título = 1239520 EMU de altura, cor padrão `#232751`; título em
  x = 806991 EMU, Arial 32 pt, negrito, branco, centralizado na vertical da barra; logo com altura 644550 EMU (52% da
  barra), centralizado na vertical da barra, margem direita 359252 EMU.
- Padrão de cliques: trecho 1 `mediacall`/`clickEffect`; cada trecho seguinte `entr`/`clickEffect` (visibilidade) +
  `mediacall`/`afterEffect`; `dur` = duração do trecho em ms; sem sequências `togglePause`.
- Nenhuma imagem de terceiros no repositório; `preview.gif` de estilo com 640 px, 12 fps, ≤ 3 MB.
- Toda mensagem de commit termina com:
  ```
  Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01RJzeEWjbBw3wVipfLsTfSJ
  ```
- Comando dos testes (da raiz do repositório):
  `uv run --with pytest --with numpy --with matplotlib --with python-pptx pytest tests -q`

## Review Focus

1. **O deck aberto no PowerPoint** quando o `cut.py --pptx` roda → recusa antes de cortar qualquer coisa, sem
   gravar por cima (teste `test_refuses_an_open_deck`, Task 2).
2. **`pauses.toml` editado à mão**: comentários reescritos, apagados, em menor número que os trechos, seções com nome
   entre aspas → as notas saem mesmo assim, sem erro (teste `test_clip_comments`, Task 2).
3. **Vídeo que não é 16:9** (vertical 1080×1920) → cabe abaixo da barra, centralizado, nada fora do slide (teste
   `test_video_box`, e o vídeo vertical em `test_deck_round_trip`, Task 2).
4. **`--bar` inválido ou `--logo` inexistente** → erro claro antes de cortar (teste `test_bar_color`; o logo,
   conferido à mão no passo de ponta a ponta da Task 2).
5. **Vídeo sem pausas** (um trecho só) → um slide com um trecho que toca no 1º clique, e a checagem passa (o vídeo
   "Vertical" de um trecho em `test_deck_round_trip`, Task 2).

---

### Task 1: título do slide no `pauses.toml` (e a base dos testes)

**Files:**
- Create: `tests/conftest.py`, `tests/test_engine.py`
- Modify: `skills/mpl-animation/scripts/anim.py` (`_TOML_HEAD` e `sync_pauses`, ~linhas 399–422)

**Interfaces:**
- Consumes: `anim.sync_pauses(name, total, pauses)`, `anim.PAUSES_FILE` (existentes).
- Produces: toda seção nova do `pauses.toml` tem `title = "<nome>"` antes de `pauses = [`. A Task 2 lê
  `config[name].get("title", name)`.

- [ ] **Step 1: Write the failing test**

`tests/conftest.py`:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "mpl-animation" / "scripts"))
```

`tests/test_engine.py`:

```python
"""Checks of the engine's logic (no rendering):
uv run --with pytest --with numpy --with matplotlib --with python-pptx pytest tests -q"""
import tomllib

import anim


def test_new_pauses_section_has_a_title(tmp_path, monkeypatch):
    monkeypatch.setattr(anim, "PAUSES_FILE", tmp_path / "pauses.toml")
    anim.sync_pauses("intro", 12.0, [(1.9, "flow", 1), (4.5, "flow", 2)])
    section = tomllib.loads((tmp_path / "pauses.toml").read_text())["intro"]
    assert section["title"] == "intro"
    assert section["pauses"] == [1.9, 4.5]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --with pytest --with numpy --with matplotlib --with python-pptx pytest tests -q`
Expected: FAIL com `KeyError: 'title'`.

- [ ] **Step 3: Write minimal implementation**

Em `anim.py`, troque `_TOML_HEAD` por:

```python
_TOML_HEAD = """\
# Where each video is cut into clips. Each number is an instant of the video, in seconds: the clip before it stops
# on that frame and the next clip starts from it. Delete a number to merge two clips, add one to split. Describe in
# each comment what is on screen at that stop: it becomes the presenter note of that click in the deck.
# `title` is the video's slide title in `cut.py --pptx`; section order = slide order.
"""
```

e, em `sync_pauses`, a linha que monta o bloco:

```python
        block = "\n".join([f"\n[{key}]  # {total:.1f} s", f'title = "{name}"', "pauses = [", *rows, "]"])
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --with pytest --with numpy --with matplotlib --with python-pptx pytest tests -q`
Expected: `1 passed`.
Run também: `uv run --with numpy --with matplotlib skills/mpl-animation/scripts/anim.py`
Expected: `anim.py self-check ok`.

- [ ] **Step 5: Commit**

```bash
git add tests/conftest.py tests/test_engine.py skills/mpl-animation/scripts/anim.py
git commit -m "anim: write a slide title into each new pauses.toml section

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01RJzeEWjbBw3wVipfLsTfSJ"
```

---

### Task 2: o deck por cliques em `cut.py`

**Files:**
- Modify: `skills/mpl-animation/scripts/cut.py` (reescrito por inteiro; abaixo, o arquivo completo)
- Test: `tests/test_engine.py` (acrescentar)

**Interfaces:**
- Consumes: `title` nas seções do `pauses.toml` (Task 1); de `anim`: `OUT`, `PAUSES_FILE`, `sheet`, `to_gif`.
- Produces (usado pelos testes e, por nome, pela Task 5):
  - `probe(path) -> (frames: int, fps: float, width: int, height: int)`
  - `clip_comments(text: str, name: str) -> list[str]`
  - `video_box(vw: int, vh: int) -> (x, y, w, h)` em EMU
  - `bar_color(s: str) -> str` (6 hex maiúsculos, sem `#`; `argparse.ArgumentTypeError` se inválido)
  - `refuse_if_open(deck: Path) -> None` (`SystemExit` se `~$<nome>` existe)
  - `timing(spids: list[int], durs: list[int]) -> str` (o `<p:timing>`)
  - `build_pptx(videos, dst, bar=BAR, logo=None)` e `check_deck(deck, videos)`, com
    `videos = [(title, clips, notes)]`, `clips = [(mp4: Path, poster: Path, dur_ms: int, width: int, height: int)]`,
    `notes = [str, …]` (uma linha por clique)
  - constantes `SLIDE_W, SLIDE_H, BAR_H, BAR`
  - nos slides: a barra se chama `"title bar"`, o título `"title"`, o logo `"logo"`, os trechos `"01"`, `"02"`…

- [ ] **Step 1: Write the failing tests**

Acrescente a `tests/test_engine.py` (os imports vão para o topo do arquivo):

```python
import argparse
import re
import subprocess
import xml.etree.ElementTree as ET

import pytest

import cut

PAUSES = '''
[intro]  # 12.0 s
title = "Intro"
pauses = [
  1.9,    # 1  flow, step 1
  4.5,    # the fitted line
          # 3  (to the end)
]

["my video"]  # 5.0 s
pauses = [
  2.0,    # 1  a, step 1
]
'''


def test_clip_comments():
    assert cut.clip_comments(PAUSES, "intro") == ["flow, step 1", "the fitted line", "(to the end)"]
    assert cut.clip_comments(PAUSES, "my video") == ["a, step 1"]
    assert cut.clip_comments(PAUSES, "missing") == []


def test_video_box():
    assert cut.video_box(1920, 1080) == (1101795, 1239520, 9988409, 5618480)
    x, y, w, h = cut.video_box(1080, 1920)  # vertical: as tall as the room under the bar, centered
    assert y == cut.BAR_H and h == cut.SLIDE_H - cut.BAR_H and abs(2 * x + w - cut.SLIDE_W) <= 1


def test_bar_color():
    assert cut.bar_color("#232751") == "232751" and cut.bar_color("1f4e79") == "1F4E79"
    with pytest.raises(argparse.ArgumentTypeError):
        cut.bar_color("navy")


def test_timing_pattern():
    xml = cut.timing([5, 6, 7], [1000, 2000, 3000])
    ET.fromstring(xml)  # well-formed
    kinds = re.findall(r'presetClass="(\w+)"[^>]*nodeType="(\w+)"', xml)
    assert kinds == [("mediacall", "clickEffect"), ("entr", "clickEffect"), ("mediacall", "afterEffect"),
                     ("entr", "clickEffect"), ("mediacall", "afterEffect")]
    plays = re.findall(r'dur="(\d+)" fill="hold"/><p:tgtEl><p:spTgt spid="(\d+)"', xml)
    assert plays == [("1000", "5"), ("2000", "6"), ("3000", "7")]
    ids = [int(i) for i in re.findall(r'<p:cTn id="(\d+)"', xml)]
    assert ids == sorted(set(ids))  # unique, in document order
    assert "togglePause" not in xml


def make_clip(path, size="320x180"):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"testsrc=size={size}:rate=30",
                    "-t", "1", "-pix_fmt", "yuv420p", "-c:v", "libx264", str(path)], check=True)
    poster = path.with_suffix(".png")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(path), "-frames:v", "1", str(poster)], check=True)
    n, fps, w, h = cut.probe(path)
    return path, poster, round(n / fps * 1000), w, h


def test_deck_round_trip(tmp_path):
    a = [make_clip(tmp_path / f"a{k}.mp4") for k in (1, 2, 3)]
    b = [make_clip(tmp_path / "b1.mp4", "180x320")]  # one clip (no pauses), vertical
    videos = [("Intro", a, ["click 1 · x", "click 2", "click 3"]), ("Vertical", b, ["click 1"])]
    deck = tmp_path / "deck.pptx"
    cut.build_pptx(videos, deck, "232751", a[0][1])
    cut.check_deck(deck, videos)
    with pytest.raises(SystemExit, match="notes"):
        cut.check_deck(deck, [videos[0], ("Vertical", b, ["other"])])
    with pytest.raises(SystemExit, match="slides"):
        cut.check_deck(deck, videos[:1])


def test_refuses_an_open_deck(tmp_path):
    deck = tmp_path / "deck.pptx"
    cut.refuse_if_open(deck)  # nothing open: fine
    (tmp_path / "~$deck.pptx").write_text("")
    with pytest.raises(SystemExit, match="open in PowerPoint"):
        cut.refuse_if_open(deck)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --with pytest --with numpy --with matplotlib --with python-pptx pytest tests -q`
Expected: FAIL — `AttributeError: module 'cut' has no attribute 'clip_comments'` (e as outras funções novas);
`test_new_pauses_section_has_a_title` continua passando.

- [ ] **Step 3: Write the implementation**

Substitua `skills/mpl-animation/scripts/cut.py` inteiro por:

```python
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy>=1.26", "matplotlib>=3.8", "python-pptx>=1.0"]
# ///
"""Cut rendered videos into clips at the pauses in pauses.toml, and optionally build a deck that plays them.

    uv run animations/cut.py                # every video in pauses.toml: clips + pause sheets
    uv run animations/cut.py intro outro    # only these videos
    uv run animations/cut.py --sheet        # only the pause sheets (quick check of where the cuts fall)
    uv run animations/cut.py --gif          # also each clip as a GIF that plays once and holds its last frame
    uv run animations/cut.py --pptx         # also videos/clips/deck.pptx: one slide per video, one click per clip
    uv run animations/cut.py --pptx --bar '#1f4e79' --logo animations/data/logo.png   # title bar color, a logo

Renders nothing new and writes only under videos/clips/:
    <video>/01.mp4, 02.mp4, ...   the last frame of each clip is the first frame of the next (seamless)
    <video>_pauses.png            the frame where each clip stops, with its instant
    deck.pptx                     one 16:9 slide per video cut in this run, in pauses.toml order: a title bar (the
                                  video's `title` in pauses.toml) and under it the video's clips, stacked. Clip 1
                                  plays on the first click; each next click shows the next clip and plays it. The
                                  notes list each click with its pause comment. Checked after saving.
"""
import argparse
import itertools
import re
import shutil
import subprocess
import tempfile
import tomllib
from pathlib import Path

from anim import OUT, PAUSES_FILE, sheet, to_gif

DEST = OUT / "clips"
# the deck, in EMU: a 16:9 slide; a title bar 18% of its height; the title's left edge; the logo's height and margin
SLIDE_W, SLIDE_H, BAR_H = 12192000, 6858000, 1239520
TITLE_X, LOGO_H, LOGO_MARGIN = 806991, 644550, 359252
BAR = "232751"


def run(*cmd):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *cmd], check=True)


def probe(path):
    """(frame count, fps, width, height) of a video."""
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=nb_frames,r_frame_rate,width,height", "-of", "default=noprint_wrappers=1",
                          str(path)], check=True, capture_output=True, text=True).stdout
    info = dict(line.split("=", 1) for line in out.split())
    num, den = info["r_frame_rate"].split("/")
    return int(info["nb_frames"]), int(num) / int(den), int(info["width"]), int(info["height"])


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


ROW = re.compile(r"^\s*(?:[\d.]+\s*,\s*)?#\s*(.*?)\s*$")  # a pause line with its comment, or a comment alone


def clip_comments(text, name):
    """The comment of each clip of video `name`, in order, from the text of pauses.toml (tomllib drops comments):
    the one on each pause line, then the one after the last pause. The clip number anim.py writes in front of the
    comment ("2  scene, step 1") is left out."""
    head = re.compile(r'^\[\s*"?' + re.escape(name) + r'"?\s*\]')
    out, inside = [], False
    for line in text.splitlines():
        if head.match(line):
            inside = True
        elif inside and line.lstrip().startswith("["):
            break
        elif inside and (m := ROW.match(line)):
            k, c = str(len(out) + 1), m.group(1)
            out.append(c[len(k):].strip() if c.startswith(k + " ") else c)
    return out


def video_box(vw, vh):
    """(x, y, w, h) in EMU: the largest vw:vh rectangle under the title bar, centered, touching the bar."""
    s = min(SLIDE_W / vw, (SLIDE_H - BAR_H) / vh)
    w, h = round(vw * s), round(vh * s)
    return (SLIDE_W - w) // 2, BAR_H, w, h


def bar_color(s):
    """'#232751' or '232751' -> '232751' (the type of --bar)."""
    if not re.fullmatch(r"#?[0-9A-Fa-f]{6}", s):
        raise argparse.ArgumentTypeError(f"{s!r} is not a color like '#232751'")
    return s.lstrip("#").upper()


def refuse_if_open(deck):
    """PowerPoint keeps ~$<name> beside a deck it has open: writing the deck then would lose the edits made there."""
    if (deck.parent / f"~${deck.name}").exists():
        raise SystemExit(f"{deck.name} is open in PowerPoint: close it (save it under another name to keep any "
                         "edits) and run again")


# A slide's animation as PowerPoint writes it (ported from a deck it played). Each click is one <p:par> of the main
# sequence: the first plays clip 1, which is on screen from the start; every other one makes its clip appear and
# then play. No togglePause triggers: a mouse click on a video advances, like the clicker.
CLICK = ('<p:par><p:cTn id="{id}" fill="hold"><p:stCondLst><p:cond delay="indefinite"/></p:stCondLst>'
         '<p:childTnLst>{body}</p:childTnLst></p:cTn></p:par>')
APPEAR = ('<p:par><p:cTn id="{a}" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst>'
          '<p:par><p:cTn id="{b}" presetID="1" presetClass="entr" presetSubtype="0" fill="hold" '
          'nodeType="clickEffect"><p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst><p:set><p:cBhvr>'
          '<p:cTn id="{c}" dur="1" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst></p:cTn>'
          '<p:tgtEl><p:spTgt spid="{sp}"/></p:tgtEl><p:attrNameLst><p:attrName>style.visibility</p:attrName>'
          '</p:attrNameLst></p:cBhvr><p:to><p:strVal val="visible"/></p:to></p:set></p:childTnLst></p:cTn></p:par>'
          '</p:childTnLst></p:cTn></p:par>')
PLAY = ('<p:par><p:cTn id="{a}" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst>'
        '<p:par><p:cTn id="{b}" presetID="1" presetClass="mediacall" presetSubtype="0" fill="hold" '
        'nodeType="{node}"><p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst>'
        '<p:cmd type="call" cmd="playFrom(0.0)"><p:cBhvr><p:cTn id="{c}" dur="{dur}" fill="hold"/>'
        '<p:tgtEl><p:spTgt spid="{sp}"/></p:tgtEl></p:cBhvr></p:cmd></p:childTnLst></p:cTn></p:par>'
        '</p:childTnLst></p:cTn></p:par>')
MEDIA = ('<p:video><p:cMediaNode vol="80000"><p:cTn id="{id}" fill="hold" display="0"><p:stCondLst>'
         '<p:cond delay="indefinite"/></p:stCondLst></p:cTn><p:tgtEl><p:spTgt spid="{sp}"/></p:tgtEl>'
         '</p:cMediaNode></p:video>')
TIMING = ('<p:timing xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:tnLst><p:par>'
          '<p:cTn id="1" dur="indefinite" restart="never" nodeType="tmRoot"><p:childTnLst>'
          '<p:seq concurrent="1" nextAc="seek"><p:cTn id="2" dur="indefinite" nodeType="mainSeq"><p:childTnLst>'
          '{clicks}</p:childTnLst></p:cTn><p:prevCondLst><p:cond evt="onPrev" delay="0"><p:tgtEl><p:sldTgt/>'
          '</p:tgtEl></p:cond></p:prevCondLst><p:nextCondLst><p:cond evt="onNext" delay="0"><p:tgtEl><p:sldTgt/>'
          '</p:tgtEl></p:cond></p:nextCondLst></p:seq>{media}</p:childTnLst></p:cTn></p:par></p:tnLst></p:timing>')


def timing(spids, durs):
    """The <p:timing> of a slide whose clips (shape ids `spids`, durations `durs` in ms) play one per click."""
    ids = itertools.count(3)  # 1 and 2 are the root and the main sequence
    clicks = []
    for k, (sp, dur) in enumerate(zip(spids, durs)):
        cid = next(ids)
        appear = "" if k == 0 else APPEAR.format(a=next(ids), b=next(ids), c=next(ids), sp=sp)
        play = PLAY.format(a=next(ids), b=next(ids), c=next(ids), sp=sp, dur=dur,
                           node="clickEffect" if k == 0 else "afterEffect")
        clicks.append(CLICK.format(id=cid, body=appear + play))
    media = "".join(MEDIA.format(id=next(ids), sp=sp) for sp in spids)
    return TIMING.format(clicks="".join(clicks), media=media)


def build_pptx(videos, dst, bar=BAR, logo=None):
    """videos: [(title, clips, notes)], clips = [(mp4, poster png, duration ms, width, height)], notes = one line
    per click. One slide per video: the title bar, then the clips stacked in order (01 at the back)."""
    from pptx import Presentation
    from pptx.dml.color import RGBColor
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.enum.text import MSO_ANCHOR
    from pptx.oxml import parse_xml
    from pptx.oxml.ns import qn
    from pptx.util import Emu, Pt

    prs = Presentation()
    prs.slide_width, prs.slide_height = Emu(SLIDE_W), Emu(SLIDE_H)
    for title, clips, notes in videos:
        slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank
        band = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SLIDE_W, BAR_H)
        band.name = "title bar"
        band.fill.solid()
        band.fill.fore_color.rgb = RGBColor.from_string(bar)
        band.line.fill.background()
        band.shadow.inherit = False
        box = slide.shapes.add_textbox(TITLE_X, 0, SLIDE_W - TITLE_X - 2 * LOGO_MARGIN - LOGO_H, BAR_H)
        box.name = "title"
        box.text_frame.vertical_anchor = MSO_ANCHOR.MIDDLE
        box.text_frame.word_wrap = True
        r = box.text_frame.paragraphs[0].add_run()
        r.text = title
        r.font.name, r.font.size, r.font.bold = "Arial", Pt(32), True
        r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        if logo:
            pic = slide.shapes.add_picture(str(logo), 0, (BAR_H - LOGO_H) // 2, height=LOGO_H)
            pic.left = SLIDE_W - LOGO_MARGIN - pic.width
            pic.name = "logo"
        spids, durs = [], []
        for k, (mp4, poster, dur, vw, vh) in enumerate(clips, 1):
            movie = slide.shapes.add_movie(str(mp4), *video_box(vw, vh), poster_frame_image=str(poster),
                                           mime_type="video/mp4")
            movie.name = f"{k:02d}"
            spids.append(movie.shape_id)
            durs.append(dur)
        old = slide._element.find(qn("p:timing"))  # add_movie writes a timing of its own: replace it
        old.addprevious(parse_xml(timing(spids, durs)))
        slide._element.remove(old)
        slide.notes_slide.notes_text_frame.text = "\n".join(notes)
    prs.save(dst)


def check_deck(deck, videos):
    """Reopen the deck and check what PowerPoint will play, against `videos` as given to build_pptx: one slide per
    video with its title; its clips in order, under the title bar and inside the slide; the click pattern; each
    play as long as its clip; the notes. Stops with an error otherwise."""
    from lxml import etree
    from pptx import Presentation
    from pptx.oxml.ns import qn

    slides = list(Presentation(deck).slides)
    if len(slides) != len(videos):
        raise SystemExit(f"{deck.name}: {len(slides)} slides for {len(videos)} videos")
    for n, (slide, (title, clips, notes)) in enumerate(zip(slides, videos), 1):
        def bad(why):
            return SystemExit(f"{deck.name}, slide {n} ({title}): {why}")
        movies = [s for s in slide.shapes if s._element.find(".//" + qn("a:videoFile")) is not None]
        if len(movies) != len(clips):
            raise bad(f"{len(movies)} videos for {len(clips)} clips")
        for m in movies:
            if m.top < BAR_H or m.left < 0 or m.left + m.width > SLIDE_W or m.top + m.height > SLIDE_H:
                raise bad(f"video {m.name} is not under the title bar and inside the slide")
        xml = etree.tostring(slide._element.find(qn("p:timing"))).decode()
        kinds = re.findall(r'presetClass="(\w+)"[^>]*nodeType="(\w+)"', xml)
        want = [("mediacall", "clickEffect")] + [("entr", "clickEffect"), ("mediacall", "afterEffect")] * (
            len(clips) - 1)
        if kinds != want:
            raise bad(f"click pattern {kinds}")
        plays = re.findall(r'dur="(\d+)" fill="hold"/><p:tgtEl><p:spTgt spid="(\d+)"', xml)
        if [int(sp) for _, sp in plays] != [m.shape_id for m in movies]:
            raise bad("the clips do not play in order")
        for (dur, _), (mp4, *_) in zip(plays, clips):
            frames, fps, _, _ = probe(mp4)
            if abs(int(dur) - frames / fps * 1000) > 50:
                raise bad(f"{mp4.name} plays for {dur} ms but lasts {frames / fps * 1000:.0f} ms")
        if title not in [s.text_frame.text for s in slide.shapes if s.has_text_frame]:
            raise bad("no title")
        if slide.notes_slide.notes_text_frame.text != "\n".join(notes):
            raise bad("the notes differ")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("videos", nargs="*", help="sections of pauses.toml (default: all, in file order)")
    ap.add_argument("--sheet", action="store_true", help="only the pause sheets: cut nothing")
    ap.add_argument("--gif", action="store_true", help="also each clip as a GIF that plays once")
    ap.add_argument("--pptx", action="store_true", help="also build videos/clips/deck.pptx from the clips")
    ap.add_argument("--bar", type=bar_color, default=BAR, help="the deck's title bar color (default #%(default)s)")
    ap.add_argument("--logo", type=Path, help="a picture for the right end of the deck's title bar")
    args = ap.parse_args()
    if not PAUSES_FILE.exists():
        raise SystemExit(f"no {PAUSES_FILE}: render a video first (it writes its section there)")
    if args.logo and not args.logo.is_file():
        raise SystemExit(f"{args.logo} does not exist")
    text = PAUSES_FILE.read_text()
    config = tomllib.loads(text)
    names = args.videos or list(config)
    for name in names:
        if name not in config:
            raise SystemExit(f"'{name}' is not in {PAUSES_FILE.name} (there: {', '.join(config)})")
        if not (OUT / f"{name}.mp4").exists():
            raise SystemExit(f"{OUT / name}.mp4 does not exist: render it first")
    deck = DEST / "deck.pptx"
    if args.pptx:
        refuse_if_open(deck)
    DEST.mkdir(parents=True, exist_ok=True)
    videos = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for name in names:
            src, pauses = OUT / f"{name}.mp4", [float(t) for t in config[name].get("pauses", [])]
            n, fps, vw, vh = probe(src)
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
            comments = clip_comments(text, name)
            clips, notes = [], []
            for k, (a, e) in enumerate(zip(b[:-1], b[1:]), 1):
                clip, poster = out_dir / f"{k:02d}.mp4", tmp / f"{name}_start{k:02d}.png"
                cut(src, a, e, clip)
                if args.gif:
                    to_gif(clip, clip.with_suffix(".gif"), loop=-1)
                frame_png(src, a, poster)
                clips.append((clip, poster, int(round((e - a + 1) / fps * 1000)), vw, vh))
                comment = comments[k - 1] if k <= len(comments) else ""
                notes.append(f"click {k} · {a / fps:.2f}–{e / fps:.2f} s · {comment}".rstrip(" ·"))
            videos.append((config[name].get("title", name), clips, notes))
            print(f"{name}: {len(clips)} clips in {out_dir}")
        if args.pptx and videos:
            build_pptx(videos, deck, args.bar, args.logo)
            check_deck(deck, videos)
            print(f"{deck.name}: {len(videos)} slides, {sum(len(c) for _, c, _ in videos)} clips, checked")
    print("pause sheets in", DEST)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --with pytest --with numpy --with matplotlib --with python-pptx pytest tests -q`
Expected: `7 passed`.

- [ ] **Step 5: De ponta a ponta com um vídeo de verdade**

```bash
E2E=${TMPDIR:-/tmp}/mpl-animation-e2e; rm -rf "$E2E"; mkdir -p "$E2E/animations"
cp skills/mpl-animation/scripts/{anim,cut,example}.py "$E2E/animations/"
ffmpeg -y -loglevel error -f lavfi -i color=c=white:s=200x200 -frames:v 1 "$E2E/logo.png"
uv run "$E2E/animations/example.py"
grep -n 'title' "$E2E/animations/pauses.toml"
sed -i '' 's/^title = "averaging"/title = "Averaging scans"/' "$E2E/animations/pauses.toml"
uv run "$E2E/animations/cut.py" --pptx --logo "$E2E/logo.png"
```

Expected: o `grep` mostra `title = "averaging"`; o `cut.py` termina com
`deck.pptx: 1 slides, N clips, checked` (N = número de trechos do `averaging`, 4 ou mais).

Conferir também as entradas ruins (Review Focus 4), cada uma deve parar com a mensagem, sem cortar nada:

```bash
uv run "$E2E/animations/cut.py" --pptx --bar navy        # argument --bar: 'navy' is not a color like '#232751'
uv run "$E2E/animations/cut.py" --pptx --logo /nao/existe.png   # /nao/existe.png does not exist
touch "$E2E/videos/clips/~\$deck.pptx"; uv run "$E2E/animations/cut.py" --pptx; rm "$E2E/videos/clips/~\$deck.pptx"
# deck.pptx is open in PowerPoint: close it (...)
```

- [ ] **Step 6: Abrir no PowerPoint**

```bash
E2E=${TMPDIR:-/tmp}/mpl-animation-e2e
open -a "Microsoft PowerPoint" "$E2E/videos/clips/deck.pptx"; osascript -e 'delay 8'
screencapture -x "$E2E/powerpoint.png"
```

Leia `$E2E/powerpoint.png` com Read. Expected: o deck aberto, sem diálogo de reparo ("PowerPoint found a problem
with content…"); o slide 1 com a barra azul-marinho, "Averaging scans" em branco, o logo à direita e o vídeo
abaixo. Se aparecer o diálogo de reparo: PARE e reporte (não siga para o commit). Depois feche sem salvar:

```bash
osascript -e 'tell application "Microsoft PowerPoint" to close active presentation saving no'
```

- [ ] **Step 7: Commit**

```bash
git add skills/mpl-animation/scripts/cut.py tests/test_engine.py
git commit -m "cut: deck with one slide per video, clips that appear and play one per click

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01RJzeEWjbBw3wVipfLsTfSJ"
```

---

### Task 3: a pergunta do produto final e a documentação do deck

**Files:**
- Modify: `skills/mpl-animation/SKILL.md`, `skills/mpl-animation/references/recipes.md` (seção 14),
  `README.md`

**Interfaces:**
- Consumes: as opções `--pptx`, `--bar`, `--logo` e a chave `title` (Tasks 1–2).
- Produces: a seção `## Ask what to deliver` do `SKILL.md`, à qual a Task 4 acrescenta a oferta de estilos (já
  mencionada aqui, apontando para `## Styles`).

- [ ] **Step 1: `SKILL.md` — descrição e introdução**

Na linha `description:` do frontmatter, troque
`rendered to MP4 (default) or GIF and then cut into clips at the pauses (one clip per slide, optionally a ready PowerPoint deck), so a presenter can talk between movements.`
por
`rendered to MP4 or GIF and then cut into clips at the pauses, optionally with a ready PowerPoint deck where each click plays the next clip, so a presenter can talk between movements.`

No parágrafo de abertura, troque `` a cutter (`scripts/cut.py`), a complete template
(`scriptas/example.py`) `` por `` a cutter that also builds the deck (`scripts/cut.py`), a complete template
(`scripts/example.py`) `` (isto também corrige o `scriptas/`, erro de digitação não commitado).

Em `## The rule: build in steps, then cut into clips`, troque as frases
`In a slide deck each clip plays by itself and stops on its last frame while the presenter talks; the next click starts the next clip from exactly that frame.`
por
`In the deck each video is one slide: a click plays a clip, which stops on its last frame while the presenter talks; the next click shows the next clip on top of it and plays it from exactly that frame.`

- [ ] **Step 2: `SKILL.md` — a regra "Ask what to deliver"**

Apague desde `Default deliverables for every animation:` até `what you made.` (a tabela, a lista "The user can ask
for something else" e o parágrafo "Don't ask about these…") e ponha no lugar:

```markdown
## Ask what to deliver

Before planning, ask what the user wants to get, in one round of questions (AskUserQuestion when available), and
only what the request leaves open:

1. **Format**: MP4, GIF, or both.
2. **If MP4**: also a PowerPoint deck, each video on one slide whose clips play one per click?

Read the request first. ".pptx", "PowerPoint", "slides" or "to present" means MP4 + deck: nothing to ask about the
format. "GIF" alone means a GIF: nothing to ask. "Video" or "MP4" without a deck: ask only about the deck. A change,
re-timing, re-cut or new version of an existing animation keeps the deliverables it already has: ask nothing. If the
content fits a style (see Styles), offer it in the same round, next to "free", with the path of its `preview.gif`.

| Choice | Deliverables |
|---|---|
| GIF | `videos/<name>.gif` (`--gif`), 960 px, 20 fps; no clips (a GIF has no pause control); the MP4 it is made from stays in `videos/` |
| MP4 | `videos/<name>.mp4` (1920×1080, 30 fps, H.264) and its last frame `videos/<name>.png`; the clips cut at the pauses, `videos/clips/<name>/01.mp4`, `02.mp4`, …; a sheet with the frame where each clip stops, `videos/clips/<name>_pauses.png`; the cut points, one comment per stop, in a `[<name>]` section of `animations/pauses.toml` |
| MP4 + deck | all of the above, a slide title (`title`) in each video's section of `pauses.toml`, and `videos/clips/deck.pptx` (`cut.py --pptx`) |

Everything else has a default and is not asked: make it and say what you made. When the user asks for it:

- **One continuous video** (website, social media): render and skip the cut. Still build it in steps: it costs
  nothing, and the pause checks keep catching half-finished frames.
- **Another size, frame rate or aspect**: `W`, `H`, `FPS` at the top of `anim.py` (the canvas height follows).
- **Clip GIFs** that play once and hold: `cut.py --gif`.
- **The deck's look**: `cut.py --pptx --bar '#RRGGBB' --logo <png>` (the title bar's color, a logo at its right end).
```

- [ ] **Step 3: `SKILL.md` — Workflow, formatos e entrega**

Em `## Workflow`, insira como primeiro item e renumere os demais (2 a 8):

```markdown
1. **Ask** what to deliver (above), unless the request already says it all.
```

No item **Pauses**, troque `Replace each comment with what is on screen there: it documents the clips for whoever
presents.` por `Replace each comment with what is on screen there: it documents the clips for whoever presents and
becomes the presenter note of that click in the deck. With a deck, set the video's `title` too: it is the slide
title.`

No item **Cut**, troque `(with `--gif` and `--pptx` as needed)` por `(with `--gif` and `--pptx` as chosen)`.

Em `## Output formats`, depois do item **GIF**, acrescente:

```markdown
- **Deck** (`cut.py --pptx`): `videos/clips/deck.pptx`, one 16:9 slide per video: a title bar (`#232751` by
  default, `--bar`; the video's `title`; `--logo` at its right end) and under it the video's clips, stacked at the
  largest size that fits. Clip 1 plays on the first click; each next click shows the next clip and plays it. The
  presenter notes list each click with its pause comment. `cut.py` checks the deck after saving and will not
  overwrite it while PowerPoint has it open. By hand, and in Keynote or Google Slides: `references/recipes.md`,
  section 14.
```

Em `## Before saying it's done`, no item 3, troque `how to change the pauses (edit `pauses.toml`, run `cut.py`
again);` por `how to change the pauses (edit `pauses.toml`, run `cut.py` again); with a deck, that it was checked in
structure and should be played once in presentation mode on the presenting computer;`.

- [ ] **Step 4: `recipes.md` — seção 14**

Substitua a seção `## 14. Presenting the clips` inteira (até antes de `## 15. Pitfalls`) por:

```markdown
## 14. Presenting the clips

`cut.py --pptx` writes `videos/clips/deck.pptx`: 16:9, one slide per video, a title bar on top (`--bar` color,
`--logo`, the title from `title` in `pauses.toml`) and the video's clips stacked under it at the same place. Clip 1
is on screen when the slide opens and plays on the first click; each further click shows the next clip on top and
plays it. Each clip starts on the frame where the previous one stopped, so the audience sees one video that pauses.
The presenter notes list each click with its pause comment. Copy the slides into the real deck (paste with "keep
source formatting"). The deck is checked in structure; play it once in presentation mode on the presenting
computer.

By hand:

- **PowerPoint**, one slide per video: insert every clip at the same position and size, in order (01 at the back).
  Animations: clip 01 → Play, "On Click"; each next clip → Appear, "On Click", then Play, "After Previous".
  Playback: "Rewind after playing" off (keeps the last frame on screen), "Hide while not playing" off. Transitions →
  None.
- **Keynote**: one clip per slide, full size; in the Movie tab of the Format sidebar, start the movie automatically
  and set Repeat to None; no transition.
- **Google Slides**: one clip per slide, inserted from Drive; Format options → Video playback → Play
  (automatically). Slides shows a poster frame between clips, so the joins are less seamless.

While presenting, a click while a clip is still moving starts the next one and cuts the movement: wait for it to
stop.
```

- [ ] **Step 5: `README.md`**

Troque o primeiro parágrafo de `## Usar` (de `É só pedir:` até `o `.pptx` montado, outro tamanho.`) por:

```markdown
É só pedir: "faz uma animação mostrando como a coluna separa dois compostos", "anima essa curva de calibração para
a apresentação", "um GIF para o README mostrando o gradiente descendente". A skill primeiro pergunta o que você quer
receber — .gif e/ou .mp4 e, com .mp4, se quer também o `.pptx` — só o que o pedido não disse. Depois copia o motor
para `<projeto>/animations/` e segue a regra: planejar as etapas → conferir quadros sem renderizar → renderizar →
cortar em trechos → conferir a folha de pausas → listar os fatos na tela para você conferir.

O `.pptx` tem um slide por vídeo: uma barra de título (cor e logo à escolha) e, embaixo, os trechos empilhados. O
trecho 1 toca no primeiro clique e cada clique seguinte mostra e toca o próximo, então você encaixa a fala nas
pausas. As notas do apresentador trazem o que está na tela em cada clique.
```

No bloco de comandos, troque a linha do `cut.py` por:

```
uv run animations/cut.py [vídeos] [--gif] [--pptx] [--bar '#232751'] [--logo logo.png] [--sheet]
```

Na tabela, troque o papel do `cut.py` por: `corta nos pontos de `pauses.toml`, folhas de pausas, GIFs dos
trechos, `.pptx` com um slide por vídeo e um clique por trecho`.

- [ ] **Step 6: Conferir**

Run: `grep -n "scriptas\|one clip per slide\|full-screen autoplay\|Don't ask about these" skills/mpl-animation/SKILL.md skills/mpl-animation/references/recipes.md README.md`
Expected: nenhuma linha.
Run: `grep -c "Ask what to deliver" skills/mpl-animation/SKILL.md`
Expected: `1` ou mais. Leia o `SKILL.md` inteiro uma vez: a numeração do Workflow vai de 1 a 8 e nada se contradiz.

- [ ] **Step 7: Commit**

```bash
git add skills/mpl-animation/SKILL.md skills/mpl-animation/references/recipes.md README.md
git commit -m "Skill: ask what to deliver; document the click deck

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01RJzeEWjbBw3wVipfLsTfSJ"
```

---

### Task 4: o estilo linha do tempo

**Files:**
- Create: `skills/mpl-animation/styles/timeline/timeline.py`, `skills/mpl-animation/styles/timeline/preview.gif`,
  `skills/mpl-animation/styles/timeline/sheet.png`
- Modify: `skills/mpl-animation/SKILL.md` (descrição, Setup, nova seção `## Styles`),
  `skills/mpl-animation/references/recipes.md` (seção 4), `README.md`

**Interfaces:**
- Consumes: de `anim`: `BLUE, CW, D, INK, INK_2, MUTED, SURFACE, Scene, arrow, circle, heading, image, lerp,
  line_h, main, mix, pop, ramp, steps, text_w, txt` (todos existentes).
- Produces: `styles/timeline/` no formato da spec; `NAME = "timeline"`; 9 trechos.

- [ ] **Step 1: Conferir os fatos**

Com WebSearch, confirme cada linha abaixo (já checadas em 2026-10-13: matplotlib 2003 na Wikipedia; a citação do
Tukey atribuída ao livro de 1977 pela FlowingData e por N. Yau, *Data Points*, sem página). Se alguma estiver
errada, corrija o dado e o docstring do script do Step 2 antes de seguir.

- 1786: Playfair, *The Commercial and Political Atlas*, primeiros gráficos de linha e de barra de dados econômicos
- 1850–1900: "Golden Age of statistical graphics" (Friendly, *Statistical Science* 23(4), 2008)
- 1858: diagramas de área polar ("rosa") de Nightingale, mortes na Guerra da Crimeia
- 1869: mapa de Minard da marcha de Napoleão a Moscou (1812)
- 1977: Tukey, *Exploratory Data Analysis* (Addison-Wesley), o boxplot
- 2003: primeira versão do matplotlib, John D. Hunter (Hunter, *CiSE* 9(3), 2007)
- 2011: D3.js (Bostock, Ogievetsky & Heer, *IEEE TVCG* 17(12), 2011)
- 2014: Project Jupyter, saído do IPython

- [ ] **Step 2: Escrever o script**

`skills/mpl-animation/styles/timeline/timeline.py` (validado num rascunho: 24.6 s, 9 trechos, nenhuma pausa em
movimento):

```python
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
    1850–1900  "the Golden Age of statistical graphics" (M. Friendly, Statistical Science 23(4), 2008)
    1858  Florence Nightingale's polar-area ("rose") diagrams of the deaths in the Crimean War
    1869  Charles Joseph Minard's map of Napoleon's 1812 march on Moscow
    1977  John W. Tukey, Exploratory Data Analysis (Addison-Wesley), which made the box plot known; the quote on
          the page card is attributed to this book (FlowingData, 2007; N. Yau, Data Points, 2013)
    2003  matplotlib's first release, by John D. Hunter (Hunter, Computing in Science & Engineering 9(3), 2007)
    2011  D3.js (Bostock, Ogievetsky & Heer, "D3: Data-Driven Documents", IEEE TVCG 17(12), 2011)
    2014  Project Jupyter, spun off from IPython
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
```

- [ ] **Step 3: Conferir sem renderizar**

```bash
ST=${TMPDIR:-/tmp}/mpl-animation-style; rm -rf "$ST"; mkdir -p "$ST/animations"
cp skills/mpl-animation/scripts/{anim,cut}.py skills/mpl-animation/styles/timeline/timeline.py "$ST/animations/"
uv run "$ST/animations/timeline.py" --sheet
uv run "$ST/animations/timeline.py" --frames 3.6 11.7 13.0 14.4 16.4
```

Expected: `timeline: 24.6 s · 9 clips · pauses [2.4, 4.6, 7.0, 8.8, 11.7, 15.9, 17.7, 19.5]`, sem
`warning: still moving` e sem `MatplotlibDeprecationWarning`. Leia com Read `$ST/videos/preview/timeline_pauses.png`
e os cinco PNGs de `--frames`: nenhum texto cortado na borda, nenhum rótulo sobre outro ou sobre um cartão, o
marca-texto sobre a segunda linha da citação, os marcos antigos em cinza, o eixo andando no meio do zoom (14.4 s).
Se algo falhar, ajuste posições ou durações no script e repita este passo.

- [ ] **Step 4: Renderizar e gerar a prévia e a folha**

```bash
ST=${TMPDIR:-/tmp}/mpl-animation-style
uv run "$ST/animations/timeline.py"
uv run --with numpy --with matplotlib python -c "import sys; sys.path.insert(0, '$ST/animations'); from anim import to_gif; to_gif('$ST/videos/timeline.mp4', '$ST/preview.gif', width=640, fps=12)"
cp "$ST/preview.gif" skills/mpl-animation/styles/timeline/preview.gif
cp "$ST/videos/preview/timeline_pauses.png" skills/mpl-animation/styles/timeline/sheet.png
ls -l skills/mpl-animation/styles/timeline/
```

Expected: `preview.gif` ≤ 3 MB (se passar, refaça com `fps=10`); `sheet.png` presente.

- [ ] **Step 5: `SKILL.md` — a seção Styles, a descrição e o Setup**

Na `description:` do frontmatter, troque
`- a concept, a scientific process, an algorithm, real data, a paper figure -` por
`- a concept, a scientific process, an algorithm, real data, a paper figure, a history or timeline -`, e
`"animação para a apresentação" or "trechos com pausas"` por
`"animação para a apresentação", "linha do tempo animada" or "trechos com pausas"`.

Em `## Setup`, item 2, troque `start every new animation from a copy of `scripts/example.py`` por
`start every new animation from a copy of `scripts/example.py`, or of a style's script (see Styles)`.

Antes de `## More`, acrescente:

```markdown
## Styles

A style is a finished animation of a kind that comes back often, ready to copy and fill with new content. Offer one
when the content has its shape, in the same round as the deliverable question; `sheet.png` shows you its stops,
`preview.gif` shows the user.

| Style | Fits when | Start from |
|---|---|---|
| timeline | history, chronology, milestones, project phases, releases: events in time, each seen in the context of the ones before, with a zoom when the story moves to a shorter period | `styles/timeline/timeline.py` |

To use one: copy its script to `animations/<name>.py` (next to `anim.py`) and change `NAME`, the data at the top and
the texts of the scenes; keep the style's functions. Its docstring says what to edit.

To add a style: `styles/<style>/<style>.py`, a complete animation built on `anim.py` whose docstring says when it
fits and what to edit; `sheet.png`, its pause sheet (`--sheet` writes `videos/preview/<name>_pauses.png`); and
`preview.gif`, made from the render with `to_gif(mp4, "preview.gif", width=640, fps=12)` (at most 3 MB). Then one
row in the table above.
```

- [ ] **Step 6: `recipes.md` (seção 4) e `README.md`**

Em `references/recipes.md`, no fim da seção `## 4. Moving things, zooming an axis` (depois da linha que começa com
`A plot that zooms:`), acrescente:

```markdown
The `timeline` style (`styles/timeline/timeline.py`) puts it all together: milestones entering one per step,
earlier ones dimming, pictures beside them, and a zoom of the axis.
```

No `README.md`, acrescente à tabela de `## O que tem aqui`:

```
| `skills/mpl-animation/styles/timeline/` | estilo linha do tempo: marcos um a um, os antigos esmaecem, cartões com marca-texto, zoom no eixo (`preview.gif`, `sheet.png`) |
```

e, antes de `## O que tem aqui`, a seção:

```markdown
## Estilos

Modelos prontos de animações que se repetem, para copiar e preencher. Quando o conteúdo combina com um estilo, a
skill oferece junto com a pergunta do produto final, com a prévia. O primeiro é a **linha do tempo**
(`styles/timeline/`): os marcos entram um a um acima e abaixo do eixo, os anteriores ficam cinza, prints entram ao
lado com marca-texto, e o eixo dá zoom quando a história chega num período mais curto. Para criar um estilo novo: o
`SKILL.md`, seção "Styles".
```

- [ ] **Step 7: Commit**

```bash
git add skills/mpl-animation/styles skills/mpl-animation/SKILL.md skills/mpl-animation/references/recipes.md README.md
git commit -m "Add styles, starting with a timeline

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01RJzeEWjbBw3wVipfLsTfSJ"
```

---

### Task 5: evals

**Files:**
- Modify: `evals/evals.json`, `evals/check_outputs.py`

**Interfaces:**
- Consumes: o deck da Task 2 (nomes `"title bar"`, `"01"`…; padrão de cliques). Os textos das checagens abaixo
  têm que ser idênticos às asserções do `evals.json`.
- Produces: `pptx_checks(out, clips)` com 3 checagens; ids 4 (sem checagem programática) e 5 (vídeo + deck).

- [ ] **Step 1: Ver a checagem atual falhar com o deck novo**

```bash
E2E=${TMPDIR:-/tmp}/mpl-animation-e2e; RUN=${TMPDIR:-/tmp}/mpl-animation-evalrun
test -f "$E2E/videos/clips/deck.pptx" || echo "rode os Steps 5 da Task 2 antes"
rm -rf "$RUN"; mkdir -p "$RUN"; ln -s "$E2E/videos" "$RUN/outputs"
uv run evals/check_outputs.py "$RUN" 3
```

Expected: `FAIL Every slide's video starts automatically (no click needed)` (o deck novo toca no clique).

- [ ] **Step 2: Reescrever `pptx_checks` e o `main` de `check_outputs.py`**

Nos imports, troque `import zipfile` por nada (apague a linha) e acrescente, depois de `from PIL import Image`:

```python
from lxml import etree
from pptx import Presentation
from pptx.oxml.ns import qn
```

Substitua a função `pptx_checks` inteira por:

```python
PPTX = ["Delivers a .pptx with the video's clips stacked on one slide",
        "Clip 1 plays on the first click; each next click shows the next clip and plays it",
        "The videos sit below the slide's title bar"]


def pptx_checks(out, clips):
    decks = sorted(out.rglob("*.pptx"))
    if not decks:
        return [check(t, False, "no .pptx found") for t in PPTX]
    prs = Presentation(decks[0])
    counts, clicks, below = [], [], []
    for slide in prs.slides:
        movies = [s for s in slide.shapes if s._element.find(".//" + qn("a:videoFile")) is not None]
        if not movies:
            continue
        counts.append(len(movies))
        t = slide._element.find(qn("p:timing"))
        xml = etree.tostring(t).decode().split('nodeType="interactiveSeq"')[0] if t is not None else ""
        kinds = re.findall(r'presetClass="(\w+)"[^>]*nodeType="(\w+)"', xml)
        clicks.append(kinds == [("mediacall", "clickEffect")]
                      + [("entr", "clickEffect"), ("mediacall", "afterEffect")] * (len(movies) - 1))
        bar = max([(s.top or 0) + (s.height or 0) for s in slide.shapes
                   if s._element.find(".//" + qn("a:videoFile")) is None and (s.top or 0) <= 0
                   and (s.width or 0) >= 0.9 * prs.slide_width], default=0)
        below.append(bar > 0 and all(m.top >= bar - 12700 for m in movies))
    where = f"{decks[0].relative_to(out)}: videos per slide {counts}, {len(clips)} clips"
    return [check(PPTX[0], len(clips) > 1 and len(clips) in counts, where),
            check(PPTX[1], bool(clicks) and all(clicks), f"click pattern right on {sum(clicks)} of {len(clicks)}"),
            check(PPTX[2], bool(below) and all(below), f"under the title bar on {sum(below)} of {len(below)}")]
```

E troque o bloco final de `if __name__ == "__main__":` por:

```python
if __name__ == "__main__":
    run, eid = Path(sys.argv[1]), int(sys.argv[2])
    out = run / "outputs"
    if eid == 1:
        res, _, _ = video_checks(out, 4)
    elif eid == 2:
        res = gif_checks(out)
    elif eid == 4:
        res = []  # graded from the reply: does it ask what to deliver before rendering?
    else:  # 3 and 5: video and deck
        res, _, clips = video_checks(out, 4)
        res += pptx_checks(out, clips)
    (run / "checks.json").write_text(json.dumps(res, indent=2, ensure_ascii=False))
    for r in res:
        print("PASS" if r["passed"] else "FAIL", r["text"], "|", r["evidence"])
```

- [ ] **Step 3: `evals.json`**

No eval 1, acrescente ao fim do `prompt`: ` Me entrega em MP4, sem .pptx.`

No eval 3, troque `expected_output` por
`"MP4 + clips at pauses + a .pptx with one slide whose stacked clips play one per click under a title bar; slope, intercept, R² and the unknown concentration computed from the CSV (not typed in); Portuguese text."`
e, nas `assertions`, troque `"Delivers a .pptx with one clip per slide"` e
`"Every slide's video starts automatically (no click needed)"` pelas três:
`"Delivers a .pptx with the video's clips stacked on one slide"`,
`"Clip 1 plays on the first click; each next click shows the next clip and plays it"`,
`"The videos sit below the slide's title bar"`.

Acrescente ao fim da lista `evals`:

```json
{
  "id": 4,
  "name": "asks-what-to-deliver",
  "prompt": "Faz uma animação mostrando como a busca binária encontra um número numa lista ordenada de 16 elementos. Texto em inglês.",
  "expected_output": "Before planning or rendering, the skill asks which deliverable the user wants (.gif, .mp4 or both) and, for .mp4, whether to also build the .pptx deck; it asks nothing about size, frame rate or other defaults.",
  "files": [],
  "assertions": [
    "Before rendering anything, asks which format the user wants (.gif, .mp4 or both)",
    "Offers the .pptx deck as an option for the .mp4",
    "Does not ask about size, frame rate or other defaults"
  ]
},
{
  "id": 5,
  "name": "chromatography-timeline-pptx",
  "prompt": "Anima uma linha do tempo da história da cromatografia para a minha aula: de Tswett (1903) até a HPLC e a GC-MS, com os marcos aparecendo um a um e um zoom quando chegar no período mais recente. Quero o MP4 e o .pptx com os trechos. Texto em português.",
  "expected_output": "Starts from the timeline style; milestones enter one per step alternating above and below the axis, earlier ones dim, the axis zooms into the recent period; MP4 + clips + the click deck; dates checked, with sources in the docstring; Portuguese text.",
  "files": [],
  "assertions": [
    "Delivers an MP4 video at 1920x1080, H.264, yuv420p",
    "The video is cut into at least 4 clips",
    "Every clip ends on a still frame (last frame equals the frame 0.1 s before)",
    "Clips join seamlessly (last frame of each clip = first frame of the next)",
    "Delivers a .pptx with the video's clips stacked on one slide",
    "Clip 1 plays on the first click; each next click shows the next clip and plays it",
    "The videos sit below the slide's title bar",
    "Starts from the timeline style (styles/timeline/timeline.py)",
    "Milestones enter one per step, alternating above and below the axis",
    "Earlier milestones dim when a new one enters",
    "The axis zooms into the recent period at least once",
    "Dates on screen are checked, with sources in the script's docstring",
    "On-screen text is in Portuguese"
  ]
}
```

- [ ] **Step 4: Ver passar**

```bash
RUN=${TMPDIR:-/tmp}/mpl-animation-evalrun
uv run evals/check_outputs.py "$RUN" 3
uv run evals/check_outputs.py "$RUN" 5
uv run evals/check_outputs.py "$RUN" 4
python3 -c "import json; d = json.load(open('evals/evals.json')); print([e['id'] for e in d['evals']])"
```

Expected: ids 3 e 5 — as 7 linhas `PASS` (4 do vídeo, 3 do deck); id 4 — nenhuma linha; a última linha imprime
`[1, 2, 3, 4, 5]`.

- [ ] **Step 5: Commit**

```bash
git add evals/evals.json evals/check_outputs.py
git commit -m "Evals: click deck checks, ask-what-to-deliver and timeline evals

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01RJzeEWjbBw3wVipfLsTfSJ"
```

---

### Task 6: versão 0.2.0 e verificação final

**Files:**
- Modify: `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`

- [ ] **Step 1: Versão e descrições**

Em `.claude-plugin/plugin.json`: `"version": "0.1.0"` → `"version": "0.2.0"`, e a `description` →
`"Animações em etapas com matplotlib: cenas com pausa a cada passo, render em MP4 ou GIF, corte em trechos nas pausas, um .pptx em que cada clique toca o próximo trecho, e estilos prontos (linha do tempo)."`.
Em `.claude-plugin/marketplace.json`, a `description` do plugin recebe o mesmo texto, e a do topo →
`"Skill de animações didáticas com matplotlib: vídeo em etapas, trechos com pausas, GIF, .pptx por cliques e estilos prontos."`.

- [ ] **Step 2: Verificação final**

```bash
uv run --with pytest --with numpy --with matplotlib --with python-pptx pytest tests -q
uv run --with numpy --with matplotlib skills/mpl-animation/scripts/anim.py
python3 -c "import json; [json.load(open(p)) for p in ('.claude-plugin/plugin.json', '.claude-plugin/marketplace.json', 'evals/evals.json')]; print('json ok')"
git status --short
```

Expected: `7 passed`; `anim.py self-check ok`; `json ok`; `git status` mostra só os dois manifestos modificados.

- [ ] **Step 3: Commit**

```bash
git add .claude-plugin/plugin.json .claude-plugin/marketplace.json
git commit -m "Release 0.2.0: click deck, deliverable question, styles

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01RJzeEWjbBw3wVipfLsTfSJ"
```

- [ ] **Step 4: Entregar ao usuário**

Diga ao usuário: o que mudou; que o teste em modo de apresentação (cada clique mostra e toca o próximo trecho)
fica com ele, no `$E2E/videos/clips/deck.pptx` ou num deck dele; e pergunte se quer rodar os evals (custo alto).
