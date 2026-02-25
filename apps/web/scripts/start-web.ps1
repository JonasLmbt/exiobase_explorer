[CmdletBinding()]
param(
    [string]$DbDir,
    [switch]$InstallDeps
)

$ErrorActionPreference = "Stop"

function Resolve-NpmCmd {
    $cmd = Get-Command npm.cmd -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }

    $defaultNpm = Join-Path $env:ProgramFiles "nodejs\npm.cmd"
    if (Test-Path $defaultNpm) { return $defaultNpm }

    $wingetBase = Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Packages"
    if (Test-Path $wingetBase) {
        $npm = Get-ChildItem -Path $wingetBase -Recurse -Filter "npm.cmd" -ErrorAction SilentlyContinue |
            Select-Object -First 1
        if ($npm) { return $npm.FullName }
    }

    throw "npm.cmd nicht gefunden. Installiere Node.js LTS (winget install -e --id OpenJS.NodeJS.LTS)."
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$uiDir = Join-Path $repoRoot "apps\web\ui"
$apiRequirements = Join-Path $repoRoot "apps\web\api\requirements.txt"
$venvPython = Join-Path $repoRoot "venv\Scripts\python.exe"

if (-not $DbDir) {
    $DbDir = Join-Path $repoRoot "exiobase"
}

if (-not (Test-Path $DbDir)) {
    throw "Datenordner nicht gefunden: $DbDir"
}
$DbDir = (Resolve-Path $DbDir).Path

$fastPath = Join-Path $DbDir "fast_databases"
if (-not (Test-Path $fastPath)) {
    Write-Warning "fast_databases wurde nicht gefunden unter: $fastPath"
    Write-Warning "Die API startet evtl. trotzdem, aber Analysen/Jahresliste koennen fehlschlagen."
}

$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    throw "python nicht gefunden. Bitte Python installieren und PATH pruefen."
}
$pythonExe = if (Test-Path $venvPython) { $venvPython } else { $pythonCmd.Source }

$npmCmd = Resolve-NpmCmd
$nodeDir = Split-Path -Parent $npmCmd
$nodeExe = Join-Path $nodeDir "node.exe"
if (-not (Test-Path $nodeExe)) {
    throw "node.exe nicht gefunden neben npm.cmd: $nodeExe"
}

Write-Host "Repo: $repoRoot"
Write-Host "DB:   $DbDir"
Write-Host "Py:   $pythonExe"
Write-Host "npm:  $npmCmd"

if ($InstallDeps) {
    Write-Host "Installiere API-Abhaengigkeiten..."
    & $pythonExe -m pip install -r $apiRequirements

    Write-Host "Installiere UI-Abhaengigkeiten..."
    Push-Location $uiDir
    try {
        & $npmCmd install
    }
    finally {
        Pop-Location
    }
}

$null = & $pythonExe -c "import importlib.util, sys; sys.exit(0 if importlib.util.find_spec('uvicorn') else 1)" 2>$null
if ($LASTEXITCODE -ne 0) {
    throw "uvicorn fehlt fuer $pythonExe. Starte mit -InstallDeps oder installiere: `"$pythonExe`" -m pip install -r apps/web/api/requirements.txt"
}

$apiCmd = 'set "EXIOBASE_EXPLORER_DB_DIR=' + $DbDir + '" && set "USE_SYNC_JOBS=1" && "' + $pythonExe + '" -m uvicorn app.main:app --app-dir apps/web/api --host 127.0.0.1 --port 8000'
$uiCmd = 'set "PATH=' + $nodeDir + ';%PATH%" && "' + $npmCmd + '" run dev -- --host 127.0.0.1 --port 5173'

Start-Process -FilePath "cmd.exe" -WorkingDirectory $repoRoot -ArgumentList "/k", $apiCmd | Out-Null
Start-Process -FilePath "cmd.exe" -WorkingDirectory $uiDir -ArgumentList "/k", $uiCmd | Out-Null

Write-Host ""
Write-Host "Gestartet."
Write-Host "UI:  http://127.0.0.1:5173"
Write-Host "API: http://127.0.0.1:8000/api/v1/health"
Write-Host "Stoppen: powershell -ExecutionPolicy Bypass -File .\apps\web\scripts\stop-web.ps1"
