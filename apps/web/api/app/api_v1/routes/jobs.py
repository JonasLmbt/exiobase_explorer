from __future__ import annotations

from rq import Queue
from rq.job import Job

from fastapi import APIRouter, HTTPException

from ...redis_conn import get_redis_connection
from ...schemas import JobRequest, JobStatus
from ...jobs import run_analysis

router = APIRouter()


@router.post("/jobs")
def create_job(req: JobRequest) -> dict:
    conn = get_redis_connection()
    queue = Queue(connection=conn)
    job = queue.enqueue(run_analysis, req.model_dump())
    return {"job_id": job.id}


@router.get("/jobs/{job_id}", response_model=JobStatus)
def get_job_status(job_id: str) -> JobStatus:
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
    conn = get_redis_connection()
    try:
        job = Job.fetch(job_id, connection=conn)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Job not found: {e}") from e

    status = job.get_status(refresh=True)
    if status != "finished":
        raise HTTPException(status_code=409, detail=f"Job not finished (status={status})")

    return {"job_id": job.id, "result": job.result}

