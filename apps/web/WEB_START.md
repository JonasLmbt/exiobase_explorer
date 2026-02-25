# EXIOBASE Explorer Web Start (Windows)

Diese Anleitung ist nur fuer die Webversion (UI + API) und liegt bewusst getrennt vom Root-README.

## Ziel

Mit einem Kommando beide Dienste starten:

- UI: `http://127.0.0.1:5173`
- API: `http://127.0.0.1:8000/api/v1/health`

## Voraussetzungen

- Windows + PowerShell
- Python 3.11+ (`python --version`)
- Node.js LTS (`node -v`)
- Vorbereitete EXIOBASE Fast-Daten:
  - Erwartet: `exiobase\fast_databases\FAST_IOT_2022_pxp`

Wenn nur `fast load databases\Fast_IOT_...` existiert, bitte nach `fast_databases\FAST_IOT_...` umbenennen/verschieben.

## Schnellstart (empfohlen)

Im Repo-Root ausfuehren:

```powershell
powershell -ExecutionPolicy Bypass -File .\apps\web\scripts\start-web.ps1 -InstallDeps
```

Das Script:

- installiert API- und UI-Abhaengigkeiten (optional via `-InstallDeps`)
- setzt `EXIOBASE_EXPLORER_DB_DIR`
- startet API im Sync-Job-Modus (`USE_SYNC_JOBS=1`)
- startet UI mit Vite

## Stoppen

```powershell
powershell -ExecutionPolicy Bypass -File .\apps\web\scripts\stop-web.ps1
```

## Optionen

Eigener Datenpfad:

```powershell
powershell -ExecutionPolicy Bypass -File .\apps\web\scripts\start-web.ps1 -DbDir "D:\data\exiobase" -InstallDeps
```

## Falls etwas nicht startet

- API pruefen:
  - `http://127.0.0.1:8000/api/v1/health`
  - `http://127.0.0.1:8000/api/v1/health/details?year=2022`
- UI pruefen:
  - `http://127.0.0.1:5173`
  - `http://127.0.0.1:5173/api/v1/health` (Proxy auf API)

