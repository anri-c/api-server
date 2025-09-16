"""Health check router for API server monitoring.

This module provides health check endpoints for monitoring the API server
status, database connectivity, and system information.
"""

from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session
from datetime import datetime

from ..database import get_session, test_database_connection, get_database_info
from ..config import get_settings, Settings

router = APIRouter(
    prefix="/api/health",
    tags=["health"],
    responses={
        500: {"description": "Internal server error"},
        503: {"description": "Service unavailable"}
    }
)


@router.get(
    "/",
    response_model=Dict[str, Any],
    summary="Basic health check",
    description="Returns basic health status of the API server"
)
async def health_check() -> Dict[str, Any]:
    """Basic health check endpoint.
    
    Returns basic information about the API server status including
    timestamp and service availability.
    
    Returns:
        Dict[str, Any]: Health status information
        
    Example:
        {
            "status": "healthy",
            "timestamp": "2024-01-01T12:00:00Z",
            "service": "api-server",
            "version": "1.0.0"
        }
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "service": "api-server",
        "version": "1.0.0"
    }


@router.get(
    "/detailed",
    response_model=Dict[str, Any],
    summary="Detailed health check with database connectivity",
    description="Returns detailed health status including database connectivity check"
)
async def detailed_health_check(
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings)
) -> Dict[str, Any]:
    """Detailed health check with database connectivity.
    
    Performs comprehensive health checks including database connectivity,
    configuration status, and system information.
    
    Args:
        session: Database session for connectivity testing
        settings: Application settings
        
    Returns:
        Dict[str, Any]: Detailed health status information
        
    Raises:
        HTTPException: If critical services are unavailable
        
    Example:
        {
            "status": "healthy",
            "timestamp": "2024-01-01T12:00:00Z",
            "service": "api-server",
            "version": "1.0.0",
            "database": {
                "status": "connected",
                "info": {...}
            },
            "environment": "development"
        }
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "service": "api-server",
        "version": "1.0.0",
        "environment": settings.environment
    }
    
    # Test database connectivity
    try:
        db_connected = test_database_connection()
        if db_connected:
            health_status["database"] = {
                "status": "connected",
                "info": get_database_info()
            }
        else:
            health_status["database"] = {
                "status": "disconnected",
                "error": "Database connection failed"
            }
            health_status["status"] = "unhealthy"
    except Exception as e:
        health_status["database"] = {
            "status": "error",
            "error": str(e)
        }
        health_status["status"] = "unhealthy"
    
    # If database is unhealthy, return 503 Service Unavailable
    if health_status["status"] == "unhealthy":
        raise HTTPException(
            status_code=503,
            detail="Service unavailable - database connectivity issues"
        )
    
    return health_status


@router.get(
    "/ready",
    response_model=Dict[str, Any],
    summary="Readiness probe",
    description="Kubernetes-style readiness probe for deployment health checks"
)
async def readiness_probe() -> Dict[str, Any]:
    """Readiness probe for Kubernetes deployments.
    
    This endpoint is designed for Kubernetes readiness probes to determine
    if the service is ready to receive traffic.
    
    Returns:
        Dict[str, Any]: Readiness status
        
    Raises:
        HTTPException: If service is not ready
        
    Example:
        {
            "ready": true,
            "timestamp": "2024-01-01T12:00:00Z"
        }
    """
    # Test database connectivity for readiness
    try:
        db_connected = test_database_connection()
        if not db_connected:
            raise HTTPException(
                status_code=503,
                detail="Service not ready - database unavailable"
            )
        
        return {
            "ready": True,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Service not ready - {str(e)}"
        )


@router.get(
    "/live",
    response_model=Dict[str, Any],
    summary="Liveness probe",
    description="Kubernetes-style liveness probe for container health checks"
)
async def liveness_probe() -> Dict[str, Any]:
    """Liveness probe for Kubernetes deployments.
    
    This endpoint is designed for Kubernetes liveness probes to determine
    if the service is alive and should not be restarted.
    
    Returns:
        Dict[str, Any]: Liveness status
        
    Example:
        {
            "alive": true,
            "timestamp": "2024-01-01T12:00:00Z"
        }
    """
    return {
        "alive": True,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
