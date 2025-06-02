from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.core.queue_manager import get_queue_manager, QueueManager
from app.core.circuit_breaker import ThirdPartyService, CircuitBreakerService
from app.core.config import get_redis_connection
from app.core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()

class ServicePauseRequest(BaseModel):
    service: str
    reason: str = "manual_pause"

class ServiceResumeRequest(BaseModel):
    service: str

class QueueStatusResponse(BaseModel):
    status: str
    data: Dict[str, Any]

@router.get("/status", response_model=QueueStatusResponse)
async def get_queue_status(
    queue_manager: QueueManager = Depends(get_queue_manager)
):
    """Get comprehensive queue and circuit breaker status."""
    try:
        status_data = queue_manager.get_queue_status()
        
        return QueueStatusResponse(
            status="success",
            data=status_data
        )
        
    except Exception as e:
        logger.error(f"Error getting queue status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting queue status: {str(e)}"
        )

@router.post("/pause-service", response_model=QueueStatusResponse)
async def pause_service(
    request: ServicePauseRequest,
    queue_manager: QueueManager = Depends(get_queue_manager)
):
    """Manually pause a service and its related queues."""
    try:
        # Validate service name
        try:
            service = ThirdPartyService(request.service.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid service name: {request.service}. Valid services: {[s.value for s in ThirdPartyService]}"
            )
        
        # Pause the service
        queue_manager.circuit_breaker.manually_pause_service(service, request.reason)
        
        # Pause related jobs
        paused_jobs = queue_manager.pause_jobs_for_service(service, request.reason)
        
        return QueueStatusResponse(
            status="success",
            data={
                "service": service.value,
                "paused": True,
                "reason": request.reason,
                "jobs_paused": paused_jobs,
                "message": f"Service {service.value} paused successfully"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error pausing service {request.service}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error pausing service: {str(e)}"
        )

@router.post("/resume-service", response_model=QueueStatusResponse)
async def resume_service(
    request: ServiceResumeRequest,
    queue_manager: QueueManager = Depends(get_queue_manager)
):
    """Manually resume a service and its related queues."""
    try:
        # Validate service name
        try:
            service = ThirdPartyService(request.service.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid service name: {request.service}. Valid services: {[s.value for s in ThirdPartyService]}"
            )
        
        # Resume the service
        queue_manager.circuit_breaker.manually_resume_service(service)
        
        # Resume related jobs
        resumed_jobs = queue_manager.resume_jobs_for_service(service)
        
        return QueueStatusResponse(
            status="success",
            data={
                "service": service.value,
                "resumed": True,
                "jobs_resumed": resumed_jobs,
                "message": f"Service {service.value} resumed successfully"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resuming service {request.service}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error resuming service: {str(e)}"
        )

@router.get("/paused-jobs/{service}", response_model=QueueStatusResponse)
async def get_paused_jobs_for_service(
    service: str,
    queue_manager: QueueManager = Depends(get_queue_manager)
):
    """Get paused jobs for a specific service."""
    try:
        # Validate service name
        try:
            service_enum = ThirdPartyService(service.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid service name: {service}. Valid services: {[s.value for s in ThirdPartyService]}"
            )
        
        paused_jobs = queue_manager.get_paused_jobs_by_service(service_enum)
        
        # Convert jobs to dict format
        jobs_data = []
        for job in paused_jobs:
            jobs_data.append({
                "id": job.id,
                "name": job.name,
                "job_type": job.job_type.value,
                "campaign_id": job.campaign_id,
                "error": job.error,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "updated_at": job.updated_at.isoformat() if job.updated_at else None
            })
        
        return QueueStatusResponse(
            status="success",
            data={
                "service": service_enum.value,
                "paused_jobs": jobs_data,
                "count": len(jobs_data)
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting paused jobs for service {service}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting paused jobs: {str(e)}"
        )

@router.get("/paused-leads/{service}", response_model=QueueStatusResponse)
async def get_paused_leads_for_service(
    service: str,
    queue_manager: QueueManager = Depends(get_queue_manager)
):
    """Get lead recovery information for paused enrichment jobs."""
    try:
        # Validate service name
        try:
            service_enum = ThirdPartyService(service.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid service name: {service}. Valid services: {[s.value for s in ThirdPartyService]}"
            )
        
        recovery_info = queue_manager.get_paused_leads_for_recovery(service_enum)
        
        return QueueStatusResponse(
            status="success",
            data={
                "service": service_enum.value,
                "paused_leads": recovery_info,
                "count": len(recovery_info),
                "message": f"Found {len(recovery_info)} leads that need recovery for {service_enum.value}"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting paused leads for service {service}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting paused leads: {str(e)}"
        )

@router.get("/circuit-breakers", response_model=QueueStatusResponse)
async def get_circuit_breaker_status():
    """Get status of all circuit breakers."""
    try:
        redis_client = get_redis_connection()
        circuit_breaker = CircuitBreakerService(redis_client)
        
        status_data = circuit_breaker.get_circuit_status()
        
        return QueueStatusResponse(
            status="success",
            data={
                "circuit_breakers": status_data,
                "timestamp": status_data.get("timestamp", "unknown")
            }
        )
        
    except Exception as e:
        logger.error(f"Error getting circuit breaker status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting circuit breaker status: {str(e)}"
        ) 