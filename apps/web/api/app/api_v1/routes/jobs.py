from __future__ import annotations

import hashlib
import json
import time
import uuid

from rq import Queue
from rq.job import Job
from rq.registry import StartedJobRegistry

from fastapi import APIRouter, HTTPException

from ...jobs import run_analysis
from ...redis_conn import get_redis_connection
from ...schemas import JobRequest, JobStatus
from ...settings import max_active_jobs, sync_job_ttl_seconds, use_sync_jobs

router = APIRouter()

CACHE_TTL_SECONDS = 24 * 60 * 60
_SYNC_JOBS: dict[str, dict] = {}
_SYNC_HASH_TO_JOB: dict[str, str] = {}


def _purge_sync_jobs() -> None:
    ttl = sync_job_ttl_seconds()
    now = time.time()
    expired = [job_id for job_id, rec in _SYNC_JOBS.items() if (now - float(rec.get("ts", now))) > ttl]
    for job_id in expired:
        _SYNC_JOBS.pop(job_id, None)
    for h, job_id in list(_SYNC_HASH_TO_JOB.items()):
        if job_id not in _SYNC_JOBS:
            _SYNC_HASH_TO_JOB.pop(h, None)


@router.post("/jobs")
def create_job(req: JobRequest) -> dict:
    payload = req.model_dump()
    cache_key = "jobcache:" + hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()

    _purge_sync_jobs()
    if use_sync_jobs():
        cached = _SYNC_HASH_TO_JOB.get(cache_key)
        if cached and cached in _SYNC_JOBS:
            return {"job_id": cached, "cached": True, "sync": True}

        job_id = uuid.uuid4().hex
        try:
            result = run_analysis(payload)
            state = "failed" if (isinstance(result, dict) and result.get("ok") is False) else "done"
            _SYNC_JOBS[job_id] = {
                "ts": time.time(),
                "state": state,
                "progress": 1.0,
                "message": "done" if state == "done" else "failed",
                "result": result,
            }
            _SYNC_HASH_TO_JOB[cache_key] = job_id
            return {"job_id": job_id, "cached": False, "sync": True}
        except Exception as e:
            _SYNC_JOBS[job_id] = {
                "ts": time.time(),
                "state": "failed",
                "progress": 1.0,
                "message": str(e),
                "result": {"ok": False, "error": str(e)},
            }
            _SYNC_HASH_TO_JOB[cache_key] = job_id
            return {"job_id": job_id, "cached": False, "sync": True}

    conn = get_redis_connection()
    queue = Queue(connection=conn)

    started = StartedJobRegistry(queue=queue).count
    queued = queue.count
    if (started + queued) >= max_active_jobs():
        raise HTTPException(
            status_code=429,
            detail=f"Server busy (active_jobs={started + queued}). Try again later.",
        )

    cached_job_id = conn.get(cache_key)
    if cached_job_id:
        cached_job_id_str = cached_job_id.decode("utf-8", errors="ignore")
        try:
            Job.fetch(cached_job_id_str, connection=conn)
            return {"job_id": cached_job_id_str, "cached": True}
        except Exception:
            conn.delete(cache_key)

    job = queue.enqueue(run_analysis, payload, result_ttl=CACHE_TTL_SECONDS)
    conn.set(cache_key, job.id, ex=CACHE_TTL_SECONDS)
    return {"job_id": job.id, "cached": False}


@router.get("/jobs/{job_id}", response_model=JobStatus)
def get_job_status(job_id: str) -> JobStatus:
    _purge_sync_jobs()
    if use_sync_jobs():
        rec = _SYNC_JOBS.get(job_id)
        if not rec:
            raise HTTPException(status_code=404, detail="Job not found")
        return JobStatus(
            job_id=job_id,
            state=rec.get("state", "done"),
            progress=float(rec.get("progress", 1.0)),
            message=rec.get("message"),
        )

    conn = get_redis_connection()
    try:
        job = Job.fetch(job_id, connection=conn)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Job not found: {e}") from e

    status = job.get_status(refresh=True)
    if status in {"queued", "deferred"}:
        state = "queued"
    elif status in {"started"}:
        state = "running"
    elif status in {"finished"}:
        state = "done"
    else:
        state = "failed"

    progress = float(job.meta.get("progress", 0.0) or 0.0)
    message = job.meta.get("message")
    return JobStatus(job_id=job.id, state=state, progress=progress, message=message)


@router.get("/jobs/{job_id}/result")
def get_job_result(job_id: str) -> dict:
    _purge_sync_jobs()
    if use_sync_jobs():
        rec = _SYNC_JOBS.get(job_id)
        if not rec:
            raise HTTPException(status_code=404, detail="Job not found")
        if rec.get("state") != "done":
            raise HTTPException(status_code=409, detail=f"Job not finished (state={rec.get('state')})")
        return {"job_id": job_id, "result": rec.get("result")}

    conn = get_redis_connection()
    try:
        job = Job.fetch(job_id, connection=conn)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Job not found: {e}") from e

    status = job.get_status(refresh=True)
    if status != "finished":
        raise HTTPException(status_code=409, detail=f"Job not finished (status={status})")

    return {"job_id": job.id, "result": job.result}
