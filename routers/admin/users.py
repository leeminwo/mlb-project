from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette import status as status_codes
from database.connection import database
from .utils import hash_password
from routers.admin.security import require_admin
from models.users import get_level_name, LEVEL_NAMES

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/admin/users", response_class=HTMLResponse, dependencies=[Depends(require_admin)])
async def admin_users(request: Request):
    query = """
    SELECT id, user_id, name, nickname, email, role, status, joined_at, 
           COALESCE(level, 1) as level, COALESCE(exp, 0) as exp,
           COALESCE(total_posts, 0) as total_posts, 
           COALESCE(total_comments, 0) as total_comments,
           COALESCE(total_likes, 0) as total_likes
    FROM users 
    WHERE deleted = 0 
    ORDER BY id DESC
    """
    users = await database.fetch_all(query)
    
    # 등급 정보 추가
    users_list = []
    for user in users:
        user_dict = dict(user)
        user_dict["level_name"] = get_level_name(user_dict["level"])
        users_list.append(user_dict)
    
    return templates.TemplateResponse("admin/users.html", {
        "request": request,
        "users": users_list,
        "active_page": "users",
        "level_names": LEVEL_NAMES
    })

# ✅ 팝업: 사용자 추가 폼
@router.get("/admin/users/create", response_class=HTMLResponse, dependencies=[Depends(require_admin)])
async def create_user_form(request: Request):
    return templates.TemplateResponse("admin/create_user.html", {
        "request": request,
        "active_page": "users"
    })

# ✅ 팝업: 사용자 추가 처리 → 같은 팝업 URL로 success=true
@router.post("/admin/users/create", dependencies=[Depends(require_admin)])
async def create_user(
    request: Request,
    id: str = Form(""),  # 빈 문자열로 받아서 처리
    user_id: str = Form(...),
    name: str = Form(...),
    nickname: str = Form(...),
    email: str = Form(""),
    password: str = Form(...),
    role: str = Form("user"),
    status: str = Form("active"),
    level: int = Form(1),
    exp: int = Form(0)
):
    hashed_pw = hash_password(password)
    
    # 빈 이메일을 None으로 처리
    email_value = email if email.strip() else None
    
    # id가 빈 문자열이면 None으로 처리
    id_value = int(id) if id.strip() else None

    # 중복 체크 수행
    try:
        # user_id 중복 체크
        existing_user = await database.fetch_one(
            "SELECT user_id FROM users WHERE user_id = :user_id AND deleted = 0",
            {"user_id": user_id}
        )
        if existing_user:
            return HTMLResponse("❌ 이미 사용 중인 아이디입니다.", status_code=400)
        
        # nickname 중복 체크
        existing_nickname = await database.fetch_one(
            "SELECT nickname FROM users WHERE nickname = :nickname AND deleted = 0",
            {"nickname": nickname}
        )
        if existing_nickname:
            return HTMLResponse("❌ 이미 사용 중인 닉네임입니다.", status_code=400)
        
        # email 중복 체크 (이메일이 입력된 경우에만)
        if email_value:
            existing_email = await database.fetch_one(
                "SELECT email FROM users WHERE email = :email AND deleted = 0",
                {"email": email_value}
            )
            if existing_email:
                return HTMLResponse("❌ 이미 사용 중인 이메일입니다.", status_code=400)
    
    except Exception as e:
        return HTMLResponse(f"❌ 중복 체크 중 오류 발생: {str(e)}", status_code=400)

    # 중복이 없으면 사용자 생성
    if id_value:
        sql = """
            INSERT INTO users (id, user_id, name, nickname, email, password, role, status, joined_at, two_factor, deleted, level, exp, total_posts, total_comments, total_likes)
            VALUES (:id, :user_id, :name, :nickname, :email, :password, :role, :status, CURRENT_TIMESTAMP, 0, 0, :level, :exp, 0, 0, 0)
        """
        values = {"id": id_value, "user_id": user_id, "name": name, "nickname": nickname,
                  "email": email_value, "password": hashed_pw, "role": role, "status": status,
                  "level": level, "exp": exp}
    else:
        sql = """
            INSERT INTO users (user_id, name, nickname, email, password, role, status, joined_at, two_factor, deleted, level, exp, total_posts, total_comments, total_likes)
            VALUES (:user_id, :name, :nickname, :email, :password, :role, :status, CURRENT_TIMESTAMP, 0, 0, :level, :exp, 0, 0, 0)
        """
        values = {"user_id": user_id, "name": name, "nickname": nickname,
                  "email": email_value, "password": hashed_pw, "role": role, "status": status,
                  "level": level, "exp": exp}

    try:
        await database.execute(sql, values)
    except Exception as e:
        msg = str(e)
        return HTMLResponse(f"❌ 사용자 생성 중 오류 발생: {msg}", status_code=400)

    # ✅ 팝업 닫기 로직을 위해 동일 URL로 success=true (303)
    return RedirectResponse("/admin/users/create?success=true", status_code=status_codes.HTTP_303_SEE_OTHER)

