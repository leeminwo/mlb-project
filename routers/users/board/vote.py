from fastapi import APIRouter, Depends, HTTPException, Form, Request
from fastapi.responses import JSONResponse
from typing import Optional
from database.connection import database
from routers.users.auth import get_current_user
from models.users import add_user_exp, increment_user_stats

router = APIRouter()

@router.post("/vote")
async def vote_post(
    post_id: int = Form(...),
    vote_type: str = Form(...),
    current_user: dict = Depends(get_current_user)
):
    """게시글에 히트/폭망 투표"""
    
    if vote_type not in ['hit', 'bomb']:
        raise HTTPException(status_code=400, detail="잘못된 투표 타입입니다")
    
    # 현재 사용자의 포인트 확인
    user_query = "SELECT points FROM users WHERE id = :user_id"
    user_result = await database.fetch_one(user_query, {"user_id": current_user["id"]})
    
    if not user_result:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")
    
    current_points = user_result["points"]
    
    # 투표에 필요한 포인트 (5개)
    required_points = 5
    
    if current_points < required_points:
        raise HTTPException(status_code=400, detail=f"포인트가 부족합니다. 필요: {required_points}, 보유: {current_points}")
    
    # 게시글 정보 조회
    post_query = "SELECT id, author, user_id FROM posts WHERE id = :post_id AND deleted = 0"
    post_result = await database.fetch_one(post_query, {"post_id": post_id})
    
    if not post_result:
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다")
    
    # 자기 자신에게 투표할 수 없음
    if post_result["user_id"] == current_user["id"]:
        raise HTTPException(status_code=400, detail="자신의 게시글에는 투표할 수 없습니다")
    
    # 기존 투표 확인
    existing_vote_query = "SELECT id, vote_type FROM post_votes WHERE post_id = :post_id AND user_id = :user_id"
    existing_vote = await database.fetch_one(existing_vote_query, {
        "post_id": post_id,
        "user_id": current_user["id"]
    })
    
    async with database.transaction():
        if existing_vote:
            # 기존 투표가 있으면 취소
            if existing_vote["vote_type"] == vote_type:
                # 같은 타입이면 투표 취소
                await database.execute(
                    "DELETE FROM post_votes WHERE id = :vote_id",
                    {"vote_id": existing_vote["id"]}
                )
                
                # 게시글 카운트 감소
                if vote_type == 'hit':
                    await database.execute(
                        "UPDATE posts SET likes = likes - 1 WHERE id = :post_id",
                        {"post_id": post_id}
                    )
                else:  # bomb
                    await database.execute(
                        "UPDATE posts SET dislikes = dislikes - 1 WHERE id = :post_id",
                        {"post_id": post_id}
                    )
                
                # 포인트 반환
                await database.execute(
                    "UPDATE users SET points = points + :points WHERE id = :user_id",
                    {"points": required_points, "user_id": current_user["id"]}
                )
                
                # 게시글 작성자 포인트 복원
                if vote_type == 'hit':
                    await database.execute(
                        "UPDATE users SET points = points - :points WHERE id = :post_user_id",
                        {"points": required_points, "user_id": post_result["user_id"]}
                    )
                else:  # bomb
                    await database.execute(
                        "UPDATE users SET points = points + :points WHERE id = :post_user_id",
                        {"points": required_points, "user_id": post_result["user_id"]}
                    )
                
                return JSONResponse({
                    "success": True,
                    "action": "cancelled",
                    "message": "투표가 취소되었습니다",
                    "points_returned": required_points
                })
            else:
                # 다른 타입이면 기존 투표 삭제 후 새로 투표
                await database.execute(
                    "DELETE FROM post_votes WHERE id = :vote_id",
                    {"vote_id": existing_vote["id"]}
                )
                
                # 기존 투표 타입에 따른 카운트 감소
                if existing_vote["vote_type"] == 'hit':
                    await database.execute(
                        "UPDATE posts SET likes = likes - 1 WHERE id = :post_id",
                        {"post_id": post_id}
                    )
                else:  # bomb
                    await database.execute(
                        "UPDATE posts SET dislikes = dislikes - 1 WHERE id = :post_id",
                        {"post_id": post_id}
                    )
                
                # 기존 투표 타입에 따른 포인트 복원
                if existing_vote["vote_type"] == 'hit':
                    await database.execute(
                        "UPDATE users SET points = points - :points WHERE id = :post_user_id",
                        {"points": required_points, "user_id": post_result["user_id"]}
                    )
                else:  # bomb
                    await database.execute(
                        "UPDATE users SET points = points + :points WHERE id = :post_user_id",
                        {"points": required_points, "user_id": post_result["user_id"]}
                    )
        
        # 새 투표 생성
        await database.execute(
            "INSERT INTO post_votes (post_id, user_id, vote_type) VALUES (:post_id, :user_id, :vote_type)",
            {"post_id": post_id, "user_id": current_user["id"], "vote_type": vote_type}
        )
        
        # 게시글 카운트 증가
        if vote_type == 'hit':
            await database.execute(
                "UPDATE posts SET likes = likes + 1 WHERE id = :post_id",
                {"post_id": post_id}
            )
        else:  # bomb
            await database.execute(
                "UPDATE posts SET dislikes = dislikes + 1 WHERE id = :post_id",
                {"post_id": post_id}
            )
        
        # 투표자 포인트 차감
        await database.execute(
            "UPDATE users SET points = points - :points WHERE id = :user_id",
            {"points": required_points, "user_id": current_user["id"]}
        )
        
        # 게시글 작성자 포인트 지급/차감
        if vote_type == 'hit':
            await database.execute(
                "UPDATE users SET points = points + :points WHERE id = :post_user_id",
                {"points": required_points, "user_id": post_result["user_id"]}
            )
        else:  # bomb
            # 폭망 시 포인트 차감 (0 이하로 내려가지 않도록)
            await database.execute(
                "UPDATE users SET points = CASE WHEN points >= :points THEN points - :points ELSE 0 END WHERE id = :post_user_id",
                {"points": required_points, "user_id": post_result["user_id"]}
            )
        
        # 게시글 작성자에게 경험치 지급 (히트만)
        if vote_type == 'hit':
            await add_user_exp(post_result["user_id"], 10)  # 히트 받으면 10경험치
            await increment_user_stats(post_result["user_id"], "total_likes", 1)
    
    return JSONResponse({
        "success": True,
        "action": "voted",
        "message": f"{'히트' if vote_type == 'hit' else '폭망'} 투표가 완료되었습니다",
        "points_spent": required_points
    })

