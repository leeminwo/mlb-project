# routers/admin/posts/__init__.py
from fastapi import APIRouter
from .boards import router as boards_router   # <- 우리가 만든 범용 라우터

router = APIRouter()
router.include_router(boards_router)
