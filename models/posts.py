# models/posts.py

import datetime
from sqlalchemy import Table, Column, Integer, String, Text, DateTime, ForeignKey
from database.connection import metadata

posts = Table(
    "posts",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("title", String, nullable=False),              # 제목
    Column("content", Text, nullable=False),              # 본문
    Column("author", String, nullable=False),             # 작성자 (ex. '익명')
    Column("category", String, nullable=False),           # 게시판 종류 (예: invest, humor)
    Column("subcategory", String, nullable=True),         # 말머리 (예: 비트코인, 공지)
    Column("views", Integer, default=0),                  # 조회수
    Column("likes", Integer, default=0),                  # 추천수
    Column("created_at", DateTime, default=datetime.datetime.utcnow)  # 작성일시
)

# 댓글 테이블 추가
comments = Table(
    "comments",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("post_id", Integer, ForeignKey("posts.id"), nullable=False),  # 게시글 ID
    Column("author", String, nullable=False),             # 작성자
    Column("content", Text, nullable=False),              # 댓글 내용
    Column("created_at", DateTime, default=datetime.datetime.utcnow),  # 작성일시
    Column("updated_at", DateTime, nullable=True),        # 수정일시
    Column("deleted", Integer, default=0)                # 삭제 여부 (0: 활성, 1: 삭제)
)
