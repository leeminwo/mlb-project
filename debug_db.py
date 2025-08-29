import sqlite3
import os

# 데이터베이스 파일 경로
db_path = os.path.join(os.path.dirname(__file__), "db.sqlite3")

try:
    # 데이터베이스 연결
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("=== 데이터베이스 상세 분석 ===")
    
    # 1. posts 테이블의 모든 컬럼과 순서 확인
    cursor.execute("PRAGMA table_info(posts)")
    columns = cursor.fetchall()
    print("\n[posts 테이블 컬럼 순서]")
    for col in columns:
        print(f"  {col[0]}: {col[1]} ({col[2]}) - 기본값: {col[4]}")
    
    # 2. 실제 데이터 샘플 확인
    cursor.execute("""
        SELECT * FROM posts 
        WHERE board = 'invest' 
        ORDER BY id DESC 
        LIMIT 1
    """)
    
    post = cursor.fetchone()
    if post:
        print(f"\n[샘플 데이터 (모든 컬럼)]")
        for i, col in enumerate(columns):
            print(f"  {col[1]}: {post[i]}")
    
    # 3. 특정 컬럼만 조회해서 문제 확인
    cursor.execute("""
        SELECT id, title, likes, dislikes, board 
        FROM posts 
        WHERE board = 'invest' 
        ORDER BY id DESC 
        LIMIT 3
    """)
    
    posts = cursor.fetchall()
    print(f"\n[투자게시판 데이터 (특정 컬럼)]")
    for post in posts:
        print(f"  ID: {post[0]}, 제목: {post[1]}")
        print(f"    likes: {post[2]} (타입: {type(post[2])})")
        print(f"    dislikes: {post[3]} (타입: {type(post[3])})")
        print()
    
    # 4. 컬럼 존재 여부 확인
    cursor.execute("SELECT COUNT(*) FROM posts WHERE dislikes IS NULL")
    null_dislikes = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM posts WHERE dislikes = ''")
    empty_dislikes = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM posts WHERE dislikes = 0")
    zero_dislikes = cursor.fetchone()[0]
    
    print(f"[dislikes 컬럼 값 분석]")
    print(f"  NULL 값: {null_dislikes}개")
    print(f"  빈 문자열: {empty_dislikes}개")
    print(f"  0 값: {zero_dislikes}개")
    
    conn.close()
    
except Exception as e:
    print(f"❌ 오류 발생: {e}")
    import traceback
    traceback.print_exc()
