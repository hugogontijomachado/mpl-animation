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
/plugin marketplace add hugogontijomachado/mpl-animation     # ou o caminho local: /Users/hugocemep/GitHub/mpl-animation
/plugin install mpl-animation@mpl-animation
```

Ou só a skill, por link: `ln -s /Users/hugocemep/GitHub/mpl-animation/skills/mpl-animation ~/.claude/skills/mpl-animation`.

Precisa de [uv](https://docs.astral.sh/uv/) e `ffmpeg`.

## Usar

É só pedir: "faz uma animação mostrando como a coluna separa dois compostos", "anima essa curva de calibração para
a apresentação", "um GIF para o README mostrando o gradiente descendente". A skill primeiro pergunta o que você quer
receber — .gif e/ou .mp4 e, com .mp4, se quer também o `.pptx` e se o título segue o padrão do CEMEP — só o que
o pedido não disse. Depois copia o motor para `<projeto>/animations/` e segue a regra: planejar as etapas →
conferir quadros sem renderizar → renderizar → cortar em trechos → conferir a folha de pausas → listar os fatos na
tela para você conferir.

O `.pptx` tem um slide por vídeo: o título no alto (simples, ou o padrão do CEMEP — barra azul, título em branco e
o símbolo do CEMEP à direita, `--cemep`) e, embaixo, os trechos empilhados. O trecho 1 toca no primeiro clique e
cada clique seguinte faz o próximo aparecer e já tocar ("com o anterior"), continuando do quadro em que o outro
parou; você encaixa a fala nas pausas. As notas do apresentador trazem o que está na tela em cada clique.
Muitos vídeos deixam o PowerPoint lento e causam travadas em alguns computadores: no computador da apresentação,
em Arquivo > Opções > Avançado, marque "Desativar a aceleração de elementos gráficos de hardware da apresentação de
slides".

```bash
uv run animations/<script>.py               # videos/<nome>.mp4 + último quadro; escreve as pausas em pauses.toml
uv run animations/<script>.py --gif         # também o GIF
uv run animations/<script>.py --sheet       # folha com o quadro de cada pausa, sem renderizar; acusa pausa em movimento
uv run animations/<script>.py --preview     # último quadro de cada cena
uv run animations/<script>.py --frames 3 7  # quadros avulsos
uv run animations/<script>.py --draft       # meia resolução, 15 fps (conferir o movimento rápido)
uv run animations/cut.py [vídeos] [--gif] [--pptx] [--cemep] [--bar '#232751'] [--logo logo.png] [--sheet]
```

## Estilos

Modelos prontos de animações que se repetem, para copiar e preencher. Quando o conteúdo combina com um estilo, a
skill oferece junto com a pergunta do produto final, com a prévia. O primeiro é a **linha do tempo**
(`styles/timeline/`): os marcos entram um a um acima e abaixo do eixo, os anteriores ficam cinza, prints entram ao
lado com marca-texto, e o eixo dá zoom quando a história chega num período mais curto. Para criar um estilo novo: o
`SKILL.md`, seção "Styles".

## O que tem aqui

| Arquivo | Papel |
|---|---|
| `skills/mpl-animation/SKILL.md` | a regra, o fluxo, convenções visuais e de conteúdo |
| `skills/mpl-animation/scripts/anim.py` | o motor: tela 192×108, primitivas, `Panel`, `steps`, `Scene`, render, checagens |
| `skills/mpl-animation/scripts/cut.py` | corta nos pontos de `pauses.toml`, folhas de pausas, GIFs dos trechos, `.pptx` com um slide por vídeo e um clique por trecho |
| `skills/mpl-animation/scripts/example.py` | modelo completo (média de varreduras e S/N), ponto de partida de cada animação nova |
| `skills/mpl-animation/references/recipes.md` | receitas: continuar de outro vídeo, versões, zoom em linha do tempo, diagrama de sequência, imagens, idiomas, `FuncAnimation`, apresentar |
| `skills/mpl-animation/styles/timeline/` | estilo linha do tempo: marcos um a um, os antigos esmaecem, cartões com marca-texto, zoom no eixo (`preview.gif`, `sheet.png`) |

Checagem rápida do motor: `uv run --with numpy --with matplotlib skills/mpl-animation/scripts/anim.py`.
