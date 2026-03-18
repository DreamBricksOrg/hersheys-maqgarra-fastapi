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


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def page_home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@router.get("/found-bars", response_class=HTMLResponse, include_in_schema=False)
async def page_found_bars(request: Request):
    return templates.TemplateResponse("found-bars.html", {"request": request})

@router.get("/scan-qrcode", response_class=HTMLResponse, include_in_schema=False)
async def page_scan_qrcode(request: Request):
    return templates.TemplateResponse("scan-qrcode.html", {"request": request})

@router.get("/more-receipts", response_class=HTMLResponse, include_in_schema=False)
async def page_more_receipts(request: Request):
    return templates.TemplateResponse("more-receipts.html", {"request": request})

@router.get("/read-camera", response_class=HTMLResponse, include_in_schema=False)
async def page_read_camera(request: Request):
    return templates.TemplateResponse("read-camera.html", {"request": request})

@router.get("/associate-tag", response_class=HTMLResponse, include_in_schema=False)
async def page_associate_tag(request: Request):
    return templates.TemplateResponse("associate-tag.html", {"request": request})

@router.get("/add-manually", response_class=HTMLResponse, include_in_schema=False)
async def page_add_manually(request: Request):
    return templates.TemplateResponse("add-manually.html", {"request": request})

@router.get("/user-qrcode", response_class=HTMLResponse, include_in_schema=False)
async def page_user_qrcode(request: Request):
    return templates.TemplateResponse("user-qrcode.html", {"request": request})
    
@router.get("/tag-validation", response_class=HTMLResponse, include_in_schema=False)
async def page_tag_validation(request: Request):
    return templates.TemplateResponse("tag_validation.html", {"request": request})