# ✅ 팝업: 사용자 수정 폼
@router.get("/admin/users/edit/{user_id}", response_class=HTMLResponse, dependencies=[Depends(require_admin)])
async def edit_user_form(request: Request, user_id: int):
    sql = """
    SELECT id, user_id, name, nickname, email, role, status, joined_at,
           COALESCE(level, 1) as level, COALESCE(exp, 0) as exp,
           COALESCE(total_posts, 0) as total_posts, 
           COALESCE(total_comments, 0) as total_comments,
           COALESCE(total_likes, 0) as total_likes
    FROM users WHERE id = :id
    """
    user = await database.fetch_one(sql, {"id": user_id})
    if not user:
        return HTMLResponse("사용자를 찾을 수 없습니다.", status_code=404)
    
    user_dict = dict(user)
    user_dict["level_name"] = get_level_name(user_dict["level"])
    
    return templates.TemplateResponse("admin/edit_user.html", {
        "request": request, 
        "user": user_dict,
        "level_names": LEVEL_NAMES
    })

# ✅ 팝업: 사용자 수정 처리 → 같은 팝업 URL로 success=true
@router.post("/admin/users/edit/{user_id}", dependencies=[Depends(require_admin)])
async def edit_user(
    user_id: int,
    name: str = Form(...),
    nickname: str = Form(...),
    email: str = Form(""),
    password: str | None = Form(None),
    role: str = Form(...),
    status: str = Form(...),
    level: int = Form(1),
    exp: int = Form(0),
):
    # 빈 이메일을 None으로 처리
    email_value = email if email.strip() else None
    
    # 중복 체크 수행 (자기 자신 제외)
    try:
        # nickname 중복 체크 (자기 자신 제외)
        existing_nickname = await database.fetch_one(
            "SELECT nickname FROM users WHERE nickname = :nickname AND id != :user_id AND deleted = 0",
            {"nickname": nickname, "user_id": user_id}
        )
        if existing_nickname:
            return HTMLResponse("❌ 이미 사용 중인 닉네임입니다.", status_code=400)
        
        # email 중복 체크 (이메일이 입력된 경우에만, 자기 자신 제외)
        if email_value:
            existing_email = await database.fetch_one(
                "SELECT email FROM users WHERE email = :email AND id != :user_id AND deleted = 0",
                {"email": email_value, "user_id": user_id}
            )
            if existing_email:
                return HTMLResponse("❌ 이미 사용 중인 이메일입니다.", status_code=400)
    
    except Exception as e:
        return HTMLResponse(f"❌ 중복 체크 중 오류 발생: {str(e)}", status_code=400)

    # 중복이 없으면 사용자 수정
    if password:
        sql = """
            UPDATE users
            SET name = :name, nickname = :nickname, email = :email, password = :password,
                role = :role, status = :status, level = :level, exp = :exp
            WHERE id = :user_id
        """
        values = {"name": name, "nickname": nickname, "email": email_value,
                  "password": hash_password(password),
                  "role": role, "status": status, "user_id": user_id,
                  "level": level, "exp": exp}
    else:
        sql = """
            UPDATE users
            SET name = :name, nickname = :nickname, email = :email,
                role = :role, status = :status, level = :level, exp = :exp
            WHERE id = :user_id
        """
        values = {"name": name, "nickname": nickname, "email": email_value,
                  "role": role, "status": status, "user_id": user_id,
                  "level": level, "exp": exp}

    try:
        await database.execute(sql, values)
    except Exception as e:
        msg = str(e)
        return HTMLResponse(f"❌ 사용자 수정 중 오류 발생: {msg}", status_code=400)

    # ✅ 팝업 닫기 로직과 일치 (success=true)
    return RedirectResponse(f"/admin/users/edit/{user_id}?success=true", status_code=status_codes.HTTP_303_SEE_OTHER)

# 🔹 사용자 삭제 (Soft Delete)
@router.get("/admin/users/delete/{user_id}", dependencies=[Depends(require_admin)])
async def delete_user(user_id: int):
    await database.execute("UPDATE users SET deleted = 1 WHERE id = :user_id", {"user_id": user_id})
    return RedirectResponse("/admin/users?deleted=1", status_code=status_codes.HTTP_302_FOUND)
