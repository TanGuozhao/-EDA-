from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.adapters.db.mysql.database import get_db
from app.adapters.db.mysql.models import Tool

router = APIRouter()

# ==================== 工具列表 ====================
@router.get("/")
def get_tools(db: Session = Depends(get_db)):
    tools = db.query(Tool).filter(Tool.is_active == True).all()
    return tools

# ==================== 工具验证记录（占位） ====================
@router.post("/{tool_id}/verify")
def verify_tool(tool_id: int, db: Session = Depends(get_db)):
    tool = db.query(Tool).filter(Tool.id == tool_id).first()
    if not tool:
        return {"status": "error", "message": "工具不存在"}
    # 占位返回，后面接入真实工具时再扩展
    return {
        "tool_id": tool_id,
        "tool_name": tool.name,
        "status": "pending",
        "message": "工具验证功能开发中，当前为占位响应"
    }