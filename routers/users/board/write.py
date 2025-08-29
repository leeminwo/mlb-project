from fastapi import APIRouter, Request, Form, UploadFile, File, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette import status
from typing import List, Optional
from datetime import datetime, timezone
from urllib.parse import urlencode, quote
import os
from fastapi.templating import Jinja2Templates
from database.connection import database
from .utils import validate_board, normalize_category, save_upload
from . import config
from models.users import add_user_exp, increment_user_stats, EXP_RULES

router = APIRouter()
templates = Jinja2Templates(directory="templates")

LOGIN_URL = "/login"  # 로그인 페이지 경로(프로젝트에 맞게 조정 가능)

# --- helpers ---------------------------------------------------------------

async def table_has_column(table: str, column: str) -> bool:
    row = await database.fetch_one(
        "SELECT 1 FROM pragma_table_info(:t) WHERE name = :c",
        {"t": table, "c": column},
    )
    return row is not None

def get_current_user(request: Request) -> Optional[dict]:
    """
    세션에서 로그인 사용자 반환.
    - main.py에서 SessionMiddleware 세팅되어 있고,
      로그인시 request.session['user'] = {'id': ..., 'name': ..., 'is_admin': ...}
      형태로 저장되어 있다고 가정.
    """
    # 강제 디버깅: 세션 상태 확인
    print(f"🚨 get_current_user 디버깅:")
    print(f"   - request.session 존재: {hasattr(request, 'session')}")
    if hasattr(request, 'session'):
        print(f"   - request.session 내용: {request.session}")
        print(f"   - request.session.get('user'): {request.session.get('user')}")
        print(f"   - request.session.get('admin_logged_in'): {request.session.get('admin_logged_in')}")
    
    u = request.session.get("user") if hasattr(request, "session") else None
    result = u if isinstance(u, dict) else None
    
    print(f"   - 최종 결과: {result}")
    
    # 🚨 강제 에러 발생으로 디버깅
    if not result:
        raise Exception(f"🚨 사용자 세션 없음! 세션 내용: {request.session if hasattr(request, 'session') else '세션 없음'}")
    
    return result

def redirect_to_login(next_url: str) -> RedirectResponse:
    return RedirectResponse(
        url=f"{LOGIN_URL}?next={quote(next_url, safe='')}",
        status_code=status.HTTP_303_SEE_OTHER,
    )

# --- routes ----------------------------------------------------------------

@router.get("/invest/write", response_class=HTMLResponse, name="invest_write")
async def invest_write_form(
    request: Request,
    # ▶ 목록 상태 보존 파라미터(목록 → 쓰기 이동 시 그대로 전달 받기)
    page: int | None = Query(None, ge=1),
    size: int | None = Query(None, ge=1, le=50),
    sort: str | None = Query(None, pattern="^(new|view|like)$"),
    q: str | None = Query(None, min_length=1, max_length=50),
    category: str | None = Query(None),
):
    validate_board("invest")

    # ✨ 로그인 필수: 비로그인 사용자는 로그인 페이지로 보냄(목록 상태 next로 유지)
    user = get_current_user(request)
    if not user:
        # 현재 요청 URL을 next로 넘겨서 로그인 후 다시 돌아오도록
        cur_params = dict(page=page, size=size, sort=sort, q=q, category=category)
        cur_query = urlencode({k: v for k, v in cur_params.items() if v is not None}, doseq=True)
        cur_path = f"/invest/write" + (f"?{cur_query}" if cur_query else "")
        return redirect_to_login(cur_path)

    tabs = config.USER_BOARD_TABS.get("invest", [])

    # 목록 복귀용 back_url
    back_params = {}
    if page: back_params["page"] = page
    if size: back_params["size"] = size
    if sort: back_params["sort"] = sort
    if q:    back_params["q"] = q
    if category: back_params["category"] = category
    back_query = urlencode(back_params, doseq=True)
    back_url = f"/invest" + (f"?{back_query}" if back_query else "")

    return templates.TemplateResponse(
        "boards/invest_write.html",
        {
            "request": request,
            "category": "invest_write",
            "board": "invest",
            "tabs": tabs,
            # 로그인 사용자 정보 전달
            "current_user": user,
            "author_prefill": user.get("nickname") or user.get("name"),
            # ▼ 템플릿에서 hidden input 등으로 활용 가능
            "page": page, "size": size, "sort": sort, "q": q, "selected_category": category,
            "back_url": back_url,
        }
    )

