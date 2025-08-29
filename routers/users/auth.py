# routers/users/auth.py
from fastapi import APIRouter, Request, Form, Query, Depends, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from starlette import status
from urllib.parse import urlparse
import re

from models.users import get_user_by_user_id, get_user_by_email, get_user_by_nickname, verify_password, create_user

router = APIRouter(prefix="", tags=["auth"])
templates = Jinja2Templates(directory="templates")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

async def get_current_user(request: Request):
    """현재 로그인한 사용자 정보를 반환하는 의존성 함수"""
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다")
    return user

def safe_next(next_url: str | None, default: str = "/") -> str:
    """외부 도메인으로의 오픈 리다이렉트를 방지."""
    if not next_url:
        return default
    parsed = urlparse(next_url)
    # 스킴/호스트가 없고, 루트 상대경로만 허용
    if parsed.scheme or parsed.netloc:
        return default
    if not next_url.startswith("/"):
        return default
    return next_url

@router.get("/check-duplicate")
async def check_duplicate(type: str = Query(...), value: str = Query(...)):
    """중복 검사 API"""
    if not value or len(value.strip()) < 2:
        return JSONResponse({"available": False, "message": "최소 2자 이상 입력해주세요"})
    
    value = value.strip()
    
    try:
        if type == "user_id":
            existing = await get_user_by_user_id(value)
        elif type == "nickname":
            # 닉네임 중복 검사를 위한 함수가 필요합니다
            from models.users import get_user_by_nickname
            existing = await get_user_by_nickname(value)
        elif type == "email":
            existing = await get_user_by_email(value)
        else:
            return JSONResponse({"available": False, "message": "잘못된 검사 타입입니다"})
        
        return JSONResponse({"available": existing is None, "message": "이미 사용 중입니다" if existing else "사용 가능합니다"})
    
    except Exception as e:
        return JSONResponse({"available": False, "message": f"검사 중 오류가 발생했습니다: {str(e)}"})

@router.get("/login")
async def login_form(request: Request, next: str = "/"):
    # 이미 로그인 상태면 next로 바로
    if request.session.get("user"):
        return RedirectResponse(url=safe_next(next), status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(
        "users/login.html",
        {"request": request, "next": next, "error": None}
    )

@router.post("/login")
async def login_submit(
    request: Request,
    user_id: str = Form(...),
    password: str = Form(...),
    next: str = Form("/")
):
    user_id = user_id.strip()
    if not user_id:
        return templates.TemplateResponse(
            "users/login.html",
            {"request": request, "next": next, "error": "아이디를 입력해주세요."},
            status_code=status.HTTP_401_UNAUTHORIZED
        )

    user = await get_user_by_user_id(user_id)
    if not user or not verify_password(password, user["password_hash"]):
        return templates.TemplateResponse(
            "users/login.html",
            {"request": request, "next": next, "error": "아이디 또는 비밀번호가 올바르지 않습니다."},
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    # ✅ 유저 세션만 세팅 (관리자와 분리)
    request.session["user"] = {
        "id": user["id"],
        "user_id": user["user_id"],
        "name": user["name"],
        "nickname": user["nickname"],
        "is_admin": (user["role"] == "admin"),
        "points": user.get("points", 0),
        "level": user.get("level", 1),
    }
    return RedirectResponse(url=safe_next(next), status_code=status.HTTP_303_SEE_OTHER)

@router.get("/register")
async def register_form(request: Request, next: str = "/"):
    if request.session.get("user"):
        return RedirectResponse(url=safe_next(next), status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(
        "users/register.html",
        {"request": request, "next": next, "error": None}
    )

@router.post("/register")
async def register_submit(
    request: Request,
    user_id: str = Form(...),
    nickname: str = Form(...),
    email: str = Form(""),
    password: str = Form(...),
    password_confirm: str = Form(...),
    next: str = Form("/")
):
    user_id = user_id.strip()
    nickname = nickname.strip()
    email = email.strip().lower() if email else None

    if not user_id:
        return templates.TemplateResponse(
            "users/register.html",
            {"request": request, "next": next, "error": "아이디를 입력해주세요."},
            status_code=status.HTTP_400_BAD_REQUEST
        )
    if len(user_id) < 3:
        return templates.TemplateResponse(
            "users/register.html",
            {"request": request, "next": next, "error": "아이디는 3자 이상이어야 합니다."},
            status_code=status.HTTP_400_BAD_REQUEST
        )
    if password != password_confirm:
        return templates.TemplateResponse(
            "users/register.html",
            {"request": request, "next": next, "error": "비밀번호가 일치하지 않습니다."},
            status_code=status.HTTP_400_BAD_REQUEST
        )
    if len(nickname) < 2:
        return templates.TemplateResponse(
            "users/register.html",
            {"request": request, "next": next, "error": "닉네임은 2자 이상이어야 합니다."},
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    # 비밀번호 규칙 검사 (회원가입에서만)
    import re
    password_pattern = re.compile(r'^(?=.*[a-zA-Z])(?=.*\d)(?=.*[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>/?])[a-zA-Z\d!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>/?]{6,}$')
    if not password_pattern.match(password):
        return templates.TemplateResponse(
            "users/register.html",
            {"request": request, "next": next, "error": "비밀번호는 영문+숫자+특수문자를 포함하여 6자 이상이어야 합니다."},
            status_code=status.HTTP_400_BAD_REQUEST
        )

    # 아이디 중복 확인
    existing_user_id = await get_user_by_user_id(user_id)
    if existing_user_id:
        return templates.TemplateResponse(
            "users/register.html",
            {"request": request, "next": next, "error": "이미 사용 중인 아이디입니다."},
            status_code=status.HTTP_400_BAD_REQUEST
        )

    # 닉네임 중복 확인 (닉네임도 unique해야 함)
    if email:
        from models.users import get_user_by_email
        existing_email = await get_user_by_email(email)
        if existing_email:
            return templates.TemplateResponse(
                "users/register.html",
                {"request": request, "next": next, "error": "이미 가입된 이메일입니다."},
                status_code=status.HTTP_400_BAD_REQUEST
            )

    uid = await create_user(user_id=user_id, nickname=nickname, email=email, name=nickname, plain_password=password, role="user")
    # 가입 직후 자동 로그인
    request.session["user"] = {"id": uid, "user_id": user_id, "name": nickname, "nickname": nickname, "is_admin": False}
    return RedirectResponse(url=safe_next(next), status_code=status.HTTP_303_SEE_OTHER)

@router.post("/logout")
async def logout(request: Request, next: str = Form("/", alias="next")):
    # ✅ 유저 세션만 제거 (관리자 세션은 건드리지 않음)
    request.session.pop("user", None)
    return RedirectResponse(url=safe_next(next), status_code=status.HTTP_303_SEE_OTHER)
