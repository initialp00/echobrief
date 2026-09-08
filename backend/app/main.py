"""EchoBrief FastAPI application entrypoint."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.routers import briefs, health
from app.services.producer import close_producer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.getLogger("echobrief").info("EchoBrief API starting up.")
    yield
    close_producer()
    logging.getLogger("echobrief").info("EchoBrief API shutting down.")


app = FastAPI(
    title="EchoBrief",
    description="Async voice brief → structured incident notes.",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(briefs.router)


@app.get("/", tags=["root"])
async def root() -> dict:
    return {
        "service": "EchoBrief",
        "docs": "/docs",
        "health": "/health",
    }
