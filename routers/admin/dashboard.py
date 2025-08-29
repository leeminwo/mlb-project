# routers/admin/dashboard.py
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette import status

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory="templates")

@router.get("/", include_in_schema=False)
async def admin_root():
    # /admin → /admin/dashboard
    return RedirectResponse("/admin/dashboard", status_code=status.HTTP_302_FOUND)

@router.get("/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    # ✅ 관리자 로그인 플래그 확인
    if not request.session.get("admin_logged_in"):
        return RedirectResponse("/admin/login", status_code=status.HTTP_302_FOUND)

    response = templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request,
            "active_page": "dashboard",
            "admin_name": request.session.get("admin_name"),
        },
    )
    # (선택) 캐시 방지: 로그아웃 후 뒤로가기로 보이는 것 방지
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    return response
