# routers/admin/__init__.py
from fastapi import APIRouter
from .dashboard import router as dashboard_router
from .users import router as users_router
from .login import router as login_router
from .posts import router as posts_router
from .views import router as views_router

router = APIRouter()

# 각각의 세부 라우터들을 포함
router.include_router(login_router)
router.include_router(dashboard_router)
router.include_router(users_router)
router.include_router(posts_router)
router.include_router(views_router)
