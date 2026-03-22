from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from loguru import logger
from apscheduler.schedulers.background import BackgroundScheduler

from app.core.config import get_settings
from app.core.database import init_db
from app.api.v1.router import api_router

settings = get_settings()
DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting MatchPredict API...")
    await init_db()
    logger.info("Database tables ensured")

    scheduler = BackgroundScheduler()
    try:
        from app.scheduler.jobs import setup_scheduler
        setup_scheduler(scheduler)
        scheduler.start()
        logger.info("Scheduler started")
    except Exception as e:
        logger.warning(f"Scheduler failed to start: {e}")

    yield

    scheduler.shutdown(wait=False)
    logger.info("MatchPredict API shut down")


app = FastAPI(
    title="MatchPredict API",
    description="AI football prediction engine",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

logos_dir = DATA_DIR / "logos"
logos_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static/logos", StaticFiles(directory=str(logos_dir)), name="logos")


@app.get("/api/health")
async def health():
    return {"status": "healthy", "version": "2.0.0"}
