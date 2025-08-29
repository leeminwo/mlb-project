# routers/admin/posts/boards.py
from enum import Enum
from fastapi import APIRouter, Request, Form, Depends, HTTPException, File, UploadFile
from fastapi.responses import RedirectResponse
from starlette import status
from database.connection import database
from routers.admin.security import require_admin  # is_admin 세션 확인

# ▶ 시간 포맷(KST) 재사용
from routers.users.board.utils import format_dt_to_kst

from datetime import datetime, timezone  # updated_at 갱신용
from typing import List
import os
from routers.admin.utils import save_upload

router = APIRouter(prefix="/admin/posts", tags=["admin:posts"])

# 지원 게시판 슬러그
class Board(str, Enum):
    best = "best"
    game = "game"
    sports = "sports"
    invest = "invest"
    gallery = "gallery"
    free = "free"
    humor = "humor"
    report = "report"

# 게시판별 탭(카테고리)
BOARD_TABS: dict[str, list[str]] = {
    "invest": ["인기", "비트코인", "국내주식", "해외주식", "종목토론", "정보공유", "이벤트", "공지", "잡담"],
    "best":   ["인기", "공지"],
    "game":   ["공지", "잡담"],
    "sports": ["축구", "야구", "농구", "기타", "공지"],
    "gallery": ["일반", "공지"],
    "free":    ["일반", "공지"],
    "humor":   ["유머", "공지"],
    "report":  ["신고", "건의", "공지"],
}

BOARD_LABEL = {
    "best": "베스트",
    "game": "게임",
    "sports": "스포츠",
    "invest": "투자",
    "gallery": "갤러리",
    "free": "일반",
    "humor": "유머",
    "report": "신문고",
}

# ✅ 카테고리 서버 검증(POST에도 재사용)
def _validate_category(board: Board, category: str | None):
    if category is None:
        return
    tabs = BOARD_TABS.get(board.value, [])
    if tabs and category not in tabs:
        raise HTTPException(status_code=400, detail="잘못된 카테고리")

@router.get("/{board}", name="admin_board_list")
async def admin_board_list(
    request: Request,
    board: Board,
    category: str | None = None,
    _=Depends(require_admin),
):
    tabs = BOARD_TABS.get(board.value, [])
    if category and tabs and category not in tabs:
        raise HTTPException(status_code=400, detail="잘못된 카테고리")

    # ✅ 삭제글 제외 + updated_at 포함
    rows = await database.fetch_all(
        """
        SELECT id, title, author, category, created_at, updated_at, views, likes
        FROM posts
        WHERE board = :board
          AND deleted = 0
          AND (:category IS NULL OR category = :category)
        ORDER BY created_at DESC
        LIMIT 50
        """,
        {"board": board.value, "category": category},
    )

    # ✅ 시간 포맷(KST) + 'T' 제거
    posts = []
    for r in rows:
        d = dict(r)
        d["created_at_fmt"] = format_dt_to_kst(d.get("created_at"))
        d["updated_at_fmt"] = format_dt_to_kst(d.get("updated_at"))
        posts.append(d)

    return request.app.state.templates.TemplateResponse(
        "admin/board_content_admin.html",
        {
            "request": request,
            "board": board.value,
            "board_label": BOARD_LABEL.get(board.value, board.value),
            "tabs": tabs,
            "active_tab": category,
            "posts": posts,
            "admin_mode": True,
            "active_page": f"posts_{board.value}",
        },
    )

@router.get("/{board}/{post_id}/edit", name="admin_board_edit_form")
async def admin_board_edit_form(
    request: Request,
    board: Board,
    post_id: int,
    _=Depends(require_admin),
):
    row = await database.fetch_one(
        """
        SELECT id, title, content, author, category, created_at, updated_at
        FROM posts
        WHERE id=:id AND board=:board AND deleted=0
        """,
        {"id": post_id, "board": board.value},
    )
    if not row:
        url = request.url_for("admin_board_list", board=board.value)
        return RedirectResponse(url=url, status_code=status.HTTP_303_SEE_OTHER)

    post = dict(row)
    post["created_at_fmt"] = format_dt_to_kst(post.get("created_at"))
    post["updated_at_fmt"] = format_dt_to_kst(post.get("updated_at"))

    return request.app.state.templates.TemplateResponse(
        "admin/board_edit.html",
        {
            "request": request,
            "post": post,
            "board": board.value,
            "board_label": BOARD_LABEL.get(board.value, ""),
        },
    )

