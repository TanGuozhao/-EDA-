from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.adapters.db.mysql.database import get_db
from app.adapters.db.mysql.models import Level, Question

router = APIRouter()


@router.get("/levels/{level_id}/questions")
def get_level_questions(level_id: int, db: Session = Depends(get_db)):
    level = db.query(Level).filter(Level.id == level_id).first()
    if not level:
        raise HTTPException(status_code=404, detail="Level not found")

    return db.query(Question).filter(Question.level_id == level_id).all()


@router.get("/questions/{question_id}")
def get_question_detail(question_id: int, db: Session = Depends(get_db)):
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    return question
