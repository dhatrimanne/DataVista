from fastapi import APIRouter

from backend.config import get_settings


router = APIRouter(tags=["Health"])


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": get_settings().app_name}
