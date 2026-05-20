from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .core.config import settings, load_ai_config
from .api import (
    sim,
    websocket,
    experiment,
    kpi,
    ai,
    carbon,
    statistics,
    academic_lab,
    gurobi,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("LinerDT API starting up...")
    load_ai_config()
    yield
    print("LinerDT API shutting down...")


app = FastAPI(
    title="LinerDT API",
    description="班轮航运数字孪生仿真平台 API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sim.router)
app.include_router(websocket.router)
app.include_router(experiment.router, prefix="/api")
app.include_router(kpi.router, prefix="/api")
app.include_router(ai.router)
app.include_router(carbon.router, prefix="/api")
app.include_router(statistics.router)
app.include_router(academic_lab.router)
app.include_router(gurobi.router)


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "app": settings.app_name}
