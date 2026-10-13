# Deck por cliques, pergunta do produto final e estilos — design

Data: 2026-10-13. Repositório: `mpl-animation` (o plugin). Referência só lida, nunca alterada:
`cemep/harness_presentation` (`docs/presentation_harness.pptx`, `animacoes/montar_deck.py`, `animacoes/historia*.py`).

## Objetivo

Três acréscimos ao plugin, implementados nesta ordem:

1. **Deck por cliques**: `cut.py --pptx` passa a gerar um slide por vídeo, com todos os trechos empilhados, que
   entram e tocam a cada clique, abaixo de um cabeçalho — o padrão dos slides que o usuário montou à mão.
2. **Pergunta do produto final**: a skill pergunta .gif e/ou .mp4 e, havendo .mp4, se quer o .pptx — só o que o
   pedido não disse.
3. **Estilos**: uma biblioteca `styles/` de animações-modelo que a skill sugere quando o conteúdo combina; o
   primeiro é a linha do tempo.

Sucesso: um usuário pede uma animação, responde a pergunta do produto, e recebe um `.pptx` em que cada clique
mostra e toca o próximo trecho, com a fala encaixada nas pausas; e pode partir do estilo linha do tempo para uma
cronologia.

## 1. Deck por cliques (`scripts/cut.py --pptx`)

### Estrutura

- `videos/clips/deck.pptx`, 16:9 (12192000 × 6858000 EMU), **um slide por vídeo**, na ordem do `pauses.toml` (ou
  dos vídeos passados na linha de comando). O deck é sempre refeito inteiro com os vídeos cortados naquela chamada:
  `cut.py intro --pptx` gera um deck só com `intro` (como hoje).
- Substitui o modo atual (um trecho por slide, autoplay): a constante `AUTOPLAY` e esse caminho saem do código.

### Cabeçalho

Medidas tiradas do deck de referência:

- **Barra**: retângulo na largura toda, do topo até 1239520 EMU (18% da altura), sem contorno. Cor padrão
  `#232751`; `--bar '#RRGGBB'` troca.
- **Título**: caixa de texto em x = 806991 EMU, centralizada na vertical da barra; Arial 32 pt, negrito, branco.
  Texto: a chave `title` da seção do vídeo no `pauses.toml`; sem ela, o nome do vídeo.
- **Logo** (opcional, `--logo arquivo.png`): altura = 52% da barra, centralizado na vertical da barra, margem
  direita de 359252 EMU, proporção da imagem mantida.
- `anim.py` (`sync_pauses`) passa a escrever `title = "<nome>"` ao criar a seção de um vídeo, para o campo ficar
  visível. Seções antigas, sem `title`, continuam válidas.

### Vídeo

- Área disponível: abaixo da barra até o rodapé, na largura toda. O vídeo ocupa o maior retângulo com a proporção
  dele (largura × altura lidas com `ffprobe`) que cabe nessa área, centralizado na horizontal e encostado na barra.
  Num vídeo 16:9: altura 5618480, largura 9988409, x = 1101795, y = 1239520.
- Todos os trechos do vídeo na mesma posição e tamanho, empilhados em ordem (o 01 embaixo), com nomes `01`, `02`…;
  pôster de cada um = o primeiro quadro do trecho.

### Animação (a timeline do slide)

Portada de `tempo()` em `harness_presentation/animacoes/montar_deck.py`, que já rodou no deck real:

- o trecho 01 está visível desde o início e toca no 1º clique (`mediacall` / `clickEffect`, `playFrom(0.0)`);
- para cada trecho k ≥ 2, um clique faz o trecho aparecer (`entr`, `style.visibility` → `visible`,
  `clickEffect`) e, em seguida, tocar (`mediacall` / `afterEffect`);
- a duração (`dur`) de cada "tocar" é a do trecho, em ms;
- um nó `<p:video><p:cMediaNode>` por trecho, como o PowerPoint escreve;
- **sem** as sequências interativas `togglePause` (clique no vídeo pausa): um clique do mouse sobre o vídeo avança
  a apresentação, como o clicker.

Como o último quadro do trecho k é o primeiro do trecho k+1 (o corte já é feito assim), a troca é invisível.

### Notas do apresentador

Uma linha por clique: `click k · <início>–<fim> s · <comentário>` (em inglês, como o resto da skill), em que o comentário é o da pausa
correspondente no `pauses.toml` (`# k  <texto>`; o último é o da linha `(to the end)`). Os comentários são lidos do
texto da seção (o `tomllib` os descarta).

