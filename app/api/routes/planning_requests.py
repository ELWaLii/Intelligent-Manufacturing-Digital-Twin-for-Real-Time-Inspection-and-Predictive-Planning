from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.planning_request import (
    PlanningRequestCreate,
    PlanningRequestListItem,
    PlanningRequestResponse,
)
from app.services.planning_request_service import PlanningRequestService

router = APIRouter(prefix="/planning-requests")


@router.post(
    "",
    response_model=PlanningRequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new production planning request",
)
def create_planning_request(
    payload: PlanningRequestCreate,
    db: Session = Depends(get_db),
) -> PlanningRequestResponse:
    service = PlanningRequestService(db)
    return service.create(payload)


@router.get(
    "",
    response_model=list[PlanningRequestListItem],
    summary="List production planning requests",
)
def list_planning_requests(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[PlanningRequestListItem]:
    service = PlanningRequestService(db)
    return service.list(limit=limit, offset=offset)


@router.get(
    "/{request_id}",
    response_model=PlanningRequestResponse,
    summary="Get one production planning request by id",
)
def get_planning_request(
    request_id: int,
    db: Session = Depends(get_db),
) -> PlanningRequestResponse:
    service = PlanningRequestService(db)
    item = service.get(request_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Planning request {request_id} was not found.",
        )
    return item
