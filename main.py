from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.auth.routes import router as auth_router
from app.config import settings
from app.mobile import router as mobile_router


APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "app" / "static"

app = FastAPI(
    title="NavPark",
    version="2.1.0"
)

app.include_router(auth_router)
app.include_router(router)
app.include_router(mobile_router)
app.mount(
    "/static",
    StaticFiles(directory=STATIC_DIR),
    name="static"
)


@app.get("/", include_in_schema=False)
def voice_console():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health_check():

    return {
        "healthy": True,
        "llm_provider": settings.LLM_PROVIDER,
        "llm_configured": bool(settings.DEEPSEEK_API_KEY),
    }
