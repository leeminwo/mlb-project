from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="templates")

# ✅ 메인 홈 페이지
@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "category": "trendy"
    })

# ✅ 상단 탭 페이지 (trendy, game, sports 등)
@router.get("/{category}", response_class=HTMLResponse)
async def show_category(request: Request, category: str):
    # 인증 관련 경로는 제외 (다른 라우터에서 처리)
    auth_paths = ["login", "register", "logout", "profile", "check-duplicate", "invest/write", "invest/view"]
    if category in auth_paths or category.startswith(("login", "register", "logout", "profile")):
        raise HTTPException(status_code=404, detail="페이지를 찾을 수 없습니다")
    
    valid_tabs = [
        "trendy", "game", "sports", "invest",
        "gallery", "free", "humor",
        "report", "counsel"
    ]
    if category not in valid_tabs:
        category = "trendy"

    return templates.TemplateResponse("index.html", {
        "request": request,
        "category": category,
        "posts": []
    })
