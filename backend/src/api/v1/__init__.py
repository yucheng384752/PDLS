"""API v1 router for PDLS"""

from fastapi import APIRouter
from .projects_simple import router as projects_simple_router
# from .projects import router as projects_router
# from .invitations import router as invitations_router

# Create v1 router
v1_router = APIRouter(prefix="/v1")

# Include all v1 endpoints
v1_router.include_router(projects_simple_router)
# v1_router.include_router(projects_router)
# v1_router.include_router(invitations_router)

__all__ = ["v1_router"]