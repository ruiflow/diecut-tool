<#
.SYNOPSIS
    Publica o DieCUT Tool no GitHub: repositorio, commit inicial e releases com os .exe.

.DESCRIPTION
    Pre-requisito (uma unica vez):
        & "$env:USERPROFILE\tools\gh\gh.exe" auth login

    O Git e o GitHub CLI portateis ja estao em %USERPROFILE%\tools\.
    Se estiverem instalados no sistema (PATH), este script usa essas versoes.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\publicar.ps1

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\publicar.ps1 -Repo diecut-tool -Visibility private
#>
[CmdletBinding()]
param(
    [string]$Owner,
    [string]$Repo = "diecut-tool",
    [ValidateSet("public", "private")][string]$Visibility = "public",
    [switch]$SkipReleases
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

function Passo($texto) { Write-Host "`n==> $texto" -ForegroundColor Cyan }
function Falhar($texto) { Write-Host "ERRO: $texto" -ForegroundColor Red; exit 1 }

function AcharFerramenta($nome, $alternativas) {
    $cmd = Get-Command $nome -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    foreach ($caminho in $alternativas) {
        if (Test-Path $caminho) { return $caminho }
    }
    return $null
}

# Executa uma ferramenta nativa sem que o stderr dela vire erro fatal.
function Rodar($exe, [string[]]$argumentos, [switch]$Silencioso) {
    $anterior = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        if ($Silencioso) {
            & $exe @argumentos 2>&1 | Out-Null
        } else {
            & $exe @argumentos
        }
        return $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $anterior
    }
}

# Captura a saida de uma ferramenta nativa (stdout) sem tratar stderr como erro fatal.
function Capturar($exe, [string[]]$argumentos) {
    $anterior = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        return (& $exe @argumentos 2>$null)
    } finally {
        $ErrorActionPreference = $anterior
    }
}

# --- 1. Ferramentas -------------------------------------------------------
Passo "Verificando ferramentas"
$Git = AcharFerramenta "git" @("$env:USERPROFILE\tools\git\cmd\git.exe")
if (-not $Git) { Falhar "Git nao encontrado. Instale em https://git-scm.com/download/win." }
$Gh = AcharFerramenta "gh" @("$env:USERPROFILE\tools\gh\gh.exe", "$env:USERPROFILE\tools\gh\bin\gh.exe")
if (-not $Gh) { Falhar "GitHub CLI nao encontrado. Instale em https://cli.github.com/." }

# garante que o git consegue invocar o gh como credential helper
$env:PATH = (Split-Path $Git) + ";" + (Split-Path $Gh) + ";" + $env:PATH

Write-Host "git: $(& $Git --version)"
Write-Host "gh:  $((& $Gh --version | Select-Object -First 1))"

