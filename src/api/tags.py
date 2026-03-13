import os
from typing import List, Optional, Any, Dict
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from core.config import settings
import json
from pydantic import BaseModel
router = APIRouter(prefix="/tags")

BASE_DIR = os.path.dirname(__file__)
TEST_DIR = os.path.normpath(os.path.join(BASE_DIR, "..", "static", "tests_files"))
whitelist = TEST_DIR + "/whitelist.json"
blacklist = TEST_DIR + "/blacklist.json"

class validateTag(BaseModel):
    code: str

print(whitelist)
@router.post("/validate", status_code=200)
async def validate(request: Request, data: validateTag):    
    with open(whitelist, 'r') as file:
        whitelist_data = json.load(file)
    if data.code in whitelist_data:
        with open(blacklist, 'r+') as file:
            file_data = json.load(file)
            if data.code not in file_data:
                file_data.append(data.code)
                file.seek(0)      
                json.dump(file_data, file, indent=4)
                file.truncate()
                return "Valid"
        
    return "Invalid"