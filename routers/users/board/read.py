from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from database.connection import database
from .utils import validate_board, clamp_page, format_dt_to_kst
from . import config
from models.users import get_user_level_info, get_level_name
import logging

# 로깅 설정
logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/{board}", response_class=HTMLResponse, name="user_board_list")
async def user_board_list(
    board: str,
    request: Request,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=50),
    sort: str = Query("new", pattern="^(new|view|like)$"),
    q: str | None = Query(None, min_length=1, max_length=50),
    category: str | None = Query(None),
):
    validate_board(board)
    page, size = clamp_page(page, size)
    offset = (page - 1) * size

    tabs = config.USER_BOARD_TABS.get(board, [])
    if category and tabs and category not in tabs:
        category = None

    order_by = {
        "new":  "created_at DESC",
        "view": "views DESC, created_at DESC",
        "like": "likes DESC, created_at DESC",
    }[sort]

    # 총 개수
    total_row = await database.fetch_one("""
        SELECT COUNT(*) AS cnt
        FROM posts
        WHERE board = :board
          AND deleted = 0
          AND (is_published = 1 OR is_published IS NULL)
          AND (:category IS NULL OR category = :category)
          AND (:q IS NULL OR (title LIKE '%%' || :q || '%%' OR content LIKE '%%' || :q || '%%'))
    """, {"board": board, "q": q, "category": category})
    total = total_row["cnt"] if total_row else 0
    total_pages = max((total + size - 1) // size, 1)

    if page > total_pages:
        page = total_pages
        offset = (page - 1) * size

    # 목록 조회 - 어드민과 동일한 로직 적용
    rows = await database.fetch_all(f"""
    SELECT
      p.id, p.title, p.author, p.category,
      p.created_at, p.updated_at,
      p.views, p.likes
    FROM posts p
    WHERE p.board = :board
      AND p.deleted = 0
      AND (p.is_published = 1 OR p.is_published IS NULL)
      AND (:category IS NULL OR p.category = :category)
      AND (:q IS NULL OR (p.title LIKE '%%' || :q || '%%' OR p.content LIKE '%%' || :q || '%%'))
    ORDER BY {order_by}
    LIMIT :limit OFFSET :offset
    """, {"board": board, "limit": size, "offset": offset, "q": q, "category": category})

    posts = []
    for r in rows:
        d = dict(r)
        d["created_at_fmt"] = format_dt_to_kst(d.get("created_at"))
        d["updated_at_fmt"] = format_dt_to_kst(d.get("updated_at"))
        
        # 등급 정보는 기본값 사용
        d["level"] = 1
        d["level_name"] = "새내기"
        
        posts.append(d)

    # 모든 게시판은 index.html을 사용하여 일관성 유지
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "category": f"{board}_content",
            "board": board,
            "tabs": tabs,
            "selected_category": category,
            "posts": posts,
            "page": page, "size": size, "total": total,
            "total_pages": total_pages, "sort": sort,
            "q": q,
        }
    )
