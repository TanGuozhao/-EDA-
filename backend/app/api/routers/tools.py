from fastapi import APIRouter, Depends, HTTPException
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
        raise HTTPException(status_code=404, detail="Tool not found")

    raise HTTPException(
        status_code=501,
        detail=f"Verification is not implemented for tool '{tool.name}'.",
    )
