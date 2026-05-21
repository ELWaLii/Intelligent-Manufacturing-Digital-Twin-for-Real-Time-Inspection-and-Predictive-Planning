from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["System Monitor"])

@router.get("")
def health_check():
    return {"status": "healthy", "service": "Digital Twin Production API Layers"}