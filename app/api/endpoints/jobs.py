from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.job import Job, JobStatus
from app.schemas.job import JobCreate, JobResponse, JobUpdate
from app.workers.tasks import process_job

router = APIRouter()

@router.post("/", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    job_in: JobCreate,
    db: Session = Depends(get_db)
):
    """Create a new job and queue it for processing"""
    # Create job in database
    job = Job(
        name=job_in.name,
        description=job_in.description,
        status=JobStatus.PENDING
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    
    # Queue job for processing
    task = process_job.delay(job.id)
    
    # Update job with task ID
    job.task_id = task.id
    db.commit()
    db.refresh(job)
    
    return job

@router.get("/", response_model=List[JobResponse])
async def list_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[JobStatus] = None,
    db: Session = Depends(get_db)
):
    """List all jobs with optional status filter"""
    query = db.query(Job)
    if status:
        query = query.filter(Job.status == status)
    
    jobs = query.offset(skip).limit(limit).all()
    return jobs

@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific job by ID"""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    return job

@router.get("/{job_id}/status")
async def get_job_status(
    job_id: int,
    db: Session = Depends(get_db)
):
    """Get job status including Celery task progress"""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    response = {
        "job_id": job.id,
        "status": job.status,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
        "completed_at": job.completed_at
    }
    
    # Get Celery task status if available
    if job.task_id and job.status == JobStatus.PROCESSING:
        from app.workers.celery_app import celery_app
        task_result = celery_app.AsyncResult(job.task_id)
        
        if task_result.state == "PROGRESS":
            response["progress"] = task_result.info
        else:
            response["task_state"] = task_result.state
    
    return response

@router.delete("/{job_id}")
async def cancel_job(
    job_id: int,
    db: Session = Depends(get_db)
):
    """Cancel a pending or processing job"""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    if job.status not in [JobStatus.PENDING, JobStatus.PROCESSING]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel job in {job.status} status"
        )
    
    # Revoke Celery task if it exists
    if job.task_id:
        from app.workers.celery_app import celery_app
        celery_app.control.revoke(job.task_id, terminate=True)
    
    # Update job status
    job.status = JobStatus.CANCELLED
    db.commit()
    
    return {"message": f"Job {job_id} cancelled"} 