if ((Rodar $Gh @("auth", "status") -Silencioso) -ne 0) {
    Falhar "Sem sessao no GitHub. Rode uma vez:`n    & `"$Gh`" auth login"
}

if (-not $Owner) {
    $Owner = (& $Gh api user --jq .login).Trim()
    if (-not $Owner) { Falhar "Nao consegui detectar o utilizador. Passe -Owner <nome>." }
}
Write-Host "repositorio: $Owner/$Repo ($Visibility)"

# --- 2. README com as URLs corretas --------------------------------------
Passo "Ajustando os links do README para $Owner/$Repo"
$readmePath = Join-Path $PWD "README.md"
$readme = [System.IO.File]::ReadAllText($readmePath)
$readme = $readme.Replace("__OWNER__", $Owner).Replace("__REPO__", $Repo)
if ($readme -match "__OWNER__|__REPO__") { Falhar "README ainda contem placeholders." }
[System.IO.File]::WriteAllText($readmePath, $readme, (New-Object System.Text.UTF8Encoding $false))

# --- 3. Repositorio local -------------------------------------------------
Passo "Preparando o commit"
if (-not (Test-Path ".git")) {
    Rodar $Git @("init") -Silencioso | Out-Null
    Rodar $Git @("symbolic-ref", "HEAD", "refs/heads/main") -Silencioso | Out-Null
}
Rodar $Git @("add", "-A") -Silencioso | Out-Null
$staged = @(& $Git diff --cached --name-only)
if ($staged.Count -gt 0) {
    Rodar $Git @("-c", "user.name=$Owner", "-c", "user.email=$Owner@users.noreply.github.com",
        "commit", "-m", "DieCUT Tool v2.2: estrategias de percurso e guardar corte") -Silencioso | Out-Null
    Write-Host "$($staged.Count) arquivo(s) no commit"
} else {
    Write-Host "nada novo para commitar"
}

# --- 4. Repositorio remoto ------------------------------------------------
Passo "Criando/atualizando $Owner/$Repo no GitHub"
Rodar $Gh @("auth", "setup-git") -Silencioso | Out-Null

if ((Rodar $Gh @("repo", "view", "$Owner/$Repo") -Silencioso) -ne 0) {
    Rodar $Gh @("repo", "create", "$Owner/$Repo", "--$Visibility", "--source", ".", "--remote", "origin", "--push",
        "--description", "Gerador de cortantes (dielines) para etiquetas: pre-visualizacao 2D/3D, simulacao de corte, PDF e DXF") | Out-Null
} else {
    Write-Host "repositorio ja existe - enviando commits"
    if ((Rodar $Git @("remote", "get-url", "origin") -Silencioso) -ne 0) {
        Rodar $Git @("remote", "add", "origin", "https://github.com/$Owner/$Repo.git") -Silencioso | Out-Null
    }
    Rodar $Git @("push", "-u", "origin", "HEAD:main") | Out-Null
}
Rodar $Gh @("repo", "edit", "$Owner/$Repo",
    "--add-topic", "dieline", "--add-topic", "die-cut", "--add-topic", "labels",
    "--add-topic", "dxf", "--add-topic", "pdf", "--add-topic", "python",
    "--add-topic", "tkinter", "--add-topic", "cutting-plotter") -Silencioso | Out-Null

# --- 5. Releases com os .exe ---------------------------------------------
if (-not $SkipReleases) {
    Passo "Criando as releases com os executaveis"
    $v2exe = "v2\dist\DieCutTool v2.2.exe"
    $v1exe = "_legacy\v1\dist\DieCutTool v1.0.exe"
    $stage = Join-Path $env:TEMP "diecut-release"
    New-Item -ItemType Directory -Force $stage | Out-Null

    $notesV2 = @(
        "Percurso de corte configuravel, menos elevacoes de lamina e exportacao do traçado otimizado.",
        "",
        "- Tema escuro com cartoes e paleta magenta/ciano",
        "- Pre-visualizacao 2D/3D com orbita 360 graus pelo rato, zoom, pan e grelha adaptativa",
        "- Simulacao de corte com cabeca animada e velocidade ajustavel",
        "- Ordem de corte por proximidade (vizinho mais proximo + 2-opt) ou em zigue-zague",
        "- Contornos encostados fundidos num grafo de arestas unicas, sem cortar duas vezes a mesma aresta",
        "- Estatisticas de corte, ligacoes, deslocamento e numero de elevacoes",
        "- Guardar o percurso otimizado em DXF (layers CORTE e DESLOCAMENTO) ou PDF",
        "- Margem de seguranca removida: a folha e usada por inteiro",
        "- Modo automatico de colunas e fileiras",
        "- Formatos retangulo (raio de canto), oval e circulo",
        "- Over-compensate para a lamina fechar o corte",
        "- Exportacao PDF vetorial no tamanho exato da folha",
        "- Exportacao DXF em milimetros, layer DIELINE",
        "- 32 testes automatizados",
        "",
        "**Requisitos:** Windows 10/11. Nao e necessaria instalacao."
    ) -join "`n"

    $notesV1 = @(
        "Versao original do DieCUT Tool, em arquivo unico (Tkinter: FlowCutApp, LayoutCalculator).",
        "",
        "Mantida como legado para download e consulta. O desenvolvimento continua na v2."
    ) -join "`n"

    $notesV2Path = Join-Path $stage "notas-v2.md"
    $notesV1Path = Join-Path $stage "notas-v1.md"
    [System.IO.File]::WriteAllText($notesV2Path, $notesV2, (New-Object System.Text.UTF8Encoding $false))
    [System.IO.File]::WriteAllText($notesV1Path, $notesV1, (New-Object System.Text.UTF8Encoding $false))

    if (Test-Path $v2exe) {
        $asset2 = Join-Path $stage "DieCutTool-v2.2.exe"
        Copy-Item $v2exe $asset2 -Force
        if ((Rodar $Gh @("release", "view", "v2.2") -Silencioso) -ne 0) {
            Rodar $Gh @("release", "create", "v2.2", $asset2, "--title", "DieCUT Tool v2.2",
                "--notes-file", $notesV2Path, "--latest") | Out-Null
        } else {
            Rodar $Gh @("release", "upload", "v2.2", $asset2, "--clobber") | Out-Null
        }
        Write-Host "release v2.2 publicada"
    } else {
        Write-Host "aviso: $v2exe nao encontrado - release v2.2 ignorada" -ForegroundColor Yellow
    }

    if (Test-Path $v1exe) {
        $asset1 = Join-Path $stage "DieCutTool-v1.0.exe"
        Copy-Item $v1exe $asset1 -Force
        if ((Rodar $Gh @("release", "view", "v1.0") -Silencioso) -ne 0) {
            Rodar $Gh @("release", "create", "v1.0", $asset1, "--title", "DieCUT Tool v1.0 (legado)",
                "--notes-file", $notesV1Path, "--latest=false") | Out-Null
        } else {
            Rodar $Gh @("release", "upload", "v1.0", $asset1, "--clobber") | Out-Null
        }
        Write-Host "release v1.0 publicada"
    } else {
        Write-Host "aviso: $v1exe nao encontrado - release v1.0 ignorada" -ForegroundColor Yellow
    }

    # A release v1.0 e criada depois da v2.2; o GitHub marca a mais recente como
    # "Latest" por padrao. Forca a v2.2 como Latest para o botao principal.
    $releaseJson = Capturar $Gh @("api", "repos/$Owner/$Repo/releases/tags/v2.2")
    if ($releaseJson) {
        $v2id = ($releaseJson | ConvertFrom-Json).id
        if ($v2id) {
            Rodar $Gh @("api", "-X", "PATCH", "repos/$Owner/$Repo/releases/$v2id", "-F", "make_latest=true") -Silencioso | Out-Null
            Write-Host "v2.2 marcada como Latest"
        }
    }
}

Passo "Concluido"
Write-Host "https://github.com/$Owner/$Repo" -ForegroundColor Green
Write-Host "https://github.com/$Owner/$Repo/releases" -ForegroundColor Green
exit 0
