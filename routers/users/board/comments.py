from fastapi import APIRouter, Request, HTTPException, Form, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from database.connection import database
from .utils import format_dt_to_kst
from ..auth import get_current_user
from models.posts import comments
from models.users import add_user_exp, increment_user_stats, EXP_RULES
import datetime

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.post("/{board}/comment/{post_id}")
async def create_comment(
    board: str,
    post_id: int,
    content: str = Form(...),
    current_user = Depends(get_current_user)
):
    """댓글 작성"""
    if not content.strip():
        raise HTTPException(status_code=400, detail="댓글 내용을 입력해주세요.")
    
    # 게시글이 존재하는지 확인
    post = await database.fetch_one(
        "SELECT id FROM posts WHERE id = :id AND deleted = 0",
        {"id": post_id}
    )
    if not post:
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")
    
    # 댓글 등록
    await database.execute("""
        INSERT INTO comments (post_id, author, content, created_at)
        VALUES (:post_id, :author, :content, :created_at)
    """, {
        "post_id": post_id,
        "author": current_user.get('nickname', '익명'),
        "content": content.strip(),
        "created_at": datetime.datetime.utcnow()
    })
    
    # ✅ 등급 시스템: 댓글 작성 경험치 추가
    try:
        await add_user_exp(current_user.get("id"), EXP_RULES["comment_created"], "comment_created")
        await increment_user_stats(current_user.get("id"), "comments")
    except Exception as e:
        print(f"등급 시스템 오류: {e}")
    
    return RedirectResponse(url=f"/{board}/view/{post_id}", status_code=303)

@router.post("/{board}/comment/{post_id}/edit/{comment_id}")
async def edit_comment(
    board: str,
    post_id: int,
    comment_id: int,
    content: str = Form(...),
    current_user = Depends(get_current_user)
):
    """댓글 수정"""
    if not content.strip():
        raise HTTPException(status_code=400, detail="댓글 내용을 입력해주세요.")
    
    # 댓글 작성자 확인
    comment = await database.fetch_one("""
        SELECT author FROM comments 
        WHERE id = :id AND post_id = :post_id AND deleted = 0
    """, {"id": comment_id, "post_id": post_id})
    
    if not comment:
        raise HTTPException(status_code=404, detail="댓글을 찾을 수 없습니다.")
    
    # 작성자 또는 관리자만 수정 가능
    if comment.author != current_user.get('nickname') and not current_user.get('is_admin', False):
        raise HTTPException(status_code=403, detail="댓글을 수정할 권한이 없습니다.")
    
    # 댓글 수정
    await database.execute("""
        UPDATE comments 
        SET content = :content, updated_at = :updated_at
        WHERE id = :id
    """, {
        "content": content.strip(),
        "updated_at": datetime.datetime.utcnow(),
        "id": comment_id
    })
    
    return RedirectResponse(url=f"/{board}/view/{post_id}", status_code=303)

@router.post("/{board}/comment/{post_id}/delete/{comment_id}")
async def delete_comment(
    board: str,
    post_id: int,
    comment_id: int,
    current_user = Depends(get_current_user)
):
    """댓글 삭제"""
    # 댓글 작성자 확인
    comment = await database.fetch_one("""
        SELECT author FROM comments 
        WHERE id = :id AND post_id = :post_id AND deleted = 0
    """, {"id": comment_id, "post_id": post_id})
    
    if not comment:
        raise HTTPException(status_code=404, detail="댓글을 찾을 수 없습니다.")
    
    # 작성자 또는 관리자만 삭제 가능
    if comment.author != current_user.get('nickname') and not current_user.get('is_admin', False):
        raise HTTPException(status_code=403, detail="댓글을 삭제할 권한이 없습니다.")
    
    # 댓글 삭제 (soft delete)
    await database.execute("""
        UPDATE comments SET deleted = 1 WHERE id = :id
    """, {"id": comment_id})
    
    return RedirectResponse(url=f"/{board}/view/{post_id}", status_code=303)
