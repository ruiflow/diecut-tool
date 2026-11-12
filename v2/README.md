# DieCUT Tool v2.2

Gerador de cortantes (dielines) para etiquetas em folhas autocolantes.
Esta versão nasce da v1 e implementa as melhorias planeadas para a linha 2.x.

![Pré-visualização](assets/icon.png)

## O que há de novo na v2.2

| Melhoria | Como ficou implementada |
| --- | --- |
| Ordem de corte por proximidade | Vizinho mais próximo a partir da origem + melhoria 2-opt, para encurtar os deslocamentos entre etiquetas. |
| Ordem de corte em zigue-zague | A folha é percorrida linha a linha, alternando o sentido em cada linha. Quando os contornos se tocam, o percurso continua em serpentina de um para o outro. |
| Menos elevações de lâmina | Os contornos são convertidos num grafo de arestas únicas: arestas partilhadas são cortadas uma só vez e os contornos que se tocam são encadeados no ponto comum. A lâmina só levanta quando não existe um trilho contínuo válido. |
| Sem cortes repetidos | O percurso nunca passa duas vezes sobre a mesma aresta; pode passar pelo mesmo vértice ou ponto de contacto. |
| Guardar o percurso otimizado | Durante a simulação, o botão **Guardar** exporta o percurso pela ordem calculada, em DXF (plotter) ou PDF (referência). |

## Funcionalidades

- **Pré-visualização 2D** com zoom, pan, grelha adaptativa e recorte das dielines fora da folha.
- **Pré-visualização 3D** com espessura da folha, relevo das etiquetas, oclusão por profundidade e órbita livre com o rato.
- **Modo automático**: calcula o número máximo de colunas/fileiras que cabem na folha, atualizado em tempo real.
- **Múltiplos formatos**: retângulo (com raio de canto), oval e círculo.
- **Over-compensate (mm)**: sobreposição no início do caminho para a lâmina fechar o corte. Não altera o tamanho da etiqueta; o troço sobreposto aparece em ciano.
- **Simulação de corte**: animação do percurso completo, com troços de corte em magenta, deslocamentos em vazio a tracejado ciano, estatísticas de corte/ligações/deslocamento/elevações e controlo de velocidade.
- **Percurso configurável**: estratégia **Proximidade** ou **Zigue-zague**; contornos que se tocam são cortados num só percurso, sem repetir arestas.
- **Guardar percurso**: DXF com os layers `CORTE` e `DESLOCAMENTO`, ou PDF com o traçado pela ordem da simulação.
- **Exportação PDF** vetorial, no tamanho exato da folha.
- **Exportação DXF** em milímetros (layer `DIELINE`).
- **Validação em tempo real** e bloqueio da exportação quando o layout excede a folha.
- **Atalhos**: `Ctrl+P` (PDF), `Ctrl+D` (DXF), `Ctrl+0` (ajustar), `Ctrl+ +/-` (zoom), `F5` (simulação).

## Executar

Requisitos: Python 3.10 ou superior.

```powershell
cd "DieCUT Tool - Gerador de cortantes\v2"
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

## Testes

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Os 32 testes cobrem cálculo automático, alinhamento, compensação, geometria,
projeção 3D, planeamento do percurso de corte (incluindo as duas estratégias, a
redução de elevações, a partilha de arestas e os trilhos em serpentina) e
exportação real para PDF/DXF (validada com `ezdxf`).

Para verificar rapidamente as exportações no ambiente atual (ou no executável),
sem abrir a interface:

```powershell
python main.py --selftest .\saida_teste
```

## Criar o executável

```powershell
.\.venv\Scripts\python.exe -m pip install pyinstaller
.\.venv\Scripts\pyinstaller.exe --noconfirm DieCutTool_v2.spec
```

O executável fica em `dist/DieCutTool v2.2.exe`.

## Estrutura

```text
v2/
├── main.py                  # entrada da aplicação
├── app/
│   ├── models.py            # folha, etiqueta, layout, compensação
│   ├── geometry.py          # contornos, áreas e projeção 3D com órbita
│   ├── layout.py            # modo automático e posicionamento
│   ├── cutting.py           # estratégias de percurso e plano de corte
│   ├── exporters.py         # PDF/DXF das dielines e do percurso otimizado
│   ├── resources.py         # recursos em dev e no executável
│   └── ui/
│       ├── main_window.py   # janela, painel lateral, toolbar e estado
│       ├── preview.py       # canvas 2D/3D, órbita, zoom e simulação
│       ├── widgets.py       # campos numéricos e cartões
│       └── theme.py         # paleta e tipografia
├── assets/                  # ícones
├── tests/                   # testes do núcleo
├── tools/make_icon.py       # gerador do ícone
├── requirements.txt
├── requirements.lock.txt
└── DieCutTool_v2.spec
```

## Notas de utilização

- **Vista 3D**: arraste com o botão esquerdo para rodar 360° na horizontal e
  inclinar a vista. Se ainda não tiver feito zoom, a vista reajusta-se
  automaticamente para manter a folha inteira visível. Duplo clique repõe a
  câmara.
- **Estratégia de percurso**: **Proximidade** encurta os deslocamentos totais e
  é a melhor opção para layouts irregulares. **Zigue-zague** percorre a folha
  linha a linha e é útil para layouts regulares ou quando se pretende um
  movimento previsível da cabeça de corte. Em ambas, os contornos que se tocam
  são encadeados num percurso contínuo.
- **Manter lâmina em baixo**: os contornos são fundidos num grafo de arestas
  únicas. Arestas coincidentes entre etiquetas vizinhas são cortadas uma só vez
  e os contactos num ponto são atravessados sem levantar a lâmina. Quando o
  grafo não permite um trilho contínuo (por exemplo, uma grelha 2×2 tem quatro
  vértices ímpares), o componente é dividido em trilhos válidos e a lâmina
  levanta entre eles. O corte nunca passa duas vezes sobre a mesma aresta.
- **Guardar**: durante a simulação, o botão **Guardar** abre as opções DXF e
  PDF. O DXF usa o layer `CORTE` para os traços com a lâmina em baixo e
  `DESLOCAMENTO` para os movimentos em vazio (este layer não é plotado). Cada
  trilho contínuo fica numa única polilinha, pelo que a plotter o corta num só
  movimento.
- **Over-compensate**: o corte percorre o contorno completo e regressa sobre o
  início durante os milímetros indicados. Isto garante que a lâmina fecha o
  corte sem alterar as dimensões da etiqueta nem o layout.
- **Modo automático**: colunas e fileiras são calculadas a partir da folha
  inteira, do espaçamento e das dimensões reais da etiqueta.
- **Modo manual**: o layout é validado contra a folha e a exportação é
  bloqueada se as dielines saírem da folha.
- **PDF**: criado no tamanho exato da folha. Com compensação, o caminho é
  desenhado já com a sobreposição; sem compensação, usa curvas vetoriais.
- **DXF**: usa milímetros, `$INSUNITS = 4`, e coloca todas as dielines no layer
  `DIELINE`. Com compensação, cada dieline é uma `LWPOLYLINE` aberta com o troço
  de sobreposição; sem compensação, usa `LWPOLYLINE` com bulge para retângulos e
  entidades `ELLIPSE`/`CIRCLE` para ovos e círculos.
