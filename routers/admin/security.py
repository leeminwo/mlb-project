from fastapi import Request, HTTPException, status, Depends

async def get_current_user_optional(request: Request):
    """
    세션에서 user 딕셔너리를 반환하거나 None 반환.
    """
    return request.session.get("user")

async def get_current_user_required(request: Request):
    """
    로그인 필수 버전. user 없으면 401 에러.
    """
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Login required")
    return user

async def require_admin(request: Request, user=Depends(get_current_user_optional)):
    """
    관리자 전용 보호. user.is_admin 또는 session['is_admin'] 키를 함께 확인.
    """
    # 1) 새 구조: {"id":.., "name":.., "is_admin": True}
    if user and user.get("is_admin"):
        return True

    # 2) 하위 호환: request.session["is_admin"] 직접 확인
    if request.session.get("is_admin"):
        return True

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
