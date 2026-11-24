<div align="center">

<img src="docs/screenshots/01-preview-2d.png" alt="DieCUT Tool v4 — pré-visualização 2D" width="860">

# DieCUT Tool

**Gerador de cortantes (dielines) para etiquetas em folhas autocolantes.**

Pré-visualização 2D/3D com órbita livre, simulação de corte com percurso otimizado, importação de **DXF/PDF**, distribuição automática e exportação vetorial para **PDF** e **DXF**.

[![Baixar v4](https://img.shields.io/badge/Baixar-v4%20EXE-ff2d95?style=for-the-badge&logo=windows&logoColor=white)](https://github.com/ruiflow/diecut-tool/releases/latest/download/DieCutTool-v4.exe)
[![Baixar v3](https://img.shields.io/badge/Baixar-v3%20EXE-4b4b63?style=for-the-badge&logo=windows&logoColor=white)](https://github.com/ruiflow/diecut-tool/releases/download/v3/DieCutTool-v3.exe)
[![Baixar v2](https://img.shields.io/badge/Baixar-v2%20EXE-4b4b63?style=for-the-badge&logo=windows&logoColor=white)](https://github.com/ruiflow/diecut-tool/releases/download/v2/DieCutTool-v2.exe)
[![Baixar v1](https://img.shields.io/badge/Baixar-v1%20EXE%20(legado)-2b2b38?style=for-the-badge&logo=windows&logoColor=white)](https://github.com/ruiflow/diecut-tool/releases/download/v1/DieCutTool-v1.exe)

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![Windows](https://img.shields.io/badge/Windows-10%20%2F%2011-0078D6?logo=windows&logoColor=white)
![Testes](https://img.shields.io/badge/testes-48%20a%20passar-2ea043)
![Sem instalação](https://img.shields.io/badge/EXE-sem%20instala%C3%A7%C3%A3o-8957e5)

</div>

---

## O que é

O **DieCUT Tool** calcula e desenha o corte (dieline) de etiquetas numa folha autocolante.
Você informa as medidas da folha e da etiqueta, o programa distribui as etiquetas, mostra o
resultado em pré-visualização e exporta o arquivo pronto para a plotter/cortante.

Nasceu de uma necessidade real de produção: substituir o cálculo manual de colunas e
espaçamentos por um arquivo vetorial que já sai na medida exata da folha.

## Novidades na v4

- **Otimização do percurso em primeiro lugar**: cinco estratégias — **Proximidade+**,
  **Zigue-zague**, **Colunas**, **Espiral** e **Por etiqueta** — com objetivo de
  **menos distância**, **menos elevações**, **mais rápido** ou **equilibrado**.
- **Comparar percursos**: calcula todas as estratégias de uma vez e mostra corte,
  deslocamento, ligações, elevações, tempo estimado e pontuação; aplica a
  melhor com um clique.
- **Ponto de início** configurável: cantos ou centro da folha.
- **Importar DXF/PDF**: um DXF ou um PDF vetorial passa a ser o documento ativo,
  com pré-visualização 2D/3D, simulação, comparação de percursos e exportação.
- **Acerca de** (`F1`) com versão, ambiente, créditos a **OpenCode**, **DeepSeek**
  e **Rui Flow**, e ligações para repositório e releases.
- **Sem cortes repetidos**: os contornos são fundidos num grafo de arestas
  únicas. Cada aresta é cortada uma só vez; o percurso pode passar pelo mesmo
  vértice ou ponto de contacto.
- **Menos elevações de lâmina**: contornos que se tocam são cortados num só
  percurso. Quando um único trilho é impossível, o componente é dividido em
  trilhos válidos e a lâmina levanta apenas entre eles.
- **Guardar o percurso**: durante a simulação, exporte o traçado pela ordem
  calculada em DXF (layers `CORTE` e `DESLOCAMENTO`) ou PDF de referência.

## Demonstração

| Pré-visualização 2D | Vista 3D com órbita |
| :---: | :---: |
| <img src="docs/screenshots/01-preview-2d.png" width="430"> | <img src="docs/screenshots/02-preview-3d.png" width="430"> |
| Grelha adaptativa e recorte das dielines que saem da folha | Folha em perspetiva com espessura, relevo e rotação 360° com o rato |

| Simulação de corte |
| :---: |
| <img src="docs/screenshots/07-simulacao-corte.png" width="430"> |
| Percurso por cinco estratégias, objetivos de otimização, contornos encostados cortados sem repetir arestas e exportação do percurso otimizado |

| Formatos ovais e círculos | Over-compensate e modo automático |
| :---: | :---: |
| <img src="docs/screenshots/03-formato-oval.png" width="430"> | <img src="docs/screenshots/05-overcompensate.png" width="430"> |
| Etiquetas ovais, além de retângulo com raio de canto e círculo | Troço de sobreposição de 6 mm em ciano, com zoom em 149% |

| Círculo (medidas acopladas) | Modo automático |
| :---: | :---: |
| <img src="docs/screenshots/04-formato-circulo.png" width="430"> | <img src="docs/screenshots/06-modo-automatico.png" width="430"> |
| No formato círculo, largura e altura são sincronizadas | Colunas e fileiras calculadas a partir da folha inteira: 4 × 9 = 36 etiquetas |

## Funcionalidades

| | |
| --- | --- |
| **Pré-visualização 2D/3D** | Vista 2D com zoom/pan e vista 3D com órbita 360° pelo rato, espessura, relevo e oclusão por profundidade. |
| **Simulação de corte** | Reproduz uma plotter a cortar a folha, com cabeça animada, velocidade ajustável, estatísticas (corte, ligações, deslocamento, elevações e tempo estimado) e percurso otimizado por cinco estratégias. |
| **Otimização do percurso** | Estratégias **Proximidade+**, **Zigue-zague**, **Colunas**, **Espiral** e **Por etiqueta**; objetivo de menos distância, menos elevações, mais rápido ou equilibrado; início no canto ou centro. |
| **Comparar percursos** | Calcula todas as estratégias e ordena-as pelo objetivo ativo; aplicar a melhor com um clique. |
| **Importar DXF/PDF** | Carrega um DXF (com seleção de camadas) ou um PDF vetorial (com seleção de página); curvas de Bézier achatadas e tudo convertido para milímetros. |
| **Menos elevações de lâmina** | Os contornos que se tocam são fundidos num grafo de arestas únicas: o corte continua de um para o outro sem levantar a lâmina e sem passar duas vezes sobre a mesma aresta. |
| **Guardar percurso** | Exporta o traçado pela ordem da simulação em DXF (layers `CORTE` e `DESLOCAMENTO`) ou PDF de referência. Cada trilho contínuo fica numa única polilinha, cortada num só movimento. |
| **Modo automático** | Calcula o número máximo de colunas e fileiras que cabem na folha, atualizado em tempo real. |
| **Formatos de etiqueta** | Retângulo (com raio de canto), oval e círculo. |
| **Over-compensate** | Sobreposição no início do caminho para a lâmina fechar o corte, sem alterar a medida da etiqueta. O troço aparece em ciano. |
| **Exportação PDF** | Vetorial, uma página no tamanho exato da folha. |
| **Exportação DXF** | Milímetros, `$INSUNITS = 4`, todas as dielines no layer `DIELINE`. |
| **Acerca de** | Versão, ambiente, créditos (OpenCode, DeepSeek, Rui Flow), repositório e releases; copiar informação com um clique. |
| **Validação em tempo real** | Avisa quando o layout excede a folha e bloqueia a exportação de dielines fora da área. |
| **Atalhos** | `Ctrl+P` PDF, `Ctrl+D` DXF, `Ctrl+I` importar, `Ctrl+0` ajustar, `Ctrl+ + / -` zoom, `F5` simulação, `F1` acerca. |

## Download

Os executáveis ficam na aba [**Releases**](https://github.com/ruiflow/diecut-tool/releases) —
não é preciso instalar Python nem dependências.

| Versão | Arquivo | Tamanho | Observação |
| --- | --- | --- | --- |
| **v4** | `DieCutTool-v4.exe` | ~40 MB | Atual: cinco estratégias, comparação de percursos, importação DXF/PDF e “Acerca de” |
| **v3** | `DieCutTool-v3.exe` | ~38 MB | Percurso por proximidade/zigue-zague, sem repetir arestas, guardar corte em DXF/PDF |
| **v2** | `DieCutTool-v2.exe` | ~36 MB | Interface nova, 2D/3D, DXF e modo automático |
| **v1** | `DieCutTool-v1.exe` | ~30 MB | Versão original (legado), mantida para compatibilidade |

> O código-fonte atual está em **`app/`** e corresponde à **v4**. O executável
> publicado já inclui todas as funcionalidades descritas acima.

> O Windows pode exibir o aviso do SmartScreen porque o executável não é assinado
> digitalmente. Clique em **Mais informações → Executar assim mesmo**.

## Executar a partir do código

Requisitos: Python 3.10+ no Windows.

A partir da raiz do repositório:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

### Testes

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

48 testes cobrem cálculo automático, alinhamento, compensação, geometria,
projeção 3D, as cinco estratégias de percurso, objetivos, ponto de início, a
partilha de arestas, os trilhos em serpentina, importação DXF/PDF e exportação
real para PDF/DXF (validada com `ezdxf`).

### Gerar o executável

```powershell
.\.venv\Scripts\python.exe -m pip install pyinstaller
.\.venv\Scripts\pyinstaller.exe --noconfirm --clean DieCutTool.spec
```

O resultado fica em `dist/DieCutTool v4.exe`. Também pode usar
`.\scripts\build.ps1`.

## Estrutura do repositório

```text
.
├── main.py                  # entrada da aplicação
├── app/                     # código da aplicação
│   ├── models.py            # folha, etiqueta, layout e compensação
│   ├── geometry.py          # contornos, áreas e projeção 3D
│   ├── layout.py            # modo automático e posicionamento
│   ├── cutting.py           # estratégias de percurso, objetivos e plano de corte
│   ├── exporters.py         # PDF/DXF das dielines, do percurso e de importados
│   ├── importers/           # leitura de DXF e PDF vetorial
│   ├── resources.py         # recursos em dev e no executável
│   └── ui/                  # janela, pré-visualização, diálogos e widgets
├── assets/                  # ícones
├── tests/                   # testes do núcleo
├── tools/                   # gerador do ícone
├── docs/                    # documentação e capturas de ecrã
├── scripts/                 # build e publicação
├── legacy/                  # versão 1 arquivada (não usada pela aplicação)
├── requirements.txt
├── requirements.lock.txt
├── DieCutTool.spec          # build PyInstaller
└── README.md
```

**v1 × v4:** a v1 é um aplicativo único em Tkinter (`FlowCutApp`, `LayoutCalculator`),
mantido em `legacy/` apenas como histórico e para download. Todo o desenvolvimento
acontece na versão atual, modular (`app/models.py`, `geometry.py`, `layout.py`,
`cutting.py`, `exporters.py`, `importers/`, `ui/`) e sem qualquer dependência da v1.

Documentação técnica e instruções de build: [`docs/development.md`](docs/development.md).

## Licença

Sem licença definida até o momento — todos os direitos reservados ao autor.
