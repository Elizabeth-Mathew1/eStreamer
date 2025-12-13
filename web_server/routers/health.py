from fastapi import APIRouter
from fastapi.responses import PlainTextResponse


router = APIRouter(tags=["Health Check"])


@router.get("/")
async def health_check() -> PlainTextResponse:
    """Endpoint for ping-pong healthcheck."""
    return PlainTextResponse(content="PONG")
