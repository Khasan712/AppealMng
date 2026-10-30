from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app import models
from app.database import Base, engine
from app.exceptions import AppError
from app.routers import auth, categories, users, appeals, notifications, statistics
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from app.telegram import tg_bot


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    if tg_bot:
        await tg_bot.session.close()
    await engine.dispose()


app = FastAPI(title="Appeal Management API", version="1.0.0", lifespan=lifespan)
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


# Service errors become regular JSON error responses.
@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.get("/api/health", tags=["health"])
async def health():
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(categories.router)
app.include_router(users.router)
app.include_router(appeals.router)
app.include_router(notifications.router)
app.include_router(statistics.router)
# Must stay last: "/" would otherwise catch /api and /docs requests.
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")