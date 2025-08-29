# run.py
import sys
import os
import uvicorn

# 현재 파일 기준 루트 디렉토리를 모듈 경로로 등록
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