### Segurança e checagem

- Se existir `videos/clips/~$deck.pptx` (o deck aberto no PowerPoint), `cut.py` para com uma mensagem, sem gravar.
- Depois de salvar, `cut.py` reabre o deck com python-pptx e confere, parando com erro se algo falhar:
  número de slides = número de vídeos; vídeos por slide = trechos; padrão de cliques (1º `mediacall/clickEffect`,
  depois pares `entr/clickEffect` + `mediacall/afterEffect`); `dur` de cada play = duração do trecho (± 50 ms);
  cada vídeo abaixo da barra e dentro do slide; as notas trazem o comentário de cada pausa.

### Linha de comando

`cut.py [vídeos] [--gif] [--pptx] [--sheet] [--bar COR] [--logo PNG]`. `--bar` e `--logo` só valem com `--pptx`.

## 2. Pergunta do produto final (`SKILL.md`)

O parágrafo "Don't ask about these unless the request is unclear…" sai; entra a regra **Ask what to deliver**,
antes do Workflow:

- Antes de planejar, uma rodada de perguntas (`AskUserQuestion` quando disponível), **só sobre o que o pedido não
  disse**:
  1. formato: .mp4, .gif ou ambos;
  2. havendo .mp4: também o .pptx com os trechos por clique?
- Leitura do pedido:
  - cita .pptx, PowerPoint, slides ou "para apresentar" → .mp4 + .pptx, nada a perguntar sobre formato;
  - cita só GIF → nada a perguntar;
  - cita "vídeo" ou .mp4 sem deck → pergunta só o .pptx;
  - mudar, recortar ou fazer versão de uma animação existente → os produtos que ela já tem, sem pergunta.
- Na mesma rodada, se o conteúdo combina com um estilo (seção 3), a pergunta inclui a opção do estilo (com o caminho
  da prévia) ao lado de "livre".
- A tabela "Default deliverables" vira:

  | Escolha | Entrega |
  |---|---|
  | .gif | `--gif`; sem trechos (GIF não tem controle de pausa); o .mp4 sai como subproduto e fica em `videos/` |
  | .mp4 | vídeo + trechos + folha de pausas |
  | .mp4 + .pptx | o acima + `title` de cada vídeo no `pauses.toml` + `cut.py --pptx` |

- Tamanho, fps e vídeo contínuo seguem sem pergunta: padrão, e o relatório final diz o que foi feito. O caso "me
  proponha" (envia o plano e espera) continua.
- A seção 14 de `references/recipes.md` (apresentar os trechos) é reescrita para o deck por cliques, com o passo a
  passo manual equivalente no PowerPoint (trecho 1 "ao clicar"; cada seguinte "Aparecer" ao clicar + "Reproduzir"
  após o anterior; sem retroceder; sem ocultar).
- O README do plugin ganha um parágrafo sobre a pergunta e sobre o deck.

## 3. Estilos (`skills/mpl-animation/styles/`)

### Formato de um estilo

```
styles/<nome>/
  <nome>.py     a animação completa; copiada para <projeto>/animations/<video>.py, ao lado de anim.py
  preview.gif   a prévia para o usuário: 640 px, 12 fps, ≤ 3 MB
  sheet.png     a folha de pausas (o quadro de cada pausa), para o Claude ver o estilo sem assistir ao GIF
```

O docstring do script diz quando o estilo combina, o que editar e as fontes dos fatos. No `SKILL.md`, uma seção
**Styles** com:

- a tabela: estilo | combina quando | começar de;
- como usar: copiar o script para `animations/<nome>.py`, editar os dados, manter as funções do estilo;
- como criar um estilo: pasta nova com script + `preview.gif` + `sheet.png`, os comandos que geram os dois arquivos
  e uma linha na tabela.

A receita 4 de `recipes.md` ("zooming an axis") passa a apontar para o estilo; o README lista os estilos.

### O estilo `timeline`

Texto na tela em inglês, como o `example.py`. Tema: uma história curta da visualização de dados.

- **Dados no topo**:
  - `MILESTONES`: uma lista só, na ordem de entrada — (início, fim, rótulo do ano, nome, linhas de detalhe, lado,
    cor); fim = início num marco, fim > início numa era;
  - `RANGES`: os intervalos do eixo, `(1750, 2030)` e `(1990, 2030)`;
  - asserts: os rótulos cabem na tela e não encostam no vizinho do mesmo lado (`text_w`).
