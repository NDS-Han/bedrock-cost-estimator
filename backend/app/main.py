from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.presets import load_presets
from app.core.settings import get_settings


@asynccontextmanager
async def lifespan(_: FastAPI):
    load_presets(get_settings().preset_path)
    yield


app = FastAPI(title="Bedrock Cost Estimator API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)