@router.get("/vote-status/{post_id}")
async def get_vote_status(
    post_id: int,
    current_user: Optional[dict] = Depends(get_current_user)
):
    """게시글의 투표 상태 확인"""
    
    if not current_user:
        return JSONResponse({
            "voted": False,
            "vote_type": None,
            "likes_count": 0,
            "dislikes_count": 0,
            "can_vote": False
        })
    
    # 게시글 정보 조회
    post_query = "SELECT likes, dislikes FROM posts WHERE id = :post_id AND deleted = 0"
    post_result = await database.fetch_one(post_query, {"post_id": post_id})
    
    if not post_result:
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다")
    
    # 현재 사용자의 투표 상태 확인
    vote_query = "SELECT vote_type FROM post_votes WHERE post_id = :post_id AND user_id = :user_id"
    vote_result = await database.fetch_one(vote_query, {
        "post_id": post_id,
        "user_id": current_user["id"]
    })
    
    # 현재 사용자의 포인트 확인
    user_query = "SELECT points FROM users WHERE id = :user_id"
    user_result = await database.fetch_one(user_query, {"user_id": current_user["id"]})
    current_points = user_result["points"] if user_result else 0
    
    return JSONResponse({
        "voted": vote_result is not None,
        "vote_type": vote_result["vote_type"] if vote_result else None,
        "likes_count": post_result["likes"],
        "dislikes_count": post_result["dislikes"],
        "can_vote": current_points >= 5
    })

@router.get("/user-points")
async def get_user_points(current_user: dict = Depends(get_current_user)):
    """현재 사용자의 포인트 조회"""
    
    query = "SELECT points FROM users WHERE id = :user_id"
    result = await database.fetch_one(query, {"user_id": current_user["id"]})
    
    if not result:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")
    
    return JSONResponse({
        "points": result["points"]
    })
