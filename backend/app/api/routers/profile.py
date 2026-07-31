from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.adapters.db.mysql.database import get_db
from app.adapters.db.mysql.models import Submission, Question, Level

router = APIRouter()

@router.get("/{user_id}")
def get_user_profile(user_id: int, db: Session = Depends(get_db)):
    # 1. 查询用户所有提交记录
    submissions = db.query(Submission).filter(Submission.user_id == user_id).all()
    
    total = len(submissions)
    correct = sum(1 for s in submissions if s.status == "correct")
    wrong = sum(1 for s in submissions if s.status == "wrong")
    
    # 2. 错题列表
    wrong_question_ids = [s.question_id for s in submissions if s.status == "wrong"]
    
    # 3. 按章节统计错题分布
    chapter_wrong_count = {}
    for qid in wrong_question_ids:
        q = db.query(Question).filter(Question.id == qid).first()
        if q:
            level = db.query(Level).filter(Level.id == q.level_id).first()
            if level:
                chapter_wrong_count[level.chapter_id] = chapter_wrong_count.get(level.chapter_id, 0) + 1
    
    # 找出薄弱章节（错题最多的前2章）
    weak_chapters = sorted(chapter_wrong_count.items(), key=lambda x: x[1], reverse=True)[:2]
    
    # 4. 推荐下一关（简单规则：从薄弱章节中选未完成的关卡）
    recommended_levels = []
    for chapter_id, _ in weak_chapters:
        levels = db.query(Level).filter(Level.chapter_id == chapter_id, Level.status != "completed").all()
        for lv in levels:
            if len(recommended_levels) < 3:
                recommended_levels.append(lv.id)
    
    return {
        "user_id": user_id,
        "total_submissions": total,
        "correct_rate": correct / total if total > 0 else 0,
        "wrong_questions": wrong_question_ids[:10],
        "weak_chapters": weak_chapters,
        "recommended_levels": recommended_levels
    }