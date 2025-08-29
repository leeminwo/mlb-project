from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from database.connection import database
from routers.users.auth import get_current_user
from models.users import add_user_exp, increment_user_stats, EXP_RULES

router = APIRouter()

@router.post("/{board}/like/{post_id}", dependencies=[Depends(get_current_user)])
async def like_post(
    board: str,
    post_id: int,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """게시물 추천/취소 기능"""
    
    # 게시물 존재 확인 및 작성자 정보 가져오기
    post = await database.fetch_one("""
        SELECT id, author, likes, user_id 
        FROM posts 
        WHERE id = :post_id AND deleted = 0
    """, {"post_id": post_id})
    
    if not post:
        raise HTTPException(status_code=404, detail="게시물을 찾을 수 없습니다.")
    
    # 본인 게시물 추천 방지
    if post["user_id"] == current_user.get("id"):
        raise HTTPException(status_code=400, detail="자신의 게시물에는 추천할 수 없습니다.")
    
    user_id = current_user.get("id")
    
    # 이미 추천했는지 확인
    existing_like = await database.fetch_one("""
        SELECT id FROM post_likes 
        WHERE post_id = :post_id AND user_id = :user_id
    """, {"post_id": post_id, "user_id": user_id})
    
    if existing_like:
        # 추천 취소
        await database.execute("""
            DELETE FROM post_likes 
            WHERE post_id = :post_id AND user_id = :user_id
        """, {"post_id": post_id, "user_id": user_id})
        
        # 게시물 추천 수 감소
        await database.execute("""
            UPDATE posts 
            SET likes = likes - 1 
            WHERE id = :post_id
        """, {"post_id": post_id})
        
        return JSONResponse({
            "success": True,
            "action": "unliked",
            "message": "추천이 취소되었습니다."
        })
    
    else:
        # 추천 추가
        await database.execute("""
            INSERT INTO post_likes (post_id, user_id)
            VALUES (:post_id, :user_id)
        """, {"post_id": post_id, "user_id": user_id})
        
        # 게시물 추천 수 증가
        await database.execute("""
            UPDATE posts 
            SET likes = likes + 1 
            WHERE id = :post_id
        """, {"post_id": post_id})
        
        # 게시물 작성자에게 경험치 추가
        if post["user_id"]:
            await add_user_exp(post["user_id"], EXP_RULES["post_liked"], "post_liked")
            await increment_user_stats(post["user_id"], "likes")
        
        return JSONResponse({
            "success": True,
            "action": "liked",
            "message": "추천되었습니다."
        })

@router.get("/{board}/like/{post_id}/status")
async def get_like_status(
    board: str,
    post_id: int,
    request: Request
):
    """게시물 추천 상태 확인 (로그인하지 않은 사용자도 확인 가능)"""
    
    current_user = request.session.get("user")
    if not current_user:
        return JSONResponse({"liked": False, "likes_count": 0})
    
    user_id = current_user.get("id")
    
    # 추천 여부 확인
    existing_like = await database.fetch_one("""
        SELECT id FROM post_likes 
        WHERE post_id = :post_id AND user_id = :user_id
    """, {"post_id": post_id, "user_id": user_id})
    
    # 총 추천 수 확인
    likes_count = await database.fetch_one("""
        SELECT likes FROM posts 
        WHERE id = :post_id AND deleted = 0
    """, {"post_id": post_id})
    
    return JSONResponse({
        "liked": bool(existing_like),
        "likes_count": likes_count["likes"] if likes_count else 0
    })
