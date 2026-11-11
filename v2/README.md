# DieCUT Tool v2.0

Gerador de cortantes (dielines) para etiquetas em folhas autocolantes.
Esta versão nasce da v1 e implementa as melhorias planeadas para a versão 2.0.

![Pré-visualização](assets/icon.png)

## O que há de novo

| Melhoria pedida | Como ficou implementada |
| --- | --- |
| Visual mais moderno | Tema escuro com cartões, paleta magenta/ciano, cabeçalho, barra de estado e tipografia consistente. |
| Ícones, barras de ferramentas e botões visuais | Barra de ferramentas da pré-visualização, botões com ícones, separadores visuais e atalhos de teclado. |
| Pré-visualização com zoom, grelhas e margens | Zoom com roda do rato e botões, pan com botão direito/central, ajustar à janela, grelha adaptativa e margem sombreada com contorno tracejado. |
| Pré-visualização 2D ou 3D | Alternador **2D/3D** com vista isométrica da folha, espessura, relevo das etiquetas e ordenação por profundidade. |
| Modo automático | Calcula o número máximo de colunas/fileiras que cabem na área útil, atualizado em tempo real. |
| Múltiplos formatos de etiqueta | Retângulo (com raio de canto), oval e círculo. |
| Over-compensate (mm) | Sobreposição no início do caminho da dieline, para a lâmina fechar o corte. Não altera o tamanho da etiqueta; o troço sobreposto aparece em ciano na pré-visualização. |

### Extras incluídos

- **Exportação DXF** em milímetros (layer `DIELINE`), além do PDF vetorial.
- Validação em tempo real: avisa quando o layout excede a folha ou quando a etiqueta não cabe.
- Recorte visual das dielines que saem da folha na pré-visualização.
- Destaque em ciano do troço de sobreposição do corte.
- Indicadores de ocupação da folha, quantidade de etiquetas e estado do layout.
- Atalhos: `Ctrl+P` (PDF), `Ctrl+D` (DXF), `Ctrl+0` (ajustar), `Ctrl+ +/-` (zoom).
- Ícone próprio da aplicação.

## Executar

Requisitos: Python 3.10 ou superior.

Recomenda-se um ambiente virtual próprio. As versões exatas usadas no
desenvolvimento estão registadas em `requirements.lock.txt` (o `requirements.txt`
mantém apenas os limites mínimos):

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

Os testes cobrem o cálculo automático, alinhamento, compensação, geometria e
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

O executável fica em `dist/DieCutTool v2.0.exe`.

## Estrutura

```text
v2/
├── main.py                  # entrada da aplicação
├── app/
│   ├── models.py            # folha, etiqueta, layout, compensação
│   ├── geometry.py          # contornos, áreas e projeção isométrica
│   ├── layout.py            # modo automático e posicionamento
│   ├── exporters.py         # PDF (ReportLab) e DXF (ezdxf)
│   ├── resources.py         # recursos em dev e no executável
│   └── ui/
│       ├── main_window.py   # janela, painel lateral, toolbar e estado
│       ├── preview.py       # canvas 2D/3D, zoom, grelha e margens
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

- O **over-compensate** é uma sobreposição de caminho: o corte percorre o
  contorno completo e regressa sobre o início durante os milímetros indicados.
  Isto garante que a lâmina fecha o corte sem alterar as dimensões da etiqueta
  nem o layout. O troço sobreposto é mostrado em ciano na pré-visualização.
- No **modo automático**, colunas e fileiras são calculadas a partir da área
  útil (folha menos margem), do espaçamento e das dimensões reais da etiqueta.
- No **modo manual**, o layout é validado contra a área útil e a exportação é
  bloqueada se as dielines saírem da folha.
- O **PDF** é criado no tamanho exato da folha. Com compensação, o caminho é
  desenhado já com a sobreposição; sem compensação, usa curvas vetoriais.
- O **DXF** usa milímetros, `$INSUNITS = 4`, e coloca todas as dielines no layer
  `DIELINE`. Com compensação, cada dieline é uma `LWPOLYLINE` aberta com o troço
  de sobreposição; sem compensação, usa `LWPOLYLINE` com bulge para retângulos e
  entidades `ELLIPSE`/`CIRCLE` para ovos e círculos.
