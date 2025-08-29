# database/connection.py
import os
from databases import Database
from sqlalchemy import MetaData, create_engine

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.abspath(os.path.join(BASE_DIR, "..", "db.sqlite3"))

DATABASE_URL_ASYNC = f"sqlite+aiosqlite:///{DB_PATH}"
DATABASE_URL_SYNC  = f"sqlite:///{DB_PATH}"

database  = Database(DATABASE_URL_ASYNC)
metadata  = MetaData()
engine    = create_engine(DATABASE_URL_SYNC)

async def create_tables():
    if not database.is_connected:
        await database.connect()

    # users
    await database.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL UNIQUE,
        name TEXT NOT NULL,
        nickname TEXT NOT NULL UNIQUE,
        email TEXT UNIQUE,
        password TEXT NOT NULL,
        role TEXT DEFAULT 'user',
        status TEXT DEFAULT 'active',
        joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        two_factor BOOLEAN DEFAULT 0,
        last_login DATETIME,
        deleted BOOLEAN DEFAULT 0,
        level INTEGER DEFAULT 1,
        exp INTEGER DEFAULT 0,
        total_posts INTEGER DEFAULT 0,
        total_comments INTEGER DEFAULT 0,
        total_likes INTEGER DEFAULT 0,
        points INTEGER DEFAULT 0
    );
    """)

    # posts (유저/관리자 공용)
    await database.execute("""
    CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        board TEXT NOT NULL,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        author TEXT NOT NULL,
        category TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        views INTEGER NOT NULL DEFAULT 0,
        likes INTEGER NOT NULL DEFAULT 0,
        dislikes INTEGER NOT NULL DEFAULT 0
        -- updated_at / deleted 는 아래 ALTER 로 보강
    );
    """)

    # ✅ 기존 DB에도 안전하게 컬럼 추가(이미 있으면 무시)
    try:
        await database.execute("ALTER TABLE posts ADD COLUMN updated_at TEXT;")
    except Exception:
        pass
    try:
        await database.execute("ALTER TABLE posts ADD COLUMN deleted INTEGER NOT NULL DEFAULT 0;")
    except Exception:
        pass
    try:
        await database.execute("ALTER TABLE posts ADD COLUMN dislikes INTEGER NOT NULL DEFAULT 0;")
    except Exception:
        pass
    try:
        await database.execute("ALTER TABLE posts ADD COLUMN user_id INTEGER;")
    except Exception:
        pass
    try:
        await database.execute("ALTER TABLE posts ADD COLUMN is_published INTEGER NOT NULL DEFAULT 1;")
    except Exception:
        pass
    
    # 기존 게시글들의 user_id 설정 (author 이름을 기준으로)
    try:
        await database.execute("""
            UPDATE posts 
            SET user_id = (
                SELECT id FROM users 
                WHERE users.name = posts.author
            )
            WHERE user_id IS NULL
        """)
    except Exception:
        pass
    
    # 기존 게시글들의 is_published 설정 (기본값 1)
    try:
        await database.execute("""
            UPDATE posts 
            SET is_published = 1
            WHERE is_published IS NULL
        """)
    except Exception:
        pass

    # ✅ 댓글 테이블
    await database.execute("""
    CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER NOT NULL,
        author TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT,
        deleted INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY(post_id) REFERENCES posts(id)
    );
    """)
    
    # ✅ 댓글 테이블에 updated_at 컬럼 추가
    try:
        await database.execute("ALTER TABLE comments ADD COLUMN updated_at TEXT;")
    except Exception:
        pass
    
    # ✅ 사용자 테이블에 등급 시스템 컬럼 추가
    try:
        await database.execute("ALTER TABLE users ADD COLUMN level INTEGER DEFAULT 1;")
    except Exception:
        pass
    try:
        await database.execute("ALTER TABLE users ADD COLUMN exp INTEGER DEFAULT 0;")
    except Exception:
        pass
    try:
        await database.execute("ALTER TABLE users ADD COLUMN total_posts INTEGER DEFAULT 0;")
    except Exception:
        pass
    try:
        await database.execute("ALTER TABLE users ADD COLUMN total_comments INTEGER DEFAULT 0;")
    except Exception:
        pass
    try:
        await database.execute("ALTER TABLE users ADD COLUMN total_likes INTEGER DEFAULT 0;")
    except Exception:
        pass
    try:
        await database.execute("ALTER TABLE users ADD COLUMN points INTEGER DEFAULT 0;")
    except Exception:
        pass
    
    # ✅ 투표 테이블 (히트/폭망 구분)
    await database.execute("""
    CREATE TABLE IF NOT EXISTS post_votes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        vote_type TEXT NOT NULL CHECK (vote_type IN ('hit', 'bomb')),
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        UNIQUE(post_id, user_id),
        FOREIGN KEY(post_id) REFERENCES posts(id),
        FOREIGN KEY(user_id) REFERENCES users(id)
    );
    """)

    # 인덱스
    await database.execute("""
    CREATE INDEX IF NOT EXISTS idx_posts_board_created 
    ON posts(board, created_at DESC);
    """)
    await database.execute("""
    CREATE INDEX IF NOT EXISTS idx_posts_board_category 
    ON posts(board, category);
    """)
    await database.execute("""
    CREATE INDEX IF NOT EXISTS idx_posts_board_views 
    ON posts(board, views DESC, created_at DESC);
    """)
    await database.execute("""
    CREATE INDEX IF NOT EXISTS idx_posts_board_likes 
    ON posts(board, likes DESC, created_at DESC);
    """)
    await database.execute("""
    CREATE INDEX IF NOT EXISTS idx_posts_board_dislikes 
    ON posts(board, dislikes DESC, created_at DESC);
    """)
    await database.execute("""
    CREATE INDEX IF NOT EXISTS idx_comments_post 
    ON comments(post_id, created_at);
    """)
    await database.execute("""
    CREATE INDEX IF NOT EXISTS idx_post_votes_post_user 
    ON post_votes(post_id, user_id);
    """)

    # databases 는 자동 커밋
