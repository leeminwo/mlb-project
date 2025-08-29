# models/users.py
from typing import Optional, Dict, Any
import datetime

from passlib.context import CryptContext
from sqlalchemy import Table, Column, Integer, String, DateTime, Boolean, select, insert

from database.connection import metadata, database  # ✅ connect_db 대신 database 사용

# =========================
# 유저 테이블 정의
# =========================
users = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", String, unique=True),          # 외부용 식별자 필요 시
    Column("name", String),
    Column("nickname", String, unique=True),
    Column("email", String, unique=True),            # 로그인 키이므로 UNIQUE 권장
    Column("password", String),                      # bcrypt 해시 저장
    Column("role", String, default="user"),
    Column("status", String, default="active"),
    Column("joined_at", DateTime, default=datetime.datetime.utcnow),
    Column("two_factor", Boolean, default=False),
    Column("deleted", Boolean, default=False),
    # 등급 시스템 추가
    Column("level", Integer, default=1),             # 현재 등급 (1-10)
    Column("exp", Integer, default=0),               # 현재 경험치
    Column("total_posts", Integer, default=0),       # 총 게시글 수
    Column("total_comments", Integer, default=0),    # 총 댓글 수
    Column("total_likes", Integer, default=0),       # 받은 총 추천 수
)

# =========================
# 등급 시스템 설정
# =========================
# 등급별 필요 경험치 (1-10단계)
LEVEL_EXP_REQUIREMENTS = {
    1: 0,
    2: 100,
    3: 300,
    4: 600,
    5: 1000,
    6: 1500,
    7: 2100,
    8: 2800,
    9: 3600,
    10: 4500
}

# 등급별 이름
LEVEL_NAMES = {
    1: "새내기",
    2: "초보자", 
    3: "견습생",
    4: "수습생",
    5: "일반인",
    6: "열성회원",
    7: "우수회원",
    8: "전문가",
    9: "마스터",
    10: "전설"
}

# 경험치 획득 규칙
EXP_RULES = {
    "post_created": 10,      # 게시글 작성
    "comment_created": 3,    # 댓글 작성
    "post_liked": 5,         # 게시글 추천받음
    "comment_liked": 2,      # 댓글 추천받음
    "daily_login": 1,        # 일일 로그인
    "weekly_active": 5       # 주간 활동
}

def calculate_level(exp: int) -> int:
    """경험치로 현재 등급 계산"""
    for level in range(10, 0, -1):
        if exp >= LEVEL_EXP_REQUIREMENTS[level]:
            return level
    return 1

def get_level_name(level: int) -> str:
    """등급 번호로 등급 이름 반환"""
    return LEVEL_NAMES.get(level, "새내기")

def get_next_level_exp(current_level: int) -> int:
    """다음 등급까지 필요한 경험치"""
    return LEVEL_EXP_REQUIREMENTS.get(current_level + 1, LEVEL_EXP_REQUIREMENTS[10])

def get_exp_progress(exp: int, level: int) -> float:
    """현재 등급에서의 경험치 진행률 (0-100%)"""
    current_level_exp = LEVEL_EXP_REQUIREMENTS[level]
    next_level_exp = get_next_level_exp(level)
    if next_level_exp == current_level_exp:
        return 100.0
    return ((exp - current_level_exp) / (next_level_exp - current_level_exp)) * 100

# =========================
# 비밀번호 해시/검증
# =========================
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(plain: str) -> str:
    return pwd_ctx.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_ctx.verify(plain, hashed)

# =========================
# DB 헬퍼 함수 (Databases 사용)
# =========================
async def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """
    email로 사용자 1명 조회. 소프트삭제(deleted=True)면 None 반환.
    """
    q = (
        select(
            users.c.id,
            users.c.user_id,
            users.c.email,
            users.c.name,
            users.c.nickname,
            users.c.password,   # 해시
            users.c.role,
            users.c.deleted,
        )
        .where(users.c.email == email)
        .limit(1)
    )
    row = await database.fetch_one(q)
    if not row:
        return None
    # 일부 DB에서 Boolean이 0/1로 들어올 수 있으니 bool 처리
    if bool(row["deleted"]):
        return None
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "email": row["email"],
        "name": row["name"],
        "nickname": row["nickname"],
        "password_hash": row["password"],
        "role": row["role"],
    }

async def get_user_by_user_id(user_id: str) -> Optional[Dict[str, Any]]:
    """
    user_id로 사용자 1명 조회. 소프트삭제(deleted=True)면 None 반환.
    """
    q = (
        select(
            users.c.id,
            users.c.user_id,
            users.c.email,
            users.c.name,
            users.c.nickname,
            users.c.password,   # 해시
            users.c.role,
            users.c.deleted,
        )
        .where(users.c.user_id == user_id)
        .limit(1)
    )
    row = await database.fetch_one(q)
    if not row:
        return None
    # 일부 DB에서 Boolean이 0/1로 들어올 수 있으니 bool 처리
    if bool(row["deleted"]):
        return None
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "email": row["email"],
        "name": row["name"],
        "nickname": row["nickname"],
        "password_hash": row["password"],
        "role": row["role"],
    }

