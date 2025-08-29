from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from database.connection import database
from .utils import validate_board, format_dt_to_kst
from . import config
from urllib.parse import urlencode
from models.users import get_level_name

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/{board}/view/{post_id}", response_class=HTMLResponse, name="user_board_view")
async def user_board_view(
    board: str,
    post_id: int,
    request: Request,
    page: int | None = Query(None, ge=1),
    size: int | None = Query(None, ge=1, le=50),
    sort: str | None = Query(None, pattern="^(new|view|like)$"),
    q: str | None = Query(None, min_length=1, max_length=50),
    category: str | None = Query(None),
):
    validate_board(board)

    await database.execute("""
        UPDATE posts SET views = views + 1
        WHERE id = :id AND board = :board AND deleted = 0
    """, {"id": post_id, "board": board})

    row = await database.fetch_one("""
        SELECT p.id, p.title, p.content, p.author, p.category, p.user_id,
               p.created_at, p.updated_at, p.views, p.likes,
               u.level, u.exp
        FROM posts p
        LEFT JOIN users u ON p.user_id = u.id
        WHERE p.id = :id AND p.deleted = 0
    """, {"id": post_id})
    if not row:
        raise HTTPException(status_code=404, detail="게시글이 없습니다.")

    post = dict(row)
    post["created_at_fmt"] = format_dt_to_kst(post.get("created_at"))
    post["updated_at_fmt"] = format_dt_to_kst(post.get("updated_at"))
    
    # 등급 정보 추가
    if post.get("level"):
        post["level_name"] = get_level_name(post["level"])
    else:
        post["level"] = 1
        post["level_name"] = "새내기"

    # 댓글 목록 가져오기
    comments_rows = await database.fetch_all("""
        SELECT id, author, content, created_at, updated_at
        FROM comments
        WHERE post_id = :post_id AND deleted = 0
        ORDER BY created_at ASC
    """, {"post_id": post_id})
    
    comments = []
    for comment_row in comments_rows:
        comment = dict(comment_row)
        comment["created_at_fmt"] = format_dt_to_kst(comment.get("created_at"))
        comment["updated_at_fmt"] = format_dt_to_kst(comment.get("updated_at"))
        comments.append(comment)

    # 목록 복귀 URL
    back_params = {}
    if page: back_params["page"] = page
    if size: back_params["size"] = size
    if sort: back_params["sort"] = sort
    if q:    back_params["q"] = q
    if category: back_params["category"] = category
    back_query = urlencode(back_params, doseq=True)
    back_url = f"/{board}" + (f"?{back_query}" if back_query else "")

    tabs = config.USER_BOARD_TABS.get(board, [])

    # 현재 로그인한 사용자 정보 가져오기
    current_user = request.session.get("user")

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "category": f"{board}_view",
            "board": board,
            "tabs": tabs,
            "post": post,
            "comments": comments,
            "current_user": current_user,
            "page": page, "size": size, "sort": sort, "q": q, "selected_category": category,
            "back_url": back_url,
        }
    )
