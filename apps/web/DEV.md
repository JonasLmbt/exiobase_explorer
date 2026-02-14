# Web Dev – Quickstart

## Lokal (ohne Docker)

### 1) Redis starten
Am einfachsten via Docker:
```bash
docker run --rm -p 6379:6379 redis:7-alpine
```

### 2) API starten
```powershell
$env:REDIS_URL = "redis://localhost:6379/0"
$env:EXIOBASE_EXPLORER_DB_DIR = "C:\\path\\to\\exiobase"
python -m pip install -r apps/web/api/requirements.txt
python -m uvicorn app.main:app --app-dir apps/web/api --reload --port 8000
```

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

## Docker Compose (api+worker+redis+nginx)

```powershell
$env:EXIOBASE_EXPLORER_DB_DIR = "C:\\path\\to\\exiobase"
docker compose -f apps/web/compose.yml up --build
```

- UI: `http://localhost:8080`
- API: `http://localhost:8000/api/v1/health`

