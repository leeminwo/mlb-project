import sqlite3
import os

# 데이터베이스 파일 경로
db_path = os.path.join(os.path.dirname(__file__), "db.sqlite3")

try:
    # 데이터베이스 연결
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("=== dislikes 컬럼 문제 해결 ===")
    
    # 1. 현재 테이블 구조 확인
    cursor.execute("PRAGMA table_info(posts)")
    columns = cursor.fetchall()
    print("\n[현재 posts 테이블 컬럼]")
    for col in columns:
        print(f"  {col[1]}: {col[2]} (기본값: {col[4]})")
    
    # 2. dislikes 컬럼이 있는지 확인
    dislikes_exists = any(col[1] == 'dislikes' for col in columns)
    print(f"\n[dislikes 컬럼 존재 여부]")
    print(f"  존재: {dislikes_exists}")
    
    if not dislikes_exists:
        print("\n[dislikes 컬럼 추가 중...]")
        try:
            cursor.execute("ALTER TABLE posts ADD COLUMN dislikes INTEGER NOT NULL DEFAULT 0")
            print("  ✅ dislikes 컬럼 추가 완료")
        except Exception as e:
            print(f"  ❌ 컬럼 추가 실패: {e}")
    
    # 3. 기존 데이터의 dislikes 값을 0으로 설정
    print("\n[기존 데이터 업데이트 중...]")
    try:
        cursor.execute("UPDATE posts SET dislikes = 0 WHERE dislikes IS NULL")
        updated_rows = cursor.rowcount
        print(f"  ✅ {updated_rows}개 행 업데이트 완료")
    except Exception as e:
        print(f"  ❌ 데이터 업데이트 실패: {e}")
    
    # 4. 변경사항 커밋
    conn.commit()
    print("  ✅ 변경사항 저장 완료")
    
    # 5. 최종 확인
    cursor.execute("PRAGMA table_info(posts)")
    columns = cursor.fetchall()
    print(f"\n[최종 posts 테이블 컬럼]")
    for col in columns:
        if 'likes' in col[1] or 'dislikes' in col[1]:
            print(f"  {col[1]}: {col[2]} (기본값: {col[4]})")
    
    # 6. 샘플 데이터 확인
    cursor.execute("""
        SELECT id, title, likes, dislikes 
        FROM posts 
        WHERE board = 'invest' 
        ORDER BY id DESC 
        LIMIT 3
    """)
    
    posts = cursor.fetchall()
    print(f"\n[샘플 데이터 확인]")
    for post in posts:
        print(f"  ID: {post[0]}, 제목: {post[1]}")
        print(f"    🎯 히트: {post[2]}, 💣 폭망: {post[3]}")
        print()
    
    conn.close()
    print("✅ 작업 완료!")
    
except Exception as e:
    print(f"❌ 오류 발생: {e}")
