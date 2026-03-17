import os
from typing import List, Optional, Any, Dict
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from core.config import settings

router = APIRouter(prefix="/pages")

BASE_DIR = os.path.dirname(__file__)
TEMPLATES_DIR = os.path.normpath(os.path.join(BASE_DIR, "..", "static", "templates"))
templates = Jinja2Templates(directory=TEMPLATES_DIR)


@router.get("/tag_validation", response_class=HTMLResponse, include_in_schema=False)
async def page_home(request: Request):
    return templates.TemplateResponse("tag_validation.html", {"request": request})
