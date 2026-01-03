"""
FastAPI application entry point.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os

from app.database import init_db
from app.routers import scrape, push, configs, templates, batch
from app.services.workflow import workflow_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    os.makedirs("data", exist_ok=True)
    await init_db()
    try:
        await workflow_service.refresh_from_db()
    except Exception:
        pass
    yield


app = FastAPI(
    title="Data Scraper & IM Pusher",
    description="数据抓取与IM推送服务 API",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(scrape.router)
app.include_router(push.router)
app.include_router(configs.router)
app.include_router(templates.router)
app.include_router(templates.workflows_router)
app.include_router(batch.router)

# Mount static files
static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Templates
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
html_templates = Jinja2Templates(directory=templates_dir)

@app.get("/")
async def root(request: Request):
    """Serve the web interface."""
    return html_templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
