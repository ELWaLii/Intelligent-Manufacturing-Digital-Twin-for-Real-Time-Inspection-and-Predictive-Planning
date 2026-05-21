from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from session import get_db
import planning_request_service

router = APIRouter(prefix="/planning", tags=["What-If Simulation Engine"])

# 🏗️ الـ Pydantic Schemas للمدخلات والمخرجات
class SimulationRequestSchema(BaseModel):
    target_productivity: float
    max_allowed_overtime: float
    current_machine_stage: int

class SimulationResponseSchema(BaseModel):
    id: int
    decision_status: str
    required_incentive: float
    required_overtime: float
    predicted_idle_impact: float
    justification: str

# 🚀 الـ Endpoint الأساسي للمحاكاة والتخزين
@router.post("/simulate", response_model=SimulationResponseSchema)
def run_simulation(payload: SimulationRequestSchema, db: Session = Depends(get_db)):
    try:
        result = planning_request_service.simulate_and_save_request(
            db=db,
            target_productivity=payload.target_productivity,
            max_allowed_overtime=payload.max_allowed_overtime,
            current_machine_stage=payload.current_machine_stage
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"حدث خطأ داخلي في محرك المحاكاة: {str(e)}")