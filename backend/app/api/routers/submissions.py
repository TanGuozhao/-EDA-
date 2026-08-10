from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.adapters.db.mysql.database import get_db
from app.adapters.db.mysql.models import Question, Submission

router = APIRouter()


class SubmitAnswerRequest(BaseModel):
    question_id: int
    user_answer: str
    user_id: int = 1


@router.post("/submit")
def submit_answer(request: SubmitAnswerRequest, db: Session = Depends(get_db)):
    question = db.query(Question).filter(Question.id == request.question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    if question.question_type == "choice":
        is_correct = request.user_answer.strip().upper() == question.correct_answer.strip().upper()
        score = question.score if is_correct else 0
        result = "correct" if is_correct else "wrong"
        status = result
    else:
        score = 0
        result = "pending review"
        status = "pending"

    submission = Submission(
        user_id=request.user_id,
        question_id=request.question_id,
        submission_type="question",
        user_answer=request.user_answer,
        result=result,
        score=score,
        status=status,
        submitted_at=datetime.now(),
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)

    return {
        "submission_id": submission.id,
        "question_id": request.question_id,
        "score": score,
        "result": result,
        "status": status,
        "feedback": result,
    }
