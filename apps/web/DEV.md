# Web Dev – Quickstart

## Lokal (ohne Docker)

### 1) Redis starten (optional)
Für den normalen Job-Betrieb brauchst du Redis + Worker. Wenn du **kein Redis** installieren willst, kannst du Jobs auch synchron im API-Prozess laufen lassen:
```powershell
$env:USE_SYNC_JOBS="1"
```
Dann brauchst du **keinen** Redis/Worker für die ersten Tests (aber Requests blockieren während der Rechnung).

### 2) API starten
```powershell
$env:REDIS_URL = "redis://localhost:6379/0"
$env:EXIOBASE_EXPLORER_DB_DIR = "C:\\path\\to\\exiobase"
$env:USE_SYNC_JOBS="1"
python -m pip install -r apps/web/api/requirements.txt
python -m uvicorn app.main:app --app-dir apps/web/api --reload --port 8000
```
Optional: Wenn `regions.xlsx` ein Sheet `population` (EXIOBASE-Code -> Einwohner) enthÃ¤lt, zeigt die Karte im Hover-Tooltip zusÃ¤tzlich "pro Kopf" an.

### 3) Worker starten
```powershell
$env:REDIS_URL = "redis://localhost:6379/0"
$env:EXIOBASE_EXPLORER_DB_DIR = "C:\\path\\to\\exiobase"
python -m pip install -r apps/web/api/requirements.txt
rq worker --url redis://localhost:6379/0
```

### 4) UI starten
```powershell
cd apps/web/ui
npm install
npm run dev
```

### 5) Testen
- UI: `http://localhost:5173`
- API health: `http://localhost:8000/api/v1/health`
- API details (Pfadcheck): `http://localhost:8000/api/v1/health/details?year=2022`
- In der UI: oben rechts steht `API: online` wenn die API erreichbar ist.
- Dann: Tab **Visualisation** → **Stage analysis** → **Impact auswählen** → **Run** → Bubble-Diagramm erscheint (als Bild).

## Docker Compose (api+worker+redis+nginx)

```powershell
$env:EXIOBASE_EXPLORER_DB_DIR = "C:\\path\\to\\exiobase"
docker compose -f apps/web/compose.yml up --build
```

- UI: `http://localhost:8080`
- API: `http://localhost:8000/api/v1/health`
