# mpl-animation

Skill do Claude Code para fazer **animações didáticas com matplotlib**: cada animação é feita em **etapas** (cada
passo termina numa pausa), renderizada em **MP4** (padrão) ou **GIF** e depois **cortada em trechos** nas pausas —
um trecho por slide, que toca sozinho e para no último quadro enquanto você fala. Para a plateia, parece um vídeo só
que pausa.

O motor e o jeito de trabalhar vêm das animações da palestra em `cemep/harness_presentation` (tela redesenhada a
cada quadro, `steps()`, `pausas.toml` + `cortar.py`, véu entre cenas, números reais com `assert`), generalizados.

## Instalar

Como plugin (igual ao `cemep-lab`):

```
/plugin marketplace add /Users/hugocemep/GitHub/mpl-animation
/plugin install mpl-animation@mpl-animation
```

Ou só a skill, por link: `ln -s /Users/hugocemep/GitHub/mpl-animation/skills/mpl-animation ~/.claude/skills/mpl-animation`.

Precisa de [uv](https://docs.astral.sh/uv/) e `ffmpeg`.

## Usar

É só pedir: "faz uma animação mostrando como a coluna separa dois compostos", "anima essa curva de calibração para
a apresentação", "um GIF para o README mostrando o gradiente descendente". A skill copia o motor para
`<projeto>/animations/` e segue a regra: planejar as etapas → conferir quadros sem renderizar → renderizar → cortar
em trechos → conferir a folha de pausas → listar os fatos na tela para você conferir. Tudo isso é padrão, não
obrigação: dá para pedir só o GIF, um vídeo contínuo sem cortes, o `.pptx` montado, outro tamanho.

```bash
uv run animations/<script>.py               # videos/<nome>.mp4 + último quadro; escreve as pausas em pauses.toml
uv run animations/<script>.py --gif         # também o GIF
uv run animations/<script>.py --sheet       # folha com o quadro de cada pausa, sem renderizar; acusa pausa em movimento
uv run animations/<script>.py --preview     # último quadro de cada cena
uv run animations/<script>.py --frames 3 7  # quadros avulsos
uv run animations/<script>.py --draft       # meia resolução, 15 fps (conferir o movimento rápido)
uv run animations/cut.py [vídeos] [--gif] [--pptx] [--sheet]   # trechos, folhas de pausas, GIFs dos trechos, deck
```

## O que tem aqui

| Arquivo | Papel |
|---|---|
| `skills/mpl-animation/SKILL.md` | a regra, o fluxo, convenções visuais e de conteúdo |
| `skills/mpl-animation/scripts/anim.py` | o motor: tela 192×108, primitivas, `Panel`, `steps`, `Scene`, render, checagens |
| `skills/mpl-animation/scripts/cut.py` | corta nos pontos de `pauses.toml`, folhas de pausas, GIFs dos trechos, `.pptx` com autoplay |
| `skills/mpl-animation/scripts/example.py` | modelo completo (média de varreduras e S/N), ponto de partida de cada animação nova |
| `skills/mpl-animation/references/recipes.md` | receitas: continuar de outro vídeo, versões, zoom em linha do tempo, diagrama de sequência, imagens, idiomas, `FuncAnimation`, apresentar |

Checagem rápida do motor: `uv run --with numpy --with matplotlib skills/mpl-animation/scripts/anim.py`.
