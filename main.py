from fastapi import FastAPI

from app.api.routes import router

app = FastAPI(
    title="Parking AI",
    version="1.0.0"
)

app.include_router(router)


@app.get("/")
def health():

    return {
        "application": "Parking AI",
        "status": "running"
    }


@app.get("/health")
def health_check():

    return {
        "healthy": True
    }
