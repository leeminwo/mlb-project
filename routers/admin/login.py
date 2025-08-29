# routers/admin/login.py
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette import status                      # ✅ 변경: status 모듈 사용
from urllib.parse import urlparse

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory="templates")

ADMIN_ID = "admin"
ADMIN_PW = "1234"

def safe_next(next_url: str | None, default: str = "/admin/dashboard") -> str:
    if not next_url:
        return default
    parsed = urlparse(next_url)
    if parsed.scheme or parsed.netloc:
        return default
    if not next_url.startswith("/"):
        return default
    return next_url

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, next: str = "/admin/dashboard"):
    if request.session.get("admin_logged_in"):
        return RedirectResponse(safe_next(next), status_code=status.HTTP_302_FOUND)  # GET은 302 OK
    error = request.session.pop("login_error", None)
    return templates.TemplateResponse("admin/login.html", {"request": request, "error": error, "next": next})

@router.post("/login")
async def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    next: str = Form("/admin/dashboard"),
):
    if username == ADMIN_ID and password == ADMIN_PW:
        request.session["admin_logged_in"] = True
        request.session["admin_name"] = username
        return RedirectResponse(safe_next(next), status_code=status.HTTP_303_SEE_OTHER)  # ✅ 303

    request.session["login_error"] = "잘못된 아이디 또는 비밀번호입니다."
    return RedirectResponse(f"/admin/login?next={next}", status_code=status.HTTP_303_SEE_OTHER)  # ✅ 303

@router.post("/logout")
async def admin_logout_post(request: Request, next: str = Form("/admin/login")):
    request.session.pop("admin_logged_in", None)
    request.session.pop("admin_name", None)
    return RedirectResponse(safe_next(next, default="/admin/login"), status_code=status.HTTP_303_SEE_OTHER)  # ✅ 303

@router.get("/logout")
async def admin_logout_get(request: Request, next: str = "/admin/login"):
    request.session.pop("admin_logged_in", None)
    request.session.pop("admin_name", None)
    return RedirectResponse(safe_next(next, default="/admin/login"), status_code=status.HTTP_302_FOUND)
