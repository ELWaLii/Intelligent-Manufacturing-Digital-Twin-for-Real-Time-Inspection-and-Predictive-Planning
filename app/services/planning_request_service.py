from sqlalchemy.orm import Session

from app.models.planning_request import PlanningRequest
from app.schemas.planning_request import PlanningRequestCreate


class PlanningRequestService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, payload: PlanningRequestCreate) -> PlanningRequest:
        item = PlanningRequest(
            product_type=payload.product_type,
            target_quantity=payload.target_quantity,
            available_workers=payload.available_workers,
            available_raw_material=payload.available_raw_material,
            shift_hours=payload.shift_hours,
            planning_date=payload.planning_date,
            notes=payload.notes,
            status="received",
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def list(self, limit: int, offset: int) -> list[PlanningRequest]:
        return (
            self.db.query(PlanningRequest)
            .order_by(PlanningRequest.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def get(self, request_id: int) -> PlanningRequest | None:
        return (
            self.db.query(PlanningRequest)
            .filter(PlanningRequest.id == request_id)
            .first()
        )
