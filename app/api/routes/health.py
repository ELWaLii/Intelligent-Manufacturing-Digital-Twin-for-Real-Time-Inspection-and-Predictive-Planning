from fastapi import APIRouter

router = APIRouter()


@router.get("/health", summary="Basic liveness check")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready", summary="Readiness check")
def readiness_check() -> dict[str, str]:
    return {"status": "ready"}
