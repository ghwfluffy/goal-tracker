from fastapi import APIRouter

from app.api.routes.auth import router as auth_router
from app.api.routes.backups import router as backups_router
from app.api.routes.dashboards import router as dashboards_router
from app.api.routes.goals import router as goals_router
from app.api.routes.invitation_codes import router as invitation_codes_router
from app.api.routes.metrics import router as metrics_router
from app.api.routes.notifications import router as notifications_router
from app.api.routes.share_links import router as share_links_router
from app.api.routes.status import router as status_router
from app.api.routes.users import router as users_router

api_router = APIRouter()
api_router.include_router(backups_router, tags=["backups"])
api_router.include_router(auth_router, tags=["auth"])
api_router.include_router(dashboards_router, tags=["dashboards"])
api_router.include_router(goals_router, tags=["goals"])
api_router.include_router(invitation_codes_router, tags=["invitation-codes"])
api_router.include_router(metrics_router, tags=["metrics"])
api_router.include_router(notifications_router, tags=["notifications"])
api_router.include_router(share_links_router, tags=["share-links"])
api_router.include_router(status_router, tags=["status"])
api_router.include_router(users_router, tags=["users"])