@router.post("/invest/write", response_class=HTMLResponse, name="invest_write_save")
async def invest_write_post(
    request: Request,
    title: str = Form(...),
    content: str = Form(...),
    # author는 폼으로 받더라도 서버에서 세션 사용자로 강제 설정
    author: str = Form(""),
    category: str = Form(...),
    files: List[UploadFile] = File(default=[]),

    # ▶ 목록 상태 보존 파라미터(쓰기 → 저장 후 목록 복귀에 사용)
    page: int | None = Query(None, ge=1),
    size: int | None = Query(None, ge=1, le=50),
    sort: str | None = Query(None, pattern="^(new|view|like)$"),
    q: str | None = Query(None, min_length=1, max_length=50),
    selected_category: str | None = Query(None, alias="category"),
):
    validate_board("invest")

    # ✨ 로그인 필수
    user = get_current_user(request)
    if not user:
        # 폼 제출도 비로그인은 로그인 페이지로
        return redirect_to_login(f"/invest/write")

    title_s = (title or "").strip()
    content_s = (content or "").strip()
    # 작성자/소유자 이름은 세션 사용자 기준으로 고정(폼 값 덮어씀)
    author_s = (user.get("name") or "").strip()
    # 탭 정규화(잘못된 값 들어오면 첫 탭으로 보정)
    category_s = normalize_category("invest", selected_category or category)

    if len(title_s) < 2 or len(content_s) < 10 or not author_s or not category_s:
        tabs = config.USER_BOARD_TABS.get("invest", [])
        return templates.TemplateResponse(
            "boards/invest_write.html",
            {
                "request": request,
                "category": "invest_write",
                "error": "제목은 2자 이상, 내용은 10자 이상, 작성자/카테고리를 정확히 입력해주세요.",
                "title": title, "content": content, "author": author_s or author,
                "category_value": category_s, "board": "invest", "tabs": tabs,
                "current_user": user,
                # ▼ 에러 시에도 목록 상태 유지
                "page": page, "size": size, "sort": sort, "q": q, "selected_category": selected_category,
            }
        )

    # 파일 저장
    upload_dir = os.path.join("static", "uploads", "invest")
    saved_files = []
    for file in files or []:
        try:
            saved = await save_upload(upload_dir, file)
            if saved:
                saved_files.append(saved)
        finally:
            if file:
                await file.close()

    # 저장 쿼리 구성: posts.user_id 컬럼 존재 시 함께 저장
    has_user_id = await table_has_column("posts", "user_id")
    created_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")

    if has_user_id:
        sql = """
            INSERT INTO posts (board, title, content, author, user_id, category, views, likes, deleted, created_at, updated_at)
            VALUES (:board, :title, :content, :author, :user_id, :category, :views, :likes, 0, :created_at, :updated_at)
        """
        params = {
            "board": "invest",
            "title": title_s,
            "content": content_s,
            "author": author_s,
            "user_id": user.get("id"),
            "category": category_s,
            "views": 0,
            "likes": 0,
            "created_at": created_iso,
            "updated_at": created_iso,
        }
    else:
        # user_id가 없을 때도 updated_at / deleted가 있으면 맞춰서 저장
        has_updated_at = await table_has_column("posts", "updated_at")
        has_deleted = await table_has_column("posts", "deleted")

        cols = ["board","title","content","author","category","views","likes","created_at"]
        vals = [":board",":title",":content",":author",":category",":views",":likes",":created_at"]
        params = {
            "board": "invest", "title": title_s, "content": content_s, "author": author_s,
            "category": category_s, "views": 0, "likes": 0, "created_at": created_iso
        }
        if has_updated_at:
            cols.append("updated_at"); vals.append(":updated_at"); params["updated_at"] = created_iso
        if has_deleted:
            cols.append("deleted"); vals.append("0")

        sql = f"INSERT INTO posts ({', '.join(cols)}) VALUES ({', '.join(vals)})"

    await database.execute(sql, params)

    # ✅ 등급 시스템: 게시글 작성 경험치 추가
    try:
        await add_user_exp(user.get("id"), EXP_RULES["post_created"], "post_created")
        await increment_user_stats(user.get("id"), "posts")
    except Exception as e:
        print(f"등급 시스템 오류: {e}")

    # 저장 후 목록 상태로 복귀
    back_params = {}
    if page: back_params["page"] = page
    if size: back_params["size"] = size
    if sort: back_params["sort"] = sort
    if q:    back_params["q"] = q
    if selected_category: back_params["category"] = selected_category

    base = request.url_for("invest_list")
    query = urlencode(back_params, doseq=True)
    url = f"{base}?{query}" if query else base
    return RedirectResponse(url=url, status_code=status.HTTP_303_SEE_OTHER)
