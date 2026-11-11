# Legado arquivado

Esta pasta não faz parte da aplicação ativa. O projeto ativo é `../v2`.

## `v1/`

Primeira versão do DieCUT Tool (app único em Tkinter: `FlowCutApp`, `LayoutCalculator`,
`FloatSpinbox`), substituída pela reescrita modular em `v2/`. Nenhum arquivo de `v2/`
importa ou referencia `v1/` — verificado por busca textual e pelo grafo do código.

O que foi preservado:

- `main.py`, `requirements.txt`, `DieCutTool.spec` — código-fonte e receita de build;
- `dist/DieCutTool v1.0.exe` — binário distribuído da versão 1 (mantido por ser a
  cópia do release, não é gerado pelo build atual).

O que foi removido:

- `build/` — intermediários do PyInstaller, totalmente regeneráveis com
  `pyinstaller DieCutTool.spec`.

## Como reverter o arquivamento

```powershell
Move-Item "DieCUT Tool - Gerador de cortantes\_legacy\v1" "DieCUT Tool - Gerador de cortantes\v1"
```

## Snapshot

`_backup/v1-source-2026-11-11.zip` — cópia dos fontes do v1 no momento do
arquivamento (arquivos na raiz do zip, sem estrutura de pastas).
