import sqlalchemy
from sqlalchemy import Table, Column, Integer, String, DateTime, Boolean
from database import metadata
import datetime

users = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String),
    Column("email", String, unique=True),
    Column("password_hash", String),  # 🔐 비밀번호 해시 추가
    Column("role", String),           # ex: '관리자', '일반'
    Column("status", String),         # ex: 'Active', 'Inactive'
    Column("joined_at", DateTime, default=datetime.datetime.utcnow),
    Column("last_login", DateTime, nullable=True),
    Column("two_factor", Boolean, default=False),
    Column("deleted_at", DateTime, nullable=True)  # 🗑️ 소프트 삭제 일자 추가
)
posts = Table(
    "posts",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("title", String(200)),
    Column("content", String),  # 또는 Text()
    Column("author", String(50), default="익명"),
    Column("views", Integer, default=0),
    Column("likes", Integer, default=0),
    Column("category", String(50), default="invest"),
    Column("created_at", DateTime, default=datetime.datetime.utcnow)
)