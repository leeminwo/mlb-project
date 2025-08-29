# routers/users/board/config.py

# 사용 가능한 보드(관리자쪽과 동일하게 유지)
ALLOWED_BOARDS = {
    "invest", "best", "game", "sports", "gallery", "free", "humor", "report"
}

# 예약어(최상위 경로 충돌 방지)
RESERVED = {"admin", "login", "logout", "static", "api", "posts", "users"}

# 사용자 보드별 탭(말머리)
USER_BOARD_TABS = {
    "invest": ["인기","비트코인","국내주식","해외주식","종목토론","정보공유","이벤트","공지","잡담"],
    "best":   ["인기","공지"],
    "game":   ["공지","잡담"],
    "sports": ["축구","야구","농구","기타","공지"],
    "gallery":["일반","공지"],
    "free":   ["일반","공지"],
    "humor":  ["유머","공지"],
    "report": ["신고","건의","공지"],
}
