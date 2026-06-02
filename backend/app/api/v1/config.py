from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class AppConfigResponse(BaseModel):
    mocker_mode: str


@router.get("/", response_model=AppConfigResponse)
async def get_app_config():
    from app.config import settings
    return AppConfigResponse(mocker_mode=settings.MOCKER_MODE)