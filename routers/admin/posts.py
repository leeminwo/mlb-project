# routers/admin/posts.py

from fastapi import APIRouter, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.status import HTTP_302_FOUND
from typing import List, Optional
from datetime import datetime, timezone
import os

from database.connection import database
from .utils import save_upload

router = APIRouter()
templates = Jinja2Templates(directory="templates")

def check_admin_session(request: Request) -> bool:
    """어드민 세션이 유효한지 확인"""
    return request.session.get("admin_logged_in") == True

@router.get("/admin/posts", response_class=HTMLResponse)
async def admin_posts_page(request: Request):
    if not check_admin_session(request):
        return HTMLResponse("로그인이 필요합니다.", status_code=403)

    return templates.TemplateResponse("admin/posts.html", {
        "request": request,
        "active_page": "posts"
    })

@router.get("/admin/posts/invest/write", response_class=HTMLResponse, name="admin_invest_write")
async def admin_invest_write_form(request: Request):
    if not check_admin_session(request):
        return HTMLResponse("로그인이 필요합니다.", status_code=403)

    return templates.TemplateResponse("admin/posts/category/invest.html", {
        "request": request,
        "active_page": "posts_invest"
    })

@router.post("/admin/posts/invest/write", response_class=HTMLResponse, name="admin_invest_write_save")
async def admin_invest_write_post(
    request: Request,
    title: str = Form(...),
    content: str = Form(...),
    author: str = Form(...),
    category: str = Form(...),
    files: List[UploadFile] = File(default=[])
):
    if not check_admin_session(request):
        return HTMLResponse("로그인이 필요합니다.", status_code=403)

    title_s = (title or "").strip()
    content_s = (content or "").strip()
    author_s = (author or "").strip()
    category_s = (category or "").strip()

    if len(title_s) < 2 or len(content_s) < 10 or not author_s or not category_s:
        return templates.TemplateResponse("admin/posts/category/invest.html", {
            "request": request,
            "active_page": "posts_invest",
            "error": "제목은 2자 이상, 내용은 10자 이상, 작성자/카테고리를 정확히 입력해주세요.",
            "title": title, "content": content, "author": author, "category": category
        })

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

    # 저장 쿼리 구성 - 투자게시판에만 글 작성
    created_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
    
    sql = """
        INSERT INTO posts (board, title, content, author, category, views, likes, deleted, created_at, updated_at)
        VALUES (:board, :title, :content, :author, :category, :views, :likes, 0, :created_at, :updated_at)
    """
    params = {
        "board": "invest",  # 투자게시판에만 글 작성
        "title": title_s,
        "content": content_s,
        "author": author_s,
        "category": category_s,
        "views": 0,
        "likes": 0,
        "created_at": created_iso,
        "updated_at": created_iso,
    }

    await database.execute(sql, params)

    return templates.TemplateResponse("admin/posts/category/invest.html", {
        "request": request,
        "active_page": "posts_invest",
        "success": "투자게시판에 글이 성공적으로 작성되었습니다."
    })
