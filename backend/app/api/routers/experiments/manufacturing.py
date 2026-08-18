from fastapi import APIRouter, HTTPException
from typing import List
from app.schemas.experiment_schemas import manufacturing_schemas as schemas
from app.services.experiment_services import manufacturing_service as service

router = APIRouter(prefix="/experiments/manufacturing", tags=["Manufacturing"])

@router.get("/flow/start", response_model=schemas.FlowStartOut)
def start_flow(session_id: str):
    return service.start_flow(session_id)

@router.post("/flow/apply-order", response_model=schemas.OrderApplyOut)
def apply_order(req: schemas.OrderApplyIn):
    return service.apply_order(req.session_id, req.order)

@router.get("/packaging/start", response_model=schemas.PackagingStartOut)
def start_packaging(session_id: str):
    return service.start_packaging(session_id)

@router.post("/packaging/submit", response_model=schemas.PackagingSubmitOut)
def submit_packaging(req: schemas.PackagingSubmitIn):
    return service.submit_packaging(req.session_id, req.matches)