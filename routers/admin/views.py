# routers/admin/views.py
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.status import HTTP_302_FOUND

router = APIRouter()
templates = Jinja2Templates(directory="templates")

# ✅ 관리자 계정 정보
ADMIN_ID = "admin"
ADMIN_PW = "1234"

def check_admin_session(request: Request) -> bool:
    """어드민 세션이 유효한지 확인"""
    return request.session.get("admin_logged_in") == True

@router.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    if not check_admin_session(request):
        return RedirectResponse("/admin/login", status_code=HTTP_302_FOUND)
    
    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request,
        "active_page": "dashboard"
    })

@router.get("/admin/login", response_class=HTMLResponse)
async def login_page(request: Request):
    # 이미 로그인된 경우 대시보드로
    if check_admin_session(request):
        return RedirectResponse("/admin", status_code=HTTP_302_FOUND)
    
    error = request.session.pop("login_error", None)
    return templates.TemplateResponse("admin/login.html", {
        "request": request,
        "error": error
    })

@router.post("/admin/login")
async def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...)
):
    if username == ADMIN_ID and password == ADMIN_PW:
        request.session["admin_logged_in"] = True
        return RedirectResponse("/admin", status_code=HTTP_302_FOUND)

    request.session["login_error"] = "잘못된 아이디 또는 비밀번호입니다."
    return RedirectResponse("/admin/login", status_code=HTTP_302_FOUND)

@router.post("/admin/logout")
async def logout(request: Request):
    # 어드민 세션만 제거 (사용자 세션은 건드리지 않음)
    request.session.pop("admin_logged_in", None)
    return RedirectResponse("/admin/login", status_code=HTTP_302_FOUND)
