# routers/users/profile.py
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from database.connection import database

from models.users import get_user_level_info
from routers.users.auth import get_current_user

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/profile", response_class=HTMLResponse)
async def user_profile(request: Request, current_user = Depends(get_current_user)):
    """사용자 프로필 페이지"""
    
    # 사용자 등급 정보 조회
    level_info = await get_user_level_info(current_user["id"])
    
    # 사용자 포인트 정보 조회
    user_query = "SELECT points FROM users WHERE id = :user_id"
    user_result = await database.fetch_one(user_query, {"user_id": current_user["id"]})
    user_points = user_result["points"] if user_result else 0
    
    return templates.TemplateResponse("users/profile.html", {
        "request": request,
        "current_user": current_user,
        "level_info": level_info,
        "user_points": user_points
    })

@router.get("/profile/{nickname}", response_class=HTMLResponse)
async def user_profile_public(request: Request, nickname: str):
    """공개 사용자 프로필 페이지"""
    
    # TODO: nickname으로 사용자 정보 조회 구현
    # 임시로 에러 반환
    raise HTTPException(status_code=404, detail="User not found")
