from app import models
from fastapi import FastAPI
from app.database import engine, Base
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(title="Appeal Management API", version="1.0.0", lifespan=lifespan)


@app.get("/api/health", tags=["health"])
async def health():
    return {"status": "ok"}
