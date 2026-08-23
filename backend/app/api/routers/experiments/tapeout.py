# backend/app/api/routers/experiments/tapeout.py
from fastapi import APIRouter, HTTPException, Query
from typing import List

from app.schemas.experiment_schemas import tapeout_schemas as schemas
from app.schemas.experiment_schemas.tapeout_schemas import (
    ScanChainLevel1Request,
    ScanChainLevel2Request,
    ScanChainLevel3Request,
    ScanChainResponse,
)
from app.services.experiment_services import tapeout_service as service

router = APIRouter(prefix="/experiments/tapeout", tags=["Tapeout"])

# ---- existing checklist / LVS endpoints (kept for compatibility) ----
@router.get("/checklist", response_model=schemas.ChecklistOut)
def get_checklist(session_id: str = Query(...)):
    return service.get_checklist(session_id)

@router.post("/mark-item", response_model=schemas.MarkOut)
def mark_item(req: schemas.MarkIn):
    return service.mark_item(req.session_id, req.item_id, req.status)

@router.get("/lvs/session/start", response_model=schemas.LVSSessionStartOut)
def start_lvs(session_id: str = Query(...)):
    return service.start_lvs(session_id)

@router.post("/lvs/mark-diff", response_model=schemas.MarkDiffOut)
def mark_lvs_diff(req: schemas.LVSMarkDiffIn):
    return service.mark_lvs_diff(req.session_id, req.line_ids)

@router.post("/lvs/apply-change", response_model=schemas.LVSApplyChangeOut)
def apply_change(req: schemas.LVSApplyChangeIn):
    return service.apply_change(req.session_id, req.change)

@router.post("/lvs/reextract", response_model=schemas.LVSReextractOut)
def reextract(req: schemas.ReextractIn):
    return service.reextract_and_compare(req.session_id)

# -----------------------------
# Scan chain endpoints (new) - 自动 start
# -----------------------------
# ========== 扫描链 start 接口（获取初始化数据） ==========

@router.get("/scanchain/level1/start")
def start_scanchain_level1(session_id: str = Query(...)):
    try:
        result = service.start_scan_level1(session_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/scanchain/level2/start")
def start_scanchain_level2(session_id: str = Query(...)):
    try:
        result = service.start_scan_level2(session_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/scanchain/level3/start")
def start_scanchain_level3(session_id: str = Query(...)):
    try:
        result = service.start_scan_level3(session_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
@router.post("/scanchain/level1")
def submit_scanchain_level1(request: ScanChainLevel1Request):
    try:
        # 自动 start（如果已 start 则忽略）
        try:
            service.start_scan_level1(request.session_id)
        except Exception:
            pass
        
        result = service.submit_scan_level1(
            session_id=request.session_id,
            conn_order=request.connections
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/scanchain/level2")
def submit_scanchain_level2(request: ScanChainLevel2Request):
    try:
        try:
            service.start_scan_level2(request.session_id)
        except Exception:
            pass
        
        result = service.submit_scan_level2(
            session_id=request.session_id,
            order=request.connections
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/scanchain/level3")
def submit_scanchain_level3(request: ScanChainLevel3Request):
    try:
        try:
            service.start_scan_level3(request.session_id)
        except Exception:
            pass
        
        result = service.submit_scan_level3(
            session_id=request.session_id,
            suspects=request.fault_candidates
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))