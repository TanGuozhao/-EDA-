from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from app.adapters.db.mysql.database import get_db
from app.adapters.db.mysql.models import Chapter,Level,Experiment

router = APIRouter()

@router.get("/")
def get_chapters(db: Session = Depends(get_db)):
    chapters = db.query(Chapter).options(
        joinedload(Chapter.levels).joinedload(Level.experiment)
    ).order_by(Chapter.sort_order).all()
    return chapters

@router.get("/{chapter_id}")
def get_chapter(chapter_id: int, db: Session = Depends(get_db)):
    chapter = db.query(Chapter).options(joinedload(Chapter.levels)).filter(Chapter.id == chapter_id).first()
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")
    return chapter
@router.get("/levels/{level_id}")
def get_level(level_id: int, db: Session = Depends(get_db)):
    level = db.query(Level).filter(Level.id == level_id).first()
    if not level:
        raise HTTPException(status_code=404, detail="关卡不存在")
    return level
@router.get("/experiments/list")
def get_experiment_levels(db: Session = Depends(get_db)):
    # 查询所有有关联实验的关卡
    levels = db.query(Level).join(Level.experiment).filter(Experiment.id.isnot(None)).all()
    return levels