from fastapi import APIRouter, HTTPException
from typing import List
from app.schemas.experiment_schemas import drc_schemas as schemas
from app.services.experiment_services import drc_service as service

router = APIRouter(prefix="/experiments/drc", tags=["DRC"])

@router.get("/rules", response_model=List[schemas.RuleOut])
def get_rules():
    """返回规则列表（用于侧边栏展示）"""
    return service.get_rules()

@router.post("/level/{level_id}/start", response_model=schemas.DRCStartOut)
def start_level(level_id: int, req: schemas.DRCStartIn):
    """初始化关卡状态（返回版图摘要、违例计数、可查看次数等）"""
    try:
        return service.start_level(req.session_id, level_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/level/1/submit-matches", response_model=schemas.MatchResultOut)
def submit_matches(req: schemas.Level1Submit):
    """关卡1：学生为每个高亮位置选择规则ID，系统校验全部匹配"""
    return service.submit_level1_matches(req.session_id, req.matches)

@router.post("/level/2/inspect", response_model=schemas.InspectOut)
def inspect_sidebar(req: schemas.InspectIn):
    """打开侧边栏（会消耗查阅次数，返回规则列表或剩余次数）"""
    return service.inspect_sidebar(req.session_id)

@router.post("/level/2/apply-fix", response_model=schemas.FixApplyOut)
def apply_fix_level2(req: schemas.Level2FixIn):
    """关卡2：应用一次局部修改（如调整线宽/间距/孔径），返回当前违例计数"""
    return service.apply_fix_level2(req.session_id, req.fix)

@router.post("/level/2/recheck", response_model=schemas.RecheckOut)
def recheck_level2(req: schemas.RecheckIn):
    """关卡2：触发重新检查，返回是否清零和剩余违例数"""
    return service.recheck_level2(req.session_id)

@router.post("/level/3/apply-fix", response_model=schemas.FixApplyOut)
def apply_fix_level3(req: schemas.Level3FixIn):
    """关卡3：在有限空间做修改，服务会追踪步数并可能触发连锁违例"""
    return service.apply_fix_level3(req.session_id, req.fix)

@router.post("/level/3/recheck", response_model=schemas.RecheckOut)
def recheck_level3(req: schemas.RecheckIn):
    """关卡3：检查是否全部清零且步数是否在最优上限内"""
    return service.recheck_level3(req.session_id)