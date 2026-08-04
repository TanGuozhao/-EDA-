# name=backend/app/api/routers/rtl.py
"""
RTL 路由：
- POST /api/rtl/generate
- POST /api/rtl/validate
- POST /api/rtl/questions/repair
- GET  /api/rtl/questions/{question_id}
- POST /api/rtl/questions/{question_id}/submit
- GET  /api/rtl/designs/{design_id}/artifacts
"""
from fastapi import APIRouter, HTTPException, status
from app.schemas.rtl_schemas import (
    RTLGenerateRequest,
    RTLGenerateResponse,
    RTLValidateRequest,
    RTLValidateResponse,
    RTLRepairQuestionRequest,
    RTLRepairQuestionResponse,
    RTLQuestionGetResponse,
    RTLSubmissionRequest,
    RTLSubmissionResponse,
)
from app.services.rtl_service import RTLService
import logging

logger = logging.getLogger("api.rtl")
router = APIRouter()
service = RTLService()


@router.post("/generate", response_model=RTLGenerateResponse)
def generate_design(req: RTLGenerateRequest):
    try:
        res = service.generate_design(req.requirement, req.module_name, [p.dict() for p in req.ports])
        return res
    except Exception as e:
        logger.exception("生成设计失败")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate", response_model=RTLValidateResponse)
def validate_verilog(req: RTLValidateRequest):
    try:
        res = service.validate_verilog(req.verilog, req.top_module, design_id=req.design_id)
        if res is None:
            raise HTTPException(status_code=500, detail="验证失败")
        return res
    except Exception as e:
        logger.exception("验证出错")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/questions/repair", response_model=RTLRepairQuestionResponse)
def create_repair_question(req: RTLRepairQuestionRequest):
    try:
        res = service.create_repair_question(
            req.requirement, req.module_name, [p.dict() for p in req.ports], req.error_type
        )
        return res
    except ValueError as e:
        logger.exception("请求参数错误")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("创建 repair 题目失败")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/questions/{question_id}", response_model=RTLQuestionGetResponse)
def get_question(question_id: str):
    try:
        q = service.get_repair_question(question_id)
        if not q:
            raise HTTPException(status_code=404, detail="question not found")
        return q
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("查询题目失败")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/questions/{question_id}/submit", response_model=RTLSubmissionResponse)
def submit_question(question_id: str, req: RTLSubmissionRequest):
    try:
        res = service.submit_repair(question_id, req.user_id, req.submitted_verilog)
        return {
            "submission_id": res["submission_id"],
            "passed": res["passed"],
            "score": res["score"],
            "feedback": res["feedback"],
            "validation_run_id": res.get("validation_run_id"),
        }
    except LookupError:
        raise HTTPException(status_code=404, detail="question not found")
    except Exception as e:
        logger.exception("提交处理失败")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/designs/{design_id}/artifacts")
def get_design_artifacts(design_id: str):
    try:
        res = service.get_design_artifacts(design_id)
        if not res:
            raise HTTPException(status_code=404, detail="design not found")
        return res
    except Exception as e:
        logger.exception("获取 artifacts 失败")
        raise HTTPException(status_code=500, detail=str(e))