# name=backend/app/api/routers/hls.py
"""
HLS 路由：
- GET /api/hls/challenges/current
- POST /api/hls/challenges/generate
- GET /api/hls/challenges/{challenge_id}
- POST /api/hls/challenges/{challenge_id}/submit
"""
from fastapi import APIRouter, HTTPException
from app.schemas.hls_schemas import (
    HLSChallengeResponse,
    HLSGenerateRequest,
    HLSSubmitRequest,
    HLSSubmitResponse,
)
from app.services.hls_service import HLSService
import logging

logger = logging.getLogger("api.hls")
router = APIRouter()
service = HLSService()


@router.get("/challenges/current", response_model=HLSChallengeResponse)
def get_current_challenge():
    try:
        c = service.get_current_challenge()
        if not c:
            raise HTTPException(status_code=404, detail="no challenge available")
        return c
    except Exception as e:
        logger.exception("获取当前题目失败")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/challenges/generate", response_model=HLSChallengeResponse)
def generate_challenge(req: HLSGenerateRequest):
    try:
        alg = req.algorithm or "ASAP"
        max_nodes = req.max_nodes or 6
        c = service.generate_challenge(algorithm=alg, max_nodes=max_nodes)
        return c
    except Exception as e:
        logger.exception("生成 HLS 题目失败")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/challenges/{challenge_id}", response_model=HLSChallengeResponse)
def get_challenge(challenge_id: str):
    try:
        c = service.get_challenge(challenge_id)
        if not c:
            raise HTTPException(status_code=404, detail="challenge not found")
        return c
    except Exception as e:
        logger.exception("查询 HLS 题目失败")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/challenges/{challenge_id}/submit", response_model=HLSSubmitResponse)
def submit_challenge(challenge_id: str, req: HLSSubmitRequest):
    try:
        res = service.submit(challenge_id, req.user_id, req.student_answer)
        return res
    except LookupError:
        raise HTTPException(status_code=404, detail="challenge not found")
    except Exception as e:
        logger.exception("提交答题失败")
        raise HTTPException(status_code=500, detail=str(e))