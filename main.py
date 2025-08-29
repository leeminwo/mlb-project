from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
import os

from database.connection import database, create_tables

# 집계 라우터 (관리자 하위 전부 포함)
from routers.admin import router as admin_router
from routers.public import router as public_router
from routers.users.board import router as board_router

# ✅ 유저 인증 라우터 추가
from routers.users import auth as user_auth
from routers.users import profile as user_profile
from routers.users.board import vote as vote_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    await database.connect()
    await create_tables()
    yield
    await database.disconnect()

app = FastAPI(lifespan=lifespan)

# 세션/정적/템플릿
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET", "dev-secret"),
    same_site="lax",
)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.state.templates = Jinja2Templates(directory="templates")

# ✅ 라우터 등록 — 순서 중요!
app.include_router(admin_router)          # 1) admin (더 구체적인 경로 먼저)
app.include_router(user_auth.router)      # 2) 유저 로그인/회원가입(/login, /register, /logout) - 구체적 경로 먼저
app.include_router(user_profile.router)   # 3) 유저 프로필(/profile) - 구체적 경로 먼저
app.include_router(board_router)          # 4) 사용자 게시판 (/invest, /game 등) - 구체적 경로 먼저
app.include_router(vote_router.router)    # 5) 투표 시스템 - 구체적 경로 먼저
app.include_router(public_router)         # 6) public (/{category} catch-all) - 가장 마지막

# (선택) 라우트 디버그
print("=== ROUTES ===")
for r in app.router.routes:
    try:
        print(getattr(r, "name", None), getattr(r, "path", None))
    except Exception:
        pass
print("=== END ===")

# ❌ 아래 리다이렉트는 삭제해야 유저용 /login이 정상 작동합니다.
# from fastapi.responses import RedirectResponse
# from starlette import status
# @app.get("/login")
# async def login_redirect():
#     return RedirectResponse(url="/admin/login", status_code=status.HTTP_307_TEMPORARY_REDIRECT)
