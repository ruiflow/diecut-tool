<#
.SYNOPSIS
    Gera o executável da DieCUT Tool com PyInstaller.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\scripts\build.ps1
#>
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
Set-Location -Path (Split-Path $PSScriptRoot -Parent)

$python = Join-Path $PWD ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Ambiente virtual nao encontrado. Crie com: python -m venv .venv; .\.venv\Scripts\python.exe -m pip install -r requirements.txt"
}

& $python -m PyInstaller --noconfirm --clean DieCutTool.spec
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller falhou."
}

Write-Host "Executavel gerado em dist\DieCutTool v2.2.exe" -ForegroundColor Green
