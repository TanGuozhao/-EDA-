from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from app.adapters.db.mysql.database import get_db
from app.adapters.db.mysql.models import Submission, Question
from pydantic import BaseModel

router = APIRouter()

# ==================== 请求模型 ====================
class SubmitAnswerRequest(BaseModel):
    question_id: int
    user_answer: str
    user_id: int = 1  # 暂时写死，等用户认证做好后再改


# ==================== 提交答案接口 ====================
@router.post("/submit")
def submit_answer(request: SubmitAnswerRequest, db: Session = Depends(get_db)):
    # 1. 查询题目
    question = db.query(Question).filter(Question.id == request.question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="题目不存在")
    
    # 2. 判题逻辑（选择题直接判，问答题占位）
    if question.question_type == "choice":
        # 选择题：直接对比答案
        is_correct = request.user_answer.strip().upper() == question.correct_answer.strip().upper()
        score = question.score if is_correct else 0
        result = "正确" if is_correct else "错误"
        status = "correct" if is_correct else "wrong"
    else:
        # 问答题/代码题：暂时占位，等大模型组接口
        score = 0
        result = "待判题（大模型接口开发中）"
        status = "pending"
    
    # 3. 保存提交记录
    submission = Submission(
        user_id=request.user_id,
        question_id=request.question_id,
        submission_type="question",
        user_answer=request.user_answer,
        result=result,
        score=score,
        status=status,
        submitted_at=datetime.now()
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)
    
    # 4. 返回结果
    return {
        "submission_id": submission.id,
        "question_id": request.question_id,
        "score": score,
        "result": result,
        "status": status,
        "feedback": result  # 简单反馈
    }