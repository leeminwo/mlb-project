from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/posts/invest")
async def invest_board(request: Request):
    return templates.TemplateResponse("admin/posts/category/invest.html", {"request": request})
