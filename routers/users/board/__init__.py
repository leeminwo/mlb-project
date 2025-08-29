from fastapi import APIRouter
from .read import router as read_router
from .view import router as view_router
from .write import router as write_router
from .like import router as like_router
from .edit import router as edit_router
from .comments import router as comments_router


router = APIRouter()
router.include_router(read_router)
router.include_router(view_router)
router.include_router(write_router)
router.include_router(like_router)
router.include_router(edit_router)
router.include_router(comments_router)