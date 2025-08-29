from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette import status
from datetime import datetime, timezone
from database.connection import database
from .utils import validate_board, normalize_category
from . import config

router = APIRouter()

@router.get("/{board}/edit/{post_id}", response_class=HTMLResponse, name="user_board_edit_form")
async def edit_form(board: str, post_id: int, request: Request):
    validate_board(board)
    row = await database.fetch_one("""
        SELECT id, title, content, author, category
        FROM posts WHERE id=:id AND board=:board AND deleted=0
    """, {"id": post_id, "board": board})
    if not row:
        raise HTTPException(status_code=404, detail="게시글이 없습니다.")
    return request.app.state.templates.TemplateResponse("index.html", {
        "request": request,
        "category": f"{board}_edit",           # invest_edit.html 파셜 사용
        "board": board,
        "tabs": config.USER_BOARD_TABS.get(board, []),
        "post": dict(row),
    })

@router.post("/{board}/edit/{post_id}", response_class=HTMLResponse, name="user_board_edit_save")
async def edit_save(
    board: str, post_id: int, request: Request,
    title: str = Form(...),
    content: str = Form(...),
    category: str = Form(...)
):
    validate_board(board)
    title_s = (title or "").strip()
    content_s = (content or "").strip()
    category_s = normalize_category(board, category)
    if len(title_s) < 2 or len(content_s) < 10:
        raise HTTPException(status_code=400, detail="제목 2자 이상, 내용 10자 이상")
    updated_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")

    row = await database.fetch_one("""
        UPDATE posts
        SET title=:title, content=:content, category=:category, updated_at=:updated
        WHERE id=:id AND board=:board AND deleted=0
        RETURNING id
    """, {"title": title_s, "content": content_s, "category": category_s,
          "updated": updated_iso, "id": post_id, "board": board})
    if not row:
        raise HTTPException(status_code=404, detail="게시글이 없습니다.")

    return RedirectResponse(
        url=request.url_for("user_board_view", board=board, post_id=post_id),
        status_code=status.HTTP_303_SEE_OTHER
    )

@router.post("/{board}/delete/{post_id}", response_class=HTMLResponse, name="user_board_delete")
async def delete_post(board: str, post_id: int, request: Request):
    validate_board(board)
    row = await database.fetch_one("""
        UPDATE posts SET deleted=1
        WHERE id=:id AND board=:board AND deleted=0
        RETURNING id
    """, {"id": post_id, "board": board})
    if not row:
        raise HTTPException(status_code=404, detail="이미 삭제되었거나 없습니다.")
    return RedirectResponse(url=request.url_for("user_board_list", board=board),
                            status_code=status.HTTP_303_SEE_OTHER)
