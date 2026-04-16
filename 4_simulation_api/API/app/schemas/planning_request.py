from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PlanningRequestCreate(BaseModel):
    product_type: str = Field(min_length=1, max_length=100, examples=["cement_bag"])
    target_quantity: float = Field(gt=0, examples=[1000])
    available_workers: int = Field(ge=0, examples=[12])
    available_raw_material: float | None = Field(default=None, ge=0, examples=[1500])
    shift_hours: float = Field(gt=0, le=24, examples=[8])
    planning_date: str | None = Field(default=None, examples=["2026-04-20"])
    notes: str | None = Field(default=None, max_length=1000, examples=["Priority order"])


class PlanningRequestListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_type: str
    target_quantity: float
    available_workers: int
    status: str
    created_at: datetime


class PlanningRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_type: str
    target_quantity: float
    available_workers: int
    available_raw_material: float | None
    shift_hours: float
    planning_date: str | None
    notes: str | None
    status: str
    created_at: datetime
