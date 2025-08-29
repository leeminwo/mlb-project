import sqlite3
import os

# 데이터베이스 파일 경로
db_path = os.path.join(os.path.dirname(__file__), "db.sqlite3")

try:
    # 데이터베이스 연결
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("=== 투표 데이터 확인 ===")
    
    # posts 테이블의 투표 관련 컬럼 확인
    cursor.execute("PRAGMA table_info(posts)")
    columns = cursor.fetchall()
    print("\n[posts 테이블 컬럼]")
    for col in columns:
        if 'likes' in col[1] or 'dislikes' in col[1]:
            print(f"  {col[1]}: {col[2]} (기본값: {col[4]})")
    
    # 실제 투표 데이터 확인
    cursor.execute("""
        SELECT id, title, likes, dislikes, board 
        FROM posts 
        WHERE board = 'invest' 
        ORDER BY id DESC 
        LIMIT 5
    """)
    
    posts = cursor.fetchall()
    print(f"\n[투자게시판 최근 5개 글의 투표 현황]")
    for post in posts:
        print(f"  ID: {post[0]}, 제목: {post[1]}")
        print(f"    🎯 히트: {post[2]}, 💣 폭망: {post[3]}")
        print()
    
    # 전체 투표 통계
    cursor.execute("""
        SELECT 
            COUNT(*) as total_posts,
            SUM(likes) as total_likes,
            SUM(dislikes) as total_dislikes,
            AVG(likes) as avg_likes,
            AVG(dislikes) as avg_dislikes
        FROM posts 
        WHERE board = 'invest'
    """)
    
    stats = cursor.fetchone()
    print(f"[투자게시판 전체 통계]")
    print(f"  총 게시글: {stats[0]}")
    print(f"  총 히트: {stats[1] or 0}")
    print(f"  총 폭망: {stats[2] or 0}")
    print(f"  평균 히트: {stats[3] or 0:.1f}")
    print(f"  평균 폭망: {stats[4] or 0:.1f}")
    
    conn.close()
    
except Exception as e:
    print(f"오류 발생: {e}")
