<div align="center">

<img src="docs/screenshots/01-preview-2d.png" alt="DieCUT Tool v2 — pré-visualização 2D" width="860">

# DieCUT Tool

**Gerador de cortantes (dielines) para etiquetas em folhas autocolantes.**

Pré-visualização 2D/3D, distribuição automática e exportação vetorial para **PDF** e **DXF**.

[![Baixar v2.0](https://img.shields.io/badge/Baixar-v2.0%20EXE-ff2d95?style=for-the-badge&logo=windows&logoColor=white)](https://github.com/ruiflow/diecut-tool/releases/latest/download/DieCutTool-v2.0.exe)
[![Baixar v1.0](https://img.shields.io/badge/Baixar-v1.0%20EXE%20(legado)-4b4b63?style=for-the-badge&logo=windows&logoColor=white)](https://github.com/ruiflow/diecut-tool/releases/download/v1.0/DieCutTool-v1.0.exe)

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![Windows](https://img.shields.io/badge/Windows-10%20%2F%2011-0078D6?logo=windows&logoColor=white)
![Testes](https://img.shields.io/badge/testes-19%20a%20passar-2ea043)
![Sem instalação](https://img.shields.io/badge/EXE-sem%20instala%C3%A7%C3%A3o-8957e5)

</div>

---

## O que é

O **DieCUT Tool** calcula e desenha o corte (dieline) de etiquetas numa folha autocolante.
Você informa as medidas da folha e da etiqueta, o programa distribui as etiquetas, mostra o
resultado em pré-visualização e exporta o arquivo pronto para a plotter/cortante.

Nasceu de uma necessidade real de produção: substituir o cálculo manual de colunas e
espaçamentos por um arquivo vetorial que já sai na medida exata da folha.

## Demonstração

| Pré-visualização 2D | Vista isométrica 3D |
| :---: | :---: |
| <img src="docs/screenshots/01-preview-2d.png" width="430"> | <img src="docs/screenshots/02-preview-3d.png" width="430"> |
| Grelha adaptativa, margem sombreada e recorte das dielines que saem da folha | Folha em perspectiva com espessura, relevo e ordenação por profundidade |

| Formatos ovais e círculos | Over-compensate e modo automático |
| :---: | :---: |
| <img src="docs/screenshots/03-formato-oval.png" width="430"> | <img src="docs/screenshots/05-overcompensate.png" width="430"> |
| Etiquetas ovais, além de retângulo com raio de canto e círculo | Troço de sobreposição de 6 mm em ciano, com zoom em 149% |

| Círculo (medidas acopladas) | Modo automático |
| :---: | :---: |
| <img src="docs/screenshots/04-formato-circulo.png" width="430"> | <img src="docs/screenshots/06-modo-automatico.png" width="430"> |
| No formato círculo, largura e altura são sincronizadas | Colunas e fileiras calculadas da área útil: 3 × 9 = 27 etiquetas |

## Funcionalidades

| | |
| --- | --- |
| **Pré-visualização 2D/3D** | Alternador com vista isométrica, zoom (roda do rato e botões), pan, grelha adaptativa e margem sombreada. |
| **Modo automático** | Calcula o número máximo de colunas e fileiras que cabem na área útil, atualizado em tempo real. |
| **Formatos de etiqueta** | Retângulo (com raio de canto), oval e círculo. |
| **Over-compensate** | Sobreposição no início do caminho para a lâmina fechar o corte, sem alterar a medida da etiqueta. O troço aparece em ciano. |
| **Exportação PDF** | Vetorial, uma página no tamanho exato da folha. |
| **Exportação DXF** | Milímetros, `$INSUNITS = 4`, todas as dielines no layer `DIELINE`. |
| **Validação em tempo real** | Avisa quando o layout excede a folha e bloqueia a exportação de dielines fora da área. |
| **Atalhos** | `Ctrl+P` PDF, `Ctrl+D` DXF, `Ctrl+0` ajustar, `Ctrl+ + / -` zoom. |

## Download

Os executáveis ficam na aba [**Releases**](https://github.com/ruiflow/diecut-tool/releases) —
não é preciso instalar Python nem dependências.

| Versão | Arquivo | Tamanho | Observação |
| --- | --- | --- | --- |
| **v2.0** | `DieCutTool-v2.0.exe` | ~36 MB | Versão atual: interface nova, 2D/3D, DXF, modo automático |
| **v1.0** | `DieCutTool-v1.0.exe` | ~30 MB | Versão original (legado), mantida para compatibilidade |

> O Windows pode exibir o aviso do SmartScreen porque o executável não é assinado
> digitalmente. Clique em **Mais informações → Executar assim mesmo**.

## Executar a partir do código

Requisitos: Python 3.10+ no Windows.

```powershell
cd v2
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

### Testes

```powershell
cd v2
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

19 testes cobrem cálculo automático, alinhamento, compensação, geometria e a exportação
real para PDF/DXF (validada com `ezdxf`).

### Gerar o executável

```powershell
cd v2
.\.venv\Scripts\python.exe -m pip install pyinstaller
.\.venv\Scripts\pyinstaller.exe --noconfirm DieCutTool_v2.spec
```

O resultado fica em `v2/dist/DieCutTool v2.0.exe`.

## Estrutura do repositório

```text
.
├── v2/                     # versão atual (aplicação ativa)
│   ├── main.py
│   ├── app/                # models, geometry, layout, exporters, ui/
│   ├── tests/              # testes do núcleo
│   ├── assets/             # ícones
│   └── DieCutTool_v2.spec  # build PyInstaller
├── _legacy/
│   └── v1/                 # versão 1 arquivada (não é usada pela v2)
└── docs/screenshots/       # imagens deste README
```

**v1 × v2:** a v1 é um aplicativo único em Tkinter (`FlowCutApp`, `LayoutCalculator`),
mantido em `_legacy/` apenas como histórico e para download. Todo o desenvolvimento
acontece na `v2`, modular (`app/models.py`, `geometry.py`, `layout.py`, `exporters.py`, `ui/`)
e sem qualquer dependência da v1.

## Licença

Sem licença definida até o momento — todos os direitos reservados ao autor.
