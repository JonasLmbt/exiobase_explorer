# API v1 – Entwurf

Base path: `/api/v1`

Ziel:
- Browser-Frontend ohne Login
- Gleiches Feature-Set wie PyQt (Selection/Stage/Region Analysis)
- Lange Berechnungen als Jobs (Queue), damit Requests nicht timeouten

## Grundprinzipien

- **Stateless Requests**: Client schickt `year` + `language` (und Auswahl) pro Request/Job.
- **Server-side Cache**: Backend cached geladene `IOSystem`/Fast-DB pro Worker-Prozess (keyed by `year`,`language`).
- **Jobs**: Rechenintensive Analysen laufen asynchron. API liefert `job_id`, UI pollt Status.

## Endpoints

### Health
- `GET /health`
  - Response: `{ "status": "ok" }`

### Meta / Optionen
- `GET /meta/years`
  - Scannt `fast_databases_dir` nach `FAST_IOT_YYYY_pxp`
  - Response: `{ "years": ["2022","2021", ...] }`

- `GET /meta/languages?year=2022`
  - Liest verfügbare Sprachen aus `general.xlsx` (Sheets)
  - Response: `{ "languages": ["Deutsch", "English", ...] }`

### Hierarchien (für Selection-UI)
- `GET /hierarchy/regions?year=2022&language=Deutsch`
  - Response: `{ "names": [...levelNames], "tree": {...} }`
  - `tree` ist ein verschachteltes Dict (wie Qt `multiindex_to_nested_dict`).

- `GET /hierarchy/sectors?year=2022&language=Deutsch`
  - Response: `{ "names": [...levelNames], "tree": {...} }`

- `GET /impacts?year=2022&language=Deutsch`
  - Response: `{ "impacts": [{ "key": "...", "label": "...", "unit": "..."? }, ...] }`

### Jobs
- `POST /jobs`
  - Startet eine Analyse als Job.
  - Request:
    ```json
    {
      "year": 2022,
      "language": "Deutsch",
      "selection": {
        "mode": "regions_sectors",
        "regions": [0, 1, 2],
        "sectors": [0, 5, 10]
      },
      "analysis": {
        "type": "stage_bubble",
        "impacts": ["..."]
      }
    }
    ```
  - Response: `{ "job_id": "..." }`

- `GET /jobs/{job_id}`
  - Response:
    ```json
    { "job_id":"...", "state":"queued|running|done|failed", "progress": 0.0, "message": "..." }
    ```

- `GET /jobs/{job_id}/result`
  - Response ist je nach `analysis.type` unterschiedlich (JSON für Daten, ggf. signierte Download-URLs).

## Analysen (erste Iteration)

### Stage analysis (Bubble)
- `analysis.type = "stage_bubble"`
- Output (MVP): JSON-Daten (für Frontend-Chart) **oder** serverseitig gerendertes PNG/SVG.

### Region analysis
- `analysis.type = "region_world_map" | "region_topn" | "region_flopn" | "region_pie"`
- Output (MVP): Daten-Frames (TopN/Pie) als JSON + optional Bildexport.

