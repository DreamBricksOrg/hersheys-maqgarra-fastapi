from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from api.pages import router as router_api_pages
from api.uploads import router as router_uploads
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from core.config import settings

def create_app() -> FastAPI:
    app = FastAPI(title="Hersheys-Maqgarra", version="0.1.7-dev")

    app.mount("/static", StaticFiles(directory="src/static"), name="static")
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router_api_pages)
    app.include_router(router_uploads)
    return app


app = create_app()
