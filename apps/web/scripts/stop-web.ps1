$ErrorActionPreference = "Stop"

$ports = @(5173, 8000)
$connections = Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
    Where-Object { $ports -contains $_.LocalPort }

if (-not $connections) {
    Write-Host "Keine laufenden Web-Prozesse auf Ports 5173/8000 gefunden."
    exit 0
}

$procIds = $connections.OwningProcess | Sort-Object -Unique
foreach ($procId in $procIds) {
    try {
        Stop-Process -Id $procId -Force
        Write-Host "Prozess gestoppt: PID $procId"
    }
    catch {
        Write-Warning "Konnte PID $procId nicht stoppen: $($_.Exception.Message)"
    }
}

Write-Host "Fertig."