async def get_user_by_nickname(nickname: str) -> Optional[Dict[str, Any]]:
    """
    nickname으로 사용자 1명 조회. 소프트삭제(deleted=True)면 None 반환.
    """
    q = (
        select(
            users.c.id,
            users.c.user_id,
            users.c.email,
            users.c.name,
            users.c.nickname,
            users.c.password,   # 해시
            users.c.role,
            users.c.deleted,
        )
        .where(users.c.nickname == nickname)
        .limit(1)
    )
    row = await database.fetch_one(q)
    if not row:
        return None
    # 일부 DB에서 Boolean이 0/1로 들어올 수 있으니 bool 처리
    if bool(row["deleted"]):
        return None
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "email": row["email"],
        "name": row["name"],
        "nickname": row["nickname"],
        "password_hash": row["password"],
        "role": row["role"],
    }

async def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """
    id로 사용자 1명 조회. 소프트삭제(deleted=True)면 None 반환.
    """
    q = (
        select(
            users.c.id,
            users.c.user_id,
            users.c.email,
            users.c.name,
            users.c.nickname,
            users.c.password,   # 해시
            users.c.role,
            users.c.level,
            users.c.exp,
            users.c.total_posts,
            users.c.total_comments,
            users.c.total_likes,
            users.c.deleted,
        )
        .where(users.c.id == user_id)
        .limit(1)
    )
    row = await database.fetch_one(q)
    if not row:
        return None
    # 일부 DB에서 Boolean이 0/1로 들어올 수 있으니 bool 처리
    if bool(row["deleted"]):
        return None
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "email": row["email"],
        "name": row["name"],
        "nickname": row["nickname"],
        "password_hash": row["password"],
        "role": row["role"],
        "level": row["level"],
        "exp": row["exp"],
        "total_posts": row["total_posts"],
        "total_comments": row["total_comments"],
        "total_likes": row["total_likes"],
    }

async def create_user(user_id: str, nickname: str, email: str, name: str, plain_password: str, role: str = "user") -> int:
    """
    사용자 생성 후 id 반환. 비밀번호는 bcrypt 해시로 저장.
    """
    ph = hash_password(plain_password)
    now = datetime.datetime.utcnow()
    q = (
        insert(users)
        .values(
            user_id=user_id,
            nickname=nickname,
            email=email,
            name=name,
            password=ph,
            role=role,
            status="active",
            joined_at=now,
            deleted=False,
            level=1,
            exp=0,
            total_posts=0,
            total_comments=0,
            total_likes=0,
        )
    )
    # databases execute는 PK를 반환합니다(SQLite/SQLite3 OK)
    new_id = await database.execute(q)
    return int(new_id) if new_id is not None else 0

# =========================
# 등급 시스템 DB 함수
# =========================
async def add_user_exp(user_id: int, exp_amount: int, reason: str = "activity") -> bool:
    """
    사용자 경험치 추가 및 등급 업데이트
    """
    from sqlalchemy import update
    
    # 현재 사용자 정보 조회
    user = await get_user_by_id(user_id)
    if not user:
        return False
    
    current_exp = user.get("exp", 0)
    current_level = user.get("level", 1)
    
    # 새로운 경험치와 등급 계산
    new_exp = current_exp + exp_amount
    new_level = calculate_level(new_exp)
    
    # DB 업데이트
    q = (
        update(users)
        .where(users.c.id == user_id)
        .values(exp=new_exp, level=new_level)
    )
    await database.execute(q)
    
    # 등급 업 확인
    if new_level > current_level:
        return True  # 등급 업 발생
    return False

async def get_user_level_info(user_id: int) -> Optional[Dict[str, Any]]:
    """
    사용자의 등급 정보 조회
    """
    q = (
        select(
            users.c.id,
            users.c.nickname,
            users.c.level,
            users.c.exp,
            users.c.total_posts,
            users.c.total_comments,
            users.c.total_likes,
        )
        .where(users.c.id == user_id)
        .limit(1)
    )
    row = await database.fetch_one(q)
    if not row:
        return None
    
    level = row["level"]
    exp = row["exp"]
    
    return {
        "id": row["id"],
        "nickname": row["nickname"],
        "level": level,
        "level_name": get_level_name(level),
        "exp": exp,
        "next_level_exp": get_next_level_exp(level),
        "exp_progress": get_exp_progress(exp, level),
        "total_posts": row["total_posts"],
        "total_comments": row["total_comments"],
        "total_likes": row["total_likes"],
    }

async def increment_user_stats(user_id: int, stat_type: str) -> bool:
    """
    사용자 통계 증가 (게시글, 댓글, 추천 수)
    """
    from sqlalchemy import update
    
    if stat_type == "posts":
        q = update(users).where(users.c.id == user_id).values(total_posts=users.c.total_posts + 1)
    elif stat_type == "comments":
        q = update(users).where(users.c.id == user_id).values(total_comments=users.c.total_comments + 1)
    elif stat_type == "likes":
        q = update(users).where(users.c.id == user_id).values(total_likes=users.c.total_likes + 1)
    else:
        return False
    
    await database.execute(q)
    return True
