from fastapi import APIRouter

from app.api.v1.endpoints import (
    admin,
    analytics,
    auth,
    conversations,
    documents,
    health,
    organizations,
    users,
    workspaces,
)

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(organizations.router)
api_router.include_router(workspaces.router)
api_router.include_router(documents.router)
api_router.include_router(conversations.router)
api_router.include_router(analytics.organization_router)
api_router.include_router(analytics.workspace_router)
api_router.include_router(admin.router)
