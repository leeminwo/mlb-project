# routers/users/board/utils.py
from fastapi import HTTPException, UploadFile
from typing import Tuple, Optional
from . import config
import os
import uuid
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

# ── 업로드 정책 ─────────────────────────────────────────────
ALLOWED_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".pdf"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

# ── 게시판 검증 ────────────────────────────────────────────
def validate_board(board: str) -> str:
    if (board not in config.ALLOWED_BOARDS) or (board in config.RESERVED):
        raise HTTPException(status_code=404, detail="Unknown board")
    return board

# ── 카테고리(탭) 보정 ──────────────────────────────────────
def normalize_category(board: str, category: Optional[str]) -> str:
    """탭(말머리) 외 값이면 기본값(첫 탭)으로 보정"""
    tabs = config.USER_BOARD_TABS.get(board, [])
    cat = (category or "").strip()
    if not tabs:
        return cat
    return cat if cat in tabs else tabs[0]

# ── 페이지/사이즈 보정 ────────────────────────────────────
def clamp_page(page: int, size: int, size_max: int = 50) -> Tuple[int, int]:
    p = page if page and page > 0 else 1
    s = size if size and 1 <= size <= size_max else min(20, size_max)
    return p, s

# ── 날짜 포맷(KST) ─────────────────────────────────────────
def format_dt_to_kst(dt_str: Optional[str], out_fmt: str = "%Y-%m-%d %H:%M") -> Optional[str]:
    """
    ISO8601('YYYY-MM-DDTHH:MM:SS[.ffffff][Z|+00:00]') 또는 'YYYY-MM-DD HH:MM:SS' 입력을
    Asia/Seoul 기준 문자열로 변환.
    - TZ 없는 값은 UTC로 가정
    - 실패 시 원문 반환
    """
    if not dt_str:
        return None
    s = dt_str.strip()
    # Z(UTC) → +00:00 치환 (파이썬 일부 버전 호환)
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        # 대부분의 ISO 포맷 처리 (공백 구분자/마이크로초/오프셋 포함)
        dt = datetime.fromisoformat(s)
    except ValueError:
        try:
            # 'YYYY-MM-DD HH:MM:SS[.ffffff]' 형태 처리
            base = s.split(".")[0]  # 마이크로초 제거
            dt = datetime.strptime(base[:19], "%Y-%m-%d %H:%M:%S")
            dt = dt.replace(tzinfo=timezone.utc)
        except Exception:
            return dt_str  # 알 수 없는 포맷이면 원문 반환
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(ZoneInfo("Asia/Seoul")).strftime(out_fmt)

# ── 업로드 저장 ────────────────────────────────────────────
async def save_upload(upload_dir: str, file: UploadFile) -> Optional[str]:
    """
    파일 1개 저장. 정책:
    - 확장자 화이트리스트
    - MAX_FILE_SIZE 초과 거절
    - 보드별 디렉토리 자동 생성
    """
    if not file or not file.filename:
        return None

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTS:
        raise HTTPException(status_code=400, detail=f"허용되지 않는 파일형식: {ext}")

    data = await file.read()
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="파일이 너무 큽니다(최대 5MB).")

    os.makedirs(upload_dir, exist_ok=True)
    safe_name = f"{uuid.uuid4().hex}{ext}"
    with open(os.path.join(upload_dir, safe_name), "wb") as f:
        f.write(data)
    return safe_name
