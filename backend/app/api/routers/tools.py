from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.adapters.db.mysql.database import get_db
from app.adapters.db.mysql.models import Tool

router = APIRouter()


@router.get("/")
def get_tools(db: Session = Depends(get_db)):
    return db.query(Tool).filter(Tool.is_active == True).all()


@router.post("/{tool_id}/verify")
def verify_tool(tool_id: int, db: Session = Depends(get_db)):
    tool = db.query(Tool).filter(Tool.id == tool_id).first()
    if not tool:
        return {"status": "error", "message": "Tool not found"}

    return {
        "tool_id": tool_id,
        "tool_name": tool.name,
        "status": "pending",
        "message": "Tool verification is a placeholder in the local dev environment.",
    }
