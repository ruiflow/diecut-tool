<#
.SYNOPSIS
    Executa a suite de testes da DieCUT Tool.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\scripts\test.ps1
#>
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
Set-Location -Path (Split-Path $PSScriptRoot -Parent)

$python = Join-Path $PWD ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Ambiente virtual nao encontrado. Crie com: python -m venv .venv; .\.venv\Scripts\python.exe -m pip install -r requirements.txt"
}

& $python -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) {
    throw "Os testes falharam."
}
