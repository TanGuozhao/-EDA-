from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.adapters.db.mysql.database import get_db
from app.adapters.db.mysql.models import Level, Question

router = APIRouter()

# ==================== 获取关卡下的所有题目 ====================
@router.get("/levels/{level_id}/questions")
def get_level_questions(level_id: int, db: Session = Depends(get_db)):
    """根据关卡ID返回该关卡下的所有题目列表"""
    level = db.query(Level).filter(Level.id == level_id).first()
    if not level:
        raise HTTPException(status_code=404, detail="关卡不存在")
    
    questions = db.query(Question).filter(Question.level_id == level_id).all()
    return questions

# ==================== 获取单道题目详情 ====================
@router.get("/questions/{question_id}")
def get_question_detail(question_id: int, db: Session = Depends(get_db)):
    """返回单道题目的完整信息"""
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="题目不存在")
    return question