- **Funções do estilo**:
  - `X(year, rng)`: ano → x; com `rng = (r0, r1, z)` mistura os dois mapeamentos (cada marco anda em linha reta
    durante o zoom);
  - `axis(rng, a)`: eixo com seta, marcas por década ou por ano conforme o intervalo;
  - `era(...)` / `event(...)`: barra ou ponto no eixo, haste, ano (pequeno, `MUTED`), nome (negrito), detalhes
    (`INK_2`), acima ou abaixo do eixo; parâmetro `dim` (0–1) leva tudo para o cinza;
  - `card(img, x, y, h, a, marks)`: o `image()` do motor, com marca-texto.
- **Cena 1, a visão longa** (1750–2030): o eixo cresce; um passo por vez — Playfair 1786 (gráficos de linha e de
  barra); a era de ouro dos gráficos estatísticos (barra 1850–1900) com a linha "1858 · Nightingale"; a linha
  "1869 · Minard" da mesma era (como marcos separados os rótulos de 1858 e 1869 se sobrepõem: viram as duas linhas de
  detalhe da era, cada uma no seu passo); Tukey 1977 (boxplot, análise exploratória). Ao entrar um marco, os
  anteriores esmaecem; cada passo traz um cartão.
- **Cena 2, o zoom** (→ 1990–2030): os cartões saem, o eixo desliza; entram matplotlib 2003, D3.js 2011, Jupyter
  2014; linha final de conclusão em negrito.
- Por volta de 25 s, 8 pausas (9 trechos).
- **Fatos**: cada data e afirmação conferida na web durante a implementação, com a fonte no docstring. Se algum
  fato da lista acima estiver errado, entra o correto.
- **Prints**: gerados no próprio script, sem imagens de terceiros no repositório — mini-figuras redesenhadas no
  espírito do original (linha à la Playfair, rosa à la Nightingale, boxplot à la Tukey), com a etiqueta
  "redrawn, illustrative", e um cartão de texto para mostrar o marca-texto. O docstring explica como trocar por
  imagens reais em `animations/data/` (origem anotada, dados pessoais cortados).

## 4. Testes, evals e entrega

### Verificação

1. `uv run --with numpy --with matplotlib skills/mpl-animation/scripts/anim.py`: o autoteste passa.
2. De ponta a ponta, num projeto no scratchpad: copiar `anim.py`, `cut.py`, `example.py` e `timeline.py`;
   renderizar os dois; `cut.py --pptx --logo <png>`; a checagem interna do `cut.py` passa.
3. Abrir o `deck.pptx` no PowerPoint instalado: abre sem pedir reparo.
4. Timeline: `--sheet` e `--frames` (transições, meio do zoom) conferidos visualmente; `preview.gif` ≤ 3 MB.
5. Fica com o usuário: um teste em modo de apresentação (cada clique mostra e toca o próximo trecho).

### Evals (`evals/`)

- eval 1 (cromatografia): o prompt ganha "em MP4, sem .pptx".
- eval 3 (calibração .pptx): asserções do deck novo — um slide por vídeo com os trechos empilhados; trecho 1 toca no
  clique, cada seguinte aparece no clique e toca em seguida; vídeos abaixo da barra. `pptx_checks` em
  `check_outputs.py` reescrito para isso.
- eval 4 (novo): pedido sem formato; asserção: antes de renderizar, a skill pergunta .gif/.mp4.
- eval 5 (novo): uma cronologia com MP4 + .pptx; asserções: parte do estilo timeline, marcos alternam acima e abaixo,
  os antigos esmaecem, o eixo dá zoom, os fatos têm fonte.
- Rodar os evals é decisão do usuário ao fim (custo alto).

### Entrega

- `SKILL.md`: corrigir `scriptas/` → `scripts/`.
- Versão `0.1.0` → `0.2.0` em `.claude-plugin/plugin.json` e `marketplace.json`.
- Commits no `main` do `mpl-animation`, por bloco (deck, pergunta, estilo, evals). Nada no `harness_presentation`.

## Fora do escopo

- Copiar o cabeçalho de um slide do deck do usuário (`--template`); fica para quando for pedido.
- Outros estilos além da linha do tempo.
- Keynote e Google Slides gerados por script (seguem as instruções manuais em `recipes.md`).
