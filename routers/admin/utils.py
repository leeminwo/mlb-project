import bcrypt
import os
from fastapi import UploadFile
from datetime import datetime

# 비밀번호 해싱
def hash_password(plain_password: str) -> str:
    return bcrypt.hashpw(plain_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

# 비밀번호 검증
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

# 파일 업로드 저장
async def save_upload(upload_dir: str, file: UploadFile) -> str:
    """파일을 업로드 디렉토리에 저장하고 파일명을 반환"""
    if not file or not file.filename:
        return None
    
    # 업로드 디렉토리 생성
    os.makedirs(upload_dir, exist_ok=True)
    
    # 파일명 중복 방지를 위한 타임스탬프 추가
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{file.filename}"
    file_path = os.path.join(upload_dir, filename)
    
    try:
        # 파일 내용 읽기 및 저장
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        return filename
    except Exception as e:
        print(f"파일 저장 오류: {e}")
        return None