@router.post("/{board}/{post_id}/edit", name="admin_board_edit_save")
async def admin_board_edit_save(
    request: Request,
    board: Board,
    post_id: int,
    title: str = Form(...),
    content: str = Form(...),
    category: str = Form(...),
    _=Depends(require_admin),
):
    _validate_category(board, category)

    # ✅ 수정 시 updated_at 갱신
    updated_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
    await database.execute(
        """
        UPDATE posts
        SET title=:title, content=:content, category=:category, updated_at=:updated_at
        WHERE id=:id AND board=:board AND deleted=0
        """,
        {
            "title": title,
            "content": content,
            "category": category,
            "updated_at": updated_iso,
            "id": post_id,
            "board": board.value,
        },
    )
    url = request.url_for("admin_board_list", board=board.value)
    return RedirectResponse(url=url, status_code=status.HTTP_303_SEE_OTHER)

@router.post("/{board}/{post_id}/delete", name="admin_board_delete")
async def admin_board_delete(
    request: Request,
    board: Board,
    post_id: int,
    _=Depends(require_admin),
):
    # ✅ 소프트 삭제로 변경 (프론트/유저 목록과 일관)
    await database.execute(
        "UPDATE posts SET deleted=1 WHERE id=:id AND board=:board",
        {"id": post_id, "board": board.value},
    )
    url = request.url_for("admin_board_list", board=board.value)
    return RedirectResponse(url=url, status_code=status.HTTP_303_SEE_OTHER)

@router.get("/{board}/write", name="admin_board_write")
async def admin_board_write_form(
    request: Request,
    board: Board,
    _=Depends(require_admin),
):
    # 투자게시판만 글쓰기 허용
    if board.value != "invest":
        raise HTTPException(status_code=400, detail="투자게시판만 글쓰기가 가능합니다.")
    
    tabs = BOARD_TABS.get(board.value, [])
    
    return request.app.state.templates.TemplateResponse(
        "admin/posts/category/invest.html",
        {
            "request": request,
            "board": board.value,
            "board_label": BOARD_LABEL.get(board.value, board.value),
            "tabs": tabs,
            "active_page": f"posts_{board.value}",
        },
    )

@router.post("/{board}/write", name="admin_board_write_save")
async def admin_board_write_post(
    request: Request,
    board: Board,
    title: str = Form(...),
    content: str = Form(...),
    author: str = Form(...),
    category: str = Form(...),
    files: List[UploadFile] = File(default=[]),
    _=Depends(require_admin),
):
    # 투자게시판만 글쓰기 허용
    if board.value != "invest":
        raise HTTPException(status_code=400, detail="투자게시판만 글쓰기가 가능합니다.")
    
    _validate_category(board, category)
    
    title_s = (title or "").strip()
    content_s = (content or "").strip()
    author_s = (author or "").strip()
    category_s = (category or "").strip()

    if len(title_s) < 2 or len(content_s) < 10 or not author_s or not category_s:
        tabs = BOARD_TABS.get(board.value, [])
        return request.app.state.templates.TemplateResponse(
            "admin/posts/category/invest.html",
            {
                "request": request,
                "board": board.value,
                "board_label": BOARD_LABEL.get(board.value, board.value),
                "tabs": tabs,
                "active_page": f"posts_{board.value}",
                "error": "제목은 2자 이상, 내용은 10자 이상, 작성자/카테고리를 정확히 입력해주세요.",
                "title": title, "content": content, "author": author, "category": category
            }
        )

    # 파일 저장
    upload_dir = os.path.join("static", "uploads", board.value)
    saved_files = []
    for file in files or []:
        try:
            saved = await save_upload(upload_dir, file)
            if saved:
                saved_files.append(saved)
        finally:
            if file:
                await file.close()

    # 저장 쿼리 구성 - 투자게시판에만 글 작성
    created_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
    
    # 실제 데이터베이스 구조에 맞춰서 저장
    sql = """
        INSERT INTO posts (board, title, content, author, category, views, likes, created_at, is_published)
        VALUES (:board, :title, :content, :author, :category, :views, :likes, :created_at, :is_published)
    """
    params = {
        "board": board.value,  # 투자게시판에만 글 작성
        "title": title_s,
        "content": content_s,
        "author": author_s,
        "category": category_s,
        "views": 0,
        "likes": 0,
        "created_at": created_iso,
        "is_published": 1,  # 기본적으로 게시됨 상태로 설정
    }

    await database.execute(sql, params)

    # 디버깅: 저장된 글 확인
    print(f"✅ 어드민 투자게시판 글 저장 완료:")
    print(f"   - board: {board.value}")
    print(f"   - title: {title_s}")
    print(f"   - author: {author_s}")
    print(f"   - category: {category_s}")

    # 성공 후 투자게시판 목록으로 리다이렉트
    url = request.url_for("admin_board_list", board=board.value)
    return RedirectResponse(url=url, status_code=status.HTTP_303_SEE_OTHER)
