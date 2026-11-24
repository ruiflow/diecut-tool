# Desenvolvimento — DieCUT Tool v4

Gerador de cortantes (dielines) para etiquetas em folhas autocolantes.
Esta versão continua a linha v3 e concentra-se na otimização do percurso de
corte, na importação de DXF/PDF e na informação “Acerca de”.

![Pré-visualização](../assets/icon.png)

## O que há de novo na v4

| Melhoria | Como ficou implementada |
| --- | --- |
| Cinco estratégias de percurso | **Proximidade+** (vizinho mais próximo + 2-opt/Or-opt), **Zigue-zague**, **Colunas**, **Espiral** e **Por etiqueta** (contornos separados). |
| Objetivos de otimização | **Menos distância**, **Menos elevações**, **Mais rápido** e **Equilibrado**; a pontuação ordena as estratégias e orienta as melhorias locais. |
| Ponto de início | Canto superior/inferior esquerdo ou direito, ou centro da folha. A origem real é o canto superior esquerdo. |
| Comparação de percursos | `compare_strategies` / `compare_imported_strategies` calculam todas as estratégias e devolvem-nas ordenadas pela pontuação do objetivo ativo. |
| Importação DXF/PDF | `app/importers/` lê DXF (com `ezdxf`) e PDF vetorial (com `pdfplumber`), converte para milímetros e expõe `ImportedDocument`. |
| Documento importado ativo | O ficheiro importado substitui o layout gerado na pré-visualização 2D/3D, simulação, comparação e exportação. |
| “Acerca de” | Diálogo com versão, ambiente, créditos a OpenCode, DeepSeek e Rui Flow, ligações e lista de tecnologias. |

## Funcionalidades

- **Pré-visualização 2D** com zoom, pan, grelha adaptativa e recorte das dielines fora da folha.
- **Pré-visualização 3D** com espessura da folha, relevo das etiquetas, oclusão por profundidade e órbita livre com o rato.
- **Modo automático**: calcula o número máximo de colunas/fileiras que cabem na folha, atualizado em tempo real.
- **Múltiplos formatos**: retângulo (com raio de canto), oval e círculo.
- **Over-compensate (mm)**: sobreposição no início do caminho para a lâmina fechar o corte. Não altera o tamanho da etiqueta; o troço sobreposto aparece em ciano.
- **Simulação de corte**: animação do percurso completo, com troços de corte em magenta, deslocamentos em vazio a tracejado ciano, estatísticas de corte/ligações/deslocamento/elevações/tempo e controlo de velocidade.
- **Percurso configurável**: cinco estratégias, quatro objetivos, ponto de início e **Fundir contornos**; contornos que se tocam são cortados num só percurso, sem repetir arestas.
- **Comparar percursos**: tabela com métricas por estratégia e aplicação da melhor.
- **Importar DXF/PDF**: seleção de camadas do DXF e de página do PDF; curvas de Bézier achatadas; texto e imagens ignorados.
- **Guardar percurso**: DXF com os layers `CORTE` e `DESLOCAMENTO`, ou PDF com o traçado pela ordem da simulação.
- **Exportação PDF** vetorial, no tamanho exato da folha.
- **Exportação DXF** em milímetros (layer `DIELINE`; importados no layer `IMPORTADO`).
- **Validação em tempo real** e bloqueio da exportação quando o layout excede a folha.
- **Atalhos**: `Ctrl+P` (PDF), `Ctrl+D` (DXF), `Ctrl+I` (importar), `Ctrl+0` (ajustar), `Ctrl+ +/-` (zoom), `F5` (simulação), `F1` (acerca).

## Estratégias de percurso

| Estratégia | Ideia |
| --- | --- |
| **Proximidade+** | Vizinho mais próximo a partir do início escolhido, refinado com 2-opt e Or-opt. |
| **Zigue-zague** | Percorre a folha linha a linha, alternando o sentido, com tolerância ajustada ao espaçamento real. |
| **Colunas** | Percorre coluna a coluna, alternando o sentido entre colunas. |
| **Espiral** | Entra do exterior para o centro da folha segundo o ângulo em relação ao centro. |
| **Por etiqueta** | Mantém cada contorno separado (não funde contornos), útil para isolamento. |

O objetivo **Mais rápido** usa as velocidades de corte e de deslocamento e o
tempo por elevação definidos em `app/cutting.py` para estimar a duração.

## Executar

Requisitos: Python 3.10 ou superior.

