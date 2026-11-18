"""HTTP routers."""

from api.routers.admin import router as admin_router
from api.routers.aia import router as aia_router
from api.routers.auth import router as auth_router
from api.routers.cae import router as cae_router
from api.routers.editor import router as editor_router
from api.routers.journalist import router as journalist_router
from api.routers.manager import router as manager_router
from api.routers.publisher import router as publisher_router

__all__ = [
    "admin_router",
    "auth_router",
    "journalist_router",
    "aia_router",
    "cae_router",
    "publisher_router",
    "editor_router",
    "manager_router",
]
