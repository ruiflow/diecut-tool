# Legado arquivado

Esta pasta não faz parte da aplicação ativa. O projeto ativo está na raiz do
repositório (`app/` e `main.py`).

## `v1/`

Primeira versão do DieCUT Tool (app único em Tkinter: `FlowCutApp`, `LayoutCalculator`,
`FloatSpinbox`), substituída pela reescrita modular em `app/`. Nenhum arquivo da
aplicação atual importa ou referencia `v1/` — verificado por busca textual e pelo
grafo do código.

O que foi preservado:

- `main.py`, `requirements.txt`, `DieCutTool.spec` — código-fonte e receita de build;
- o binário `DieCutTool-v1.0.exe` está disponível na
  [release v1.0](https://github.com/ruiflow/diecut-tool/releases/tag/v1.0).

O que foi removido:

- `build/` — intermediários do PyInstaller, totalmente regeneráveis com
  `pyinstaller DieCutTool.spec`.

## Como reverter o arquivamento

```powershell
Move-Item "legacy\v1" "v1"
```

## Snapshot

`backup/v1-source-2026-11-11.zip` — cópia dos fontes do v1 no momento do
arquivamento (arquivos na raiz do zip, sem estrutura de pastas).
