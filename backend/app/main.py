from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.router import api_router


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.on_event("startup")
def startup_event():
    """启动时输出提示信息"""
    print("[Startup] IERP AI Assistant backend started.")
    print("To run workflow tasks, start Celery worker in another terminal:")
    print("  python -m celery -A app.celery_app worker --loglevel=info --pool=solo")


@app.get("/health")
async def health_check():
    return {"status": "ok"}