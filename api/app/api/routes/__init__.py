from app.api.routes.auth import router as auth_router
from app.api.routes.dashboards import router as dashboards_router
from app.api.routes.goals import router as goals_router
from app.api.routes.invitation_codes import router as invitation_codes_router
from app.api.routes.metrics import router as metrics_router
from app.api.routes.status import router as status_router
from app.api.routes.users import router as users_router

__all__ = [
    "auth_router",
    "dashboards_router",
    "goals_router",
    "invitation_codes_router",
    "metrics_router",
    "status_router",
    "users_router",
]