A partir da raiz do repositório:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

## Testes

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Os 48 testes cobrem cálculo automático, alinhamento, compensação, geometria,
projeção 3D, planeamento do percurso de corte (cinco estratégias, objetivos,
ponto de início, redução de elevações, partilha de arestas e trilhos em
serpentina), importação DXF/PDF e exportação real para PDF/DXF (validada com
`ezdxf`).

Para verificar rapidamente as exportações e importações no ambiente atual (ou no
executável), sem abrir a interface:

```powershell
python main.py --selftest .\saida_teste
```

## Criar o executável

```powershell
.\.venv\Scripts\python.exe -m pip install pyinstaller
.\.venv\Scripts\pyinstaller.exe --noconfirm --clean DieCutTool.spec
```

O executável fica em `dist/DieCutTool v4.exe`. O spec inclui os dados e os
módulos ocultos de `pdfplumber`/`pdfminer`.

Também pode usar o script de build:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build.ps1
```

## Estrutura

```text
.
├── main.py                  # entrada da aplicação (interface e --selftest)
├── app/                     # código da aplicação
│   ├── models.py            # folha, etiqueta, layout, compensação
│   ├── geometry.py          # contornos, áreas e projeção 3D com órbita
│   ├── layout.py            # modo automático e posicionamento
│   ├── cutting.py           # estratégias, objetivos e plano de corte
│   ├── exporters.py         # PDF/DXF das dielines, percursos e importados
│   ├── importers/
│   │   ├── document.py      # modelos ImportedPath/ImportedDocument
│   │   ├── dxf.py           # leitura de DXF (ezdxf)
│   │   └── pdf.py           # leitura de PDF vetorial (pdfplumber)
│   ├── resources.py         # recursos em dev e no executável
│   └── ui/
│       ├── main_window.py   # janela, painel lateral, toolbar e estado
│       ├── preview.py       # canvas 2D/3D, órbita, zoom e simulação
│       ├── import_dialog.py # seleção de camadas/página na importação
│       ├── compare_dialog.py# tabela de comparação de percursos
│       ├── about.py         # diálogo “Acerca de”
│       ├── widgets.py       # campos numéricos e cartões
│       └── theme.py         # paleta e tipografia
├── assets/                  # ícones
├── tests/                   # testes do núcleo
├── tools/make_icon.py       # gerador do ícone
├── docs/                    # documentação e capturas de ecrã
├── scripts/                 # automação de build e publicação
├── legacy/                  # versão 1 arquivada (não usada pela aplicação)
├── requirements.txt
├── requirements.lock.txt
└── DieCutTool.spec
```

## Notas de utilização

- **Vista 3D**: arraste com o botão esquerdo para rodar 360° na horizontal e
  inclinar a vista. Se ainda não tiver feito zoom, a vista reajusta-se
  automaticamente para manter a folha inteira visível. Duplo clique repõe a
  câmara.
- **Estratégia de percurso**: comece por **Proximidade+** para layouts
  irregulares e **Zigue-zague**/**Colunas** para layouts regulares. Use
  **Comparar percursos** para ver qual ganha no objetivo ativo.
- **Fundir contornos**: os contornos são fundidos num grafo de arestas únicas.
  Arestas coincidentes entre etiquetas vizinhas são cortadas uma só vez e os
  contactos num ponto são atravessados sem levantar a lâmina. Quando o grafo não
  permite um trilho contínuo (por exemplo, uma grelha 2×2 tem quatro vértices
  ímpares), o componente é dividido em trilhos válidos e a lâmina levanta entre
  eles. O corte nunca passa duas vezes sobre a mesma aresta.
- **Guardar**: durante a simulação, o botão **Guardar** abre as opções DXF e
  PDF. O DXF usa o layer `CORTE` para os traços com a lâmina em baixo e
  `DESLOCAMENTO` para os movimentos em vazio (este layer não é plotado). Cada
  trilho contínuo fica numa única polilinha, pelo que a plotter o corta num só
  movimento.
- **Importar**: `Ctrl+I` aceita DXF e PDF vetorial. No DXF escolhem-se as
  camadas; no PDF, a página. As unidades são convertidas para milímetros
  (`$INSUNITS` no DXF; 1 pt = 25,4/72 mm no PDF) e as curvas de Bézier são
  achatadas. Enquanto um documento importado estiver ativo, o layout gerado fica
  suspenso; **Fechar importação** volta ao gerador.
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
